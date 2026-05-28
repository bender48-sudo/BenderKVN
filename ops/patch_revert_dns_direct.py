#!/usr/bin/env python3
"""Remove DNS port-53 direct rule introduced in gen=30.

The gen=30 patch routed port 53 (UDP+TCP) direct to fix "DNS via random proxy"
slowness. Regression: Russian ISPs intercept port 53 and return filtered DNS
responses even when VPN tunnel is alive.

Proper fix is patch_dns_via_relay.py (DNS through RELAY-LV only).
This script is a safe revert to pre-gen30 state.

Usage:
    python ops/patch_revert_dns_direct.py
    python ops/patch_revert_dns_direct.py --apply
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


def _is_dns_direct_rule(rule: dict) -> bool:
    return (
        rule.get("outboundTag") == "direct"
        and str(rule.get("port") or "") == "53"
    )


def apply_revert(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    rules: list[dict] = doc.get("routing", {}).get("rules", [])
    before = len(rules)
    cleaned = [r for r in rules if not _is_dns_direct_rule(r)]
    removed = before - len(cleaned)
    if removed == 0:
        return False, ["OK: no DNS port-53 direct rule found — nothing to revert"]
    doc["routing"]["rules"] = cleaned
    log.append(f"removed {removed} DNS port-53 direct rule(s)")
    return True, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient(timeout=120)
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = copy.deepcopy(tpl["templateJson"])
    changed, log = apply_revert(doc)
    for line in log:
        print(line)
    if not changed:
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_revert_dns_direct.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-revert-dns-direct-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
    after_template_patch("patch_revert_dns_direct")
    print("Applied: DNS port-53 direct rule removed (gen+1)")
    print("Next: run patch_dns_via_relay.py --apply for proper DNS-through-relay fix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
