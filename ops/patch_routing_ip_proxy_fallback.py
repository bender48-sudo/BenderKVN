#!/usr/bin/env python3
"""Add IP-CIDR proxy rules for TG/IG/Meta when sniffing fails (iOS background wake).

Symptom in access_log: 149.154.x / 194.221.250.50 go [socks -> direct] until
tunnel+sniffing work; after idle VPN drops and IP-only traffic leaks to direct.

Inserts rule before domain-based proxy rule:
  ip=[telegram + meta CIDRs] -> balancer Super_Balancer

Usage:
    python ops/patch_routing_ip_proxy_fallback.py
    python ops/patch_routing_ip_proxy_fallback.py --apply
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
DEFAULT_TEMPLATE_UUID = site_urls.REMNA_TEMPLATE_UUID

BALANCER_TAG = "Super_Balancer"
MARKER_IP = "149.154.0.0/16"

PROXY_IP_CIDRS = [
    # Telegram DC
    "149.154.0.0/16",
    "91.108.0.0/16",
    "185.60.64.0/22",
    # Meta / Instagram / Facebook
    "31.13.0.0/16",
    "57.144.0.0/16",
    "157.240.0.0/16",
    "173.252.64.0/18",
    "179.60.192.0/22",
    "194.221.0.0/16",
]


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def find_ip_proxy_rule_idx(rules: list[dict]) -> int:
    for i, r in enumerate(rules):
        if r.get("balancerTag") == BALANCER_TAG and MARKER_IP in (r.get("ip") or []):
            return i
    return -1


def find_domain_proxy_rule_idx(rules: list[dict]) -> int:
    for i, r in enumerate(rules):
        if r.get("balancerTag") == BALANCER_TAG and (r.get("domain") or []):
            return i
    return -1


def apply_patch(rules: list[dict]) -> tuple[bool, str]:
    if find_ip_proxy_rule_idx(rules) >= 0:
        return False, "OK: IP proxy rule already present"

    insert_at = find_domain_proxy_rule_idx(rules)
    if insert_at < 0:
        insert_at = 1

    rules.insert(
        insert_at,
        {"ip": list(PROXY_IP_CIDRS), "balancerTag": BALANCER_TAG},
    )
    return True, f"inserted IP proxy rule at R{insert_at} ({len(PROXY_IP_CIDRS)} CIDRs)"


def patch_template(c: PanelClient, tpl: dict, template_uuid: str) -> None:
    doc = tpl["templateJson"]
    minimal = {
        "uuid": tpl.get("uuid") or template_uuid,
        "templateJson": doc,
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        raise RuntimeError(f"PATCH HTTP {code}: {body!s}"[:500])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--template-uuid", default=DEFAULT_TEMPLATE_UUID)
    ap.add_argument("--no-sub-notify", action="store_true")
    args = ap.parse_args()

    c = PanelClient()
    tpl = fetch_template(c, args.template_uuid)
    rules = tpl["templateJson"]["routing"]["rules"]

    dup = copy.deepcopy(rules)
    changed, msg = apply_patch(dup)
    print(msg)
    if changed:
        for i, r in enumerate(dup):
            tag = r.get("outboundTag") or r.get("balancerTag")
            print(f"  R{i}: {tag} ip={len(r.get('ip') or [])} domain={len(r.get('domain') or [])}")

    if not changed:
        return 0
    if not args.apply:
        print("Dry-run. Apply: python ops/patch_routing_ip_proxy_fallback.py --apply")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"template-before-ip-proxy-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(tpl["templateJson"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    apply_patch(rules)
    patch_template(c, tpl, args.template_uuid)
    if not args.no_sub_notify:
        after_template_patch("patch_routing_ip_proxy_fallback")
    print("PATCH OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
