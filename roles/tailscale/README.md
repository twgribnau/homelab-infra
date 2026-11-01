# tailscale

Keeps Tailscale up to date and publishes every web UI with `tailscale serve` at
`https://<server>.<tailnet>.ts.net:<port>`. Tailscale itself is installed and logged in by
`./setup.sh`.

- **Runs:** with `homelab_tailscale: true` (the default). Tag: `tailscale`.
- **Settings:** `defaults/main.yml`: which app gets which HTTPS port. Apps that are off are left out.
- **Note:** it only adds addresses; one you no longer want: `sudo tailscale serve --https=<port> off`.
