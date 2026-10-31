"""Jinja filter `qbt_password_hash`: a password in the form qBittorrent stores it.

Used once, by roles/download_stack/templates/qBittorrent.conf.j2, to give a fresh
qBittorrent the shared login before it first starts. Without it, qBittorrent would start
with a random one-time password that Ansible can't know.

qBittorrent stores WebUI\\Password_PBKDF2 as "@ByteArray(<salt>:<key>)", both base64:
  key = PBKDF2-HMAC-SHA512(password, salt, 100000 iterations, 64 bytes), salt = 16 bytes.

The salt normally is random. Here it is derived from `salt_seed` (the inventory hostname),
so the rendered file is the same on every run.

    {{ homelab_password | qbt_password_hash(inventory_hostname) }}
"""

import base64
import hashlib

ITERATIONS = 100000
SALT_BYTES = 16
KEY_BYTES = 64


def qbt_password_hash(password, salt_seed):
    salt = hashlib.sha256(salt_seed.encode()).digest()[:SALT_BYTES]
    key = hashlib.pbkdf2_hmac("sha512", password.encode(), salt, ITERATIONS, KEY_BYTES)
    return "@ByteArray(%s:%s)" % (base64.b64encode(salt).decode(), base64.b64encode(key).decode())


class FilterModule:
    def filters(self):
        return {"qbt_password_hash": qbt_password_hash}
