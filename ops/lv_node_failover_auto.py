#!/usr/bin/env python3
"""P2-OPS-NODE-FAILOVER-AUTO-01: cron driver for LV down → NL template failover.

Calls lv_node_down_nl_failover.py --auto --gate --apply with cooldown and TG alerts.
Safe on healthy prod: exits 0 with skip when LV up and mode normal.

Usage:
    python ops/lv_node_failover_auto.py              # dry-run decision
    python ops/lv_node_failover_auto.py --apply    # may PATCH template
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = Path(__file__).resolve().parent
STATE = ROOT / ".secrets" / "lv_node_failover_auto_state.json"
COOLDOWN_SEC = int(os.environ.get("LV_FAILOVER_AUTO_COOLDOWN_SEC", "900"))
SCRIPT = OPS / "lv_node_down_nl_failover.py"

if str(OPS) not in sys.path:
    sys.path.insert(0, str(OPS))


def _load_state() -> dict:
    if STATE.is_file():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(data: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _send_telegram(text: str) -> bool:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
    chat_id = (
        os.getenv("ADMIN_TELEGRAM_ID")
        or os.getenv("ALERT_TELEGRAM_CHAT_ID")
        or ""
    ).strip()
    if not token or not chat_id:
        print("LV_FAILOVER_ALERT_SKIP: no BOT_TOKEN or ADMIN_TELEGRAM_ID", file=sys.stderr)
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


def _cooldown_active(state: dict, action: str) -> bool:
    last = state.get(f"last_{action}_ts")
    if not last:
        return False
    return (time.time() - float(last)) < COOLDOWN_SEC


def _decide() -> tuple[str, list[str]]:
    from lv_nl_failover_common import STATE_FILE_NAME, lv_nodes_healthy, nl_nodes_healthy  # noqa: E402
    from panel_client import PanelClient  # noqa: E402

    lines: list[str] = []
    state_path = ROOT / ".secrets" / "snapshots" / STATE_FILE_NAME
    mode = "normal"
    if state_path.is_file():
        try:
            mode = json.loads(state_path.read_text(encoding="utf-8")).get("mode", "normal")
        except (json.JSONDecodeError, OSError):
            pass
    lines.append(f"state.mode={mode}")

    c = PanelClient(timeout=60)
    nodes = c.get_or_raise("/api/nodes")["response"]
    lv_ok, lv_msg = lv_nodes_healthy(nodes)
    nl_ok, nl_msg = nl_nodes_healthy(nodes)
    lines.append(f"LV: {lv_msg}")
    lines.append(f"NL: {nl_msg}")

    if not lv_ok and nl_ok:
        return "failover", lines
    if lv_ok and mode == "nl_failover":
        return "restore", lines
    lines.append("auto: nothing to do (LV up, mode normal)")
    return "skip", lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    state = _load_state()
    action, log = _decide()
    for ln in log:
        print(ln)

    if action == "skip":
        print("LV_NODE_FAILOVER_AUTO_SKIP")
        return 0

    if _cooldown_active(state, action):
        print(f"LV_NODE_FAILOVER_AUTO_COOLDOWN ({action}, {COOLDOWN_SEC}s)")
        return 0

    if not args.apply:
        print(f"dry-run: would run lv_node_down_nl_failover --auto --gate --apply ({action})")
        print("LV_NODE_FAILOVER_AUTO_DRY_OK")
        return 0

    py = sys.executable
    cmd = [py, str(SCRIPT), "--auto", "--gate", "--apply"]
    print("exec:", " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        _send_telegram(
            f"⚠️ BenderVPN LV/NL failover auto FAILED\naction={action}\nexit={r.returncode}"
        )
        return r.returncode

    state[f"last_{action}_ts"] = time.time()
    state["last_action"] = action
    _save_state(state)

    if action == "failover":
        msg = (
            "🔴 BenderVPN: LV node down → NL-only template applied\n"
            "Users: refresh subscription in Happ."
        )
    else:
        msg = "🟢 BenderVPN: LV back → multipath template restored"
    _send_telegram(msg)
    print("LV_NODE_FAILOVER_AUTO_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
