#!/usr/bin/env python3
"""Q085: aggregate TSPU red-team smokes (report inputs, not a full re-audit)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"

SCRIPTS = (
    "transport_mux_audit.py",
    "tspu_block_probe.py",
    "smoke_sub_edge_port.py",
    "portal_bundle_audit.py",
)


def _run(name: str) -> int:
    path = OPS / name
    print(f"--- {name} ---", flush=True)
    r = subprocess.run([sys.executable, str(path)], cwd=ROOT)
    return r.returncode


def main() -> int:
    failed = []
    for script in SCRIPTS:
        if _run(script) != 0:
            failed.append(script)
    if failed:
        print(f"TSPU_REDTEAM_FAIL: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("TSPU_REDTEAM_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
