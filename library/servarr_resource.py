#!/usr/bin/python
"""Ansible module: make one Radarr/Sonarr/Prowlarr API item look the way you describe.

How it works
------------
Radarr, Sonarr and Prowlarr share one API style ("Servarr"). Every setting is an item at an
endpoint such as /api/v3/downloadclient, or a single settings object such as
/api/v3/config/host. Many items also have a "fields" list of {name, value} pairs holding
the provider-specific settings (host, port, apiKey, ...).

On each run the module:
  1. reads the item, finding it by `match_key` (default: its name);
  2. compares only the keys you passed in `body` and `fields` with what is there;
  3. writes nothing if they already match, so reruns report "ok";
  4. otherwise creates the item (starting from the app's own template at <endpoint>/schema)
     or updates just those keys.

The API never returns secrets: passwords and API keys come back as "********". Those fields
can't be compared, so they never count as a difference on their own. They are still sent
whenever the item is created or another key changes.

Reading always happens, even with --check, so a check run shows a real diff.
"""

from __future__ import annotations

DOCUMENTATION = r"""
module: servarr_resource
short_description: Make one Radarr/Sonarr/Prowlarr API item match the given settings
description:
  - Finds an item by O(match_key), creates it from the app's template when it is missing,
    and otherwise updates only the keys in O(body) and O(fields).
  - Values the API hides as C(********) (passwords, API keys) never count as a difference.
  - Supports check mode and diff mode.
options:
  url:
    description: Base URL of the app, for example C(http://127.0.0.1:7878).
    type: str
    required: true
  api_key:
    description: The app's API key (Settings > General).
    type: str
    required: true
  api_version:
    description: C(v3) for Radarr and Sonarr, C(v1) for Prowlarr.
    type: str
    default: v3
  endpoint:
    description: API path after C(/api/<version>/), for example C(downloadclient) or C(config/host).
    type: str
    required: true
  singleton:
    description: The endpoint is one settings object (the C(config/*) endpoints), not a list.
    type: bool
    default: false
  match_key:
    description: Key that identifies the item in the list, for example C(name) or C(path).
    type: str
    default: name
  body:
    description: Top-level keys to set. Must include O(match_key) unless O(singleton) is true.
    type: dict
    default: {}
  fields:
    description: "Entries of the item's C(fields) list to set, as C(name: value)."
    type: dict
    default: {}
  tags:
    description: Tag labels to attach. Missing tags are created.
    type: list
    elements: str
  schema:
    description:
      - "Keys that pick the template from C(<endpoint>/schema) when the item is created,
        for example C({implementation: QBittorrent}) or C({definitionName: <id>})."
      - Without it, a new item is created from O(body) and O(fields) only.
    type: dict
  state:
    description: C(absent) deletes the item.
    type: str
    choices: [present, absent]
    default: present
  force_save:
    description: Save even when the app's connection test fails (it may not be reachable yet).
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Radarr downloads through qBittorrent
  servarr_resource:
    url: http://127.0.0.1:7878
    api_key: "{{ radarr_api_key }}"
    endpoint: downloadclient
    schema: { implementation: QBittorrent }
    body: { name: qBittorrent, enable: true }
    fields: { host: gluetun, port: 8080, username: admin, password: "{{ password }}" }

- name: Radarr imports with hardlinks
  servarr_resource:
    url: http://127.0.0.1:7878
    api_key: "{{ radarr_api_key }}"
    endpoint: config/mediamanagement
    singleton: true
    body: { copyUsingHardlinks: true }
"""

RETURN = r"""
resource:
  description: The item as the API returned it after the change (or as it would be, in check mode).
  type: dict
  returned: when state is present
"""

import json
from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six.moves.urllib.error import HTTPError
from ansible.module_utils.urls import open_url

HIDDEN = "********"  # what the API returns instead of a stored secret


# --- Pure helpers (no API calls) ---------------------------------------------------------

def get_fields(item):
    """The item's `fields` list as a {name: value} dict."""
    return {f["name"]: f.get("value") for f in item.get("fields", [])}


def set_fields(item, fields):
    """Set entries of the item's `fields` list in place, adding the ones that are missing."""
    by_name = {f["name"]: f for f in item.setdefault("fields", [])}
    for name, value in fields.items():
        if name in by_name:
            by_name[name]["value"] = value
        else:
            item["fields"].append({"name": name, "value": value})


def is_secret(key):
    """Keys whose values are masked in the diff output (passwords, API keys, tokens)."""
    return any(word in key.lower() for word in ("pass", "key", "token"))


def differences(current, body, fields):
    """Compare the wanted keys with the current item. Returns (before, after) dicts.

    Field values the API hides can't be compared, so they are skipped.
    """
    before, after = {}, {}
    for key, wanted in body.items():
        if current.get(key) != wanted:
            before[key], after[key] = current.get(key), wanted
    current_fields = get_fields(current)
    for name, wanted in fields.items():
        have = current_fields.get(name)
        if have != HIDDEN and have != wanted:
            before["fields." + name], after["fields." + name] = have, wanted
    return before, after


def masked(diff):
    """Copy of a before/after dict with secret values replaced by the mask."""
    return {k: (HIDDEN if is_secret(k) and v is not None else v) for k, v in diff.items()}


def apply(item, body, fields):
    """Copy of the item with the wanted keys set."""
    result = deepcopy(item)
    result.update(body)
    set_fields(result, fields)
    return result


