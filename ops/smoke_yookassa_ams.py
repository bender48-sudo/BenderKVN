#!/usr/bin/env python3
"""Post-deploy smoke: YooKassa env + topup handler on AMS remna-shop-bot."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AMS = "root@168.100.11.140"
SSH_PORT = "3344"
SSH_KEY = Path.home() / ".ssh" / "bvpn_ams_ed25519"


def _ssh(cmd: str, timeout: int = 90) -> tuple[int, str]:
    if not SSH_KEY.is_file():
        SSH_KEY_ALT = Path.home() / ".ssh" / "id_ed25519"
        key = SSH_KEY_ALT if SSH_KEY_ALT.is_file() else SSH_KEY
    else:
        key = SSH_KEY
    r = subprocess.run(
        [
            "ssh",
            "-i",
            str(key),
            "-p",
            SSH_PORT,
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=40",
            "-o",
            "StrictHostKeyChecking=accept-new",
            AMS,
            cmd,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out.strip()


def main() -> int:
    checks = [
        (
            "env",
            """docker exec remna-shop-bot sh -c '
sid="$YOOKASSA_SHOP_ID"; sec="$YOOKASSA_SECRET_KEY";
test -n "$sid" && test -n "$sec" && echo YOOKASSA_ENV_OK
'""",
        ),
        (
            "handler",
            """docker exec remna-shop-bot grep -q pay_yookassa_topup_ /app/src/shop_bot/bot/handlers.py && echo TOPUP_HANDLER_OK""",
        ),
        (
            "keyboard",
            """docker exec remna-shop-bot sh -c '
grep -q pay_yookassa_topup_ /app/src/shop_bot/bot/keyboards.py &&
! grep -q pay_stars_topup_ /app/src/shop_bot/bot/keyboards.py &&
echo TOPUP_KEYBOARD_OK
'""",
        ),
        (
            "health",
            "curl -sf http://127.0.0.1:1488/health | head -c 200 && echo && echo HEALTH_OK",
        ),
    ]
    for name, cmd in checks:
        code, out = _ssh(cmd)
        if code != 0 or "OK" not in out:
            print(f"FAIL [{name}]: {out[:500]}", file=sys.stderr)
            return 1
        print(f"OK [{name}]")
    print("YOOKASSA_AMS_SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
