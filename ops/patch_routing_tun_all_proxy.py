#!/usr/bin/env python3
"""Emergency: send international + ping traffic only via VPN (narrow RU direct).

Removes geoip:ru direct rule temporarily so 8.8.8.8 / global sites hit Super_Balancer.
Keeps .ru regexp direct for Yandex/VK etc.

Usage:
    python ops/patch_routing_tun_all_proxy.py --apply
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


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def apply_patch(rules: list[dict]) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False
    new_rules: list[dict] = []
    for i, r in enumerate(rules):
        if r.get("outboundTag") == "direct" and (r.get("ip") or []) == ["geoip:ru"]:
            log.append(f"removed R{i} geoip:ru -> direct (tun-all-proxy)")
            changed = True
            continue
        new_rules.append(r)
    if changed:
        rules[:] = new_rules
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

    c = PanelClient(timeout=120)
    tpl = fetch_template(c, args.template_uuid)
    rules = tpl["templateJson"]["routing"]["rules"]

    changed, log = apply_patch(copy.deepcopy(rules))
    for line in log:
        print(line)
    if not changed:
        print("OK: geoip:ru direct already removed")
        return 0
    if not args.apply:
        print("Dry-run. Apply with --apply")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"template-before-tun-all-proxy-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(tpl["templateJson"], ensure_ascii=False, indent=2), encoding="utf-8")
    apply_patch(tpl["templateJson"]["routing"]["rules"])
    patch_template(c, tpl, args.template_uuid)
    after_template_patch("patch_routing_tun_all_proxy")
    print("PATCH OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
