#!/usr/bin/env python3
"""P6-RED-PAY-08: no DEBUG print leaking crypto api_key."""
from __future__ import annotations

import sys
from pathlib import Path

HANDLERS = Path(__file__).resolve().parent.parent / "bot_src" / "handlers.py"


def main() -> int:
    text = HANDLERS.read_text(encoding="utf-8")
    if "DEBUG [Final]" in text or "string_to_hash}'" in text:
        print("CRYPTO_DEBUG_PRINT_FAIL: debug print still present", file=sys.stderr)
        return 1
    print("CRYPTO_DEBUG_PRINT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
