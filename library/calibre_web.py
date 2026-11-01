#!/usr/bin/python
"""Ansible module: set up Calibre-Web's login, Kobo sync and extra users in its database.

How it works
------------
Calibre-Web has no API for its settings, so the module edits its SQLite database (app.db)
directly. On each run it:
  1. replaces the default admin/admin123 login with yours (a fresh install only);
  2. turns on Kobo sync, passing the Kobo store through;
  3. creates the extra users that are missing and gives each the Kobo token you passed;
  4. writes only what differs, so reruns report "ok".

Calibre-Web reads its settings only when it starts: "restart" in the result says the Kobo
settings changed. Users and tokens are read per request and need no restart.

Passwords are hashed the way Calibre-Web's werkzeug does (scrypt:32768:8:1$<salt>$<hex>).
"""

from __future__ import annotations

DOCUMENTATION = r"""
module: calibre_web
short_description: Set up Calibre-Web's login, Kobo sync and extra users
description:
  - Edits Calibre-Web's app.db. Replaces the default admin login on a fresh install, turns on
    Kobo sync with the Kobo store passed through, creates missing users and sets their Kobo
    tokens. Existing users are otherwise left alone. Supports check mode.
options:
  db:
    description: Path to Calibre-Web's C(app.db).
    type: path
    required: true
  login:
    description: The login that replaces the default admin, with C(username), C(password) and C(email).
    type: dict
    required: true
  users:
    description:
      - Extra users, each with C(name) and, to create them, C(email) and C(password).
      - An optional C(kobo_token) (32 characters) becomes their Kobo sync token.
    type: list
    elements: dict
    default: []
"""

EXAMPLES = r"""
- name: Login, Kobo sync and users
  calibre_web:
    db: /srv/books-stack/appdata/calibre/app.db
    login: { username: admin2, password: "{{ password }}", email: admin@example.com }
    users:
      - { name: reader, email: reader@example.com, password: "{{ password }}", kobo_token: "{{ token }}" }
"""

import hashlib
import hmac
import os
import secrets
import sqlite3
import string

from ansible.module_utils.basic import AnsibleModule

DEFAULT_LOGIN = ("admin", "admin123")
# View Books (256), Password (16) and Download (2): what a reader needs for Kobo sync.
READER_ROLE = 274
KOBO_TOKEN = 1  # remote_auth_token.token_type


# --- Password hashes (werkzeug's scrypt format) ---------------------------------------------

def _scrypt(password, salt, n, r, p):
    return hashlib.scrypt(password.encode(), salt=salt.encode(), n=n, r=r, p=p,
                          maxmem=132 * n * r * p).hex()


def hash_password(password):
    salt = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    return "scrypt:32768:8:1$%s$%s" % (salt, _scrypt(password, salt, 32768, 8, 1))


def check_password(stored, password):
    """True when the werkzeug scrypt hash matches; other hash methods count as no match."""
    try:
        method, salt, digest = stored.split("$", 2)
        name, n, r, p = method.split(":")
    except ValueError:
        return False
    return name == "scrypt" and hmac.compare_digest(_scrypt(password, salt, int(n), int(r), int(p)), digest)


# --- Module ---------------------------------------------------------------------------------

def main():
    module = AnsibleModule(
        argument_spec=dict(
            db=dict(type="path", required=True),
            login=dict(type="dict", required=True, no_log=True),
            users=dict(type="list", elements="dict", default=[], no_log=True),
        ),
        supports_check_mode=True,
    )
    params = module.params
    if not os.path.isfile(params["db"]):
        module.fail_json(msg="No Calibre-Web database at %s: has it started once?" % params["db"])
    db = sqlite3.connect(params["db"])
    changes = []

    # 1. The default admin becomes your login.
    admin = db.execute("SELECT password FROM user WHERE name = ?", (DEFAULT_LOGIN[0],)).fetchone()
    if admin and check_password(admin[0], DEFAULT_LOGIN[1]):
        login = params["login"]
        changes.append("login")
        db.execute("UPDATE user SET name = ?, email = ?, password = ? WHERE name = ?",
                   (login["username"], login["email"], hash_password(login["password"]), DEFAULT_LOGIN[0]))

    # 2. Kobo sync, with the Kobo store passed through.
    restart = db.execute("SELECT 1 FROM settings WHERE NOT (config_kobo_sync AND config_kobo_proxy)").fetchone()
    if restart:
        changes.append("kobo sync")
        db.execute("UPDATE settings SET config_kobo_sync = 1, config_kobo_proxy = 1")

    # 3. Extra users and their Kobo tokens. New users get the defaults new users get in the UI.
    show, locale, language = db.execute(
        "SELECT config_default_show, config_default_locale, config_default_language FROM settings").fetchone()
    for user in params["users"]:
        row = db.execute("SELECT id FROM user WHERE name = ?", (user["name"],)).fetchone()
        if row:
            user_id = row[0]
        else:
            changes.append("user " + user["name"])
            user_id = db.execute(
                "INSERT INTO user (name, email, password, role, sidebar_view, locale, default_language,"
                " kindle_mail, kindle_mail_subject, denied_tags, allowed_tags, denied_column_value,"
                " allowed_column_value, view_settings, kobo_only_shelves_sync, opds_only_shelves_sync,"
                " theme, auto_send_enabled, allow_additional_ereader_emails)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, '', '', '', '', '', '', '{}', 1, 0, 1, 0, 1)",
                (user["name"], user["email"], hash_password(user["password"]), READER_ROLE,
                 show, locale, language)).lastrowid
        if user.get("kobo_token"):
            token = db.execute("SELECT id, auth_token FROM remote_auth_token WHERE user_id = ? AND token_type = ?",
                               (user_id, KOBO_TOKEN)).fetchone()
            if not token:
                changes.append("kobo token " + user["name"])
                db.execute("INSERT INTO remote_auth_token (auth_token, user_id, verified, expiration, token_type)"
                           " VALUES (?, ?, 0, '9999-12-31 23:59:59.999999', ?)",
                           (user["kobo_token"], user_id, KOBO_TOKEN))
            elif token[1] != user["kobo_token"]:
                changes.append("kobo token " + user["name"])
                db.execute("UPDATE remote_auth_token SET auth_token = ? WHERE id = ?", (user["kobo_token"], token[0]))

    if module.check_mode:
        db.rollback()
    else:
        db.commit()
    db.close()
    # SQLite's -wal and -shm files made by this run as root must stay writable for Calibre-Web.
    owner = os.stat(params["db"])
    for path in (params["db"] + "-wal", params["db"] + "-shm"):
        if os.path.exists(path):
            os.chown(path, owner.st_uid, owner.st_gid)
    module.exit_json(changed=bool(changes), changes=changes, restart=bool(restart))


if __name__ == "__main__":
    main()
