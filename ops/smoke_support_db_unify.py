#!/usr/bin/env python3
"""P2-CHORE-SUP-01: support_handler uses database.DB_FILE."""
from __future__ import annotations

import sys
from pathlib import Path

SH = (Path(__file__).resolve().parent.parent / "bot_src" / "support_handler.py").read_text(
    encoding="utf-8"
)


def main() -> int:
    if 'Path("/app/data/shop_bot.db")' in SH:
        print("SUPPORT_DB_UNIFY_FAIL: hardcoded DB path", file=sys.stderr)
        return 1
    if "_db_path()" not in SH or "database.DB_FILE" not in SH:
        print("SUPPORT_DB_UNIFY_FAIL: expected database.DB_FILE via _db_path()", file=sys.stderr)
        return 1
    print("SUPPORT_DB_UNIFY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
