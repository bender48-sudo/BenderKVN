#!/usr/bin/env python3
"""P1-RED-TSPU-BLOCK-RU-01: RU relay cron wrapper exists and is wired."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_SH = ROOT / "ops" / "run_tspu_block_probe_ru.sh"
INSTALL = ROOT / "ops" / "install_tspu_ru_probe_cron.sh"


def main() -> int:
    for p in (RUN_SH, INSTALL):
        if not p.is_file():
            print(f"TSPU_BLOCK_PROBE_RU_FAIL: missing {p.name}", file=sys.stderr)
            return 1
    run = RUN_SH.read_text(encoding="utf-8")
    if "tspu_block_probe.py" not in run or "RU_RELAY_HOST" not in run:
        print("TSPU_BLOCK_PROBE_RU_FAIL: run script incomplete", file=sys.stderr)
        return 1
    print("TSPU_BLOCK_PROBE_RU_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
