#!/usr/bin/env python3
"""P1-PRO-VPN-SPEED-01: intl apps via Intl_Direct (RU: RELAY→LV only for TG/IG).

Keeps 14 injectHosts. **Super_Balancer** catch-all uses proxy-5..7 (RELAY→LV), same as
**Intl_Direct** — from RU LV Direct :443 is unstable; see ``patch_balancer_catchall_relay_ru.py``.
**Intl_Direct** uses proxy-5..7 (RELAY→LV :443) — from RU Direct/NL to 149.154.x is slow;
access_log showed TG on proxy-14/NL Direct. Do not put NL or RELAY-NL in Intl selector.

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
CATCHALL_BALANCER_TAG = "Super_Balancer"
INTL_BALANCER_TAG = "Intl_Direct"
CATCHALL_SELECTOR = ["proxy-5", "proxy-6", "proxy-7"]

# injectHosts order: proxy..4 LV Direct, proxy-5..7 RELAY→LV :443, proxy-8..11 NL, 12..14 RELAY→NL
# Intl apps (IG/TG/…): multi-path — RU relay TLS flaps every ~5–10 min (ru-monitor);
# relay-only (2026-05-25) caused «то грузит, то нет» for Instagram. Catch-all stays relay-only.
INTL_DIRECT_TAGS = [
    "proxy",
    "proxy-2",
    "proxy-3",
    "proxy-4",
    "proxy-5",
    "proxy-6",
    "proxy-7",
    "proxy-8",
    "proxy-9",
    "proxy-10",
    "proxy-11",
]
INTL_DOMAINS = proxy_rule_domains()


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def _is_catchall_balancer_rule(rule: dict) -> bool:
    return (
        rule.get("balancerTag") in (CATCHALL_BALANCER_TAG, INTL_BALANCER_TAG)
        and bool(rule.get("network"))
        and not rule.get("domain")
        and not rule.get("ip")
    )


def _is_intl_specific_rule(rule: dict) -> bool:
    """TG/IG/Google rules — not the default tcp,udp catch-all."""
    tag = rule.get("balancerTag")
    if tag not in (CATCHALL_BALANCER_TAG, INTL_BALANCER_TAG):
        return False
    if _is_catchall_balancer_rule(rule):
        return False
    return bool(rule.get("domain") or rule.get("ip"))


def _dedupe_intl_domain_rules(rules: list[dict]) -> int:
    """One Intl_Direct+domain rule with full matcher list."""
    kept_idx = None
    removed = 0
    intl_key = json.dumps(INTL_DOMAINS, sort_keys=True)
    for i, r in enumerate(rules):
        if r.get("balancerTag") not in (CATCHALL_BALANCER_TAG, INTL_BALANCER_TAG) or not r.get(
            "domain"
        ):
            continue
        if kept_idx is None:
            kept_idx = i
            rules[i]["balancerTag"] = INTL_BALANCER_TAG
            rules[i]["domain"] = list(INTL_DOMAINS)
        else:
            rules.pop(i)
            removed += 1
            return removed + _dedupe_intl_domain_rules(rules)
    if kept_idx is not None:
        if rules[kept_idx].get("balancerTag") != INTL_BALANCER_TAG:
            rules[kept_idx]["balancerTag"] = INTL_BALANCER_TAG
        if json.dumps(rules[kept_idx].get("domain"), sort_keys=True) != intl_key:
            rules[kept_idx]["domain"] = list(INTL_DOMAINS)
    return removed


def _migrate_intl_rules_to_intl_balancer(rules: list[dict]) -> int:
    n = 0
    for r in rules:
        if not _is_intl_specific_rule(r):
            continue
        if r.get("balancerTag") != INTL_BALANCER_TAG:
            r["balancerTag"] = INTL_BALANCER_TAG
            n += 1
    return n


def _ensure_balancer(
    balancers: list[dict],
    tag: str,
    selector: list[str],
) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False
    found = False
    for b in balancers:
        if b.get("tag") != tag:
            continue
        found = True
        if list(b.get("selector") or []) != selector:
            b["selector"] = list(selector)
            log.append(f"{tag} selector -> {selector}")
            changed = True
        b.pop("fallbackTag", None)
        if b.get("strategy", {}).get("type") != "random":
            b["strategy"] = {"type": "random"}
            log.append(f"{tag} strategy -> random")
            changed = True
    if not found:
        balancers.append(
            {
                "tag": tag,
                "selector": list(selector),
                "strategy": {"type": "random"},
            }
        )
        log.append(f"added balancer {tag} selector={selector}")
        changed = True
    return changed, log


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    rules = doc.setdefault("routing", {}).setdefault("rules", [])
    r_changed, r_log = apply_routing_leak_patch(rules)
    log.extend(r_log)
    changed |= r_changed

    migrated = _migrate_intl_rules_to_intl_balancer(rules)
    if migrated:
        log.append(f"migrated {migrated} intl rule(s) -> {INTL_BALANCER_TAG}")
        changed = True

    n = _dedupe_intl_domain_rules(rules)
    if n:
        log.append(f"deduped {n} duplicate intl domain rule(s)")
        changed = True

    for r in rules:
        if _is_catchall_balancer_rule(r) and r.get("balancerTag") != CATCHALL_BALANCER_TAG:
            r["balancerTag"] = CATCHALL_BALANCER_TAG
            log.append("catch-all rule -> Super_Balancer")
            changed = True

    balancers = doc.setdefault("routing", {}).setdefault("balancers", [])
    c_changed, c_log = _ensure_balancer(balancers, CATCHALL_BALANCER_TAG, CATCHALL_SELECTOR)
    log.extend(c_log)
    changed |= c_changed

    i_changed, i_log = _ensure_balancer(balancers, INTL_BALANCER_TAG, INTL_DIRECT_TAGS)
    log.extend(i_log)
    changed |= i_changed

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
        print("OK: Intl_Direct + Super_Balancer catch-all already correct")
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_balancer_direct_first_intl.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-intl-direct-split-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Snapshot: {snap}")

    tpl["templateJson"] = doc
    patch_template(c, tpl, args.template_uuid)
    after_template_patch("patch_balancer_direct_first_intl")
    print(
        "Applied Intl_Direct multi-path (LV+RELAY+NL) + "
        "Super_Balancer catch-all [proxy-5..7 RELAY] (gen+1)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
