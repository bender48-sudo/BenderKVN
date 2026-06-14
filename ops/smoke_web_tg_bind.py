#!/usr/bin/env python3
"""Smoke: web trial → Telegram bind (P3-FLOW-16 MVP)."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"


def main() -> int:
    for name in ("web_tg_bind.py", "web_trial_db.py", "portal_web_trial.py"):
        p = BOT / name
        if not p.is_file():
            print(f"WEB_TG_BIND_FAIL: missing {name}", file=sys.stderr)
            return 1
        ast.parse(p.read_text(encoding="utf-8"))

    handlers = (BOT / "handlers.py").read_text(encoding="utf-8")
    if "_apply_web_bind" not in handlers:
        print("WEB_TG_BIND_FAIL: handlers missing _apply_web_bind", file=sys.stderr)
        return 1
    if "bind_token" not in (BOT / "web_trial_db.py").read_text(encoding="utf-8"):
        print("WEB_TG_BIND_FAIL: web_trial_db missing bind_token", file=sys.stderr)
        return 1
    setup = (ROOT / "ops" / "setup_verify_service.py").read_text(encoding="utf-8")
    if "bind_url" not in setup:
        print("WEB_TG_BIND_FAIL: setup_verify missing bind_url passthrough", file=sys.stderr)
        return 1
    bind_js = ROOT / "web" / "portal" / "assets" / "bind-handoff.js"
    if not bind_js.is_file():
        print("WEB_TG_BIND_FAIL: missing bind-handoff.js", file=sys.stderr)
        return 1
    setup_html = (ROOT / "web" / "portal" / "setup.html").read_text(encoding="utf-8")
    for needle in ("bind-handoff.js", "btn-copy-bind-start", "btn-bind-tg-retry"):
        if needle not in setup_html:
            print(f"WEB_TG_BIND_FAIL: setup.html missing {needle!r}", file=sys.stderr)
            return 1
    setup_js = (ROOT / "web" / "portal" / "assets" / "setup.js").read_text(encoding="utf-8")
    if "web_tg_bind_rendered" not in setup_js:
        print("WEB_TG_BIND_FAIL: setup.js missing web_tg_bind_rendered", file=sys.stderr)
        return 1
    print("WEB_TG_BIND_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
