#!/usr/bin/env python3
"""Remove mislabeled Cloudflare CIDRs from Intl_Direct IP rule.

gen=28 added 104.18.0.0/16 + 104.19.0.0/16 labeled "OpenAI/ChatGPT".
These are Cloudflare ranges, not OpenAI. Effect:

  speedtest.net / fast.com (Ookla/Netflix) use Cloudflare CDN.
  Their IPs hit the Intl_Direct IP rule → Intl_Direct balancer (11 paths,
  includes NL proxy-8..11) → ~36% of speed-test connections go through NL.
  If NL is slow/throttled from Russia, speed tests fail or show 0 Mbit.

Fix: remove 104.18-19/16 from Intl_Direct IP list. Speed-test traffic
falls through to Super_Balancer catch-all (LV+relay, 7 paths). ChatGPT
is blocked in RU but its domains should be handled by domain rules, not
coarse /16 Cloudflare CIDR ranges.

Usage:
    python ops/patch_remove_cloudflare_intl_cidr.py
    python ops/patch_remove_cloudflare_intl_cidr.py --apply
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

_CLOUDFLARE_RANGES = {"104.18.0.0/16", "104.19.0.0/16"}
_INTL_BALANCER_TAG = "Intl_Direct"


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False
    rules: list[dict] = doc.get("routing", {}).get("rules", [])
    for i, r in enumerate(rules):
        if r.get("balancerTag") != _INTL_BALANCER_TAG:
            continue
        ip_list: list[str] = list(r.get("ip") or [])
        cf_found = set(ip_list) & _CLOUDFLARE_RANGES
        if not cf_found:
            log.append(f"rule[{i}] Intl_Direct: Cloudflare CIDRs already absent")
            continue
        new_ip = [x for x in ip_list if x not in _CLOUDFLARE_RANGES]
        r["ip"] = new_ip
        log.append(
            f"rule[{i}] Intl_Direct: removed {sorted(cf_found)} "
            f"({len(ip_list)} -> {len(new_ip)} CIDRs)"
        )
        changed = True
    if changed:
        log.append(
            "speedtest.net/fast.com now via Super_Balancer (LV+relay, 7 paths)"
        )
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
        print("\nDry-run. Apply: python ops/patch_remove_cloudflare_intl_cidr.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-rm-cf-cidr-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
    after_template_patch("patch_remove_cloudflare_intl_cidr")
    print("Applied: Cloudflare /16 removed from Intl_Direct — speedtest via Super_Balancer (gen+1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
