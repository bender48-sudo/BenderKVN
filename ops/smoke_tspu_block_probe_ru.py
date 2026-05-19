#!/usr/bin/env python3
"""P1-RED-TSPU-BLOCK-RU-01: relay RU probe wiring (check.py stdin path)."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"


def main() -> int:
    for name in (
        "tspu_block_probe_ru.py",
        "run_tspu_block_probe_ru.sh",
        "install_tspu_ru_probe_cron.sh",
    ):
        p = OPS / name
        if not p.is_file():
            print(f"TSPU_BLOCK_PROBE_RU_FAIL: missing {name}", file=sys.stderr)
            return 1
    py = (OPS / "tspu_block_probe_ru.py").read_text(encoding="utf-8")
    ast.parse(py)
    if "check.py" not in py and "json.dumps(targets)" not in py:
        print("TSPU_BLOCK_PROBE_RU_FAIL: must use relay check.py stdin", file=sys.stderr)
        return 1
    if "python3 tspu_block_probe" in (OPS / "run_tspu_block_probe_ru.sh").read_text():
        print("TSPU_BLOCK_PROBE_RU_FAIL: shell must not remote-exec tspu_block_probe", file=sys.stderr)
        return 1
    print("TSPU_BLOCK_PROBE_RU_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
