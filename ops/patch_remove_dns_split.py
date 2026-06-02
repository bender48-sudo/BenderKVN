#!/usr/bin/env python3
"""Emergency: remove templateJson.dns (gen=39 regression).

Happ/sing-box fails to start when dns.servers reference geosite:ru — bundled
geosite.dat has no RU section. Restores DNS via Super_Balancer catch-all (gen=38).

Usage:
    python ops/patch_remove_dns_split.py --apply
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


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    if "dns" not in doc:
        return False, ["OK: no dns block (already reverted)"]
    del doc["dns"]
    return True, ["removed templateJson.dns (Happ geosite:ru crash)"]


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
        print("\nDry-run. Apply: python ops/patch_remove_dns_split.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-remove-dns-split-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
    after_template_patch("patch_remove_dns_split")
    print("Applied: dns block removed (gen+1, no TG broadcast)")
    print("REMOVE_DNS_SPLIT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
