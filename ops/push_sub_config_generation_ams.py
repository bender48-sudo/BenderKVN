#!/usr/bin/env python3
"""Push sub_config_generation into remna-shop-bot SQLite on AMS (via docker exec).

SSH: prefers ``ssh bvpn-ams`` from ~/.ssh/config; else ``bvpn_ams_ed25519``
(P1-RED-SSH-01). Legacy ``id_ed25519`` only as last fallback — see
``docs/SSH-KEY-INVENTORY.md``.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _ams_ssh_base() -> list[str]:
    """Build ssh argv for AMS root (host alias or explicit key)."""
    if shutil.which("ssh"):
        probe = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "bvpn-ams", "echo ok"],
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0 and "ok" in (probe.stdout or ""):
            return [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=40",
                "bvpn-ams",
            ]

    ssh_dir = Path.home() / ".ssh"
    for name in ("bvpn_ams_ed25519", "id_ed25519"):
        key = ssh_dir / name
        if key.is_file():
            return [
                "ssh",
                "-i",
                str(key),
                "-p",
                "3344",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=40",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-o",
                "IdentitiesOnly=yes",
                "root@168.100.11.140",
            ]

    raise SystemExit(
        "No AMS SSH: add Host bvpn-ams to ~/.ssh/config (ssh/config.example) "
        "or install ~/.ssh/bvpn_ams_ed25519 — docs/SSH-KEY-INVENTORY.md"
    )


def _ssh_py(generation: int, reason: str) -> int:
    reason_lit = json.dumps(reason, ensure_ascii=False)
    remote_py = (
        "from shop_bot.data_manager.database import initialize_db, set_sub_config_generation; "
        "initialize_db(); "
        f"set_sub_config_generation({generation}, {reason_lit}); "
        f"print('sub_config_generation={generation}')"
    )
    remote_cmd = f"docker exec remna-shop-bot python -c {json.dumps(remote_py)}"
    cmd = _ams_ssh_base() + [remote_cmd]
    print("[push] ssh docker exec remna-shop-bot ...")
    return subprocess.call(cmd)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generation", type=int, required=True)
    ap.add_argument("--reason", default="")
    args = ap.parse_args()
    rc = _ssh_py(args.generation, args.reason)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
