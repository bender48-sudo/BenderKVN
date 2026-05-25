#!/usr/bin/env python3
"""P1-PRO-VPN-SPEED-01: intl apps via Super_Balancer on LV/NL :443 Direct first (not Relay).

Does NOT remove Relay from injectHosts (14 hosts). Only narrows balancer selector to
8 Direct node UUIDs so IG/TG/Google hit LV:443 / NL:443 before RU relay path.

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
from patch_routing_category_ru_leak import apply_patch as apply_routing_leak_patch  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
DEFAULT_TEMPLATE_UUID = site_urls.REMNA_TEMPLATE_UUID
BALANCER_TAG = "Super_Balancer"


def direct_balancer_selector(doc: dict) -> list[str]:
    """Outbound tags for LV/NL :443 Direct — exclude Relay / alt ports."""
    tags: list[str] = []
    for ob in doc.get("outbounds", []):
        tag = (ob.get("tag") or "").strip()
        if not tag or tag in ("direct", "block", "dns-out"):
            continue
        low = tag.lower()
        if "relay" in low or "xhttp" in low or "9443" in low or "8443" in low:
            continue
        tags.append(tag)
    return tags


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    rules = doc.setdefault("routing", {}).setdefault("rules", [])
    r_changed, r_log = apply_routing_leak_patch(rules)
    log.extend(r_log)
    changed |= r_changed

    direct_tags = direct_balancer_selector(doc)
    if not direct_tags:
        log.append("WARN: no direct outbound tags found — skip balancer selector")
    for b in doc.get("routing", {}).get("balancers", []):
        if b.get("tag") != BALANCER_TAG:
            continue
        current = list(b.get("selector") or [])
        if direct_tags and current != direct_tags:
            b["selector"] = list(direct_tags)
            log.append(
                f"{BALANCER_TAG} selector -> {len(direct_tags)} Direct outbounds (intl speed)"
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
