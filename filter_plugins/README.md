# filter_plugins

Jinja filters for the few values Ansible can't make with its own filters.

| Filter | Does | Used in |
|---|---|---|
| [`qbt_password_hash`](qbittorrent.py) | A password in the form qBittorrent stores it, so a fresh install starts with your login | `roles/download_stack/templates/qBittorrent.conf.j2` |
| [`bazarr_settings_form`](bazarr.py) | Only the Bazarr settings that differ, as the form fields its API wants | `roles/app_config/tasks/bazarr.yml` |
| [`bazarr_language_profile`](bazarr.py) | A subtitle language profile as Bazarr stores it | `roles/app_config/tasks/bazarr.yml` |
