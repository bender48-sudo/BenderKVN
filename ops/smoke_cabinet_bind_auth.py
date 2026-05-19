#!/usr/bin/env python3
"""P3-RED-CABINET-02: cabinet must not expose bind_url on email lookup."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CABINET = ROOT / "bot_src" / "portal_cabinet.py"


def main() -> int:
    text = CABINET.read_text(encoding="utf-8")
    ast.parse(text)
    if "bind_url" in text:
        print("CABINET_BIND_AUTH_FAIL: bind_url still in portal_cabinet.py", file=sys.stderr)
        return 1
    if "needs_telegram_bind" not in text:
        print("CABINET_BIND_AUTH_FAIL: missing needs_telegram_bind", file=sys.stderr)
        return 1
    print("CABINET_BIND_AUTH_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
