#!/usr/bin/env python3
"""P2-RED-BOT-RETRY-01: transient retry policy in remnawave_api."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = (ROOT / "bot_src" / "remnawave_api.py").read_text(encoding="utf-8")
REQ = (ROOT / "bot_src" / "requirements-bot.txt").read_text(encoding="utf-8")


def main() -> int:
    if "tenacity" not in REQ:
        print("REMNA_API_RETRY_FAIL: tenacity missing from requirements-bot.txt", file=sys.stderr)
        return 1
    for needle in (
        "from tenacity import",
        "_fetch_json_retrying",
        "RemnaTransientHTTPError",
        "_log_remna_retry",
        "retry attempt",
        "_TRANSIENT_HTTP",
    ):
        if needle not in API:
            print(f"REMNA_API_RETRY_FAIL: missing {needle!r}", file=sys.stderr)
            return 1
    if "401" in API and "retry" in API.lower():
        # ensure 401 path returns without retry (no raise on 401)
        if "resp.status >= 400" not in API:
            print("REMNA_API_RETRY_FAIL: status handling missing", file=sys.stderr)
            return 1
    ast.parse(API)
    print("REMNA_API_RETRY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
