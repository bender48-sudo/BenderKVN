#!/usr/bin/env python3
"""Route DNS (port 53) direct — fixes Happ sending 1.1.1.1:53 via random proxy.

Symptom in access_log: ~36% lines are udp 1.1.1.1:53 via proxy-*, causing churn/latency.

Usage:
    python ops/patch_dns_port53_direct.py
    python ops/patch_dns_port53_direct.py --apply
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

DNS_DIRECT_RULE = {
    "type": "field",
    "port": "53",
    "network": "udp,tcp",
    "outboundTag": "direct",
}


def has_dns_direct_rule(rules: list[dict]) -> bool:
    for r in rules:
        if r.get("outboundTag") == "direct" and r.get("port") == "53":
            return True
    return False


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    rules = doc.setdefault("routing", {}).setdefault("rules", [])
    if has_dns_direct_rule(rules):
        return False, ["OK: DNS port 53 -> direct rule already present"]
    # After bittorrent block, before Intl IP rules.
    insert_at = 0
    for i, r in enumerate(rules):
        if r.get("outboundTag") == "block":
            insert_at = i + 1
            break
    rules.insert(insert_at, copy.deepcopy(DNS_DIRECT_RULE))
    log.append(f"inserted DNS :53 -> direct at rule index {insert_at}")
    return True, log


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
        print("\nDry-run. Apply: python ops/patch_dns_port53_direct.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-dns53-direct-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
        print(f"FAIL PATCH HTTP {code}", file=sys.stderr)
        return 1
    after_template_patch("patch_dns_port53_direct")
    print("Applied DNS :53 -> direct (gen+1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
