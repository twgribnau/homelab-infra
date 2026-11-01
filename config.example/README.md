# config.example

The start of your own configuration. Copy it to `~/homelab-config` (a private git repo), which
`./setup.sh` links as `config/`. Every `.yml` in it is read; leave a file out and that part isn't
configured. Each file explains its keys.

| File | Holds | Needed |
|---|---|---|
| [`vault.yml`](vault.yml) | Passwords, API keys, extra users; encrypted by `./setup.sh` | yes |
| [`settings.yml`](settings.yml) | Your choices: optional apps, time zone, languages | yes |
| [`indexers.yml`](indexers.yml) | The sites Prowlarr searches | no |
| [`maintainerr.yml`](maintainerr.yml) | Rules that remove what has been watched | no |
| [`jellyfin.yml`](jellyfin.yml) | One home screen, profile tiles and pictures for Jellyfin's users | no |
| `wg0.conf` | Your VPN provider's WireGuard file, as downloaded; encrypted by `./setup.sh` | no |
