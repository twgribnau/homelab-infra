# homelab-infra

[![CI](https://github.com/twgribnau/homelab-infra/actions/workflows/ci.yml/badge.svg)](https://github.com/twgribnau/homelab-infra/actions/workflows/ci.yml)

Ansible for a single Ubuntu home server: request a movie or series, it downloads and shows up
in Jellyfin. Docker, a download stack (qBittorrent, optionally behind a WireGuard VPN, Prowlarr,
Cleanuparr), a media stack (Jellyfin, Radarr, Sonarr, Seerr, Recyclarr, optionally Bazarr),
optionally monitoring (Prometheus, Grafana, Homepage) and optionally ebooks with Kobo sync
(Calibre-Web Automated). The playbook also connects the apps to each other and publishes their web
UIs over Tailscale HTTPS, or on the LAN.

Runs on an empty server and on an existing one: app data is kept and only settings that
differ from this repo are changed. One username and password is used for every service.

No sites to download from are included: you add the indexers you choose yourself. Only
download what you are allowed to where you live.

## Quick start

On a server with Ubuntu 26.04 and a user with `sudo`:

```bash
sudo apt install -y git
git clone https://github.com/twgribnau/homelab-infra.git && cd homelab-infra
mkdir ~/homelab-secrets && cp secrets.example/* ~/homelab-secrets/
nano ~/homelab-secrets/vault.yml   # your username, a password for the apps, email (see Your secrets)
nano ~/homelab-secrets/local.yml   # which optional apps you want
./setup.sh
.venv/bin/ansible-playbook provision.yml
```

Optional before `./setup.sh`: the sites Prowlarr searches in `~/homelab-secrets/indexers.yml`,
and your VPN's WireGuard config as `~/homelab-secrets/wg0.conf` (see [Your secrets](#your-secrets)).

`setup.sh` asks nothing. It installs Ansible and Tailscale (unless `homelab_tailscale: false`),
links `~/homelab-secrets` as `secrets/` and encrypts your secrets with a new vault password,
which it shows once (save it in your password manager). The playbook then installs everything.
Both can be run again. Afterwards the apps are at:

| App | With Tailscale | Without |
|---|---|---|
| Seerr (request movies and series) | `https://<server>.<tailnet>.ts.net` | `http://<server-ip>:5055` |
| Jellyfin (watch) | `https://<server>.<tailnet>.ts.net:8920`, and `http://<server-ip>:8096` at home | `http://<server-ip>:8096` |
| Homepage (every app on one page) | `:3001` | `:3001` |
| Calibre-Web (ebooks) | `http://<server>.<tailnet>.ts.net:8083`, and `http://<server-ip>:8083` at home | `http://<server-ip>:8083` |
| Radarr `:7878`, Sonarr `:8989`, Bazarr `:6767`, Prowlarr `:9696`, qBittorrent `:8080`, Cleanuparr `:11011`, Grafana `:3000` | | |

Log in with the username and password from your `vault.yml`.

## Your secrets

Everything personal lives in `secrets/`, a link to `~/homelab-secrets`, never in this repo.
Start from [`secrets.example/`](secrets.example); each key is explained there.

- **`vault.yml`**: passwords and API keys. Required: `vault_homelab_user` (your Ubuntu user),
  `vault_homelab_password` (the login for every app), `vault_admin_email`, `vault_backup_password`.
- **`indexers.yml`**: the sites Prowlarr searches. Per site a `name` and its `definition`, the
  file name (without `.yml`) in [Prowlarr's indexer list](https://github.com/Prowlarr/Indexers/tree/master/definitions):
  `- { name: My indexer, definition: <id> }`. Indexers added in Prowlarr itself are kept.
- **`local.yml`**: your choices (see Options).
- **`wg0.conf`**: optional, the WireGuard file from your VPN provider, as downloaded.

`setup.sh` encrypts `vault.yml` and `wg0.conf`; change those later with
`ansible-vault edit secrets/<file>`. The others are plain text.

The vault password is in `.vault_pass` (not in git). Keep it in your password manager: with it,
the encrypted files are useless to anyone else, and without it they are useless to you.

Keep a copy of `~/homelab-secrets` somewhere private: a USB stick, or a private git repo. On a
new server, put it back in `~/homelab-secrets` and the vault password in `.vault_pass` before
`./setup.sh`. More `.yml` files of your own in `secrets/` are read too.

## Options

Choose in `secrets/local.yml`, then run the playbook again.

| Want | Do |
|---|---|
| A VPN for downloads | Put your provider's WireGuard config in `secrets/wg0.conf` and run `./setup.sh` (it encrypts it). Without it qBittorrent downloads from your own IP address. A port forwarded by the provider: `vault_torrent_port` |
| No Tailscale | `homelab_tailscale: false`: every web UI on the LAN at `http://<server-ip>:<port>`, nothing from outside |
| No subtitles | `homelab_bazarr: false` |
| No graphs | `homelab_monitoring: false` (Grafana, Prometheus) |
| No start page | `homelab_homepage: false` |
| No ebooks | `homelab_books: false` |
| Other subtitle languages | `app_config_bazarr_profile: { name: German and English, languages: [de, en] }` |
| Indexers | `secrets/indexers.yml`, or add them in Prowlarr (those are kept) |
| More settings | Any setting in `inventory/group_vars/homelab/main.yml` or `roles/*/defaults/main.yml` |

With Tailscale: in the [admin console](https://login.tailscale.com/admin/dns), DNS, turn on
MagicDNS and HTTPS Certificates. The core apps (qBittorrent, Prowlarr, Cleanuparr, Radarr, Sonarr,
Jellyfin, Seerr) are always installed: they work together.

More subtitles: an [opensubtitles.com](https://www.opensubtitles.com) account
(`vault_opensubtitles_username`, `vault_opensubtitles_password`) and API keys for
[SubDL](https://subdl.com) and [Subsource](https://subsource.net) (`vault_subdl_api_key`,
`vault_subsource_api_key`) in the vault.

## Usage

```bash
. .venv/bin/activate
ansible-playbook provision.yml
```

- Run part of it with `--tags docker|download|media|books|monitoring|apps|tailscale`, or one app with
  `--tags qbittorrent|jellyfin|arrs|prowlarr|cleanuparr|recyclarr|seerr|bazarr|calibre|homepage`.
- Preview with `--check --diff` (once Docker is installed).
- `./reset.sh` wipes the server back to Ubuntu + Tailscale (`--keep-media` keeps the library).
- Family members only need a Jellyfin user: make one in Jellyfin (Dashboard, Users) and log in
  with it on the TV.
- Ebooks: put them in `~/srv/media-data/books-ingest`; Calibre-Web imports them into the library.
  For a Kobo: open Calibre-Web at `http://<server-ip>:8083`, Profile, Kobo Sync Token, and copy
  the `api_endpoint` line into `.kobo/Kobo/Kobo eReader.conf` on the Kobo (USB), under
  `[OneStoreServices]`. The Kobo syncs on your home wifi. Each reader can get their own user
  with their own token: `vault_calibre_users` in the vault, or Admin, Add new user.

## Extras

All optional; without them nothing of it is installed. None of the above needs GitHub.

- **Telegram** (`vault_telegram_bot_token`, `vault_telegram_chat_id`): imports, errors and app
  updates from Radarr, Sonarr, Prowlarr and Seerr, and Grafana alerts (full disk, heat,
  crashing containers).
- **Automatic deploys** (`vault_homelab_repo`, the SSH address of your fork on GitHub): the server
  checks `main` every 10 minutes and runs the playbook when it changed. Add
  `~/.ssh/homelab_deploy.pub` (made by the first run) as a deploy key on your fork. Before new
  images it backs up the app data and the ebook library with [restic](https://restic.net) to
  `/backup/restic`; when the run fails, it puts that backup and the previous commit back. Log:
  `journalctl -u homelab-autodeploy`.
  With Telegram too: a bot for `/deploy`, `/status` and `/log`.
- **GitHub card on Homepage** (`vault_github_token`, with automatic deploys): a read-only
  fine-grained token (Actions, Contents, Pull requests) for your fork.

## Layout

| Path | Purpose |
|---|---|
| `provision.yml` | The playbook: the roles in order |
| `inventory/group_vars/homelab/main.yml` | Settings shared by several roles |
| `setup.sh` | First-time setup: Ansible, Tailscale, links and encrypts your secrets |
| `secrets/` | Your secrets and choices (not in git, see above); examples in `secrets.example/` |
| `roles/*/defaults/main.yml` | Settings of one role you may change |
| `roles/*/vars/main.yml` | Fixed values of one role |
| `roles/docker` | Docker Engine and Compose |
| `roles/homelab_common` | Shared Docker network and the `/data` folders |
| `roles/download_stack`, `media_stack`, `books_stack`, `monitoring_stack` | One Docker Compose project each |
| `roles/app_config` | Configures and connects the apps through their APIs, one task file per app |
| `roles/tailscale` | Keeps Tailscale updated, publishes the web UIs with `tailscale serve` |
| `library/` | Ansible modules for the Radarr/Sonarr/Prowlarr and qBittorrent APIs and Calibre-Web's database |
| `filter_plugins/` | Password hash for qBittorrent's first-start config, Bazarr's settings form |
| `roles/autodeploy` | Automatic deploys (Extras) |
| `.github/`, `renovate.json` | This repo's CI, releases and weekly image updates on GitHub; not needed to run it |

## What gets configured

| App | |
|---|---|
| qBittorrent | Automatic torrent management, a download category per app, 5 downloads at once |
| Radarr, Sonarr | Hardlinks, root folder, qBittorrent client, Jellyfin library refresh |
| Prowlarr | Your indexers (`secrets/indexers.yml`), FlareSolverr, sync to Radarr/Sonarr |
| Cleanuparr | Your login, qBittorrent, Radarr/Sonarr; removes downloads stuck on metadata (15 min) or stalled (30 min), then Radarr/Sonarr search again |
| Recyclarr | TRaSH Guides 1080p quality profiles (stock profiles removed), custom formats and naming |
| Jellyfin | Admin account, libraries, hardware transcoding, API key for Radarr/Sonarr |
| Seerr | Jellyfin login, Radarr/Sonarr as default servers |
| Bazarr | Radarr/Sonarr connection, Dutch and English subtitles for everything (`app_config_bazarr_profile`), OpenSubtitles, SubDL and Subsource (optional, account or key in the vault). Optional (`homelab_bazarr`) |
| Calibre-Web | Optional (`homelab_books`): your login instead of the default admin, Kobo sync with the Kobo store passed through, more users and their Kobo tokens (`vault_calibre_users`) |
| Grafana | Optional (`homelab_monitoring`): Prometheus datasource and one Homelab dashboard (server and containers) as home page |
| Homepage | Optional (`homelab_homepage`): every app with a link and a live widget (queues, streams, downloads), server load |

Anything not managed here, such as extra Jellyfin users and libraries or indexers you add by hand,
is left alone. Settings that are managed here are set back on the next run.

## Contributing

Issues and pull requests are welcome. PR titles follow
[Conventional Commits](https://www.conventionalcommits.org) (`feat:`, `fix:`, `chore:`), since
the release notes and version come from them. CI runs ansible-lint and a full install on a fresh
VM for every PR.
