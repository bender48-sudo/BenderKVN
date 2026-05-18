#!/usr/bin/env python3
"""P2-OPS-REMNA-KEY-01: no PUBLIC_KEY_PLACEHOLDER in VLESS URI builder."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = (ROOT / "bot_src" / "remnawave_api.py").read_text(encoding="utf-8")


def main() -> int:
    if "PUBLIC_KEY_PLACEHOLDER" in SRC:
        print("REMNA_PUBLIC_KEY_FAIL: placeholder still used", file=sys.stderr)
        return 1
    if "REMNA_PUBLIC_KEY missing" not in SRC:
        print("REMNA_PUBLIC_KEY_FAIL: missing fail-fast log", file=sys.stderr)
        return 1
    if "get_api_token" not in SRC:
        print("REMNA_PUBLIC_KEY_FAIL: lazy token helper missing", file=sys.stderr)
        return 1
    print("REMNA_PUBLIC_KEY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
