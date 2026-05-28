#!/usr/bin/env python3
"""Route DNS (port 53) through RELAY-LV balancer instead of random or direct.

Problem history:
  gen<30:  DNS → random proxy → sometimes NL (slow, ~36% DNS via proxy-8..11)
  gen=30:  DNS → direct       → Russian ISP intercepts port 53 → DNS filtering
  This:    DNS → RELAY_DNS    → relay-LV only (proxy-5..7, always fast from RU)

The RELAY_DNS balancer uses proxy-5..7 (72.56.0.145:443, relay to LV).
These are consistently reachable from Russia and have low latency (~30-50ms).
DNS queries are encrypted inside VLESS → ISP cannot filter them.

Usage:
    python ops/patch_dns_via_relay.py
    python ops/patch_dns_via_relay.py --apply
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

_DNS_BALANCER_TAG = "RELAY_DNS"
_DNS_BALANCER = {
    "tag": _DNS_BALANCER_TAG,
    "selector": ["proxy-5", "proxy-6", "proxy-7"],
    "strategy": {"type": "random"},
}
_DNS_RULE = {
    "type": "field",
    "port": "53",
    "network": "udp,tcp",
    "balancerTag": _DNS_BALANCER_TAG,
}


def _is_dns_direct_rule(rule: dict) -> bool:
    return rule.get("outboundTag") == "direct" and str(rule.get("port") or "") == "53"


def _has_dns_relay_rule(rules: list[dict]) -> bool:
    return any(
        r.get("balancerTag") == _DNS_BALANCER_TAG and str(r.get("port") or "") == "53"
        for r in rules
    )


def _has_dns_relay_balancer(balancers: list[dict]) -> bool:
    return any(b.get("tag") == _DNS_BALANCER_TAG for b in balancers)


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    routing = doc.setdefault("routing", {})
    rules: list[dict] = routing.setdefault("rules", [])
    balancers: list[dict] = routing.setdefault("balancers", [])
    changed = False

    # Remove any existing DNS direct rule
    before = len(rules)
    routing["rules"] = [r for r in rules if not _is_dns_direct_rule(r)]
    rules = routing["rules"]
    removed = before - len(rules)
    if removed:
        log.append(f"removed {removed} DNS port-53 direct rule(s)")
        changed = True

    # Add RELAY_DNS balancer if missing
    if not _has_dns_relay_balancer(balancers):
        balancers.append(copy.deepcopy(_DNS_BALANCER))
        log.append(f"added {_DNS_BALANCER_TAG} balancer (proxy-5..7)")
        changed = True
    else:
        log.append(f"OK: {_DNS_BALANCER_TAG} balancer already present")

    # Add DNS routing rule if missing
    if not _has_dns_relay_rule(rules):
        insert_at = 0
        for i, r in enumerate(rules):
            if r.get("outboundTag") == "block":
                insert_at = i + 1
                break
        rules.insert(insert_at, copy.deepcopy(_DNS_RULE))
        log.append(f"inserted DNS :53 → {_DNS_BALANCER_TAG} at rule index {insert_at}")
        changed = True
    else:
        log.append(f"OK: DNS port-53 → {_DNS_BALANCER_TAG} rule already present")

    return changed, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient(timeout=120)
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = copy.deepcopy(tpl["templateJson"])
    changed, log = apply_patch(doc)
    for line in log:
        print(line)
    if not changed:
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_dns_via_relay.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-dns-via-relay-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
        print(f"FAIL PATCH HTTP {code}: {body!s}"[:400], file=sys.stderr)
        return 1
    after_template_patch("patch_dns_via_relay")
    print(f"Applied: DNS port-53 → {_DNS_BALANCER_TAG} (relay-LV only, gen+1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
