#!/usr/bin/env python3
"""P6-RED-PAY-07: SKIP_API_VERIFY must not be enabled on prod smoke hosts."""
from __future__ import annotations

import os
import sys


def main() -> int:
    if os.getenv("YOOKASSA_WEBHOOK_SKIP_API_VERIFY", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        print("YOOKASSA_SKIP_VERIFY_FAIL: flag enabled in environment", file=sys.stderr)
        return 1
    auth = open(
        os.path.join(os.path.dirname(__file__), "..", "bot_src", "webhook_server", "auth.py"),
        encoding="utf-8",
    ).read()
    if "logger.critical" not in auth or "YOOKASSA_WEBHOOK_SKIP_API_VERIFY" not in auth:
        print("YOOKASSA_SKIP_VERIFY_FAIL: critical log on skip missing", file=sys.stderr)
        return 1
    print("YOOKASSA_SKIP_VERIFY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
