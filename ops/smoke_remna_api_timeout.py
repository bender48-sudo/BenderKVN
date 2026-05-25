#!/usr/bin/env python3
"""P2-RED-BOT-TIMEOUT-01: Remna aiohttp ClientTimeout wired from config."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = (ROOT / "bot_src" / "config.py").read_text(encoding="utf-8")
API = (ROOT / "bot_src" / "remnawave_api.py").read_text(encoding="utf-8")
BOT_SRC = ROOT / "bot_src"


def main() -> int:
    if "REMNA_API_TIMEOUT" not in CFG or "REMNA_API_CONNECT_TIMEOUT" not in CFG:
        print("REMNA_API_TIMEOUT_FAIL: config constants missing", file=sys.stderr)
        return 1
    if "remna_client_timeout" not in API or "remna_client_session" not in API:
        print("REMNA_API_TIMEOUT_FAIL: session helpers missing", file=sys.stderr)
        return 1
    if "ClientTimeout" not in API:
        print("REMNA_API_TIMEOUT_FAIL: ClientTimeout not used", file=sys.stderr)
        return 1
    bare = []
    for path in BOT_SRC.rglob("*.py"):
        if path.name == "remnawave_api.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "ClientSession()" in text:
            bare.append(str(path.relative_to(ROOT)))
    if bare:
        print("REMNA_API_TIMEOUT_FAIL: bare ClientSession() in", ", ".join(bare), file=sys.stderr)
        return 1
    ast.parse(CFG)
    ast.parse(API)
    print("REMNA_API_TIMEOUT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
