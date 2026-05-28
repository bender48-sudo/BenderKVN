#!/usr/bin/env python3
"""VPN-AUD-140: alert admin on critical Docker container die/oom (LV/AMS).

Designed for cron on panel/node host (typically LV). Reads secrets from
``/etc/bvpn/balancer.env`` (BOT_TOKEN, ADMIN_CHAT_ID).

Usage (on server):
    python3 /opt/bvpn/docker_events_tg.py --dry-run
    python3 /opt/bvpn/docker_events_tg.py

Cron (every 5 min):
    */5 * * * * /usr/bin/python3 /opt/bvpn/docker_events_tg.py >> /var/log/bvpn-docker-events.log 2>&1
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

STATE_DIR = Path("/var/lib/bvpn-monitor")
STATE_FILE = STATE_DIR / "docker_events_state.json"
ENV_FILE = Path("/etc/bvpn/balancer.env")
LOG_FILE = Path("/var/log/bvpn-docker-events.log")

# Substrings of container names worth paging (case-insensitive).
WATCH_NAME_RE = re.compile(
    r"(remnanode|remnawave|remna-shop|subscription|postgres|caddy|xray)",
    re.I,
)

DEFAULT_COOLDOWN_SEC = 900
EVENT_WINDOW_SEC = 360  # slightly > 5 min cron


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_state() -> dict:
    if not STATE_FILE.is_file():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(data: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def tg_send(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text[:4000],
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status == 200
    except Exception as e:
        log(f"TG send error: {e}")
        return False


def docker_events_since(seconds: int) -> list[dict]:
    """Collect die/oom events from docker events (one-shot, bounded wait)."""
    since = f"{seconds}s"
    cmd = [
        "docker",
        "events",
        "--since",
        since,
        "--until",
        "0s",
        "--filter",
        "event=die",
        "--filter",
        "event=oom",
        "--format",
        "{{json .}}",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=min(seconds + 15, 120),
        )
    except subprocess.TimeoutExpired:
        log("docker events timeout")
        return []
    if proc.returncode != 0:
        log(f"docker events exit {proc.returncode}: {(proc.stderr or '')[:200]}")
        return []
    rows: list[dict] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def event_container_name(ev: dict) -> str:
    actor = ev.get("Actor") or {}
    attrs = actor.get("Attributes") or {}
    return str(attrs.get("name") or attrs.get("container") or "?")


def event_exit_code(ev: dict) -> str:
    actor = ev.get("Actor") or {}
    attrs = actor.get("Attributes") or {}
    return str(attrs.get("exitCode") or "?")


def filter_events(events: list[dict]) -> list[dict]:
    out: list[dict] = []
    for ev in events:
        name = event_container_name(ev)
        if WATCH_NAME_RE.search(name):
            out.append(ev)
    return out


def format_alert(events: list[dict], host: str) -> str:
    lines = [f"🚨 <b>Docker event</b> on <code>{host}</code>"]
    for ev in events[:8]:
        action = ev.get("status") or ev.get("Action") or ev.get("Type") or "?"
        name = event_container_name(ev)
        code = event_exit_code(ev)
        lines.append(f"• <b>{name}</b> {action} exit={code}")
    if len(events) > 8:
        lines.append(f"… +{len(events) - 8} more")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cooldown-sec", type=int, default=DEFAULT_COOLDOWN_SEC)
    ap.add_argument("--window-sec", type=int, default=EVENT_WINDOW_SEC)
    ap.add_argument("--env-file", type=Path, default=ENV_FILE)
    args = ap.parse_args()

    env = load_env(args.env_file)
    token = env.get("BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN") or ""
    chat_id = env.get("ADMIN_CHAT_ID") or env.get("ADMIN_TELEGRAM_ID") or "924498094"

    import socket

    host = socket.gethostname()
    events = filter_events(docker_events_since(args.window_sec))
    if not events:
        print("DOCKER_EVENTS_OK (no critical events)")
        return 0

    state = load_state()
    now = time.time()
    last = float(state.get("last_alert_at") or 0)
    key = "|".join(sorted(f"{event_container_name(e)}:{e.get('status')}" for e in events))
    if key == state.get("last_key") and now - last < args.cooldown_sec:
        print(f"DOCKER_EVENTS_COOLDOWN ({int(args.cooldown_sec - (now - last))}s)")
        return 0

    msg = format_alert(events, host)
    log(f"events={len(events)} dry_run={args.dry_run}")
    if args.dry_run:
        print(msg)
        print("DOCKER_EVENTS_DRYRUN_OK")
        return 0

    if not token:
        log("FAIL: no BOT_TOKEN in balancer.env")
        return 2

    if tg_send(token, chat_id, msg):
        state["last_alert_at"] = now
        state["last_key"] = key
        save_state(state)
        print("DOCKER_EVENTS_ALERT_SENT")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
