# app_config

Configures the apps and connects them through their APIs, one task file per app: logins, API
keys, download clients, libraries, quality profiles, subtitles, indexers and rules. Only what
differs is changed, so a second run changes nothing.

- **Runs:** always; each app's tasks only when that app is on. Tag: `apps`, or one app:
  `qbittorrent`, `jellyfin`, `arrs`, `prowlarr`, `cleanuparr`, `recyclarr`, `seerr`,
  `maintainerr`, `bazarr`, `calibre`, `homepage`, `bookmarks`.
- **Settings:** `defaults/main.yml` (what you may change, e.g. size limits, subtitle languages,
  Jellyfin's home screen); your own values go in `config/` (see `config.example/`).
  `vars/main.yml` holds the fixed wiring between the apps.
- **Note:** on a fresh install the order in `tasks/main.yml` matters: one app's API key goes
  into the next. What you set in an app yourself and isn't managed here is left alone.
