# autodeploy

The server deploys itself: every 10 minutes it checks `main` on GitHub and your config repo, and
runs the playbook when one changed. Before new images it backs up the app data locally; when
the run fails it puts that backup and the previous commit back. With Telegram, every deploy is
reported and a bot answers `/deploy`, `/status`, `/log`, `/hold` and `/main`.

- **Runs:** when `vault_homelab_repo` is set (the SSH address of your fork). Tag: `autodeploy`.
  Add `~/.ssh/homelab_deploy.pub` (made by the first run) as a deploy key on your fork.
- **Settings:** `defaults/main.yml`: its own copy of the repo, how often it checks, where the
  local backup goes.
- **Note:** running the playbook yourself from a branch puts it on hold, so `main` doesn't replace
  what you test; from `main`, or `/main` in Telegram, it follows `main` again. Log:
  `journalctl -u homelab-autodeploy`.
