#!/usr/bin/env python3
"""Valkey/Redis memory policy audit on AMS (P6-SCALE-05)."""
from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="bvpn-ams")
    ap.add_argument("--container", default="remnawave-redis")
    args = ap.parse_args()

    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        args.host,
        f"docker exec {args.container} valkey-cli INFO memory; "
        f"echo '---'; "
        f"docker exec {args.container} valkey-cli CONFIG GET maxmemory; "
        f"docker exec {args.container} valkey-cli CONFIG GET maxmemory-policy",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    out = proc.stdout
    policy = "unknown"
    maxmem = "unknown"
    used = "unknown"
    for line in out.splitlines():
        if line.startswith("used_memory_human:"):
            used = line.split(":", 1)[1].strip()
        if line == "maxmemory-policy":
            continue
        if line.startswith("allkeys-") or line in ("noeviction", "volatile-lru"):
            policy = line.strip()
        if line.isdigit() and maxmem == "unknown":
            pass
    # Parse CONFIG GET pairs
    lines = [l.strip() for l in out.splitlines()]
    for i, line in enumerate(lines):
        if line == "maxmemory-policy" and i + 1 < len(lines):
            policy = lines[i + 1]
        if line == "maxmemory" and i + 1 < len(lines):
            maxmem = lines[i + 1]

    print(f"used_memory_human={used} maxmemory={maxmem} maxmemory-policy={policy}")
    ok = policy == "allkeys-lru" and maxmem not in ("0", "unknown")
    if ok:
        print("VALKEY_MEMORY_AUDIT_OK")
        return 0
    print("VALKEY_MEMORY_AUDIT_WARN: expected allkeys-lru + maxmemory>0", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
