#!/usr/bin/env python3
"""P2-OPS-BACKUP-01: backup archive name includes timestamp."""
from __future__ import annotations

import sys
from pathlib import Path

H = (Path(__file__).resolve().parent.parent / "bot_src" / "handlers.py").read_text(encoding="utf-8")


def main() -> int:
    if 'backup_name = f"backup_{timestamp}"' not in H:
        print("BACKUP_FILENAME_FAIL: expected backup_YYYYMMDD_HHMMSS pattern", file=sys.stderr)
        return 1
    if "backup_part_aa" in H:
        print("BACKUP_FILENAME_FAIL: legacy static name still present", file=sys.stderr)
        return 1
    print("BACKUP_FILENAME_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
