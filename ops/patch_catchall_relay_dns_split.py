#!/usr/bin/env python3
"""Ping + catch-all via relay; DNS :53 via LV direct only.

Happ ping measures catch-all (rule 6). Super=LV×4 from RU → 300–1100ms jitter.
TG already on Intl relay-only (gen=45). This patch:
  - DNS port 53 → DNS_LV (proxy..4)
  - catch-all → Intl_Direct (relay×6) — stable ping ~relay RTT

Usage:
    python ops/patch_catchall_relay_dns_split.py
    python ops/patch_catchall_relay_dns_split.py --apply
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

from balancer_selectors import (  # noqa: E402
    INTL_RELAY_ONLY_SELECTOR,
    SUPER_LV_DIRECT_SELECTOR,
)
from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"

DNS_BALANCER = "DNS_LV"
INTL_TAG = "Intl_Direct"
SUPER_TAG = "Super_Balancer"


def _ensure_balancer(balancers: list[dict], tag: str, selector: list[str]) -> bool:
    for b in balancers:
        if b.get("tag") == tag:
            old = list(b.get("selector") or [])
            if old != selector:
                b["selector"] = list(selector)
                return True
            return False
    balancers.append(
        {
            "tag": tag,
            "selector": list(selector),
            "strategy": {"type": "random"},
        }
    )
    return True


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False
    routing = doc.setdefault("routing", {})
    balancers: list[dict] = routing.setdefault("balancers", [])

    if _ensure_balancer(balancers, DNS_BALANCER, SUPER_LV_DIRECT_SELECTOR):
        log.append(f"balancer {DNS_BALANCER}: LV×4 for DNS :53")
        changed = True
    if _ensure_balancer(balancers, INTL_TAG, INTL_RELAY_ONLY_SELECTOR):
        log.append(f"{INTL_TAG}: relay×6")
        changed = True
    if _ensure_balancer(balancers, SUPER_TAG, SUPER_LV_DIRECT_SELECTOR):
        log.append(f"{SUPER_TAG}: LV×4 (unused catch-all)")
        changed = True

    rules: list[dict] = routing.setdefault("rules", [])
    # Remove legacy DNS relay rules if present
    before_len = len(rules)
    rules[:] = [
        r
        for r in rules
        if r.get("balancerTag") != "RELAY_DNS"
        and not (r.get("outboundTag") == "direct" and str(r.get("port")) == "53")
    ]
    if len(rules) != before_len:
        log.append("removed legacy DNS direct/RELAY_DNS rules")
        changed = True

    dns_rule = {
        "type": "field",
        "port": "53",
        "network": "tcp,udp",
        "balancerTag": DNS_BALANCER,
    }
    catch_idx = next(
        (i for i, r in enumerate(rules) if r.get("network") == "tcp,udp" and r.get("balancerTag")),
        None,
    )
    if catch_idx is None:
        rules.append({"type": "field", "network": "tcp,udp", "balancerTag": INTL_TAG})
        log.append("appended catch-all → Intl_Direct")
        changed = True
    else:
        old_tag = rules[catch_idx].get("balancerTag")
        if old_tag != INTL_TAG:
            rules[catch_idx]["balancerTag"] = INTL_TAG
            log.append(f"catch-all: {old_tag} → {INTL_TAG}")
            changed = True

    # Insert DNS rule before catch-all (last matching broad rule)
    insert_at = catch_idx if catch_idx is not None else len(rules) - 1
    has_dns = any(
        r.get("balancerTag") == DNS_BALANCER and str(r.get("port")) == "53" for r in rules
    )
    if not has_dns:
        rules.insert(insert_at, dns_rule)
        log.append("inserted DNS :53 → DNS_LV before catch-all")
        changed = True

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
        print("OK: already applied")
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_catchall_relay_dns_split.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-catchall-relay-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
    after_template_patch("patch_catchall_relay_dns_split")
    print("Applied: catch-all→relay (ping); DNS:53→LV. Refresh Happ sub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
