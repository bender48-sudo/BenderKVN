#!/usr/bin/env python3
"""Q-VPN-STAB-020: XHTTP incident recovery URL + enablement checklist.

Happ sub intentionally excludes XHTTP (batch-import risk). For LTE/TSPU incidents
use Hiddify/Streisand with full matrix, or Happ alt node NL:9443 / LV alt :8443.

Usage:
    python ops/generate_xhttp_recovery_url.py --short ABC123
    python ops/generate_xhttp_recovery_url.py --username user@example.com
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402
from trim_injecthosts_no_xhttp import resolve_xhttp_uuids  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SUB = site_urls.SUB_PUBLIC_ORIGIN


def _find_short(c: PanelClient, username: str | None, short: str | None) -> tuple[str, str]:
    if short:
        return short, short
    code, data = c.get("/api/users?limit=200&start=0")
    if code != 200:
        raise SystemExit(f"users HTTP {code}")
    for u in (data.get("response") or {}).get("users") or []:
        if username and u.get("username") == username:
            s = u.get("shortUuid") or u.get("subscriptionUuid")
            if s:
                return s, u.get("username") or s
        if short and (u.get("shortUuid") == short or u.get("subscriptionUuid") == short):
            return short, u.get("username") or short
    raise SystemExit(f"user not found: username={username!r} short={short!r}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--short", help="subscription shortUuid")
    ap.add_argument("--username", help="panel username / email")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.short and not args.username:
        ap.error("pass --short or --username")

    c = PanelClient(timeout=60)
    short, label = _find_short(c, args.username, args.short)
    sub_url = f"{SUB}/api/sub/{short}"

    xhttp_hosts = resolve_xhttp_uuids(c)
    xhttp_in_nodes = [f"{uid[:8]}… {remark}" for uid, remark in xhttp_hosts]

    payload = {
        "user": label,
        "shortUuid": short,
        "subscription_url": sub_url,
        "happ_note": "Happ sub excludes XHTTP — use alt NL:9443 or LV:8443 in Happ UI",
        "full_matrix_clients": ["Hiddify", "Streisand", "v2rayN"],
        "xhttp_hosts_on_panel": len(xhttp_hosts),
        "xhttp_host_remarks": [r for _, r in xhttp_hosts],
        "incident_steps": [
            "1. User: refresh subscription in client",
            "2. Happ LTE: pick alt node (NL 9443 or LV 8443) — see FAQ",
            "3. TSPU hard block: import same URL in Hiddify/Streisand (includes XHTTP if in injectHosts)",
            "4. Ops: to expose XHTTP temporarily — restore XHTTP UUIDs from snapshot (see trim_injecthosts_no_xhttp rollback)",
        ],
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"User: {label}")
    print(f"Recovery subscription URL:\n  {sub_url}\n")
    print("Happ (default): XHTTP not in sub — use alt transport in app:")
    print("  • NL / port 9443")
    print("  • LV / port 8443")
    print("\nFull matrix (XHTTP if enabled in template):")
    for client in payload["full_matrix_clients"]:
        print(f"  • {client}: import URL above, User-Agent not Happ")
    print(f"\nPanel XHTTP hosts (not in Happ injectHosts): {len(xhttp_hosts)}")
    for line in xhttp_in_nodes[:5]:
        print(f"  - {line}")
    print("\nIncident ops checklist:")
    for step in payload["incident_steps"]:
        print(f"  {step}")
    print("\nXHTTP_RECOVERY_URL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
