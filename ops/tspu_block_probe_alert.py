#!/usr/bin/env python3
"""P2-RED-TSPU-ALERT-01: Telegram alert when RU TSPU block probe fails (with cooldown)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".secrets" / "tspu_alert_state.json"
DEFAULT_COOLDOWN_SEC = 3600


def _load_state() -> dict:
    if not STATE.exists():
        return {}
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(data: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _send_telegram(text: str) -> bool:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
    chat_id = (
        os.getenv("ADMIN_TELEGRAM_ID")
        or os.getenv("ALERT_TELEGRAM_CHAT_ID")
        or ""
    ).strip()
    if not token or not chat_id:
        print("TSPU_ALERT_SKIP: no BOT_TOKEN or ADMIN_TELEGRAM_ID", file=sys.stderr)
        return False
    import urllib.parse
    import urllib.request

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": "true"}
    ).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status == 200


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cooldown-sec", type=int, default=DEFAULT_COOLDOWN_SEC)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--probe", default=str(ROOT / "ops" / "tspu_block_probe.py"))
    args = p.parse_args()

    proc = subprocess.run(
        [sys.executable, args.probe],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0 and "TSPU_BLOCK_PROBE_OK" in out:
        print("TSPU_BLOCK_ALERT_OK")
        return 0

    state = _load_state()
    last = float(state.get("last_alert_at") or 0)
    now = time.time()
    if now - last < args.cooldown_sec:
        print(f"TSPU_ALERT_COOLDOWN ({int(args.cooldown_sec - (now - last))}s left)")
        return 0

    msg = (
        "⚠️ TSPU block probe FAILED on RU path.\n"
        "Check relay / edge :8443 / RUNBOOK-TSPU-VLESS-INCIDENT.\n\n"
        f"{out.strip()[:500]}"
    )
    if args.dry_run:
        print("DRY-RUN alert:\n", msg)
        print("TSPU_BLOCK_ALERT_DRYRUN_OK")
        return 0

    if _send_telegram(msg):
        state["last_alert_at"] = now
        _save_state(state)
        print("TSPU_BLOCK_ALERT_SENT")
        return 1
    print("TSPU_BLOCK_ALERT_FAIL: telegram send failed", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
