# library

Ansible modules of this repo, for apps that Ansible has no module for. Each one reads first and
only writes what differs, so a second run reports "ok", and each supports `--check`. How each
works is at the top of its file.

| Module | For | Used in |
|---|---|---|
| [`servarr_resource`](servarr_resource.py) | One item in Radarr, Sonarr or Prowlarr (a download client, a root folder, an indexer, a setting) through their API | `roles/app_config/tasks/arrs.yml`, `prowlarr.yml`, `access.yml` |
| [`qbittorrent_config`](qbittorrent_config.py) | qBittorrent's preferences and download categories through its Web API | `roles/app_config/tasks/qbittorrent.yml` |
| [`calibre_web`](calibre_web.py) | Calibre-Web's login, Kobo sync and users, in its database (it has no API for them) | `roles/app_config/tasks/calibre.yml` |
