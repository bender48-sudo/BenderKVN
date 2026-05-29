#!/usr/bin/env python3
"""Hotfix: split Super (LV direct DNS) vs Intl (relay-only TG/IG).

Regression gen=44: same 10-path random on Super+Intl sent TG/DNS through
LV direct (dead from RU) and relay (DNS :53 blocked) → 955ms ping, TG files fail.

Fix (VPN-INCIDENT-LESSONS §4):
  Super_Balancer → SUPER_LV_DIRECT_SELECTOR (proxy..4) — catch-all/DNS/Happ ping
  Intl_Direct    → INTL_RELAY_ONLY_SELECTOR (proxy-5..7,12..14) — Meta/TG only

Usage:
    python ops/patch_relay_routing_split.py
    python ops/patch_relay_routing_split.py --apply
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

SUPER_TAG = "Super_Balancer"
INTL_TAG = "Intl_Direct"


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False
    want = {
        SUPER_TAG: list(SUPER_LV_DIRECT_SELECTOR),
        INTL_TAG: list(INTL_RELAY_ONLY_SELECTOR),
    }
    for b in doc.get("routing", {}).get("balancers", []):
        tag = b.get("tag")
        if tag not in want:
            continue
        old = list(b.get("selector") or [])
        if old != want[tag]:
            b["selector"] = want[tag]
            log.append(f"{tag}: {len(old)} -> {len(want[tag])} paths")
            changed = True
        else:
            log.append(f"OK: {tag} already {len(want[tag])} paths")
        if (b.get("strategy") or {}).get("type") != "random":
            b.setdefault("strategy", {})["type"] = "random"
            log.append(f"{tag}: strategy -> random")
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
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_relay_routing_split.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-relay-routing-split-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
    after_template_patch("patch_relay_routing_split")
    print("Applied: Super=LV direct (4); Intl=relay×2 (6). Refresh Happ sub (gen+1).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
