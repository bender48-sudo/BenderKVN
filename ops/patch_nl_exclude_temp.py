#!/usr/bin/env python3
"""Temporarily exclude NL direct (proxy-8..11) from Super_Balancer + Intl_Direct.

Symptom: random balancer sends ~36% connections to NL direct; if NL IP is
throttled/blocked by RU DPI, ~36% of app connections timeout → high perceived
latency + "only Latvia works".

Selector after patch: LV direct (proxy..4) + RELAY-LV (proxy-5..7) = 7 paths.
Stable, both known reachable from Russia.

Revert with patch_balancer_direct_first_intl.py --apply (restores 11-path
RU_MULTIPATH_SELECTOR) once NL reachability from Russia is confirmed.

Usage:
    python ops/patch_nl_exclude_temp.py
    python ops/patch_nl_exclude_temp.py --apply
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

# LV direct + RELAY→LV only — no NL direct (proxy-8..11)
LV_RELAY_SELECTOR: list[str] = [
    "proxy",
    "proxy-2",
    "proxy-3",
    "proxy-4",
    "proxy-5",
    "proxy-6",
    "proxy-7",
]

_BALANCER_TAGS = ("Super_Balancer", "Intl_Direct")


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    balancers: list[dict] = doc.get("routing", {}).get("balancers", [])
    changed = False
    for b in balancers:
        if b.get("tag") not in _BALANCER_TAGS:
            continue
        old = list(b.get("selector") or [])
        if old == LV_RELAY_SELECTOR:
            log.append(f"OK {b['tag']}: already LV+relay-only selector")
            continue
        b["selector"] = list(LV_RELAY_SELECTOR)
        log.append(f"{b['tag']}: {len(old)} → {len(LV_RELAY_SELECTOR)} paths (NL excluded)")
        changed = True
    if not changed and not log:
        log.append("WARN: Super_Balancer / Intl_Direct not found in template")
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
        print(
            "\nDry-run. Apply: python ops/patch_nl_exclude_temp.py --apply"
            "\nRevert: python ops/patch_balancer_direct_first_intl.py --apply"
        )
        return 0

    snap = SNAPSHOT_DIR / f"template-before-nl-exclude-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
    after_template_patch("patch_nl_exclude_temp")
    print("Applied: NL direct excluded from balancers (7-path LV+relay selector, gen+1)")
    print("Revert when NL confirmed reachable from Russia: patch_balancer_direct_first_intl.py --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
