#!/usr/bin/env python3
"""P3-FLOW-14: validate web/portal bundle (ru.json + assets)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORTAL = ROOT / "web" / "portal"
RU = PORTAL / "content" / "ru.json"

REQUIRED_FILES = [
    PORTAL / "index.html",
    PORTAL / "setup.html",
    PORTAL / "guide.html",
    PORTAL / "help" / "errors" / "index.html",
    PORTAL / "assets" / "errors.js",
    PORTAL / "assets" / "portal.css",
    PORTAL / "assets" / "portal.js",
    PORTAL / "assets" / "setup.js",
    PORTAL / "assets" / "guide.js",
    PORTAL / "media" / "ios-first-connect.gif",
    PORTAL / "media" / "android-first-connect.gif",
    RU,
]

DEVICE_IDS = {"iphone", "android", "windows", "mac"}


def main() -> int:
    errors: list[str] = []
    for p in REQUIRED_FILES:
        if not p.is_file():
            errors.append(f"missing: {p.relative_to(ROOT)}")

    if RU.is_file():
        try:
            doc = json.loads(RU.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"ru.json invalid: {e}")
            doc = {}
        devices = doc.get("devices") or []
        ids = {d.get("id") for d in devices if isinstance(d, dict)}
        if ids != DEVICE_IDS:
            errors.append(f"devices must be {DEVICE_IDS}, got {ids}")
        note = (doc.get("home") or {}).get("devices_note", "")
        if "Windows" not in note or "Mac" not in note:
            errors.append("home.devices_note must mention Windows and Mac")
        happ = (doc.get("happ") or {}).get("phone_and_pc", "")
        if "Happ" not in happ:
            errors.append("happ.phone_and_pc must mention Happ")

    html = (PORTAL / "index.html").read_text(encoding="utf-8") if (
        PORTAL / "index.html"
    ).is_file() else ""
    if "device-grid" not in html:
        errors.append("index.html missing device-grid")
    if "site-header" not in html:
        errors.append("index.html missing site-header (HIT-style shell)")
    if "hero-badge" not in html:
        errors.append("index.html missing hero-badge")
    if "hero-stack" not in html:
        errors.append("index.html missing hero-stack (HIT-style)")
    if "events-card" not in html:
        errors.append("index.html missing events-card")
    if "telegram-web-app.js" not in html:
        errors.append("index.html missing telegram-web-app.js (Mini App)")
    if "btn-setup" not in html:
        errors.append("index.html missing btn-setup (browser setup path)")
    setup_html = (PORTAL / "setup.html").read_text(encoding="utf-8") if (
        PORTAL / "setup.html"
    ).is_file() else ""
    if "setup-signup" not in setup_html:
        errors.append("setup.html missing setup-signup (browser trial flow)")
    if "btn-signup-submit" not in setup_html:
        errors.append("setup.html missing btn-signup-submit")
    if RU.is_file():
        doc2 = json.loads(RU.read_text(encoding="utf-8"))
        feats = (doc2.get("home") or {}).get("features") or []
        if len(feats) < 3:
            errors.append("home.features must have 3 hero lines (HIT-style)")
        if not (doc2.get("events") or {}).get("ok_pill"):
            errors.append("events.ok_pill missing in ru.json")
        sv = doc2.get("setup_videos") or {}
        if not sv.get("media_ios_gif") or not sv.get("media_android_gif"):
            errors.append("setup_videos media paths missing in ru.json")
        ue = doc2.get("user_errors") or {}
        ue_items = ue.get("items") or []
        if len(ue_items) < 5:
            errors.append("user_errors.items must have at least 5 entries")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print("PORTAL_BUNDLE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
