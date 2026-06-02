#!/usr/bin/env python3
"""VPN-AUD-230: verify split DNS in live subscription + no port-53 direct routing.

Usage:
    python ops/probe_dns_leak.py
    python ops/probe_dns_leak.py --json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import site_urls  # noqa: E402
from dns_split_config import verify_dns_split_config  # noqa: E402
from subscription_fetch import HAPP_UA, decode_subscription, fetch_url, xray_config_root  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOKEN_PATH = ROOT / ".secrets" / "panel-token.txt"


def _dns_routing_regressions(cfg: dict) -> list[str]:
    errors: list[str] = []
    for i, r in enumerate((cfg.get("routing") or {}).get("rules") or []):
        port = str(r.get("port") or "")
        tag = r.get("outboundTag") or r.get("balancerTag") or ""
        if port == "53" and tag == "direct":
            errors.append(f"rule[{i}]: port 53 → direct (gen=30 regression)")
        if port == "53" and "RELAY_DNS" in str(tag):
            errors.append(f"rule[{i}]: port 53 → RELAY_DNS (gen=33 regression)")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    token = os.environ.get("PANEL_TOKEN") or os.environ.get("REMNA_API_TOKEN")
    if not token and TOKEN_PATH.is_file():
        token = TOKEN_PATH.read_text(encoding="ascii").strip()
    if not token:
        print("FAIL: set PANEL_TOKEN/REMNA_API_TOKEN or .secrets/panel-token.txt", file=sys.stderr)
        return 1
    users_resp = fetch_url(
        f"{site_urls.PANEL_URL}/api/users?limit=5&start=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    if users_resp.status != 200:
        print(f"FAIL: users HTTP {users_resp.status}", file=sys.stderr)
        return 1

    users = json.loads(users_resp.body).get("response", {}).get("users") or []
    if not users:
        print("FAIL: no users", file=sys.stderr)
        return 1

    short = users[0].get("shortUuid")
    sub_resp = fetch_url(
        f"{site_urls.SUB_PUBLIC_ORIGIN}/api/sub/{short}",
        headers={"User-Agent": HAPP_UA},
    )
    if sub_resp.status != 200:
        print(f"FAIL: sub HTTP {sub_resp.status}", file=sys.stderr)
        return 1

    cfg = xray_config_root(decode_subscription(sub_resp.body))
    dns_errs = verify_dns_split_config(cfg)
    route_errs = _dns_routing_regressions(cfg)
    all_errs = dns_errs + route_errs

    report = {
        "sub_short": short,
        "dns_present": bool(cfg.get("dns")),
        "dns_servers_count": len((cfg.get("dns") or {}).get("servers") or []),
        "ok": not all_errs,
        "errors": all_errs,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if all_errs else 0

    print(f"sub: {short}")
    print(f"dns block: {'yes' if report['dns_present'] else 'NO'} ({report['dns_servers_count']} servers)")
    if all_errs:
        for e in all_errs:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("PROBE_DNS_LEAK_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
