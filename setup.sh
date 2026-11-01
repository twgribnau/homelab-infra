#!/usr/bin/env bash
# First-time setup on the server: installs Ansible (and Tailscale, unless config/settings.yml
# turns it off), links ~/homelab-config as config/ and encrypts vault.yml and wg0.conf if
# they aren't yet. Asks nothing: fill in your configuration first (README). Safe to run again.
set -euo pipefail
cd "$(dirname "$0")"

config_dir="$HOME/homelab-config"
fail() { echo "❌ $1" >&2; exit 1; }
encrypted() { head -c 14 "$1" | grep -q '^\$ANSIBLE_VAULT'; }

# The link's old name, secrets/, becomes config/.
[ -L secrets ] && [ ! -e config ] && mv secrets config
[ -e config ] || [ -d "$config_dir" ] ||
  fail "No $config_dir. Copy config.example/ there and fill in vault.yml (README, Setup)."
[ -e config ] || ln -s "$config_dir" config
[ -f config/vault.yml ] || fail "No config/vault.yml. Copy config.example/vault.yml and fill it in."

echo "== Ansible"
sudo apt-get install -y -qq git python3-venv curl openssl >/dev/null
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
.venv/bin/ansible-galaxy collection install -r collections/requirements.yml >/dev/null

echo "== Encrypting your secrets"
if [ ! -f .vault_pass ]; then
  encrypted config/vault.yml && fail "config/vault.yml is encrypted: put its password in .vault_pass."
  (umask 077; openssl rand -base64 32 >.vault_pass)
  echo "New vault password in .vault_pass. Save it in your password manager: $(cat .vault_pass)"
fi
# The other files hold nothing secret and stay readable.
for file in config/vault.yml config/wg0.conf; do
  if [ -f "$file" ] && ! encrypted "$file"; then
    .venv/bin/ansible-vault encrypt "$file"
  fi
done

if ! grep -qs 'homelab_tailscale: *false' config/*.yml && ! command -v tailscale >/dev/null; then
  echo "== Tailscale"
  curl -fsSL https://tailscale.com/install.sh | sh
  sudo tailscale up
  echo "In the Tailscale admin console (DNS), turn on MagicDNS and HTTPS Certificates."
fi

echo
echo "✅ Ready. Install everything: .venv/bin/ansible-playbook provision.yml"
