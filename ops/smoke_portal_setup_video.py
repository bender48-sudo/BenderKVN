#!/usr/bin/env python3
"""P3-FLOW-06: setup guide GIF/video on portal + bot link."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORTAL = ROOT / "web" / "portal"
MEDIA = PORTAL / "media"

REQUIRED_GIFS = (
    MEDIA / "ios-first-connect.gif",
    MEDIA / "android-first-connect.gif",
)


def _http_ok(url: str, timeout: float = 25.0) -> bool:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "BVPN-smoke/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as exc:
        return 200 <= exc.code < 300
    except OSError:
        return False


def main() -> int:
    guide_html = PORTAL / "guide.html"
    guide_js = PORTAL / "assets" / "guide.js"
    ru = PORTAL / "content" / "ru.json"

    for path in (guide_html, guide_js, ru, *REQUIRED_GIFS):
        if not path.is_file():
            print(f"PORTAL_SETUP_VIDEO_FAIL: missing {path.relative_to(ROOT)}", file=sys.stderr)
            return 1

    kb = (ROOT / "bot_src" / "keyboards.py").read_text(encoding="utf-8")
    pl = (ROOT / "bot_src" / "portal_links.py").read_text(encoding="utf-8")
    if "public_guide_url" not in pl:
        print("PORTAL_SETUP_VIDEO_FAIL: portal_links missing public_guide_url", file=sys.stderr)
        return 1
    if "guide.html" not in kb and "public_guide_url(" not in kb:
        print("PORTAL_SETUP_VIDEO_FAIL: keyboards missing guide link", file=sys.stderr)
        return 1

    doc = json.loads(ru.read_text(encoding="utf-8"))
    sv = doc.get("setup_videos") or {}
    for key in ("media_ios_gif", "media_android_gif", "title", "lead"):
        if not sv.get(key):
            print(f"PORTAL_SETUP_VIDEO_FAIL: ru.json setup_videos.{key} empty", file=sys.stderr)
            return 1

    index_html = (PORTAL / "index.html").read_text(encoding="utf-8")
    if "btn-guide" not in index_html or "guide.html" not in index_html:
        print("PORTAL_SETUP_VIDEO_FAIL: index.html missing guide CTA", file=sys.stderr)
        return 1

    sys.path.insert(0, str(ROOT / "ops"))
    try:
        import site_urls

        guide_url = site_urls.public_guide_url()
        gif_ios = site_urls._portal_origin() + sv["media_ios_gif"]
        for url in (guide_url, gif_ios):
            if not _http_ok(url):
                print(f"PORTAL_SETUP_VIDEO_FAIL: HTTP not OK {url}", file=sys.stderr)
                return 1
    except Exception as exc:
        print(f"PORTAL_SETUP_VIDEO_FAIL: probe {exc}", file=sys.stderr)
        return 1

    print("PORTAL_SETUP_VIDEO_OK")
    print("BOT_SETUP_VIDEO_LINK_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
