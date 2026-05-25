#!/usr/bin/env python3
"""P1-PRO-VPN-SPEED-01: intl apps via Super_Balancer on LV/NL :443 Direct first (not Relay).

Keeps 14 injectHosts (RELAY stays in sub). Narrows Super_Balancer selector to 8 Direct
outbound tags (proxy … proxy-11) so IG/TG/Google avoid RU relay hop.

Usage:
    python ops/patch_balancer_direct_first_intl.py
    python ops/patch_balancer_direct_first_intl.py --apply
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
from patch_routing_category_ru_leak import (  # noqa: E402
    apply_patch as apply_routing_leak_patch,
    proxy_rule_domains,
)
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
DEFAULT_TEMPLATE_UUID = site_urls.REMNA_TEMPLATE_UUID
BALANCER_TAG = "Super_Balancer"

# Live sub outbounds (gen=20, 14 proxy): LV×4 + RELAY:443×3 + NL×4 + RELAY:9443×3
DIRECT_OUTBOUND_TAGS = [
    "proxy",
    "proxy-2",
    "proxy-3",
    "proxy-4",
    "proxy-8",
    "proxy-9",
    "proxy-10",
    "proxy-11",
]
INTL_DOMAINS = proxy_rule_domains()


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def _dedupe_balancer_domain_rules(rules: list[dict]) -> int:
    """Keep one Super_Balancer+domain rule with full intl matcher list."""
    kept_idx = None
    removed = 0
    intl_key = json.dumps(INTL_DOMAINS, sort_keys=True)
    for i, r in enumerate(rules):
        if r.get("balancerTag") != BALANCER_TAG or not r.get("domain"):
            continue
        if kept_idx is None:
            kept_idx = i
            rules[i]["domain"] = list(INTL_DOMAINS)
        else:
            rules.pop(i)
            removed += 1
            return removed + _dedupe_balancer_domain_rules(rules)
    if kept_idx is not None and json.dumps(rules[kept_idx].get("domain"), sort_keys=True) != intl_key:
        rules[kept_idx]["domain"] = list(INTL_DOMAINS)
    return removed


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    rules = doc.setdefault("routing", {}).setdefault("rules", [])
    r_changed, r_log = apply_routing_leak_patch(rules)
    log.extend(r_log)
    changed |= r_changed

    n = _dedupe_balancer_domain_rules(rules)
    if n:
        log.append(f"deduped {n} duplicate Super_Balancer domain rule(s)")
        changed = True

    balancers = doc.setdefault("routing", {}).setdefault("balancers", [])
    for b in balancers:
        if b.get("tag") != BALANCER_TAG:
            continue
        current = list(b.get("selector") or [])
        if current != DIRECT_OUTBOUND_TAGS:
            b["selector"] = list(DIRECT_OUTBOUND_TAGS)
            log.append(
                f"{BALANCER_TAG} selector -> {len(DIRECT_OUTBOUND_TAGS)} Direct outbounds (intl speed)"
            )
            changed = True
        b.pop("fallbackTag", None)
        if b.get("strategy", {}).get("type") != "random":
            b["strategy"] = {"type": "random"}
            log.append(f"{BALANCER_TAG} strategy -> random")
            changed = True

    for key in ("burstObservatory", "observatory"):
        if key in doc:
            log.append(f"WARN: {key} present — run patch_restore_14_relay_no_obs first")
    return changed, log


def patch_template(c: PanelClient, tpl: dict, template_uuid: str) -> None:
    minimal = {
        "uuid": tpl.get("uuid") or template_uuid,
        "templateJson": tpl["templateJson"],
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
    args = ap.parse_args()

    c = PanelClient(timeout=120)
    tpl = fetch_template(c, args.template_uuid)
    doc = copy.deepcopy(tpl["templateJson"])
    changed, log = apply_patch(doc)
    for line in log:
        print(line)
    if not changed:
        print("OK: direct-first balancer already applied")
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_balancer_direct_first_intl.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-direct-first-intl-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Snapshot: {snap}")

    tpl["templateJson"] = doc
    patch_template(c, tpl, args.template_uuid)
    after_template_patch("patch_balancer_direct_first_intl")
    print("Applied direct-first intl balancer (gen+1 via notify)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
