#!/usr/bin/env python3
"""Verify Prisma pool limits in AMS /opt/remnawave/.env (P6-RED-PG-01)."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

AMS = "root@168.100.11.140"
SSH = [
    "ssh",
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=40",
    "-p",
    "3344",
    "-i",
    str(Path.home() / ".ssh" / "id_ed25519"),
    AMS,
    "grep -E '^DATABASE_URL=' /opt/remnawave/.env | head -1",
]


def main() -> int:
    try:
        line = subprocess.check_output(SSH, text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as e:
        print(f"FAIL: ssh: {e.output if hasattr(e, 'output') else e}", file=sys.stderr)
        return 1

    if "connection_limit=" not in line:
        print("FAIL: DATABASE_URL missing connection_limit=", file=sys.stderr)
        print(line[:120], file=sys.stderr)
        return 1

    m = re.search(r"connection_limit=(\d+)", line)
    if not m:
        print("FAIL: could not parse connection_limit", file=sys.stderr)
        return 1
    limit = int(m.group(1))
    if limit < 5 or limit > 50:
        print(f"FAIL: connection_limit={limit} outside expected 5..50", file=sys.stderr)
        return 1

    print(f"OK: DATABASE_URL connection_limit={limit}")
    print("PG_POOL_LIMITS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
