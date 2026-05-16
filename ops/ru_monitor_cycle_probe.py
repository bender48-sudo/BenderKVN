#!/usr/bin/env python3
"""Parse last ru-monitor log line for duration_sec (P6-SCALE-06 smoke)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

LOG = Path("/var/log/bvpn-ru-monitor.log")
DUR_RE = re.compile(r"duration_sec=(?P<dur>[0-9.]+)")
TOTAL_RE = re.compile(r"total=(?P<total>\d+)")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else LOG
    if not path.exists():
        print(f"ERROR: log not found: {path}", file=sys.stderr)
        return 1
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        if "duration_sec=" not in line or "status=aborted" in line:
            continue
        dm = DUR_RE.search(line)
        if not dm:
            continue
        dur = float(dm.group("dur"))
        tm = TOTAL_RE.search(line)
        total = int(tm.group("total")) if tm else 0
        print(f"duration_sec={dur} targets={total}")
        if dur > 300:
            print("RU_MONITOR_CYCLE_FAIL: exceeds 300s", file=sys.stderr)
            return 1
        if dur > 240:
            print("RU_MONITOR_CYCLE_WARN: exceeds 240s", file=sys.stderr)
        print("RU_MONITOR_CYCLE_OK")
        return 0
    print("ERROR: no duration_sec line in log", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
