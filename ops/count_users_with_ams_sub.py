#!/usr/bin/env python3
"""Count ACTIVE users whose subscription payload still lists an AMS VLESS outbound.

Expected context: LV `daily-report.sh` after `source /etc/bvpn/balancer.env`
(PANEL_TOKEN / REMNA_API_TOKEN, optional PANEL_URL).

Exit 0 always unless fatal misconfig; prints human lines or --brief integer only.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.request


AMS_IP = "168.100.11.140"
NL_IP = "91.90.192.17"
LV_IP = "176.126.162.158"

DEFAULT_PANEL = "https://k9x2m1.conntest.xyz:2053"


def _token() -> str | None:
    for k in ("PANEL_TOKEN", "REMNA_API_TOKEN"):
        v = os.environ.get(k)
        if v:
            return v.strip()
    return None


def _panel_url() -> str:
    return os.environ.get("PANEL_URL", DEFAULT_PANEL).rstrip("/")


def _sub_origin() -> str:
    return os.environ.get("SUB_PUBLIC_ORIGIN", "https://p4n7q.conntest.xyz:2053").rstrip("/")


def fetch(url: str, headers: dict[str, str] | None = None, timeout: float = 45.0) -> bytes:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        return e.read()


def label(addr: str, port: int, relay_ip: str | None) -> str:
    if addr == LV_IP:
        return "LV"
    if addr == AMS_IP:
        return "AMS"
    if addr == NL_IP:
        return "NL"
    if relay_ip and addr == relay_ip:
        return {443: "LV", 8443: "AMS", 9443: "NL"}.get(port, "RELAY?")
    return "OTHER"


def count_ams(out_json: str, relay_ip: str | None) -> int:
    try:
        sub = json.loads(out_json)
    except json.JSONDecodeError:
        try:
            sub = json.loads(base64.b64decode(out_json))
        except Exception:
            return -1
    if isinstance(sub, list) and sub and isinstance(sub[0], dict):
        outbounds = sub[0].get("outbounds") or []
    elif isinstance(sub, dict):
        outbounds = sub.get("outbounds") or []
    else:
        return -1
    n = 0
    for o in outbounds:
        s = o.get("settings") or {}
        vnext = s.get("vnext")
        if isinstance(vnext, list) and vnext:
            v = vnext[0]
            addr = v.get("address")
            port = v.get("port")
            if addr and isinstance(port, int):
                if label(str(addr), int(port), relay_ip) == "AMS":
                    n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--brief",
        action="store_true",
        help="Print only integer count (-1 if error / token missing)",
    )
    args = ap.parse_args()

    token = _token()
    if not token:
        msg = -1 if args.brief else "ERROR:no PANEL_TOKEN/REMNA_API_TOKEN"
        print(msg, file=sys.stderr if not args.brief else sys.stdout)
        if args.brief:
            print(-1)
        return 0

    panel = _panel_url()
    sub_origin = _sub_origin()

    relay_ip = os.environ.get("RU_RELAY_HOST")
    relay_eff = relay_ip.strip() if isinstance(relay_ip, str) else None

    try:
        body = fetch(
            f"{panel}/api/users?limit=500&start=0",
            {"Authorization": f"Bearer {token}"},
        )
        payload = json.loads(body.decode())
        users = payload.get("response", {}).get("users", [])
        if not isinstance(users, list):
            users = []
    except Exception as e:
        msg = -1 if args.brief else f"ERROR:users API {e}"
        print(msg, file=sys.stderr if not args.brief else sys.stdout)
        if args.brief:
            print(-1)
        return 0

    active = [
        u
        for u in users
        if u.get("status") == "ACTIVE"
        and (u.get("shortUuid") or u.get("subscriptionUuid"))
    ]

    with_ams = 0
    errors = 0

    for u in active:
        sid = u.get("shortUuid") or u.get("subscriptionUuid")
        try:
            raw = fetch(
                f"{sub_origin}/api/sub/{sid}",
                {"User-Agent": "Happ/1.9.4 (iOS)"},
                timeout=30.0,
            )
            ct = count_ams(raw.decode("utf-8", errors="replace"), relay_eff)
            if ct < 0:
                errors += 1
                continue
            if ct > 0:
                with_ams += 1
        except Exception:
            errors += 1

    if args.brief:
        print(with_ams if errors == 0 else -1)
        return 0

    print(f"P1 AMS-decom probe: ACTIVE={len(active)} with_AMS_outbound≥1={with_ams} sub_fetch_errors={errors}")
    print(f"(panel={panel} SUB={sub_origin})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
