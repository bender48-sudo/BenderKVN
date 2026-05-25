#!/usr/bin/env python3
"""Post-deploy: verify SUB_REFRESH_JITTER on AMS bot (read-only)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SSH_KEY = Path.home() / ".ssh" / "bvpn_ams_ed25519"
AMS = "root@168.100.11.140"
PORT = "3344"


def ssh(cmd: str, timeout: int = 60) -> tuple[int, str]:
    full = [
        "ssh",
        "-i",
        str(SSH_KEY),
        "-o",
        "BatchMode=yes",
        "-p",
        PORT,
        AMS,
        cmd,
    ]
    r = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out


def main() -> int:
    code, out = ssh(
        "docker exec remna-shop-bot python -c "
        "'from shop_bot.bot.subscription_refresh import SUB_REFRESH_JITTER_MAX_SEC; "
        "print(SUB_REFRESH_JITTER_MAX_SEC)'"
    )
    if code != 0 or "300" not in out:
        print("FAIL: constant check", out)
        return 1
    print("OK: SUB_REFRESH_JITTER_MAX_SEC =", out.strip().split()[-1])

    code, out = ssh(
        "docker logs remna-shop-bot --since 15m 2>&1 | "
        "grep -E 'SUB_REFRESH_JITTER|NameError.*SUB_REFRESH' || true"
    )
    if out.strip():
        print("WARN: old errors still in 15m window:")
        print(out[:2000])
    else:
        print("OK: no SUB_REFRESH_JITTER NameError in last 15m")

    code, out = ssh(
        "docker logs remna-shop-bot --since 5m 2>&1 | tail -15"
    )
    print("--- recent logs ---")
    print(out[-1500:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
