#!/usr/bin/env python3
"""P3-FLOW-05: subscription QR in bot (show_sub_qr) + portal device view."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    handlers = (ROOT / "bot_src" / "handlers.py").read_text(encoding="utf-8")
    keyboards = (ROOT / "bot_src" / "keyboards.py").read_text(encoding="utf-8")
    sub_qr = ROOT / "bot_src" / "subscription_qr.py"
    portal_js = (ROOT / "web" / "portal" / "assets" / "portal.js").read_text(encoding="utf-8")
    setup_js = (ROOT / "web" / "portal" / "assets" / "setup.js").read_text(encoding="utf-8")
    index_html = (ROOT / "web" / "portal" / "index.html").read_text(encoding="utf-8")

    if not sub_qr.is_file():
        print("BOT_SUBSCRIPTION_QR_FAIL: missing subscription_qr.py", file=sys.stderr)
        return 1

    for needle in (
        "show_sub_qr",
        "_fetch_subscription_url",
        "subscription_qr_png",
        "subscriptionUrl",
    ):
        if needle not in handlers:
            print(f"BOT_SUBSCRIPTION_QR_FAIL: handlers missing {needle!r}", file=sys.stderr)
            return 1

    if 'callback_data="show_sub_qr"' not in keyboards:
        print("BOT_SUBSCRIPTION_QR_FAIL: keyboards missing show_sub_qr", file=sys.stderr)
        return 1

    try:
        import qrcode  # noqa: F401

        sys.path.insert(0, str(ROOT / "bot_src"))
        from subscription_qr import subscription_qr_png  # noqa: WPS433

        png = subscription_qr_png("https://example.test/sub/demo")
        if len(png) < 200 or png[:8] != b"\x89PNG\r\n\x1a\n":
            print(
                "BOT_SUBSCRIPTION_QR_FAIL: invalid PNG from subscription_qr_png",
                file=sys.stderr,
            )
            return 1
    except ImportError:
        pass
    except Exception as exc:
        print(f"BOT_SUBSCRIPTION_QR_FAIL: {exc}", file=sys.stderr)
        return 1

    if "device-sub-qr" not in index_html:
        print("PORTAL_SUBSCRIPTION_QR_FAIL: index.html missing device-sub-qr", file=sys.stderr)
        return 1
    if "bvpn_subscription_url" not in setup_js:
        print("PORTAL_SUBSCRIPTION_QR_FAIL: setup.js missing localStorage key", file=sys.stderr)
        return 1
    if "renderDeviceSubscriptionQr" not in portal_js:
        print("PORTAL_SUBSCRIPTION_QR_FAIL: portal.js missing QR render", file=sys.stderr)
        return 1
    if "qrcode.min.js" not in index_html:
        print("PORTAL_SUBSCRIPTION_QR_FAIL: index.html missing qrcode lib", file=sys.stderr)
        return 1

    ru = json.loads((ROOT / "web" / "portal" / "content" / "ru.json").read_text(encoding="utf-8"))
    dq = ru.get("device_qr") or {}
    if not dq.get("title") or not dq.get("hint"):
        print("PORTAL_SUBSCRIPTION_QR_FAIL: ru.json device_qr incomplete", file=sys.stderr)
        return 1

    print("BOT_SUBSCRIPTION_QR_OK")
    print("PORTAL_SUBSCRIPTION_QR_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
