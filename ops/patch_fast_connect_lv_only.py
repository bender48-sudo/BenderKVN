#!/usr/bin/env python3
"""Emergency: slow connect + dead tunnels — disable observatory, 4 LV direct hosts only.

Symptoms (Happ error_log): burst ping 'closed pipe' on all proxy-* at connect;
access_log routes to proxy but messages do not arrive (14 outbounds, RELAY/NL).

Changes:
  - Remove burstObservatory (no 14× health ping on connect)
  - Super_Balancer: leastLoad -> random (works without observatory)
  - injectHosts: 14 -> 4 (Latvia Direct only, no Relay/NL/AMS)
  - policy handshake: 4 -> 12

Usage:
    python ops/patch_fast_connect_lv_only.py
    python ops/patch_fast_connect_lv_only.py --apply
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

# Latvia-Node, remark contains "Direct", not Relay (stable set from panel_api hosts scan)
LV_DIRECT_HOST_UUIDS = [
    "e7e1d97b-922a-4f50-8f84-d4551620fa4f",
    "fa51422a-0b79-4f8c-9a5b-b396ec8d4ec1",
    "fb3226f7-d8fe-4637-8f95-4938682a945f",
    "33f70ce9-f637-416b-bdc2-ca4c45a6f10e",
]


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    for key in ("burstObservatory", "observatory"):
        if key in doc:
            doc.pop(key)
            log.append(f"removed {key}")
            changed = True

    for b in doc.get("routing", {}).get("balancers", []):
        if b.get("tag") != BALANCER_TAG:
            continue
        b.pop("fallbackTag", None)
        strat = b.setdefault("strategy", {})
        if strat.get("type") != "random":
            strat["type"] = "random"
            strat.pop("settings", None)
            log.append(f"{BALANCER_TAG} strategy -> random")
            changed = True

    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before = list(sel.get("values") or [])
    after = [u for u in LV_DIRECT_HOST_UUIDS if u in before] or list(LV_DIRECT_HOST_UUIDS)
    if before != after:
        sel["values"] = after
        log.append(f"injectHosts {len(before)} -> {len(after)} (LV Direct only)")
        changed = True

    levels = doc.setdefault("policy", {}).setdefault("levels", {})
    lv0 = levels.setdefault("0", {})
    if lv0.get("handshake") != 12:
        lv0["handshake"] = 12
        log.append("policy handshake 4 -> 12")
        changed = True

    return changed, log


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
    args = ap.parse_args()

    c = PanelClient()
    tpl = fetch_template(c, args.template_uuid)
    doc = tpl["templateJson"]

    changed, log = apply_patch(copy.deepcopy(doc))
    for line in log:
        print(line)
    if not changed:
        print("OK: already applied")
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_fast_connect_lv_only.py --apply")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"template-before-fast-connect-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    apply_patch(doc)
    patch_template(c, tpl, args.template_uuid)
    after_template_patch("patch_fast_connect_lv_only")
    print("PATCH OK — refresh subscription, reconnect Happ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
