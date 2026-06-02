#!/usr/bin/env python3
"""Static smoke: topup flow exposes YooKassa when credentials are configured."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    kb_src = (ROOT / "bot_src" / "keyboards.py").read_text(encoding="utf-8")
    if "pay_yookassa_topup_{topup_id}" not in kb_src:
        print("FAIL: keyboards missing yookassa topup callback", file=sys.stderr)
        return 1
    src = (ROOT / "bot_src" / "handlers.py").read_text(encoding="utf-8")
    if "pay_yookassa_topup_handler" not in src:
        print("FAIL: pay_yookassa_topup_handler missing", file=sys.stderr)
        return 3
    if '"t": "topup"' not in src or '"amount": amount_value' not in src:
        print("FAIL: topup metadata for YooKassa missing", file=sys.stderr)
        return 4
    print("OK: YooKassa topup UI wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
