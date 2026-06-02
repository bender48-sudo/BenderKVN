#!/usr/bin/env python3
"""VPN-AUD-230: split DNS in subscription template (DoH intl, localhost RU).

Replaces catch-all DNS via Super_Balancer with explicit split resolution:
  - RU (.ru, geosite:ru) → system DNS (localhost) — fast, no 1.1.1.1 leak
  - Intl → DoH (Google + Cloudflare)

Does NOT add routing port-53→direct (gen=30 regression).

Usage:
    python ops/patch_dns_split_config.py
    python ops/patch_dns_split_config.py --apply
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

from dns_split_config import build_split_dns_config, verify_dns_split_config  # noqa: E402
from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    target = build_split_dns_config()
    current = doc.get("dns")
    if current == target:
        log.append("OK: dns split config already canonical")
        return False, log
    doc["dns"] = copy.deepcopy(target)
    log.append(f"dns.servers -> {len(target['servers'])} entries (DoH intl + localhost RU)")
    log.append(f"dns.queryStrategy -> {target['queryStrategy']}")
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

    errs = verify_dns_split_config(doc if changed else tpl["templateJson"])
    if not changed:
        if errs:
            for e in errs:
                print(f"WARN: {e}")
        else:
            print("DNS_SPLIT_CONFIG_OK (already applied)")
        return 0 if not errs else 1

    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_dns_split_config.py --apply")
        if errs:
            print("Post-patch verify errors:", "; ".join(errs))
        return 0

    snap = SNAPSHOT_DIR / f"template-before-dns-split-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.parent.mkdir(parents=True, exist_ok=True)
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

    after_template_patch("patch_dns_split_config")
    post_errs = verify_dns_split_config(doc)
    if post_errs:
        print("FAIL verify:", "; ".join(post_errs), file=sys.stderr)
        return 1
    print("Applied split DNS (gen+1, no TG broadcast)")
    print("DNS_SPLIT_CONFIG_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
