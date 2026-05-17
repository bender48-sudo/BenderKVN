#!/usr/bin/env python3
"""P5-COM-01: public HTML status page returns 200 without admin Telegram."""
from __future__ import annotations

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


def _get(url: str, timeout: float = 12.0) -> tuple[int, str]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.getcode(), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def main() -> int:
    url = site_urls.public_status_url()
    code, body = _get(url)
    print(f"public_status url={url} http={code}")
    if code != 200:
        print("PUBLIC_STATUS_FAIL: not HTTP 200", file=sys.stderr)
        return 1
    for needle in ("BenderVPN", "Публичный статус", "Компоненты"):
        if needle not in body:
            print(f"PUBLIC_STATUS_FAIL: missing {needle!r}", file=sys.stderr)
            return 1
    if _SECRET_RE.search(body):
        print("PUBLIC_STATUS_FAIL: page may contain secrets", file=sys.stderr)
        return 1
    print("PUBLIC_STATUS_PAGE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
