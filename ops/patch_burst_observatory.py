#!/usr/bin/env python3
"""Q-VPN-STAB-011: tune burstObservatory in subscription template.

Changes (when drift from target):
  - pingConfig.interval: 30s (was 15s)
  - subjectSelector: ["proxy"]
  - pingConfig.destination: https://www.gstatic.com/generate_204

Usage:
    python ops/patch_burst_observatory.py              # dry-run
    python ops/patch_burst_observatory.py --apply      # PATCH + notify bump
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

TARGET_INTERVAL = "30s"
TARGET_SELECTOR = ["proxy"]
TARGET_DESTINATION = "https://www.gstatic.com/generate_204"


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def apply_observatory_tuning(doc: dict) -> tuple[bool, dict]:
    """Return (changed, before_snapshot)."""
    obs_key = "burstObservatory" if "burstObservatory" in doc else "observatory"
    if obs_key not in doc:
        raise RuntimeError("templateJson has no burstObservatory/observatory block")

    before = copy.deepcopy(doc[obs_key])
    obs = doc[obs_key]
    ping = obs.setdefault("pingConfig", {})
    ping["interval"] = TARGET_INTERVAL
    ping["destination"] = TARGET_DESTINATION
    obs["subjectSelector"] = list(TARGET_SELECTOR)

    changed = before != obs
    return changed, before


def patch_template(c: PanelClient, tpl: dict) -> None:
    doc = tpl["templateJson"]
    minimal = {
        "uuid": tpl.get("uuid") or DEFAULT_TEMPLATE_UUID,
        "templateJson": doc,
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201):
        raise RuntimeError(f"PATCH template HTTP {code}: {body!s}"[:500])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="PATCH template (default: dry-run)")
    ap.add_argument("--template-uuid", default=DEFAULT_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient()
    tpl = fetch_template(c, args.template_uuid)
    doc = copy.deepcopy(tpl["templateJson"])

    obs_key = "burstObservatory" if "burstObservatory" in doc else "observatory"
    print(f"current {obs_key}:")
    print(json.dumps(doc.get(obs_key) or {}, indent=2, ensure_ascii=False))

    changed, before = apply_observatory_tuning(doc)
    if not changed:
        print("OK: burstObservatory already matches target — no PATCH")
        return 0

    print(f"\ntarget {obs_key}:")
    print(json.dumps(doc[obs_key], indent=2, ensure_ascii=False))

    if not args.apply:
        print("\ndry-run: pass --apply to PATCH template")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    snap = SNAPSHOT_DIR / f"template-before-observatory-{ts}.json"
    snap.write_text(json.dumps({"response": tpl}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    tpl["templateJson"] = doc
    patch_template(c, tpl)
    print("OK: burstObservatory PATCH applied")

    try:
        after_template_patch("patch_burst_observatory")
    except Exception as exc:
        print(f"[sub-config] WARN: notify/push failed ({exc})")
        print("[sub-config] Run: python ops/push_sub_config_generation_ams.py --generation N")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
