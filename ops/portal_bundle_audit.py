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
    PORTAL / "assets" / "portal.css",
    PORTAL / "assets" / "portal.js",
    PORTAL / "assets" / "setup.js",
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
    if "brand-mark" not in html:
        errors.append("index.html missing brand-mark (HIT-style shell)")
    if "hero-badge" not in html:
        errors.append("index.html missing hero-badge")
    if "pill-row" not in html:
        errors.append("index.html missing pill-row")
    if "telegram-web-app.js" not in html:
        errors.append("index.html missing telegram-web-app.js (Mini App)")
    if "btn-setup" not in html:
        errors.append("index.html missing btn-setup (browser setup path)")
    setup_html = (PORTAL / "setup.html").read_text(encoding="utf-8") if (
        PORTAL / "setup.html"
    ).is_file() else ""
    if "setup-paste" not in setup_html:
        errors.append("setup.html missing setup-paste (no-Telegram flow)")
    if RU.is_file():
        doc2 = json.loads(RU.read_text(encoding="utf-8"))
        feats = (doc2.get("home") or {}).get("features") or []
        if len(feats) < 3:
            errors.append("home.features must have 3 pills (HIT-style)")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print("PORTAL_BUNDLE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
