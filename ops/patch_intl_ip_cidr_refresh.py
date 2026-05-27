#!/usr/bin/env python3
"""VPN-AUD-120/121: refresh Intl_Direct IP-CIDR rule (TG/Meta/OpenAI edge).

Updates existing rule with balancerTag Intl_Direct and ip= list.

Usage:
    python ops/patch_intl_ip_cidr_refresh.py
    python ops/patch_intl_ip_cidr_refresh.py --apply
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import sys
import time
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
INTL_BALANCER = "Intl_Direct"
MARKER = "149.154.0.0/16"

# Canonical list (deduped); extends Meta ranges for iOS background.
INTL_IP_CIDRS = [
    "149.154.0.0/16",
    "91.108.0.0/16",
    "185.60.64.0/22",
    "31.13.0.0/16",
    "31.13.64.0/18",
    "57.144.0.0/16",
    "69.63.176.0/20",
    "103.4.96.0/22",
    "129.134.0.0/17",
    "157.240.0.0/16",
    "173.252.64.0/18",
    "179.60.192.0/22",
    "194.221.0.0/16",
    # OpenAI / ChatGPT (common egress; domain rule covers desktop sniff)
    "104.18.0.0/16",
    "104.19.0.0/16",
]


def find_ip_rule(rules: list[dict]) -> int:
    for i, r in enumerate(rules):
        if r.get("balancerTag") == INTL_BALANCER and MARKER in (r.get("ip") or []):
            return i
    for i, r in enumerate(rules):
        if r.get("balancerTag") == INTL_BALANCER and r.get("ip"):
            return i
    return -1


def apply_patch(rules: list[dict]) -> tuple[bool, list[str]]:
    idx = find_ip_rule(rules)
    if idx < 0:
        return False, ["no Intl_Direct IP rule found — run patch_routing_ip_proxy_fallback first"]
    cur = list(rules[idx].get("ip") or [])
    want = list(INTL_IP_CIDRS)
    if cur == want:
        return False, [f"OK: {len(want)} CIDRs already current"]
    rules[idx]["ip"] = want
    rules[idx]["balancerTag"] = INTL_BALANCER
    return True, [f"Intl IP rule -> {len(want)} CIDRs (was {len(cur)})"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient(timeout=120)
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = copy.deepcopy(tpl["templateJson"])
    rules = doc.setdefault("routing", {}).setdefault("rules", [])
    changed, log = apply_patch(rules)
    for line in log:
        print(line)
    if not changed:
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_intl_ip_cidr_refresh.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-intl-ip-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    tpl["templateJson"] = doc
    minimal = {
        "uuid": tpl.get("uuid") or args.template_uuid,
        "templateJson": tpl["templateJson"],
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        print(f"FAIL PATCH HTTP {code}", file=sys.stderr)
        return 1
    after_template_patch("patch_intl_ip_cidr_refresh")
    print("Applied Intl IP CIDR refresh (gen+1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
