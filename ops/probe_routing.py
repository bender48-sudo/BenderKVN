"""Probe one active user's subscription and inspect the generated xray routing.

Used to verify that RU-BYPASS routing changes (extra direct domains, block-rule
without max.ru/oneme.ru) are visible in the rendered config returned to clients.
"""
from __future__ import annotations

import io
import json
import random
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TOKEN = (ROOT / ".secrets" / "panel-token.txt").read_text(encoding="ascii").strip()

PANEL = site_urls.PANEL_URL
SUB = site_urls.SUB_PUBLIC_ORIGIN
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


MATCHER_KEYS = (
    "domain",
    "domains",
    "ip",
    "port",
    "sourcePort",
    "network",
    "inboundTag",
    "protocol",
    "user",
    "sourceGeoip",
)


def _nonempty(v: object) -> bool:
    if v is None:
        return False
    if isinstance(v, (list, tuple, dict, set)):
        return len(v) > 0
    if isinstance(v, str):
        return len(v.strip()) > 0
    return True


def routing_rule_has_matchers(r: dict) -> bool:
    return any(_nonempty(r.get(k)) for k in MATCHER_KEYS)


def degenerate_rule_count(rules: list) -> int:
    return sum(
        1
        for r in rules
        if isinstance(r, dict)
        and (r.get("outboundTag") or r.get("balancerTag"))
        and not routing_rule_has_matchers(r)
    )


def main() -> None:
    users_body = fetch(f"{PANEL}/api/users?limit=200&start=0",
                       {"Authorization": f"Bearer {TOKEN}"})
    users = json.loads(users_body)["response"]["users"]
    active = [u for u in users
              if u.get("status") == "ACTIVE"
              and (u.get("shortUuid") or u.get("subscriptionUuid"))]
    print(f"active users: {len(active)} / total: {len(users)}")
    sample = random.sample(active, k=min(3, len(active)))

    UAS = [
        ("Happ/1.9.4 (iOS)", "happ"),
        ("Hiddify/2.5.0 (iOS)", "hiddify"),
        ("Streisand/1.6.50 (iOS)", "streisand"),
    ]

    for u in sample:
        short = u.get("shortUuid") or u.get("subscriptionUuid")
        username = u.get("username") or short
        print(f"\n=== user: {username} ===")
        cfg = None
        used_ua = None
        for ua, _label in UAS:
            raw = fetch(f"{SUB}/api/sub/{short}", {"User-Agent": ua})
            text = raw.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(text)
                cfg = parsed
                used_ua = ua
                print(f"  parsed as JSON via UA={ua}")
                break
            except json.JSONDecodeError:
                continue
        if cfg is None:
            print("  no UA returned JSON; try /happ endpoint")
            raw = fetch(f"{SUB}/api/sub/{short}/happ", {"User-Agent": "Happ/1.9.4 (iOS)"})
            text = raw.decode("utf-8", errors="replace")
            try:
                cfg = json.loads(text)
                used_ua = "/happ endpoint"
            except json.JSONDecodeError:
                print(f"  still not JSON. first 300: {text[:300]!r}")
                continue
        # v2rayN UA returns config as raw text-config, but might be wrapped.
        if isinstance(cfg, list) and cfg and isinstance(cfg[0], dict):
            cfg = cfg[0]
        if not isinstance(cfg, dict):
            print(f"  unexpected type: {type(cfg)}")
            continue
        routing = cfg.get("routing", {})
        rules = routing.get("rules", [])
        print(f"  routing.rules count: {len(rules)}")
        for i, r in enumerate(rules):
            doms = r.get("domain") or []
            ips = r.get("ip") or []
            tag = r.get("outboundTag") or r.get("balancerTag")
            sig = []
            if doms:
                sig.append(f"domain={len(doms)}")
            if ips:
                sig.append(f"ip={len(ips)}")
            if r.get("protocol"):
                sig.append(f"protocol={r['protocol']}")
            if r.get("network"):
                sig.append(f"network={r['network']}")
            print(f"    R{i}: {' '.join(sig)} -> {tag}")
            if doms:
                print(f"        domains: {doms}")
        degen = degenerate_rule_count(rules)
        print(f"  degenerate rules (Xray 'no effective fields'): {degen}")
        if degen:
            print("  *** run: python ops/ru_bypass_routing.py --strip-degenerate-only --apply")
        outs = cfg.get("outbounds", [])
        proxy_count = sum(1 for o in outs if o.get("tag", "").startswith("proxy"))
        print(f"  outbounds total: {len(outs)} (proxy*: {proxy_count})")


if __name__ == "__main__":
    main()
