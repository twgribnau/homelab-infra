# workflows

What runs on GitHub. None of it is needed to run the homelab itself.

| Workflow | When | Does |
|---|---|---|
| [`ci.yml`](ci.yml) | Every PR, and pushes to `main` | ansible-lint; for a PR also `./setup.sh` and the playbook twice on a fresh Ubuntu VM (the second run must change nothing). Skipped for a PR that only changes Markdown |
| [`release.yml`](release.yml) | By hand: Actions → Release | Tags `main` with the next version (from the PR titles: `feat:`, `fix:`, `feat!:`) and writes the release notes |
| [`telegram.yml`](telegram.yml) | After CI or a release | A Telegram message when a PR is ready to merge, or when CI or a release failed (repo secrets `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) |

Renovate ([`renovate.json`](../../renovate.json)) opens a PR every week with new image versions;
patch updates merge by themselves once CI passes.
