#!/usr/bin/env python3
"""Telegram bot for the homelab: /deploy, /status and /log, answered in one chat only.

It long-polls Telegram, so nothing has to reach the server from outside. Messages from other
chats are ignored, and commands older than a minute (sent while the bot was down) are
skipped instead of run late. Replies are Telegram HTML, with a row of buttons for the
commands under the message field. Started by homelab-bot.service; log: journalctl -u homelab-bot
"""

import html
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
REPO = os.environ["HOMELAB_REPO_DIR"]
WEB = os.environ["HOMELAB_REPO_URL"]
DISKS = {"System": "/", "Media": os.environ["HOMELAB_DATA_DIR"]}
DISK_WARN = 90  # percent used
MAX_AGE = 60  # seconds
POLL = 50     # seconds Telegram holds getUpdates open


def api(method, wait=10, **params):
    request = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}",
                                     json.dumps(params).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=wait) as response:
        return json.load(response)["result"]


def run(*command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    return (result.stdout or result.stderr).strip()


def commit_link(commit):
    return f'<a href="{WEB}/commit/{commit}">{commit[:7]}</a>'


def deploy():
    if run("systemctl", "is-active", "homelab-autodeploy.service") == "activating":
        return "A deploy is already running."
    subprocess.run(["systemctl", "start", "--no-block", "homelab-autodeploy.service"], check=True, timeout=30)
    return "Checking GitHub now. When main has changed, the deploy reports here; otherwise nothing follows."


def status():
    lines = []
    for line in sorted(run("docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}").splitlines()):
        name, state = line.split("\t")
        ok = state.startswith("Up") and "unhealthy" not in state
        lines.append(f"{'✅' if ok else '⚠️'} {html.escape(name)}: {html.escape(state)}")
    seen = set()
    for label, path in DISKS.items():
        if os.stat(path).st_dev in seen:  # same disk as one listed already
            continue
        seen.add(os.stat(path).st_dev)
        usage = shutil.disk_usage(path)
        used = round(usage.used / usage.total * 100)
        lines.append(f"{'⚠️' if used >= DISK_WARN else '💾'} {label} disk: {used}% used, {usage.free / 1e9:.0f} GB free")
    commit, title = run("git", "-C", REPO, "log", "-1", "--format=%H%n%s").split("\n", 1)
    # v1.1.0, or v1.1.0 + 3 commits since that release
    version = re.sub(r"-(\d+)-g[0-9a-f]+$", r" + \1 commits", run("git", "-C", REPO, "describe", "--tags", "--always"))
    failed = " (a newer commit failed, see /log)" if os.path.exists(f"{REPO}/.failed-commit") else ""
    return "\n".join(lines + ["", f"Deployed: {html.escape(version)}, {commit_link(commit)} {html.escape(title)}{failed}"])


def log():
    try:
        with open(f"{REPO}/.last-failure") as file:
            when, commit, *what = file.read().strip().split("\n")  # written by homelab-autodeploy
    except FileNotFoundError:
        return "No failed deploy recorded."
    fixed = "" if os.path.exists(f"{REPO}/.failed-commit") else "\n\nA later deploy succeeded."
    return (f"❌ Last failed deploy: {when}, {commit_link(commit)}\n{html.escape(chr(10).join(what))}{fixed}"
            "\n\nFull log: journalctl -u homelab-autodeploy")


COMMANDS = {
    "deploy": ("Check GitHub now and deploy main if it changed", deploy),
    "status": ("Containers, disk space and the deployed commit", status),
    "log": ("Why the last deploy failed", log),
}
HELP = "\n".join(f"/{name} – {description}" for name, (description, _) in COMMANDS.items())
# Buttons under the message field; a tap sends the label, which stands for the command.
BUTTONS = {"📊 Status": "status", "🔄 Deploy": "deploy", "📜 Log": "log"}
KEYBOARD = {"keyboard": [[{"text": label} for label in BUTTONS]], "resize_keyboard": True, "is_persistent": True}


def command(text):
    if text in BUTTONS:
        return BUTTONS[text]
    if text.startswith("/"):
        return text.split()[0][1:].split("@")[0]  # "/status@MyBot extra" -> "status"
    return None


def answer(name):
    if name not in COMMANDS:
        return HELP
    try:
        return COMMANDS[name][1]()
    except Exception as error:  # any failure becomes a reply
        return f"❌ /{name} failed: {type(error).__name__}"


def main():
    offset = 0
    while True:
        try:
            updates = api("getUpdates", wait=POLL + 10, offset=offset, timeout=POLL, allowed_updates=["message"])
        except Exception as error:  # a network hiccup: wait and poll again
            print(f"Telegram unreachable: {type(error).__name__}", flush=True)  # not the error itself: its URL holds the token
            time.sleep(10)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            name = command(message.get("text", ""))
            if message.get("chat", {}).get("id") != CHAT_ID or not name or time.time() - message.get("date", 0) > MAX_AGE:
                continue
            print(f"Command: {name}", flush=True)
            try:
                api("sendMessage", chat_id=CHAT_ID, text=answer(name), parse_mode="HTML",
                    link_preview_options={"is_disabled": True}, reply_markup=KEYBOARD)
            except Exception as error:
                print(f"Reply failed: {type(error).__name__}", flush=True)


if __name__ == "__main__":
    main()
