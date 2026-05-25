#!/usr/bin/env python3
"""Rollback patch_fast_connect_lv_only: restore 14 hosts + observatory + leastLoad.

Keeps safety fixes: no fallbackTag=direct, routing IP/domain proxy rules unchanged.

Usage:
    python ops/restore_template_working.py --apply
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
from trim_injecthosts_no_xhttp import is_xhttp_host  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
DEFAULT_TEMPLATE_UUID = site_urls.REMNA_TEMPLATE_UUID
BALANCER_TAG = "Super_Balancer"

OBSERVATORY = {
    "subjectSelector": ["proxy"],
    "pingConfig": {
        "destination": "https://www.gstatic.com/generate_204",
        "connectivity": "http://connectivitycheck.platform.hicloud.com/generate_204",
        "interval": "60s",
        "timeout": "10s",
        "sampling": 2,
    },
}

LEAST_LOAD_STRATEGY = {
    "type": "leastLoad",
    "settings": {
        "maxRTT": "350ms",
        "expected": 2,
        "baselines": ["50ms", "150ms"],
        "tolerance": 0.02,
    },
}


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def full_inject_uuids(c: PanelClient, template_uuid: str) -> list[str]:
    hosts = c.get_or_raise("/api/hosts")["response"]
    tpl = c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]
    current = set(
        tpl["templateJson"]["remnawave"]["injectHosts"][0]["selector"].get("values") or []
    )
    # All non-xhttp hosts that were ever in inject OR all panel hosts on LV/NL connected nodes
    nodes = {n["uuid"]: n for n in c.get_or_raise("/api/nodes")["response"]}
    out: list[str] = []
    for h in hosts:
        uid = str(h.get("uuid") or "")
        if not uid or is_xhttp_host(h):
            continue
        node_ids = h.get("nodes") or []
        if not node_ids:
            continue
        node = nodes.get(node_ids[0], {})
        if node.get("isDisabled"):
            continue
        if node.get("name") == "Amsterdam-01" and not node.get("isConnected"):
            continue
        out.append(uid)
    # Prefer restoring known 14-set order if we have them
    known_14 = [
        "e7e1d97b-922a-4f50-8f84-d4551620fa4f",
        "fa51422a-0b79-4f8c-9a5b-b396ec8d4ec1",
        "fb3226f7-d8fe-4637-8f95-4938682a945f",
        "33f70ce9-f637-416b-bdc2-ca4c45a6f10e",
        "88f34942-f0e5-445d-bc44-892858cdbc0d",
        "1ae0b3e4-6d29-43d8-978c-60f4926798f2",
        "131c6720-a76d-4e8f-b94a-efc81cb9c082",
        "5c4cc6ad-be57-4b12-8c52-42856ff716d0",
        "97bfa595-c0f6-42f0-b8d5-120311ab83c6",
        "386ad8bf-7819-4f92-9c6a-2cf1cdf6abae",
        "9a6ae156-1d1a-44d8-a5f6-264ef4babe95",
        "f434c788-2180-46ba-bb7d-d37afc5b87d8",
        "692d453a-464d-47df-997d-cffd8c6dfe13",
        "c7022d29-f232-4777-b863-aeb4aca97353",
    ]
    host_set = {str(h.get("uuid")) for h in hosts}
    restored = [u for u in known_14 if u in host_set]
    if len(restored) >= 10:
        return restored
    # fallback: union current + scanned
    merged = list(dict.fromkeys(restored + out + list(current)))
    return merged[:16]


def apply_restore(doc: dict, inject: list[str]) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    if doc.get("burstObservatory") != OBSERVATORY:
        doc["burstObservatory"] = copy.deepcopy(OBSERVATORY)
        doc.pop("observatory", None)
        log.append("restored burstObservatory (60s interval, 10s timeout)")
        changed = True

    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before = list(sel.get("values") or [])
    if before != inject:
        sel["values"] = inject
        log.append(f"injectHosts {len(before)} -> {len(inject)}")
        changed = True

    for b in doc.get("routing", {}).get("balancers", []):
        if b.get("tag") != BALANCER_TAG:
            continue
        if b.pop("fallbackTag", None):
            log.append("removed fallbackTag from balancer")
            changed = True
        strat = b.setdefault("strategy", {})
        if strat.get("type") != "leastLoad":
            b["strategy"] = copy.deepcopy(LEAST_LOAD_STRATEGY)
            log.append("balancer strategy -> leastLoad")
            changed = True

    levels = doc.setdefault("policy", {}).setdefault("levels", {}).setdefault("0", {})
    if levels.get("handshake") == 12:
        levels["handshake"] = 4
        log.append("policy handshake -> 4")
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

    c = PanelClient()
    tpl = fetch_template(c, args.template_uuid)
    doc = tpl["templateJson"]
    inject = full_inject_uuids(c, args.template_uuid)
    print(f"target injectHosts: {len(inject)} UUIDs")

    changed, log = apply_restore(copy.deepcopy(doc), inject)
    for line in log:
        print(line)
    if not changed:
        print("nothing to change")
        return 0
    if not args.apply:
        print("Dry-run. Apply: python ops/restore_template_working.py --apply")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"template-before-restore-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    apply_restore(doc, inject)
    patch_template(c, tpl, args.template_uuid)
    after_template_patch("restore_template_working")
    print("RESTORE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
