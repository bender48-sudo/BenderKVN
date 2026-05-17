#!/usr/bin/env python3
"""P3-FLOW-03: bot portal link helpers + keyboard labels."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"

REQUIRED_FRAGMENTS = (
    "(Mini App)",
    "setup_url_for_sub",
    "_add_portal_link_buttons",
    "PUBLIC_BOOTSTRAP_URL",
)


def main() -> int:
    kb = (BOT / "keyboards.py").read_text(encoding="utf-8")
    for frag in REQUIRED_FRAGMENTS:
        if frag not in kb:
            print(f"BOT_PORTAL_LINKS_FAIL: keyboards missing {frag!r}", file=sys.stderr)
            return 1

    portal_links = BOT / "portal_links.py"
    if not portal_links.is_file():
        print("BOT_PORTAL_LINKS_FAIL: portal_links.py missing", file=sys.stderr)
        return 1

    ast.parse(portal_links.read_text(encoding="utf-8"))

    sys.path.insert(0, str(BOT))
    # Import as module file (not shop_bot package layout in repo)
    import importlib.util

    spec = importlib.util.spec_from_file_location("portal_links", portal_links)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    sample = "https://p4n7q.conntest.xyz:2053/api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2"
    sid = mod.short_id_from_sub_url(sample)
    if sid != "JLCF43RGjyq4ML78Qcsbq7Kf2":
        print(f"BOT_PORTAL_LINKS_FAIL: short_id parse got {sid!r}", file=sys.stderr)
        return 1

    if not mod.PUBLIC_BOOTSTRAP_URL.startswith("https://"):
        print("BOT_PORTAL_LINKS_FAIL: PUBLIC_BOOTSTRAP_URL invalid", file=sys.stderr)
        return 1

    print("BOT_PORTAL_LINKS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
