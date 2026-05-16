"""Test a real Happ-format subscription and count outbounds per node.

Steps:
1. List panel users, pick the first active one.
2. Fetch their Happ subscription URL with a Happ User-Agent.
3. Decode the response, count outbounds per node IP (LV/AMS/NL/relay).
"""
from __future__ import annotations

import base64
import io
import json
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


def _ctx() -> ssl.SSLContext:
    # TLS verification ON: panel uses Let's Encrypt cert; system CA is enough.
    return ssl.create_default_context()


def get(url: str, headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    req = urllib.request.Request(url)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, context=_ctx(), timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def label(addr: str, port: int) -> str:
    if addr == LV_IP:
        return f"LV:{port}"
    if addr == AMS_IP:
        return f"AMS:{port}"
    if addr == NL_IP:
        return f"NL:{port}"
    if addr == RELAY_IP:
        # Disambiguate relay forwards by port (443=LV, 8443=AMS, 9443=NL)
        port_map = {443: "RELAY→LV", 8443: "RELAY→AMS", 9443: "RELAY→NL"}
        return port_map.get(port, f"RELAY:{port}")
    return f"OTHER {addr}:{port}"


def address_of_outbound(o: dict) -> tuple[str | None, int | None]:
    s = o.get("settings") or {}
    vnext = s.get("vnext")
    if isinstance(vnext, list) and vnext:
        v0 = vnext[0]
        return v0.get("address"), v0.get("port")
    servers = s.get("servers")
    if isinstance(servers, list) and servers:
        return servers[0].get("address"), servers[0].get("port")
    return None, None


def main() -> None:
    code, body = get(
        f"{PANEL}/api/users?limit=10&start=0",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    if code != 200:
        sys.exit(f"users HTTP {code}: {body[:300]!r}")
    users_data = json.loads(body)
    users = users_data.get("response", {}).get("users") or users_data.get("response") or []
    if not isinstance(users, list):
        sys.exit(f"unexpected users payload: {str(users_data)[:300]}")
    print(f"users found: {len(users)}")
    if not users:
        sys.exit("no users to test against")

    pick = None
    for u in users:
        if u.get("status") in ("ACTIVE", "active") and (u.get("shortUuid") or u.get("subscriptionUuid")):
            pick = u
            break
    if pick is None:
        pick = users[0]

    short = pick.get("shortUuid") or pick.get("shortUUID") or pick.get("subscriptionUuid")
    if not short:
        sys.exit(f"no shortUuid on user: {str(pick)[:200]}")
    print(f"test user: {pick.get('username') or pick.get('uuid')} (short={short})")

    sub_url = f"{SUB}/api/sub/{short}"
    print(f"sub_url: {sub_url}")

    happ_headers = {"User-Agent": "Happ/1.9.4 (iOS)"}
    code, body = get(sub_url, headers=happ_headers)
    print(f"Happ GET HTTP {code}, {len(body)} bytes")
    if code != 200:
        sys.exit(f"sub HTTP {code}: {body[:300]!r}")

    text = body.decode("utf-8", errors="replace")
    try:
        sub = json.loads(text)
    except json.JSONDecodeError:
        try:
            decoded = base64.b64decode(text)
            sub = json.loads(decoded.decode("utf-8", errors="replace"))
        except Exception as e:
            sys.exit(f"cannot decode sub: {e}; first 200 bytes: {text[:200]!r}")

    # Happ format: JSON array with 1 element = full xray config dict.
    if isinstance(sub, list) and len(sub) == 1 and isinstance(sub[0], dict):
        inner = sub[0]
        outbounds = inner.get("outbounds") or []
        print(f"happ-config: remarks={inner.get('remarks')!r}")
    elif isinstance(sub, list):
        outbounds = sub
    elif isinstance(sub, dict):
        outbounds = sub.get("outbounds") or []
    else:
        sys.exit(f"unexpected sub root type: {type(sub).__name__}; sample: {str(sub)[:200]}")
    print(f"outbounds: {len(outbounds)}")
    by_label: Counter[str] = Counter()
    by_kind: Counter[str] = Counter()
    for o in outbounds:
        addr, port = address_of_outbound(o)
        if not addr:
            continue
        by_label[label(addr, port)] += 1
        proto = o.get("protocol") or ""
        net = ((o.get("streamSettings") or {}).get("network")) or ""
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


if __name__ == "__main__":
    main()
