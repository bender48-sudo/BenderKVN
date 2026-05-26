#!/usr/bin/env python3
"""Smoke: Super_Balancer catch-all uses RELAY outbounds (proxy-5..7), 14 hosts, no observatory."""
from __future__ import annotations

import io
import json
import ssl
import sys
import urllib.request

from subscription_fetch import HAPP_UA, decode_subscription, extract_outbounds, xray_config_root

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import site_urls

RELAY_SELECTOR = ["proxy-5", "proxy-6", "proxy-7"]
SUB_URL = site_urls.sub_monitor_probe_url()


def main() -> int:
    req = urllib.request.Request(SUB_URL, headers={"User-Agent": HAPP_UA})
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=30) as r:
        raw = r.read()
    sub = decode_subscription(raw)
    root = xray_config_root(sub)
    errors: list[str] = []

    balancers = {b.get("tag"): b for b in root.get("routing", {}).get("balancers") or []}
    sb = balancers.get("Super_Balancer")
    if not sb or list(sb.get("selector") or []) != RELAY_SELECTOR:
        errors.append(f"Super_Balancer selector={sb.get('selector') if sb else None}")

    catch = [
        x
        for x in root.get("routing", {}).get("rules") or []
        if x.get("network") and x.get("balancerTag") == "Super_Balancer"
    ]
    if len(catch) != 1:
        errors.append(f"catch-all rules={len(catch)}")

    if root.get("burstObservatory") or root.get("observatory"):
        errors.append("observatory present")

    outbounds = extract_outbounds(sub)
    proxy_count = sum(1 for o in outbounds if str(o.get("tag", "")).startswith("proxy"))
    if proxy_count != 14:
        errors.append(f"proxy outbounds={proxy_count} (want 14)")

    lv0 = (root.get("policy") or {}).get("levels", {}).get("0") or {}
    if lv0.get("uplinkOnly") != 30 or lv0.get("downlinkOnly") != 30:
        errors.append(f"policy uplink/downlink={lv0.get('uplinkOnly')}/{lv0.get('downlinkOnly')}")

    ct = r.headers.get("Content-Type", "")
    if "application/json" not in ct.lower():
        errors.append(f"Content-Type={ct!r}")

    print(f"GET {SUB_URL} -> {len(raw)} bytes")
    print(f"Super_Balancer: {sb.get('selector') if sb else 'MISSING'}")
    print(f"proxy outbounds: {proxy_count}")
    print(f"policy: uplinkOnly={lv0.get('uplinkOnly')} downlinkOnly={lv0.get('downlinkOnly')}")

    if errors:
        print("FAIL:", "; ".join(errors), file=sys.stderr)
        return 1
    print("OK: catch-all RELAY profile on live sub")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
