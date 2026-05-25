#!/usr/bin/env python3
"""Fix Happ closed-pipe: remove burstObservatory, random balancer, keep 8 hosts + routing.

Logs: all proxy-* fail hicloud observatory ping with 'closed pipe' at connect;
leastLoad then has no healthy outbound. Traffic shows [socks >> proxy] but apps dead.

Usage:
    python ops/patch_remove_observatory_keep_routing.py --apply
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
STABLE_SNAPSHOT = SNAPSHOT_DIR / "template-before-fast-connect-20260525_194540.json"
DEFAULT_TEMPLATE_UUID = site_urls.REMNA_TEMPLATE_UUID
BALANCER_TAG = "Super_Balancer"

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


def load_stable_routing_rules() -> list[dict]:
    raw = json.loads(STABLE_SNAPSHOT.read_text(encoding="utf-8"))
    doc = raw["response"]["templateJson"] if "response" in raw else raw
    rules = copy.deepcopy(doc["routing"]["rules"])
    seen: set[str] = set()
    out: list[dict] = []
    for r in rules:
        if r.get("balancerTag") == BALANCER_TAG and r.get("domain"):
            key = json.dumps(r.get("domain"), sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
        out.append(r)
    return out


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    for key in ("burstObservatory", "observatory"):
        if key in doc:
            doc.pop(key)
            log.append(f"removed {key} (fixes closed pipe on connect)")
            changed = True

    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    if list(sel.get("values") or []) != DIRECT_HOST_UUIDS:
        sel["values"] = list(DIRECT_HOST_UUIDS)
        log.append(f"injectHosts -> {len(DIRECT_HOST_UUIDS)} LV+NL Direct")
        changed = True

    for b in doc.get("routing", {}).get("balancers", []):
        if b.get("tag") != BALANCER_TAG:
            continue
        if b.pop("fallbackTag", None):
            log.append("removed fallbackTag")
            changed = True
        if b.get("strategy", {}).get("type") != "random":
            b["strategy"] = {"type": "random"}
            log.append("balancer -> random (no observatory required)")
            changed = True

    stable_rules = load_stable_routing_rules()
    if doc["routing"]["rules"] != stable_rules:
        doc["routing"]["rules"] = stable_rules
        log.append(f"routing rules restored ({len(stable_rules)} rules, geoip:ru direct)")
        changed = True

    levels = doc.setdefault("policy", {}).setdefault("levels", {}).setdefault("0", {})
    if levels.get("handshake") != 4:
        levels["handshake"] = 4
        log.append("handshake -> 4")
        changed = True

    return changed, log


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


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
    changed, log = apply_patch(copy.deepcopy(tpl["templateJson"]))
    for line in log:
        print(line)
    if not changed:
        print("OK: already applied")
        return 0
    if not args.apply:
        print("Dry-run. Apply with --apply")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"template-before-no-obs-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(tpl["templateJson"], ensure_ascii=False, indent=2), encoding="utf-8")
    apply_patch(tpl["templateJson"])
    patch_template(c, tpl, args.template_uuid)
    after_template_patch("patch_remove_observatory_keep_routing")
    print("PATCH OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
