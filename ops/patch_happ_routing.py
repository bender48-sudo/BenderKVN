#!/usr/bin/env python3
"""Push BenderVPN RU Happ routing profile via subscription-settings.happRouting.

Happ clients import happ://routing/onadd/... on subscription refresh (iOS/Android/Windows).
Windows still needs TUN enabled locally — routing profile alone is not enough on desktop.

Usage:
    python ops/patch_happ_routing.py              # dry-run
    python ops/patch_happ_routing.py --apply
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from generate_happ_routing_link import build_profile, profile_to_deeplink  # noqa: E402
from panel_client import PanelClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"


def target_routing_link() -> str:
    return profile_to_deeplink(build_profile(use_bundled_geofiles=True), activate=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    target = target_routing_link()
    print(f"target happRouting length: {len(target)}")
    print(f"target prefix: {target[:40]}...")

    c = PanelClient()
    settings = c.get_or_raise("/api/subscription-settings")["response"]
    before = settings.get("happRouting") or ""
    print(f"current happRouting length: {len(before)}")

    if before == target:
        print("OK: already patched")
        return 0

    if not args.apply:
        print("dry-run: pass --apply to PATCH subscription-settings")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    snap = SNAPSHOT_DIR / f"subscription-settings-before-happ-routing-{ts}.json"
    snap.write_text(json.dumps({"response": settings}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    payload = copy.deepcopy(settings)
    payload["happRouting"] = target
    code, body = c.patch("/api/subscription-settings", body=payload)
    if code not in (200, 201):
        raise SystemExit(f"PATCH failed HTTP {code}: {body!s}"[:500])
    after = c.get_or_raise("/api/subscription-settings")["response"].get("happRouting") or ""
    if after != target:
        raise SystemExit(f"verify failed: happRouting length {len(after)} != {len(target)}")
    print(f"OK: happRouting patched ({len(after)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
