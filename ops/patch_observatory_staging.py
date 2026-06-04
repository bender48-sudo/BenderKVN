#!/usr/bin/env python3
"""VPN-AUD-430-staging: observatory dry-run with gstatic/204 probe target.

NO-GO: --apply on prod without --confirm-prod (see RUNBOOK-OBSERVATORY-STAGING.md).

Usage:
    python ops/patch_observatory_staging.py
    python ops/patch_observatory_staging.py --apply --confirm-prod
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
TARGET_DEST = "https://www.gstatic.com/generate_204"
TARGET_INTERVAL = "30s"
TARGET_TIMEOUT = "10s"


def _obs_block(tpl: dict) -> tuple[str | None, dict | None]:
    tj = tpl["templateJson"]
    for key in ("burstObservatory", "observatory"):
        if key in tj:
            return key, tj[key]
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm-prod", action="store_true", help="required with --apply on prod")
    args = ap.parse_args()

    if args.apply and not args.confirm_prod:
        print("FAIL: --apply requires --confirm-prod (staging gate)", file=sys.stderr)
        return 1

    c = PanelClient()
    uuid = site_urls.REMNA_TEMPLATE_UUID
    tpl = c.get_or_raise(f"/api/subscription-templates/{uuid}")["response"]
    key, obs = _obs_block(tpl)
    if not key or obs is None:
        print("OBSERVATORY_STAGING_NO_BLOCK (prod template has no observatory — OK)")
        return 0

    before = copy.deepcopy(obs)
    ping = obs.setdefault("pingConfig", {})
    ping["destination"] = TARGET_DEST
    ping["interval"] = TARGET_INTERVAL
    ping["timeout"] = TARGET_TIMEOUT
    obs.setdefault("subjectSelector", ["proxy"])

    changed = before != obs
    print(f"observatory key: {key}")
    print(f"destination: {ping.get('destination')}")
    print(f"interval: {ping.get('interval')}")

    if not changed:
        print("OBSERVATORY_STAGING_NO_CHANGE")
        return 0

    print("DRY-RUN: would PATCH observatory (gstatic/204)")
    if not args.apply:
        print("Apply: python ops/patch_observatory_staging.py --apply --confirm-prod")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"template-before-observatory-{int(time.time())}.json"
    snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    body = copy.deepcopy(tpl)
    body["templateJson"][key] = obs
    c.patch_or_raise(f"/api/subscription-templates/{uuid}", body)
    after_template_patch("patch_observatory_staging")
    print("OBSERVATORY_STAGING_APPLY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