def new_item(template, body, fields):
    """A new item: the app's template (if any) plus the wanted keys."""
    item = deepcopy(template or {})
    item.pop("id", None)
    # Prowlarr's indexer templates list the site's addresses in `indexerUrls` but leave the
    # `baseUrl` field empty; the first address is what Prowlarr's UI would pick.
    urls = item.get("indexerUrls") or []
    if urls and not get_fields(item).get("baseUrl") and "baseUrl" not in fields:
        set_fields(item, {"baseUrl": urls[0]})
    return apply(item, body, fields)


def same_identity(value, wanted):
    """Match names and paths case-insensitively and ignoring a trailing slash."""
    if isinstance(value, str) and isinstance(wanted, str):
        return value.rstrip("/").lower() == wanted.rstrip("/").lower()
    return value == wanted


def validation_errors(body):
    """The messages from a Servarr HTTP 400 answer, which is a list of validation failures."""
    try:
        return "; ".join(e["errorMessage"] for e in json.loads(body) if e.get("errorMessage"))
    except (ValueError, TypeError, KeyError):
        return ""


# --- API access -----------------------------------------------------------------------------

class Servarr:
    """Minimal JSON client for one app; any failure ends the module with a clear message."""

    def __init__(self, module):
        params = module.params
        self.module = module
        self.base = "%s/api/%s" % (params["url"].rstrip("/"), params["api_version"])
        self.headers = {"X-Api-Key": params["api_key"], "Content-Type": "application/json"}
        self.save_query = "?forceSave=true" if params["force_save"] else ""

    def request(self, method, path, data=None, query=""):
        url = "%s/%s%s" % (self.base, path, query)
        try:
            response = open_url(url, method=method, headers=self.headers, timeout=60,
                                data=None if data is None else json.dumps(data))
            raw = response.read()
            return json.loads(raw) if raw else None
        except HTTPError as e:
            body = e.read().decode(errors="replace")
            reason = validation_errors(body)
            self.module.fail_json(msg="%s %s failed: HTTP %s%s" % (method, url, e.code, " - " + reason if reason else ""),
                                  response=body)
        except Exception as e:  # connection refused, timeout, ...
            self.module.fail_json(msg="%s %s failed: %s" % (method, url, e))

    def get(self, path):
        return self.request("GET", path)

    def create(self, path, item):
        return self.request("POST", path, item, self.save_query)

    def update(self, path, item):
        return self.request("PUT", "%s/%s" % (path, item["id"]), item, self.save_query)

    def delete(self, path, item):
        return self.request("DELETE", "%s/%s" % (path, item["id"]))

    def tag_ids(self, labels, check_mode):
        """Ids for the tag labels, creating missing tags (a placeholder id in check mode)."""
        existing = {t["label"].lower(): t["id"] for t in self.get("tag") or []}
        for label in labels:
            if label.lower() not in existing:
                existing[label.lower()] = -1 if check_mode else self.request("POST", "tag", {"label": label})["id"]
        return [existing[label.lower()] for label in labels]


# --- Module ---------------------------------------------------------------------------------

def main():
    module = AnsibleModule(
        argument_spec=dict(
            url=dict(type="str", required=True),
            api_key=dict(type="str", required=True, no_log=True),
            api_version=dict(type="str", default="v3"),
            endpoint=dict(type="str", required=True),
            singleton=dict(type="bool", default=False),
            match_key=dict(type="str", default="name"),
            body=dict(type="dict", default={}),
            fields=dict(type="dict", default={}, no_log=False),
            tags=dict(type="list", elements="str"),
            schema=dict(type="dict"),
            state=dict(type="str", default="present", choices=["present", "absent"]),
            force_save=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
    )
    p = module.params
    api = Servarr(module)
    endpoint = p["endpoint"].strip("/")
    body = deepcopy(p["body"])
    fields = p["fields"]
    if p["tags"] is not None:
        body["tags"] = api.tag_ids(p["tags"], module.check_mode)

    def finish(changed, resource=None, before=None, after=None):
        result = dict(changed=changed, resource=resource)
        if changed:
            result["diff"] = dict(before=masked(before or {}), after=masked(after or {}))
        module.exit_json(**result)

    # A settings object (config/host, config/mediamanagement, ...): always exists, only update.
    if p["singleton"]:
        current = api.get(endpoint)
        before, after = differences(current, body, fields)
        if not after:
            finish(False, current)
        wanted = apply(current, body, fields)
        finish(True, wanted if module.check_mode else api.update(endpoint, wanted), before, after)

    # An item in a list (download clients, indexers, root folders, ...): find it first.
    key = p["match_key"]
    if key not in body:
        module.fail_json(msg="body.%s is required to find the item" % key)
    current = next((i for i in api.get(endpoint) or [] if same_identity(i.get(key), body[key])), None)

    if p["state"] == "absent":
        if current is None:
            finish(False)
        if not module.check_mode:
            api.delete(endpoint, current)
        finish(True, None, {key: body[key]}, {})

    if current is None:
        template = None
        if p["schema"]:
            templates = api.get(endpoint + "/schema") or []
            template = next((t for t in templates if all(t.get(k) == v for k, v in p["schema"].items())), None)
            if template is None:
                module.fail_json(msg="No %s template matches %s" % (endpoint, p["schema"]))
        wanted = new_item(template, body, fields)
        after = dict(body, **{"fields." + k: v for k, v in fields.items()})
        finish(True, wanted if module.check_mode else api.create(endpoint, wanted), {}, after)

    before, after = differences(current, body, fields)
    if not after:
        finish(False, current)
    wanted = apply(current, body, fields)
    finish(True, wanted if module.check_mode else api.update(endpoint, wanted), before, after)


if __name__ == "__main__":
    main()
