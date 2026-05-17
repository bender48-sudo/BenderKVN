#!/usr/bin/env python3
"""Smoke: browser web trial API (new user without Telegram)."""
from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "ops") not in sys.path:
    sys.path.insert(0, str(ROOT / "ops"))

import site_urls  # noqa: E402


def main() -> int:
    base = site_urls.public_setup_url("").rstrip("/")
    url = f"{base}/api/web-trial"
    email = f"smoke+{int(time.time())}@example.invalid"
    body = json.dumps({"email": email, "phone": ""}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
            code = resp.getcode()
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        code = e.code
        raw = e.read().decode("utf-8", errors="replace")
    print(f"POST {url} email={email} http={code}")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError:
        print(f"WEB_TRIAL_FAIL: not JSON: {raw[:200]}", file=sys.stderr)
        return 1
    if not doc.get("ok") or not doc.get("sub_url"):
        print(f"WEB_TRIAL_FAIL: {doc}", file=sys.stderr)
        return 1
    print("WEB_TRIAL_BROWSER_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
