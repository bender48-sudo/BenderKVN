#!/usr/bin/env python3
"""Recovery: 8× LV+NL Direct, no observatory, random balancer (RU connect).

When 4× LV-only still has no ping — add NL paths without burstObservatory
(avoid connect-time ping storm / closed pipe).

Usage:
    python ops/patch_recovery_lv_nl_random.py
    python ops/patch_recovery_lv_nl_random.py --apply
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

# LV Direct ×4 + NL Direct ×4 (no Relay)
DIRECT_HOST_UUIDS = [
    "e7e1d97b-922a-4f50-8f84-d4551620fa4f",
    "fa51422a-0b79-4f8c-9a5b-b396ec8d4ec1",
    "fb3226f7-d8fe-4637-8f95-4938682a945f",
    "33f70ce9-f637-416b-bdc2-ca4c45a6f10e",
    "97bfa595-c0f6-42f0-b8d5-120311ab83c6",
    "386ad8bf-7819-4f92-9c6a-2cf1cdf6abae",
    "9a6ae156-1d1a-44d8-a5f6-264ef4babe95",
    "5c4cc6ad-be57-4b12-8c52-42856ff716d0",
]


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def dedupe_proxy_domain_rules(rules: list[dict]) -> int:
    """Remove duplicate Super_Balancer+domain rules (same matcher list)."""
    seen: set[str] = set()
    removed = 0
    i = 0
    while i < len(rules):
        r = rules[i]
        if r.get("balancerTag") == BALANCER_TAG and r.get("domain"):
            key = json.dumps(r.get("domain"), sort_keys=True)
            if key in seen:
                rules.pop(i)
                removed += 1
                continue
            seen.add(key)
        i += 1
    return removed


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    for key in ("burstObservatory", "observatory"):
        if key in doc:
            doc.pop(key)
            log.append(f"removed {key}")
            changed = True

    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before = list(sel.get("values") or [])
    if before != DIRECT_HOST_UUIDS:
        sel["values"] = list(DIRECT_HOST_UUIDS)
        log.append(f"injectHosts {len(before)} -> {len(DIRECT_HOST_UUIDS)} (LV+NL Direct)")
        changed = True

    for b in doc.get("routing", {}).get("balancers", []):
        if b.get("tag") != BALANCER_TAG:
            continue
        if b.pop("fallbackTag", None):
            log.append("removed fallbackTag")
            changed = True
        strat = b.setdefault("strategy", {})
        if strat.get("type") != "random":
            b["strategy"] = {"type": "random"}
            log.append("balancer -> random")
            changed = True

    rules = doc.setdefault("routing", {}).setdefault("rules", [])
    n = dedupe_proxy_domain_rules(rules)
    if n:
        log.append(f"deduped {n} duplicate proxy-domain rule(s)")
        changed = True

    levels = doc.setdefault("policy", {}).setdefault("levels", {}).setdefault("0", {})
    if levels.get("handshake") != 12:
        levels["handshake"] = 12
        log.append("handshake -> 12")
        changed = True

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
    doc = tpl["templateJson"]

    changed, log = apply_patch(copy.deepcopy(doc))
    for line in log:
        print(line)
    if not changed:
        print("OK: already on recovery profile")
        return 0
    if not args.apply:
        print("Dry-run. Apply: python ops/patch_recovery_lv_nl_random.py --apply")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"template-before-recovery-lv-nl-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    apply_patch(doc)
    patch_template(c, tpl, args.template_uuid)
    after_template_patch("patch_recovery_lv_nl_random")
    print("RECOVERY OK — refresh subscription in Happ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
