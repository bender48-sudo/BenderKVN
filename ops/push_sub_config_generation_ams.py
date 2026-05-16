#!/usr/bin/env python3
"""Push sub_config_generation into remna-shop-bot SQLite on AMS (via docker exec)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "168.100.11.140"
PORT = "3344"
SSH_KEY = Path.home() / ".ssh" / "id_ed25519"


def _ssh_py(generation: int, reason: str) -> int:
    reason_lit = json.dumps(reason, ensure_ascii=False)
    remote_py = (
        "from shop_bot.data_manager.database import initialize_db, set_sub_config_generation; "
        "initialize_db(); "
        f"set_sub_config_generation({generation}, {reason_lit}); "
        f"print('sub_config_generation={generation}')"
    )
    remote_cmd = f"docker exec remna-shop-bot python -c {json.dumps(remote_py)}"
    cmd = [
        "ssh",
        "-i",
        str(SSH_KEY),
        "-p",
        PORT,
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=40",
        "-o",
        "StrictHostKeyChecking=accept-new",
        f"root@{HOST}",
        remote_cmd,
    ]
    print("[push] ssh docker exec remna-shop-bot ...")
    return subprocess.call(cmd)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generation", type=int, required=True)
    ap.add_argument("--reason", default="")
    args = ap.parse_args()
    rc = _ssh_py(args.generation, args.reason)
    if rc != 0:
        sys.exit(rc)


if __name__ == "__main__":
    main()
