#!/usr/bin/env python3
"""Keep observatory+leastLoad but only LV :443 Direct hosts (no Relay/NL).

Root cause: ping OK on 14 outbounds, apps dead — leastLoad picks RELAY/NL with
best probe RTT but broken for real TLS from RU (DPI / dead relay path).

Usage:
    python ops/patch_injecthosts_lv_direct_only.py --apply
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

LV_DIRECT_ONLY = [
    "e7e1d97b-922a-4f50-8f84-d4551620fa4f",
    "fa51422a-0b79-4f8c-9a5b-b396ec8d4ec1",
    "fb3226f7-d8fe-4637-8f95-4938682a945f",
    "33f70ce9-f637-416b-bdc2-ca4c45a6f10e",
]

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


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before = list(sel.get("values") or [])
    if before != LV_DIRECT_ONLY:
        sel["values"] = list(LV_DIRECT_ONLY)
        log.append(f"injectHosts {len(before)} -> {len(LV_DIRECT_ONLY)} (LV Direct :443 only)")
        changed = True

    if "burstObservatory" not in doc:
        doc["burstObservatory"] = copy.deepcopy(OBSERVATORY)
        log.append("ensured burstObservatory")
        changed = True
    else:
        if doc["burstObservatory"] != OBSERVATORY:
            doc["burstObservatory"] = copy.deepcopy(OBSERVATORY)
            log.append("tuned burstObservatory 60s/10s")
            changed = True

    for b in doc.get("routing", {}).get("balancers", []):
        if b.get("tag") != BALANCER_TAG:
            continue
        if b.pop("fallbackTag", None):
            log.append("removed fallbackTag")
            changed = True
        if b.get("strategy", {}).get("type") != "leastLoad":
            b["strategy"] = {
                "type": "leastLoad",
                "settings": {
                    "maxRTT": "350ms",
                    "expected": 2,
                    "baselines": ["50ms", "150ms"],
                    "tolerance": 0.02,
                },
            }
            log.append("strategy -> leastLoad")
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

    changed, log = apply_patch(copy.deepcopy(doc))
    for line in log:
        print(line)
    if not changed:
        print("OK: already LV Direct only")
        return 0
    if not args.apply:
        print("Dry-run. Apply with --apply")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"template-before-lv-direct-only-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    apply_patch(doc)
    patch_template(c, tpl, args.template_uuid)
    after_template_patch("patch_injecthosts_lv_direct_only")
    print("PATCH OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
