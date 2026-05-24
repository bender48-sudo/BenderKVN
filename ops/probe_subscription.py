"""Test a real Happ-format subscription and count outbounds per node.

Steps:
1. List panel users, pick the first active one.
2. Fetch their Happ subscription URL with a Happ User-Agent.
3. Decode the response, count outbounds per node IP (LV/AMS/NL/relay).
4. Validate Content-Type header (Q-VPN-STAB-001).
"""
from __future__ import annotations

import io
import json
import sys
from collections import Counter
from pathlib import Path

import site_urls
from subscription_fetch import (
    HAPP_UA,
    AMS_IP,
    LV_IP,
    NL_IP,
    RELAY_IP,
    decode_subscription,
    extract_outbounds,
    fetch_url,
    outbound_endpoint,
    outbound_network,
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TOKEN = (ROOT / ".secrets" / "panel-token.txt").read_text(encoding="ascii").strip()
PANEL = site_urls.PANEL_URL
SUB = site_urls.SUB_PUBLIC_ORIGIN


def destination_label(addr: str, port: int) -> str:
    if addr == LV_IP:
        return f"LV:{port}"
    if addr == AMS_IP:
        return f"AMS:{port}"
    if addr == NL_IP:
        return f"NL:{port}"
    if addr == RELAY_IP:
        port_map = {443: "RELAY→LV", 8443: "RELAY→AMS", 9443: "RELAY→NL"}
        return port_map.get(port, f"RELAY:{port}")
    return f"OTHER {addr}:{port}"


def main() -> int:
    users_resp = fetch_url(
        f"{PANEL}/api/users?limit=10&start=0",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    if users_resp.status != 200:
        print(f"users HTTP {users_resp.status}: {users_resp.body[:300]!r}", file=sys.stderr)
        return 1
    users_data = json.loads(users_resp.body)
    users = users_data.get("response", {}).get("users") or users_data.get("response") or []
    if not isinstance(users, list):
        print(f"unexpected users payload: {str(users_data)[:300]}", file=sys.stderr)
        return 1
    print(f"users found: {len(users)}")
    if not users:
        print("no users to test against", file=sys.stderr)
        return 1

    pick = None
    for u in users:
        if u.get("status") in ("ACTIVE", "active") and (u.get("shortUuid") or u.get("subscriptionUuid")):
            pick = u
            break
    if pick is None:
        pick = users[0]

    short = pick.get("shortUuid") or pick.get("shortUUID") or pick.get("subscriptionUuid")
    if not short:
        print(f"no shortUuid on user: {str(pick)[:200]}", file=sys.stderr)
        return 1
    print(f"test user: {pick.get('username') or pick.get('uuid')} (short={short})")

    sub_url = f"{SUB}/api/sub/{short}"
    print(f"sub_url: {sub_url}")

    sub_resp = fetch_url(sub_url, headers={"User-Agent": HAPP_UA})
    print(f"Happ GET HTTP {sub_resp.status}, {len(sub_resp.body)} bytes")
    ct_display = sub_resp.content_type or "(missing)"
    print(f"Content-Type: {ct_display}")
    if not sub_resp.content_type_ok:
        print("WARN: Content-Type is not application/json — may contribute to Happ UnknownContentType")
    if sub_resp.status != 200:
        print(f"sub HTTP {sub_resp.status}: {sub_resp.body[:300]!r}", file=sys.stderr)
        return 1

    sub = decode_subscription(sub_resp.body)
    inner = sub[0] if isinstance(sub, list) and sub else sub
    outbounds = extract_outbounds(sub)
    if isinstance(inner, dict):
        print(f"happ-config: remarks={inner.get('remarks')!r}")
    print(f"outbounds: {len(outbounds)}")

    by_label: Counter[str] = Counter()
    by_kind: Counter[str] = Counter()
    for o in outbounds:
        addr, port = outbound_endpoint(o)
        if not addr or port is None:
            continue
        by_label[destination_label(str(addr), int(port))] += 1
        proto = o.get("protocol") or ""
        net = outbound_network(o)
        by_kind[f"{proto}/{net}"] += 1

    print("by destination:")
    for k, v in sorted(by_label.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {k:18s} {v}")
    print("by transport:")
    for k, v in sorted(by_kind.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {k:18s} {v}")

    lv_count = by_label.get("LV:443", 0) + by_label.get("LV:8443", 0) + by_label.get("RELAY→LV", 0)
    nl_count = by_label.get("NL:443", 0) + by_label.get("NL:8443", 0) + by_label.get("RELAY→NL", 0)
    ams_count = by_label.get("AMS:443", 0) + by_label.get("AMS:8443", 0) + by_label.get("RELAY→AMS", 0)
    print(f"summary: LV={lv_count}, NL={nl_count}, AMS={ams_count}")

    if not sub_resp.content_type_ok:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
