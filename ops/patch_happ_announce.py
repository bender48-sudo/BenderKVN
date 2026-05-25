#!/usr/bin/env python3
"""Fix Happ subscription description (Announce header) showing as ????.

Happ iOS/Android often fails on UTF-8 punctuation in base64 Announce
(guillemets, em-dash). Use plain Cyrillic + ASCII hyphen.

Usage:
    python ops/patch_happ_announce.py              # dry-run
    python ops/patch_happ_announce.py --apply
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

from panel_client import PanelClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"

# No «» or em-dash — Happ-safe.
TARGET_ANNOUNCE = "Нажмите Подключить - сервер выберется автоматически"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    c = PanelClient()
    settings = c.get_or_raise("/api/subscription-settings")["response"]
    before = settings.get("happAnnounce") or ""
    print(f"current happAnnounce: {before!r}")
    print(f"target happAnnounce:  {TARGET_ANNOUNCE!r}")

    if before == TARGET_ANNOUNCE:
        print("OK: already patched")
        return 0

    if not args.apply:
        print("dry-run: pass --apply to PATCH subscription-settings")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    snap = SNAPSHOT_DIR / f"subscription-settings-before-happ-announce-{ts}.json"
    snap.write_text(json.dumps({"response": settings}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    payload = copy.deepcopy(settings)
    payload["happAnnounce"] = TARGET_ANNOUNCE
    code, body = c.patch("/api/subscription-settings", body=payload)
    if code not in (200, 201):
        raise SystemExit(f"PATCH failed HTTP {code}: {body!s}"[:500])
    after = body.get("response", body).get("happAnnounce", TARGET_ANNOUNCE)
    print(f"OK: happAnnounce -> {after!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
