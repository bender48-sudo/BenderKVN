#!/usr/bin/env python3
"""Remove RELAY_DNS-specific routing rule and balancer from template.

gen=33 added DNS port-53 → RELAY_DNS (proxy-5..7). Relay VPS providers
commonly block outbound port 53 UDP (anti-DNS-amplification). Result:
every DNS lookup times out (~1000ms) → total perceived latency 1300ms+,
speed tests fail.

Fix: DNS falls through to Super_Balancer catch-all (LV×4 + relay×3 = 7
paths after patch_nl_exclude_temp). Both LV and relay allow port 53
outbound. No dedicated DNS rule needed — Super_Balancer already handles
all unmatched traffic including DNS queries.

Usage:
    python ops/patch_remove_dns_relay_rule.py
    python ops/patch_remove_dns_relay_rule.py --apply
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


def _is_relay_dns_rule(rule: dict) -> bool:
    return rule.get("balancerTag") == _DNS_BALANCER_TAG


def _is_relay_dns_balancer(b: dict) -> bool:
    return b.get("tag") == _DNS_BALANCER_TAG


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    routing = doc.get("routing", {})
    rules: list[dict] = routing.get("rules", [])
    balancers: list[dict] = routing.get("balancers", [])

    n_rules_before = len(rules)
    routing["rules"] = [r for r in rules if not _is_relay_dns_rule(r)]
    removed_rules = n_rules_before - len(routing["rules"])

    n_bal_before = len(balancers)
    routing["balancers"] = [b for b in balancers if not _is_relay_dns_balancer(b)]
    removed_bal = n_bal_before - len(routing["balancers"])

    changed = removed_rules > 0 or removed_bal > 0
    if removed_rules:
        log.append(f"removed {removed_rules} RELAY_DNS routing rule(s)")
    if removed_bal:
        log.append(f"removed {removed_bal} RELAY_DNS balancer(s)")
    if not changed:
        log.append("OK: no RELAY_DNS rule/balancer found — nothing to remove")
    if changed:
        log.append("DNS now falls through to Super_Balancer catch-all (LV + relay, port 53 outbound OK)")
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
        print("\nDry-run. Apply: python ops/patch_remove_dns_relay_rule.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-remove-dns-relay-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
    after_template_patch("patch_remove_dns_relay_rule")
    print("Applied: RELAY_DNS rule removed — DNS via Super_Balancer catch-all (gen+1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
