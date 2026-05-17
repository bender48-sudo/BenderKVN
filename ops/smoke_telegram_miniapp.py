#!/usr/bin/env python3
"""P3-FLOW-12: portal URL serves Mini App bundle (telegram-web-app.js + ru.json)."""
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
    r"eyJ[A-Za-z0-9_-]{20,}|REMNA_API_TOKEN|BOT_TOKEN",
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
    url = site_urls.telegram_webapp_url()
    doc = json.loads(RU.read_text(encoding="utf-8"))
    json_needles = [
        doc["home"]["title"],
        doc["buttons"]["connect"],
        "Windows",
        "Mac",
        "Happ",
    ]
    html_needles = [
        "telegram-web-app.js",
        "portal.js",
        "device-grid",
        "btn-connect",
    ]

    code, body = _get(url)
    print(f"miniapp url={url} http={code}")
    if code != 200:
        print("TELEGRAM_MINIAPP_FAIL: portal not 200", file=sys.stderr)
        return 1
    for n in html_needles:
        if n not in body:
            print(f"TELEGRAM_MINIAPP_FAIL: HTML missing {n!r}", file=sys.stderr)
            return 1
    if _SECRET_RE.search(body):
        print("TELEGRAM_MINIAPP_FAIL: page may leak secrets", file=sys.stderr)
        return 1

    json_url = url.rstrip("/") + "/content/ru.json"
    jcode, jbody = _get(json_url)
    print(f"  content json={json_url} http={jcode}")
    if jcode != 200:
        print("TELEGRAM_MINIAPP_FAIL: ru.json not 200", file=sys.stderr)
        return 1
    for n in json_needles:
        if n not in jbody:
            print(f"TELEGRAM_MINIAPP_FAIL: JSON missing {n!r}", file=sys.stderr)
            return 1

    bootstrap = site_urls.public_bootstrap_url()
    bcode, bbody = _get(bootstrap)
    print(f"bootstrap url={bootstrap} http={bcode}")
    if bcode != 200 or doc["home"]["title"] not in bbody:
        print("TELEGRAM_MINIAPP_FAIL: bootstrap diverges from portal", file=sys.stderr)
        return 1

    print("TELEGRAM_MINIAPP_PORTAL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
