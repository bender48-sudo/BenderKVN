#!/usr/bin/env python3
"""P2-OPS-SCHED-01: expiry notify uses UTC-aware comparison."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SH = (ROOT / "bot_src" / "scheduler.py").read_text(encoding="utf-8")

def main() -> int:
    if "now(timezone.utc)" not in SH or "remote_dt - now_utc" not in SH.replace(" ", ""):
        # allow multiline
        if "now_utc = datetime.now(timezone.utc)" not in SH:
            print("EXPIRY_TZ_FAIL: missing UTC-aware now", file=sys.stderr)
            return 1
    if "replace(tzinfo=None)" in SH and "remote_local" in SH:
        print("EXPIRY_TZ_FAIL: legacy naive comparison still present", file=sys.stderr)
        return 1
    print("EXPIRY_TZ_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
