#!/usr/bin/env python3
"""P2-RED-DISCOVERY-PORT-01: no user-facing :2053 in bot_src or FAQ."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATHS = [
    ROOT / "bot_src",
    ROOT / "docs" / "FAQ.md",
]


def main() -> int:
    bad: list[str] = []
    for base in PATHS:
        if base.is_file():
            files = [base]
        else:
            files = list(base.rglob("*.py")) + list(base.rglob("*.md"))
        for f in files:
            if "__pycache__" in str(f):
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            if ":2053" in text:
                bad.append(str(f.relative_to(ROOT)))
    if bad:
        print("DISCOVERY_PORT_FAIL: :2053 in " + ", ".join(bad), file=sys.stderr)
        return 1
    print("DISCOVERY_PORT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
