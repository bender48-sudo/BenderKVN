#!/usr/bin/env python3
"""P1-PRO-CLIENT-V2RAYN-01."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    doc = ROOT / "docs" / "CLIENT-V2RAYN.md"
    if not doc.is_file():
        print("V2RAYN_CLIENT_FAIL: missing CLIENT-V2RAYN.md", file=sys.stderr)
        return 1
    ru = json.loads((ROOT / "web" / "portal" / "content" / "ru.json").read_text(encoding="utf-8"))
    win = next((d for d in ru.get("devices", []) if d.get("id") == "windows"), None)
    if not win or "v2rayN" not in json.dumps(win, ensure_ascii=False):
        print("V2RAYN_CLIENT_FAIL: portal windows block missing v2rayN", file=sys.stderr)
        return 1
    print("V2RAYN_CLIENT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
