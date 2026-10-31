# homelab-infra

[![CI](https://github.com/twgribnau/homelab-infra/actions/workflows/ci.yml/badge.svg)](https://github.com/twgribnau/homelab-infra/actions/workflows/ci.yml)

Ansible for a single Ubuntu home server: request a movie or series, it downloads and shows up
in Jellyfin. Docker, a download stack (qBittorrent, optionally behind a WireGuard VPN, Prowlarr),
a media stack (Jellyfin, Radarr, Sonarr, Seerr, Recyclarr, optionally Bazarr) and optionally
monitoring (Prometheus, Grafana, Homepage). The playbook also connects the apps to each other and
publishes their web UIs over Tailscale HTTPS, or on the LAN.

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
nano ~/homelab-secrets/vault.yml   # your username, a password for the apps, email
nano ~/homelab-secrets/local.yml   # which optional apps you want
./setup.sh
.venv/bin/ansible-playbook provision.yml
```

Optional before `./setup.sh`: the sites Prowlarr searches in `~/homelab-secrets/indexers.yml`,
and your VPN's WireGuard config as `~/homelab-secrets/wg0.conf`.

`setup.sh` asks nothing. It installs Ansible and Tailscale (unless `homelab_tailscale: false`),
links `~/homelab-secrets` as `secrets/` and encrypts your secrets with a new vault password,
which it shows once (save it in your password manager). The playbook then installs everything.
Both can be run again. Afterwards the apps are at:

| App | With Tailscale | Without |
|---|---|---|
| Seerr (request movies and series) | `https://<server>.<tailnet>.ts.net` | `http://<server-ip>:5055` |
| Jellyfin (watch) | `https://<server>.<tailnet>.ts.net:8920`, and `http://<server-ip>:8096` at home | `http://<server-ip>:8096` |
| Homepage (every app on one page) | `:3001` | `:3001` |
| Radarr `:7878`, Sonarr `:8989`, Bazarr `:6767`, Prowlarr `:9696`, qBittorrent `:8080`, Grafana `:3000` | | |

Log in with the username and password from your `vault.yml`.

## Your secrets

Everything personal lives in `secrets/`, a link to `~/homelab-secrets`, and never in this repo:

| File | |
|---|---|
| `vault.yml` | Passwords, accounts and API keys, encrypted with Ansible Vault |
| `local.yml` | Your choices: optional apps, other settings (`secrets.example/local.yml`) |
| `indexers.yml` | The sites Prowlarr searches (`secrets.example/indexers.yml`) |
| `wg0.conf` | Optional: your VPN, encrypted |

The vault password is in `.vault_pass` (not in git). Keep it in your password manager: with it,
the encrypted files are useless to anyone else, and without it they are useless to you.

Back up `~/homelab-secrets` in a **private** repo:

```bash
cd ~/homelab-secrets
git add -A && git commit -m "My homelab secrets"
git remote add origin git@github.com:<you>/homelab-secrets.git   # create it as Private on GitHub first
git push -u origin main
```

On a new server, clone it to `~/homelab-secrets` and put the vault password in `.vault_pass`
before `./setup.sh`. Edit with `ansible-vault edit secrets/vault.yml`; add more of your own
`.yml` files to `secrets/` and they are read too.

## Options

Choose in `secrets/local.yml`, then run the playbook again.

| Want | Do |
|---|---|
| A VPN for downloads | Put your provider's WireGuard config in `secrets/wg0.conf` and run `./setup.sh` (it encrypts it). Without it qBittorrent downloads from your own IP address. A port forwarded by the provider: `vault_torrent_port` |
| No Tailscale | `homelab_tailscale: false`: every web UI on the LAN at `http://<server-ip>:<port>`, nothing from outside |
| No subtitles | `homelab_bazarr: false` |
| No graphs | `homelab_monitoring: false` (Grafana, Prometheus) |
| No start page | `homelab_homepage: false` |
| Other subtitle languages | `app_config_bazarr_profile: { name: German and English, languages: [de, en] }` |
| Indexers | `secrets/indexers.yml`, or add them in Prowlarr (those are kept) |
| More settings | Any setting in `inventory/group_vars/homelab/main.yml` or `roles/*/defaults/main.yml` |

With Tailscale: in the [admin console](https://login.tailscale.com/admin/dns), DNS, turn on
MagicDNS and HTTPS Certificates. The core apps (qBittorrent, Prowlarr, Radarr, Sonarr, Jellyfin,
Seerr) are always installed: they work together.

Optional keys in the vault (`ansible-vault edit secrets/vault.yml`, all listed in
`secrets.example/vault.yml`):

| Key | |
|---|---|
| `vault_telegram_bot_token`, `vault_telegram_chat_id` | Notifications and alerts in Telegram |
| `vault_opensubtitles_username`, `vault_opensubtitles_password` | An [opensubtitles.com](https://www.opensubtitles.com) account for Bazarr |
| `vault_subdl_api_key`, `vault_subsource_api_key` | API keys for [SubDL](https://subdl.com) and [Subsource](https://subsource.net), more subtitles in Bazarr |
| `vault_homelab_repo` | SSH address of your fork; the server then deploys its `main` by itself |
| `vault_github_token` | With `vault_homelab_repo`: a read-only fine-grained token (Actions, Contents, Pull requests) for the GitHub card on Homepage |
| `vault_torrent_port` | A peer port forwarded by your VPN provider |

## Usage

```bash
. .venv/bin/activate
ansible-playbook provision.yml
```

- Run part of it with `--tags docker|download|media|monitoring|apps|tailscale`, or one app with
  `--tags qbittorrent|jellyfin|arrs|prowlarr|recyclarr|seerr|bazarr|homepage`.
- Preview with `--check --diff` (once Docker is installed).
- Automatic deploys (with `vault_homelab_repo`) check GitHub every 10 minutes. Add
  `~/.ssh/homelab_deploy.pub` (made by the first run) as a deploy key on GitHub. Log:
  `journalctl -u homelab-autodeploy`.
- Each automatic deploy first backs up the app data with [restic](https://restic.net) to
  `/backup/restic`. When the playbook fails, that backup and the previous commit are put back.
- `./reset.sh` wipes the server back to Ubuntu + Tailscale (`--keep-media` keeps the library).
- Family members only need a Jellyfin user: make one in Jellyfin (Dashboard, Users) and log in
  with it on the TV.

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
| `roles/download_stack`, `media_stack`, `monitoring_stack` | One Docker Compose project each |
| `roles/app_config` | Configures and connects the apps through their APIs, one task file per app |
| `roles/tailscale` | Keeps Tailscale updated, publishes the web UIs with `tailscale serve` |
| `library/` | Ansible modules for the Radarr/Sonarr/Prowlarr and qBittorrent APIs |
| `filter_plugins/` | Password hash for qBittorrent's first-start config, Bazarr's settings form |
| `roles/autodeploy` | Runs the playbook when `main` changes on GitHub: backup first, rollback on failure, reports to Telegram. With Telegram set up, also a bot for `/deploy`, `/status` (containers, disk space) and `/log` |
| `renovate.json` | [Renovate](https://github.com/apps/renovate) opens one PR a week with newer image and collection versions; patch updates merge by themselves once CI passes |
| `.github/workflows/ci.yml` | ansible-lint on every PR and push to main; for PRs that pass, the playbook twice on a fresh VM: a full install, then a run that must change nothing (no VPN, GPU or Tailscale there) |
| `.github/workflows/release.yml` | Run by hand (Actions → Release → Run workflow): tags `main` with the next version and publishes release notes from the PRs merged since the last release. `auto` picks the version from the commit titles (`feat!:` major, `feat:` minor, else patch) |
| `.github/workflows/telegram.yml` | Sends new PRs to Telegram (repo secrets `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) |

## What gets configured

| App | |
|---|---|
| qBittorrent | Automatic torrent management, a download category per app |
| Radarr, Sonarr | Hardlinks, root folder, qBittorrent client, Jellyfin library refresh |
| Prowlarr | Your indexers (`secrets/indexers.yml`), FlareSolverr, sync to Radarr/Sonarr |
| Recyclarr | TRaSH Guides 1080p quality profiles (stock profiles removed), custom formats and naming |
| Jellyfin | Admin account, libraries, hardware transcoding, API key for Radarr/Sonarr |
| Seerr | Jellyfin login, Radarr/Sonarr as default servers |
| Bazarr | Radarr/Sonarr connection, Dutch and English subtitles for everything (`app_config_bazarr_profile`), OpenSubtitles, SubDL and Subsource (optional, account or key in the vault). Optional (`homelab_bazarr`) |
| Grafana | Optional (`homelab_monitoring`): Prometheus datasource and one Homelab dashboard (server and containers) as home page |
| Homepage | Optional (`homelab_homepage`): every app with a link and a live widget (queues, streams, downloads), server load |
| Telegram | Optional (bot in the vault): imports, errors and app updates from Radarr, Sonarr, Prowlarr and Seerr; Grafana alerts for a full disk, heat and crashing containers |

Anything not managed here, such as extra Jellyfin users and libraries or indexers you add by hand,
is left alone. Settings that are managed here are set back on the next run.

## Contributing

Issues and pull requests are welcome. PR titles follow
[Conventional Commits](https://www.conventionalcommits.org) (`feat:`, `fix:`, `chore:`), since
the release notes and version come from them. CI runs ansible-lint and a full install on a fresh
VM for every PR.
