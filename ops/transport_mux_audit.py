#!/usr/bin/env python3
"""P2-RED-MUX-01: audit subscription outbounds for primary + alt transport profiles.

Exit 0 when active users have both profiles in subscription (see docs/TRANSPORT-MUX-MATRIX.md).
"""
from __future__ import annotations

import argparse
import base64
import json
import random
import ssl
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

import site_urls

ROOT = Path(__file__).resolve().parent.parent
try:
    from ops.panel_client import PanelClient
except ImportError:
    sys.path.insert(0, str(ROOT / "ops"))
    from panel_client import PanelClient  # type: ignore

LV_IP = "176.126.162.158"
AMS_IP = "168.100.11.140"
NL_IP = "91.90.192.17"
RELAY_IP = site_urls.RU_RELAY_HOST
SUB = site_urls.SUB_PUBLIC_ORIGIN

_HAPP_UA = "Happ/1.9.4 (iOS)"


def _node_port_label(addr: str, port: int) -> str:
    if addr == LV_IP:
        return "LV", port
    if addr == NL_IP:
        return "NL", port
    if addr == AMS_IP:
        return "AMS", port
    if addr == RELAY_IP:
        if port == 443:
            return "RELAY", 443
        if port == 9443:
            return "RELAY", 9443
        if port == 8443:
            return "RELAY", 8443
        return "RELAY", port
    return "OTHER", port


def classify_profile(node: str, port: int) -> str | None:
    if node in ("LV", "RELAY") and port == 443:
        return "primary"
    if node == "NL" or (node == "LV" and port == 8443) or (node == "RELAY" and port in (9443, 8443)):
        return "alt"
    return None


def parse_outbounds(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8", errors="replace")
    try:
        sub = json.loads(text)
    except json.JSONDecodeError:
        sub = json.loads(base64.b64decode(text))
    if isinstance(sub, list) and sub and isinstance(sub[0], dict):
        return sub[0].get("outbounds") or []
    if isinstance(sub, dict):
        return sub.get("outbounds") or []
    return []


def profiles_in_sub(raw: bytes) -> tuple[set[str], Counter[str]]:
    profiles: set[str] = set()
    ob_by_profile: Counter[str] = Counter()
    for o in parse_outbounds(raw):
        s = o.get("settings") or {}
        vnext = s.get("vnext")
        if not isinstance(vnext, list) or not vnext:
            continue
        addr = vnext[0].get("address")
        port = vnext[0].get("port")
        if not addr or port is None:
            continue
        node, p = _node_port_label(str(addr), int(port))
        prof = classify_profile(node, p)
        if prof:
            profiles.add(prof)
            ob_by_profile[prof] += 1
    return profiles, ob_by_profile


def fetch_sub(short: str, ctx: ssl.SSLContext) -> bytes:
    url = f"{SUB}/api/sub/{short}"
    req = urllib.request.Request(url, headers={"User-Agent": _HAPP_UA})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        return r.read()


def main() -> int:
    p = argparse.ArgumentParser(description="Transport mux audit (P2-RED-MUX-01)")
    p.add_argument("--sample", type=int, default=20, help="max active users to sample")
    p.add_argument("--json", action="store_true")
    p.add_argument("--min-both-pct", type=float, default=95.0)
    args = p.parse_args()

    client = PanelClient()
    code, data = client.get("/api/users?limit=200&start=0")
    if code != 200:
        print(f"FAIL: users HTTP {code}", file=sys.stderr)
        return 1
    users = (data.get("response") or {}).get("users") or []
    active = [
        u
        for u in users
        if u.get("status") in ("ACTIVE", "active")
        and (u.get("shortUuid") or u.get("subscriptionUuid"))
    ]
    if not active:
        print("FAIL: no active users", file=sys.stderr)
        return 2

    sample = random.sample(active, k=min(args.sample, len(active)))
    ctx = ssl.create_default_context()

    both = 0
    has_primary_n = 0
    has_alt_n = 0
    total_ob_primary = 0
    total_ob_alt = 0
    errors = 0

    for u in sample:
        short = u.get("shortUuid") or u.get("subscriptionUuid")
        try:
            raw = fetch_sub(short, ctx)
            profs, ob_cnt = profiles_in_sub(raw)
        except Exception as e:
            errors += 1
            print(f"warn: sub fetch {short}: {e}", file=sys.stderr)
            continue
        if "primary" in profs:
            has_primary_n += 1
        if "alt" in profs:
            has_alt_n += 1
        if "primary" in profs and "alt" in profs:
            both += 1
        total_ob_primary += ob_cnt.get("primary", 0)
        total_ob_alt += ob_cnt.get("alt", 0)

    n = len(sample) - errors
    if n == 0:
        print("FAIL: no successful sub fetches", file=sys.stderr)
        return 3

    both_pct = 100.0 * both / n
    alt_ob_share = (
        100.0 * total_ob_alt / (total_ob_primary + total_ob_alt)
        if (total_ob_primary + total_ob_alt)
        else 0.0
    )

    report = {
        "active_users": len(active),
        "sampled": n,
        "errors": errors,
        "has_primary_pct": round(100.0 * has_primary_n / n, 1),
        "has_alt_pct": round(100.0 * has_alt_n / n, 1),
        "users_with_both_pct": round(both_pct, 1),
        "alt_outbound_share_pct": round(alt_ob_share, 1),
        "outbounds_primary": total_ob_primary,
        "outbounds_alt": total_ob_alt,
    }

    ok = (
        has_primary_n == n
        and has_alt_n >= int(n * args.min_both_pct / 100.0)
        and both >= int(n * args.min_both_pct / 100.0)
        and total_ob_alt > 0
    )

    if args.json:
        report["ok"] = ok
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"sample={n} has_primary={has_primary_n} has_alt={has_alt_n} "
            f"both={both} ({both_pct:.1f}%) alt_ob_share={alt_ob_share:.1f}%"
        )
        print(f"outbounds: primary={total_ob_primary} alt={total_ob_alt}")

    if not ok:
        print("FAIL: transport mux criteria not met", file=sys.stderr)
        return 4
    print("TRANSPORT_MUX_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
