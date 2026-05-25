#!/usr/bin/env python3
"""Restore Happ-stable template (pre fast-connect / random / handshake=12).

Source: .secrets/snapshots/template-before-fast-connect-20260525_194540.json
  - 8× LV+NL Direct injectHosts (no xhttp)
  - burstObservatory 30s / 10s / hicloud probe
  - leastLoad Super_Balancer, handshake 4
  - geoip:ru direct (RU bypass)
Fixes on restore: dedupe duplicate Super_Balancer domain rules.

Usage:
    python ops/patch_restore_happ_stable.py
    python ops/patch_restore_happ_stable.py --apply
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
DEFAULT_SNAPSHOT = SNAPSHOT_DIR / "template-before-fast-connect-20260525_194540.json"
DEFAULT_TEMPLATE_UUID = site_urls.REMNA_TEMPLATE_UUID
BALANCER_TAG = "Super_Balancer"


def load_snapshot(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "response" in raw and "templateJson" in raw["response"]:
        return raw["response"]["templateJson"]
    if "templateJson" in raw:
        return raw["templateJson"]
    return raw


def dedupe_proxy_domain_rules(rules: list[dict]) -> int:
    seen: set[str] = set()
    removed = 0
    i = 0
    while i < len(rules):
        r = rules[i]
        if r.get("balancerTag") == BALANCER_TAG and r.get("domain"):
            key = json.dumps(r.get("domain"), sort_keys=True)
            if key in seen:
                rules.pop(i)
                removed += 1
                continue
            seen.add(key)
        i += 1
    return removed


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


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
    ap.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--template-uuid", default=DEFAULT_TEMPLATE_UUID)
    args = ap.parse_args()

    if not args.snapshot.is_file():
        raise SystemExit(f"missing snapshot: {args.snapshot}")

    target = load_snapshot(args.snapshot)
    rules = target.setdefault("routing", {}).setdefault("rules", [])
    n = dedupe_proxy_domain_rules(rules)
    if n:
        print(f"deduped {n} duplicate proxy-domain rule(s) in snapshot")

    inj = len(target["remnawave"]["injectHosts"][0]["selector"]["values"])
    obs = "burstObservatory" in target
    strat = target["routing"]["balancers"][0]["strategy"]["type"]
    hs = target.get("policy", {}).get("levels", {}).get("0", {}).get("handshake")
    print(f"restore profile: injectHosts={inj} observatory={obs} strategy={strat} handshake={hs}")

    c = PanelClient(timeout=120)
    tpl = fetch_template(c, args.template_uuid)
    current = tpl["templateJson"]
    if current == target:
        print("OK: panel already matches stable snapshot")
        return 0

    if not args.apply:
        print("Dry-run. Apply: python ops/patch_restore_happ_stable.py --apply")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"template-before-restore-happ-stable-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"backup current: {snap}")

    tpl["templateJson"] = copy.deepcopy(target)
    patch_template(c, tpl, args.template_uuid)
    after_template_patch("patch_restore_happ_stable")
    print("RESTORE OK — delete Happ profile, re-import subscription from bot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
