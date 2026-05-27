#!/usr/bin/env python3
"""P3-RED-SUP-01: support group replies only from SUPPORT_STAFF_IDS / admin."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"


def main() -> int:
    sh = (BOT / "support_handler.py").read_text(encoding="utf-8")
    sa = (BOT / "support_auth.py").read_text(encoding="utf-8")

    if "from shop_bot.support_auth import is_authorized_support_staff" not in sh:
        print(
            "SUPPORT_REPLY_AUTHZ_FAIL: support_handler must import is_authorized_support_staff",
            file=sys.stderr,
        )
        return 1

    for needle in (
        "is_authorized_support_staff",
        "SUPPORT_STAFF_IDS",
        "Ignored support reply from unauthorized",
    ):
        if needle not in sh and needle not in sa:
            print(f"SUPPORT_REPLY_AUTHZ_FAIL: missing {needle!r}", file=sys.stderr)
            return 1

    print("SUPPORT_REPLY_AUTHZ_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
