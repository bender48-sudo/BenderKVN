#!/usr/bin/env python3
"""P3-FLOW-01: public /start bootstrap page returns 200 without VPN."""
from __future__ import annotations

import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "ops") not in sys.path:
    sys.path.insert(0, str(ROOT / "ops"))

import site_urls  # noqa: E402

_SECRET_RE = re.compile(
    r"eyJ[A-Za-z0-9_-]{20,}|REMNA_API_TOKEN|BOT_TOKEN|secret_key",
    re.I,
)
RU = ROOT / "web" / "portal" / "content" / "ru.json"


def _get(url: str, timeout: float = 12.0) -> tuple[int, str]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.getcode(), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def main() -> int:
    urls = [
        site_urls.public_bootstrap_url(),
        site_urls.public_portal_url(),
    ]
    doc = json.loads(RU.read_text(encoding="utf-8"))
    json_needles = [
        doc["home"]["title"],
        doc["buttons"]["connect"],
        doc["buttons"].get("setup_browser", "настройку"),
        doc["home"].get("hero_badge", "60"),
        "Стабильный",
        "Windows",
        "Mac",
        "Happ",
        "events",
    ]
    html_needles = [
        "device-grid",
        "portal.js",
        "brand-mark",
        "hero-badge",
        "hero-stack",
        "events-card",
        "btn-setup",
        "bendervpn",
    ]

    ok = True
    for url in urls:
        code, body = _get(url)
        print(f"bootstrap url={url} http={code}")
        if code != 200:
            print(f"PUBLIC_BOOTSTRAP_FAIL: {url} not 200", file=sys.stderr)
            ok = False
            continue
        for n in html_needles:
            if n not in body:
                print(f"PUBLIC_BOOTSTRAP_FAIL: HTML missing {n!r} on {url}", file=sys.stderr)
                ok = False
        json_url = url.rstrip("/") + "/content/ru.json"
        jcode, jbody = _get(json_url)
        print(f"  content json={json_url} http={jcode}")
        if jcode != 200:
            print(f"PUBLIC_BOOTSTRAP_FAIL: ru.json not 200", file=sys.stderr)
            ok = False
        else:
            for n in json_needles:
                if n not in jbody:
                    print(
                        f"PUBLIC_BOOTSTRAP_FAIL: JSON missing {n!r}",
                        file=sys.stderr,
                    )
                    ok = False
        if _SECRET_RE.search(body) or _SECRET_RE.search(jbody if jcode == 200 else ""):
            print(f"PUBLIC_BOOTSTRAP_FAIL: possible secret on {url}", file=sys.stderr)
            ok = False

    if not ok:
        return 1
    print("PUBLIC_BOOTSTRAP_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
