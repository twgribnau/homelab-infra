#!/usr/bin/python
"""Ansible module: make qBittorrent's preferences and categories match what you describe.

How it works
------------
qBittorrent is configured through its WebUI API (/api/v2/...). On each run the module:
  1. logs in with the username and password (the session lives in a cookie);
  2. reads the current preferences and compares only the keys you passed;
  3. reads the categories and compares their save paths;
  4. writes only what differs, so reruns report "ok".

Two qBittorrent quirks it handles:
  - Every request must carry a Referer/Origin matching the WebUI address (CSRF check).
  - The login answer changed in 5.3: older versions answer 200 "Ok." / "Fails.",
    5.3 and later answer 204 (success) or 401 (wrong login).
"""

from __future__ import annotations

DOCUMENTATION = r"""
module: qbittorrent_config
short_description: Make qBittorrent's preferences and categories match the given settings
description:
  - Logs in to the WebUI API, compares the given preferences and category save paths with
    the current ones, and only writes what differs. Supports check mode and diff mode.
options:
  url:
    description: WebUI address, for example C(http://127.0.0.1:8080).
    type: str
    required: true
  username:
    description: WebUI username.
    type: str
    required: true
  password:
    description: WebUI password.
    type: str
    required: true
  preferences:
    description: Preference keys and values, as named by C(/api/v2/app/preferences).
    type: dict
    default: {}
  categories:
    description: Category names and their save paths. Missing categories are created.
    type: dict
    default: {}
"""

EXAMPLES = r"""
- name: Automatic torrent management and a category per app
  qbittorrent_config:
    url: http://127.0.0.1:8080
    username: admin
    password: "{{ password }}"
    preferences:
      auto_tmm_enabled: true
      save_path: /data/torrents
    categories:
      radarr: /data/torrents/movies
"""

import json
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from ansible.module_utils.basic import AnsibleModule

LOGIN = "/api/v2/auth/login"


# --- Pure helpers (no API calls) ---------------------------------------------------------

def preference_changes(current, wanted):
    """The wanted preferences whose current value differs."""
    return {key: value for key, value in wanted.items() if current.get(key) != value}


def category_changes(current, wanted):
    """The wanted categories that are missing or have another save path: {name: save_path}."""
    return {name: path for name, path in wanted.items()
            if name not in current or current[name].get("savePath", "") != path}


# --- API access -----------------------------------------------------------------------------

class QBittorrent:
    """WebUI client that keeps the login cookie; any failure ends the module with a clear message."""

    def __init__(self, module):
        self.module = module
        self.base = module.params["url"].rstrip("/")
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(self, path, form=None):
        data = None if form is None else urlencode(form).encode()
        headers = {"Referer": self.base, "Origin": self.base}  # the WebUI's CSRF check
        try:
            with self.opener.open(Request(self.base + path, data=data, headers=headers), timeout=30) as response:
                return response.read().decode()
        except HTTPError as e:
            if path == LOGIN and e.code in (401, 403):
                self.login_failed()
            self.module.fail_json(msg="qBittorrent %s failed: HTTP %s" % (path, e.code))
        except URLError as e:
            self.module.fail_json(msg="qBittorrent %s unreachable: %s" % (path, e.reason))

    def login(self):
        params = self.module.params
        answer = self.request(LOGIN, {"username": params["username"], "password": params["password"]})
        if answer.strip() == "Fails.":  # qBittorrent before 5.3
            self.login_failed()

    def login_failed(self):
        self.module.fail_json(msg="qBittorrent login failed for user %s" % self.module.params["username"])

    def preferences(self):
        return json.loads(self.request("/api/v2/app/preferences"))

    def set_preferences(self, changes):
        self.request("/api/v2/app/setPreferences", {"json": json.dumps(changes)})

    def categories(self):
        return json.loads(self.request("/api/v2/torrents/categories"))

    def save_category(self, name, save_path, exists):
        action = "editCategory" if exists else "createCategory"
        self.request("/api/v2/torrents/" + action, {"category": name, "savePath": save_path})


# --- Module ---------------------------------------------------------------------------------

def main():
    module = AnsibleModule(
        argument_spec=dict(
            url=dict(type="str", required=True),
            username=dict(type="str", required=True),
            password=dict(type="str", required=True, no_log=True),
            preferences=dict(type="dict", default={}),
            categories=dict(type="dict", default={}),
        ),
        supports_check_mode=True,
    )
    qbt = QBittorrent(module)
    qbt.login()
    before, after = {}, {}

    current_prefs = qbt.preferences()
    prefs = preference_changes(current_prefs, module.params["preferences"])
    for key, value in prefs.items():
        before["preferences." + key], after["preferences." + key] = current_prefs.get(key), value

    current_cats = qbt.categories()
    cats = category_changes(current_cats, module.params["categories"])
    for name, path in cats.items():
        before["categories." + name] = current_cats.get(name, {}).get("savePath")
        after["categories." + name] = path

    if not module.check_mode:
        if prefs:
            qbt.set_preferences(prefs)
        for name, path in cats.items():
            qbt.save_category(name, path, exists=name in current_cats)

    changed = bool(after)
    module.exit_json(changed=changed, diff=dict(before=before, after=after) if changed else {})


if __name__ == "__main__":
    main()
