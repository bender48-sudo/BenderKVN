#!/usr/bin/env python3
"""Verify dual ops channels: HTTPS status mirror + Telegram API reachability (P2-RED-BOOT-01)."""
from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "ops") not in sys.path:
    sys.path.insert(0, str(ROOT / "ops"))

import site_urls  # noqa: E402


def _get(url: str, timeout: float = 10.0) -> tuple[int, bytes]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.getcode(), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main() -> int:
    mirror_url = site_urls.status_mirror_url()
    ok = True

    code, body = _get(mirror_url)
    print(f"https_mirror url={mirror_url} http={code}")
    if code != 200:
        print("STATUS_CHANNEL_FAIL: mirror not HTTP 200", file=sys.stderr)
        ok = False
    else:
        try:
            doc = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            print("STATUS_CHANNEL_FAIL: mirror invalid JSON", file=sys.stderr)
            ok = False
        else:
            updated = doc.get("updated_at", "")
            print(f"mirror overall={doc.get('overall')} updated_at={updated}")
            try:
                ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - ts).total_seconds()
                if age > 600:
                    print(
                        f"STATUS_CHANNEL_WARN: mirror stale {age:.0f}s (>600)",
                        file=sys.stderr,
                    )
            except ValueError:
                print("STATUS_CHANNEL_WARN: bad updated_at", file=sys.stderr)

    tg_code, _ = _get("https://api.telegram.org/", timeout=8.0)
    print(f"telegram_api http={tg_code}")
    if tg_code not in (200, 301, 302, 404):
        print("STATUS_CHANNEL_WARN: telegram API not reachable from this network", file=sys.stderr)
    else:
        print("telegram_api=reachable")

    if not ok:
        return 1
    print("STATUS_CHANNELS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
