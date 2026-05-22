#!/usr/bin/env python3
"""P3-FLOW-04: VPN setup wizard in bot + portal deep-links."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"


def main() -> int:
    kb = (BOT / "keyboards.py").read_text(encoding="utf-8")
    handlers = (BOT / "handlers.py").read_text(encoding="utf-8")
    wizard = BOT / "vpn_setup_wizard.py"
    portal_js = (ROOT / "web" / "portal" / "assets" / "portal.js").read_text(encoding="utf-8")
    config = (BOT / "config.py").read_text(encoding="utf-8")

    required_kb = ("connect_vpn", "wizard_pick_", "create_wizard_device_picker_keyboard")
    required_handlers = ("VpnSetupWizard", "connect_vpn_wizard_start", "wizard_pick_")
    for frag in required_kb:
        if frag not in kb:
            print(f"VPN_SETUP_WIZARD_FAIL: keyboards missing {frag!r}", file=sys.stderr)
            return 1
    for frag in required_handlers:
        if frag not in handlers:
            print(f"VPN_SETUP_WIZARD_FAIL: handlers missing {frag!r}", file=sys.stderr)
            return 1
    if not wizard.is_file():
        print("VPN_SETUP_WIZARD_FAIL: vpn_setup_wizard.py missing", file=sys.stderr)
        return 1
    ast.parse(wizard.read_text(encoding="utf-8"))
    if "telegram_portal_webapp_url" not in config:
        print("VPN_SETUP_WIZARD_FAIL: config missing telegram_portal_webapp_url", file=sys.stderr)
        return 1
    if "?view=devices" in config:
        print(
            "VPN_SETUP_WIZARD_FAIL: WebApp devices must use #devices not ?view= (TG whitelist)",
            file=sys.stderr,
        )
        return 1
    if 'f"{base}#devices"' not in config:
        print("VPN_SETUP_WIZARD_FAIL: config must append #devices to TELEGRAM_WEBAPP_URL", file=sys.stderr)
        return 1
    if "applyRouteFromHash" not in portal_js or "device=(iphone" not in portal_js:
        print("VPN_SETUP_WIZARD_FAIL: portal.js hash routing missing", file=sys.stderr)
        return 1
    for dev in ("iphone", "android", "windows", "mac"):
        if dev not in wizard.read_text(encoding="utf-8"):
            print(f"VPN_SETUP_WIZARD_FAIL: device {dev!r} missing", file=sys.stderr)
            return 1

    print("VPN_SETUP_WIZARD_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
