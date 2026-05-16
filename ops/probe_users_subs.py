"""Sample N users; for each, fetch Happ subscription and count LV/NL/AMS outbounds.

This verifies that the new NL outbounds are visible across users (not just one).
"""
from __future__ import annotations

import base64
import io
import json
import random
import ssl
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TOKEN = (ROOT / ".secrets" / "panel-token.txt").read_text(encoding="ascii").strip()
PANEL = site_urls.PANEL_URL
SUB = site_urls.SUB_PUBLIC_ORIGIN

LV_IP = "176.126.162.158"
AMS_IP = "168.100.11.140"
NL_IP = "91.90.192.17"
RELAY_IP = site_urls.RU_RELAY_HOST

ctx = ssl.create_default_context()


def fetch(url: str, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        return e.read()


def label(addr: str, port: int) -> str:
    if addr == LV_IP:
        return "LV"
    if addr == AMS_IP:
        return "AMS"
    if addr == NL_IP:
        return "NL"
    if addr == RELAY_IP:
        return {443: "LV", 8443: "AMS", 9443: "NL"}.get(port, "RELAY?")
    return "OTHER"


def count(text: str) -> dict[str, int]:
    try:
        sub = json.loads(text)
    except json.JSONDecodeError:
        try:
            sub = json.loads(base64.b64decode(text))
        except Exception:
            return {}
    if isinstance(sub, list) and sub and isinstance(sub[0], dict):
        outbounds = sub[0].get("outbounds") or []
    elif isinstance(sub, dict):
        outbounds = sub.get("outbounds") or []
    else:
        return {}
    c: Counter[str] = Counter()
    for o in outbounds:
        s = o.get("settings") or {}
        vnext = s.get("vnext")
        if isinstance(vnext, list) and vnext:
            v = vnext[0]
            addr = v.get("address")
            port = v.get("port")
        else:
            continue
        if not addr:
            continue
        c[label(addr, port)] += 1
    return dict(c)


def main() -> None:
    body = fetch(f"{PANEL}/api/users?limit=200&start=0", {"Authorization": f"Bearer {TOKEN}"})
    users = json.loads(body)["response"]["users"]
    active = [u for u in users if u.get("status") == "ACTIVE" and (u.get("shortUuid") or u.get("subscriptionUuid"))]
    print(f"active users: {len(active)} / total: {len(users)}")
    sample = random.sample(active, k=min(10, len(active)))

    summary: Counter[str] = Counter()
    print(f"{'user':40s} {'LV':>3s} {'NL':>3s} {'AMS':>4s} {'sum':>4s}")
    for u in sample:
        short = u.get("shortUuid") or u.get("subscriptionUuid")
        raw = fetch(f"{SUB}/api/sub/{short}", {"User-Agent": "Happ/1.9.4 (iOS)"})
        c = count(raw.decode("utf-8", errors="replace"))
        lv = c.get("LV", 0)
        nl = c.get("NL", 0)
        ams = c.get("AMS", 0)
        total = lv + nl + ams
        summary["LV"] += lv
        summary["NL"] += nl
        summary["AMS"] += ams
        username = (u.get("username") or short)[:40]
        print(f"{username:40s} {lv:>3d} {nl:>3d} {ams:>4d} {total:>4d}")
    print()
    print(f"sum across {len(sample)} users: LV={summary['LV']}, NL={summary['NL']}, AMS={summary['AMS']}")


if __name__ == "__main__":
    main()
