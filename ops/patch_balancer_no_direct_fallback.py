#!/usr/bin/env python3
"""Hotfix: Super_Balancer fallbackTag=direct sends TG/IG to bypass when observatory fails.

User error_log: all proxy-* ping timeout (2s) to gstatic → leastLoad has no healthy
outbound → fallbackTag direct → access_log 100% [socks -> direct], messages fail.

Changes:
  - Remove routing.balancers[].fallbackTag (never silently bypass VPN)
  - burstObservatory pingConfig.timeout: 10s (was 2s)
  - burstObservatory pingConfig.destination: hicloud generate_204 (RU-friendly probe)

Usage:
    python ops/patch_balancer_no_direct_fallback.py
    python ops/patch_balancer_no_direct_fallback.py --apply
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

TARGET_TIMEOUT = "10s"
TARGET_DESTINATION = "http://connectivitycheck.platform.hicloud.com/generate_204"
BALANCER_TAG = "Super_Balancer"


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    balancers = doc.setdefault("routing", {}).setdefault("balancers", [])
    for b in balancers:
        if b.get("tag") != BALANCER_TAG:
            continue
        if b.pop("fallbackTag", None) == "direct":
            log.append(f"removed fallbackTag=direct from {BALANCER_TAG}")
            changed = True
        elif "fallbackTag" in b:
            log.append(f"removed fallbackTag={b.pop('fallbackTag')!r} from {BALANCER_TAG}")
            changed = True

    obs_key = "burstObservatory" if "burstObservatory" in doc else "observatory"
    if obs_key not in doc:
        log.append(f"WARN: no {obs_key} in template")
        return changed, log

    ping = doc[obs_key].setdefault("pingConfig", {})
    if ping.get("timeout") != TARGET_TIMEOUT:
        ping["timeout"] = TARGET_TIMEOUT
        log.append(f"{obs_key} timeout -> {TARGET_TIMEOUT}")
        changed = True
    if ping.get("destination") != TARGET_DESTINATION:
        ping["destination"] = TARGET_DESTINATION
        log.append(f"{obs_key} destination -> hicloud generate_204")
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

    print("BEFORE balancer:", json.dumps(doc["routing"]["balancers"], ensure_ascii=False))
    obs_key = "burstObservatory" if "burstObservatory" in doc else "observatory"
    print("BEFORE observatory ping:", json.dumps(doc.get(obs_key, {}).get("pingConfig"), ensure_ascii=False))

    changed, log = apply_patch(copy.deepcopy(doc))
    for line in log:
        print(line)
    if not changed:
        print("OK: already patched")
        return 0

    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_balancer_no_direct_fallback.py --apply")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"template-before-balancer-fallback-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    apply_patch(doc)
    patch_template(c, tpl, args.template_uuid)
    after_template_patch("patch_balancer_no_direct_fallback")
    print("PATCH OK — refresh subscription in Happ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
