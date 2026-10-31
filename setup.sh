#!/usr/bin/env bash
# First-time setup on the server: installs Ansible (and Tailscale, unless secrets/local.yml
# turns it off), links ~/homelab-secrets as secrets/ and encrypts vault.yml, indexers.yml and
# wg0.conf if they aren't yet. Asks nothing: fill in your secrets first (README). Safe to run again.
set -euo pipefail
cd "$(dirname "$0")"

secrets_dir="$HOME/homelab-secrets"
fail() { echo "❌ $1" >&2; exit 1; }
encrypted() { head -c 14 "$1" | grep -q '^\$ANSIBLE_VAULT'; }

[ -e secrets ] || [ -d "$secrets_dir" ] ||
  fail "No $secrets_dir. Copy secrets.example/ there and fill in vault.yml (README, Setup)."
[ -e secrets ] || ln -s "$secrets_dir" secrets
[ -f secrets/vault.yml ] || fail "No secrets/vault.yml. Copy secrets.example/vault.yml and fill it in."

echo "== Ansible"
sudo apt-get install -y -qq git python3-venv curl openssl >/dev/null
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
.venv/bin/ansible-galaxy collection install -r collections/requirements.yml >/dev/null

echo "== Encrypting your secrets"
if [ ! -f .vault_pass ]; then
  encrypted secrets/vault.yml && fail "secrets/vault.yml is encrypted: put its password in .vault_pass."
  (umask 077; openssl rand -base64 32 >.vault_pass)
  echo "New vault password in .vault_pass. Save it in your password manager: $(cat .vault_pass)"
fi
# local.yml (your choices) stays readable.
for file in secrets/vault.yml secrets/indexers.yml secrets/wg0.conf; do
  if [ -f "$file" ] && ! encrypted "$file"; then
    .venv/bin/ansible-vault encrypt "$file"
  fi
done

if ! grep -qs 'homelab_tailscale: *false' secrets/*.yml && ! command -v tailscale >/dev/null; then
  echo "== Tailscale"
  curl -fsSL https://tailscale.com/install.sh | sh
  sudo tailscale up
  echo "In the Tailscale admin console (DNS), turn on MagicDNS and HTTPS Certificates."
fi

echo
echo "✅ Ready. Install everything: .venv/bin/ansible-playbook provision.yml"
