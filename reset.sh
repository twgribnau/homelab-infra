#!/usr/bin/env bash
# Wipe the homelab back to Ubuntu + Tailscale, so provision.yml can rebuild it from zero.
# Tailscale itself stays installed and logged in (it is how you reach the server).
#
#   ./reset.sh               remove Docker, all containers, app data and media
#   ./reset.sh --keep-media  same, but keep the media library and torrents
set -euo pipefail

srv="$HOME/srv"   # homelab_base_dir in inventory/group_vars/homelab/main.yml
keep_media=false
[[ "${1:-}" == "--keep-media" ]] && keep_media=true

if $keep_media; then
  echo "This removes Docker, every container and image, and all app data in $srv (media is kept)."
else
  echo "This removes Docker, every container and image, and EVERYTHING in $srv, including all media."
fi
read -rp "Type 'reset' to continue: " answer
[[ "$answer" == "reset" ]] || { echo "Cancelled."; exit 1; }

echo "Stopping the automatic deploys (the backups in /backup stay)..."
sudo systemctl disable --now homelab-autodeploy.timer 2>/dev/null || true
sudo rm -f /etc/systemd/system/homelab-autodeploy.{service,timer} /usr/local/bin/homelab-autodeploy \
  /etc/homelab-autodeploy.env
sudo systemctl daemon-reload

echo "Stopping and removing Docker..."
sudo systemctl stop docker.socket docker.service containerd.service 2>/dev/null || true
sudo apt-get purge -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin \
  docker-compose-plugin docker-ce-rootless-extras 2>/dev/null || true
sudo rm -rf /var/lib/docker /var/lib/containerd /etc/docker \
  /etc/apt/keyrings/docker.asc /etc/apt/sources.list.d/docker.sources
sudo groupdel docker 2>/dev/null || true

echo "Removing the Tailscale HTTPS addresses (Tailscale itself stays)..."
sudo tailscale serve reset

echo "Removing app data..."
if $keep_media; then
  sudo find "$srv" -mindepth 1 -maxdepth 1 ! -name media-data -exec rm -rf {} +
else
  sudo rm -rf "$srv"
fi

echo "Done."
