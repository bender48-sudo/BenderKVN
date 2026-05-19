#!/usr/bin/env python3
"""P2-RED-SNI-LIVE-01: live subscription must not use deprecated github/bing SNI cluster."""
from __future__ import annotations

import base64
import json
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ops"))
import site_urls  # noqa: E402

# Deprecated cluster (Q058); production template should prefer yandex/neutral RF.
FORBIDDEN_SNI = frozenset(
    {
        "api.github.com",
        "www.bing.com",
        "www.microsoft.com",
        "www.apple.com",
        "github.com",
    }
)
PREFERRED_PREFIX = ("www.yandex.ru", "yandex.ru", "ads.x5.ru")  # RF-neutral decoy set


def _load_sub() -> list[dict]:
    url = site_urls.sub_monitor_probe_url()
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Happ/1.9.4 (iOS)"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        raw = r.read()
    try:
        sub = json.loads(raw)
    except json.JSONDecodeError:
        sub = json.loads(base64.b64decode(raw))
    if isinstance(sub, list) and sub:
        return sub[0].get("outbounds") or []
    if isinstance(sub, dict):
        return sub.get("outbounds") or []
    return []


def main() -> int:
    bad: list[str] = []
    good = 0
    for o in _load_sub():
        rs = o.get("streamSettings") or {}
        sni = (rs.get("realitySettings") or {}).get("serverName") or ""
        if not sni:
            continue
        if sni in FORBIDDEN_SNI:
            bad.append(sni)
        elif any(sni.startswith(p) for p in PREFERRED_PREFIX):
            good += 1
    if bad:
        uniq = sorted(set(bad))
        print(
            f"LIVE_SUB_SNI_FAIL: forbidden SNI in live sub: {', '.join(uniq)}",
            file=sys.stderr,
        )
        print("fix: panel Reality template -> www.yandex.ru (Q102)", file=sys.stderr)
        return 1
    if good == 0:
        print(
            "LIVE_SUB_SNI_FAIL: no preferred yandex/neutral SNI found in reality outbounds",
            file=sys.stderr,
        )
        return 1
    print(f"LIVE_SUB_SNI_OK (preferred-like SNI count={good})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
