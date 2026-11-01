# download_stack

The Compose project for downloading: qBittorrent (behind the WireGuard VPN of
[gluetun](https://github.com/qdm12/gluetun) when there is a `config/wg0.conf`), Prowlarr,
FlareSolverr, [Cleanuparr](https://github.com/Cleanuparr/Cleanuparr) and autoheal, which restarts
qBittorrent when it loses the VPN.

- **Runs:** always. Tag: `download`.
- **Settings:** `defaults/main.yml`: the image versions (updated by Renovate).
- **Note:** qBittorrent's login is set on a fresh install only; the apps are configured by `app_config`.
