#!/usr/bin/env python3
"""Super_Balancer catch-all: LV+relay only (7 paths); Intl_Direct keeps 11 paths.

Happ ping measures catch-all traffic. Random 11-path on Super_Balancer (gen=35)
sends ~36% connections via NL → high ping in Happ UI (Q132 footgun).

Intl apps (TG/IG) still use Intl_Direct with full RU_MULTIPATH_SELECTOR.

Usage:
    python ops/patch_super_balancer_lv_relay_only.py
    python ops/patch_super_balancer_lv_relay_only.py --apply
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
    LV_RELAY_SELECTOR,
    RU_MULTIPATH_SELECTOR,
)
from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402
from vpn_apply_guard import print_guardrail_banner, require_owner_approval  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"

SUPER_TAG = "Super_Balancer"
INTL_TAG = "Intl_Direct"


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False
    for b in doc.get("routing", {}).get("balancers", []):
        tag = b.get("tag")
        if tag == SUPER_TAG:
            want = list(LV_RELAY_SELECTOR)
            old = list(b.get("selector") or [])
            if old != want:
                b["selector"] = want
                log.append(f"{SUPER_TAG}: {len(old)} -> {len(want)} paths (LV+relay, Happ ping)")
                changed = True
            else:
                log.append(f"OK: {SUPER_TAG} already LV+relay ({len(want)} paths)")
        elif tag == INTL_TAG:
            want = list(RU_MULTIPATH_SELECTOR)
            old = list(b.get("selector") or [])
            if old != want:
                b["selector"] = want
                log.append(f"{INTL_TAG}: {len(old)} -> {len(want)} paths (full multipath)")
                changed = True
            else:
                log.append(f"OK: {INTL_TAG} already {len(want)} paths")
    return changed, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--owner-approved", action="store_true",
                    help="Required for --apply: explicit owner approval for this capacity-reducing patch")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    print_guardrail_banner("patch_super_balancer_lv_relay_only", capacity_reducing=True)

    c = PanelClient(timeout=120)
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = copy.deepcopy(tpl["templateJson"])
    changed, log = apply_patch(doc)
    for line in log:
        print(line)
    if not changed:
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_super_balancer_lv_relay_only.py --apply --owner-approved")
        return 0

    require_owner_approval(
        "patch_super_balancer_lv_relay_only", owner_approved=args.owner_approved
    )

    snap = SNAPSHOT_DIR / f"template-before-super-lv-relay-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
    after_template_patch("patch_super_balancer_lv_relay_only")
    print("Applied: Super_Balancer LV+relay only; Intl_Direct 11-path (gen+1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
