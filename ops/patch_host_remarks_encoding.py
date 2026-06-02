#!/usr/bin/env python3
"""Repair panel host remarks corrupted to literal '?' (Happ / sub-page show ?????).

Root cause: remarks were saved with ASCII replacement (emoji U+1F1FB+U+1F1F7 and
middle dot U+00B7 became '?'). Netherlands hosts are OK; Latvia / Amsterdam /
Relay LV|AMS rows need PATCH.

Canonical pattern (see BenderVPN_Documentation_v2_5.md + NL hosts):
  Latvia · Direct · MS  ->  🇱🇻 Latvia · Direct · MS
  Relay LV · X5         ->  🇱🇻 Relay LV · X5
  Amsterdam · Direct · MS (no flag; AMS decom)
  Relay AMS · X5

Usage:
    python ops/patch_host_remarks_encoding.py              # dry-run
    python ops/patch_host_remarks_encoding.py --apply
"""
from __future__ import annotations

import argparse
import io
import json
import re
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
SEP = " · "
LV_FLAG = "\U0001f1f1\U0001f1fb "  # 🇱🇻 (L+V regional indicators)
# Wrong flag from an earlier botched patch (V+R instead of L+V).
_BAD_LV_PREFIX = "\U0001f1fb\U0001f1f7 "


def fix_remark(old: str) -> str | None:
    if old.startswith(_BAD_LV_PREFIX):
        rest = old[len(_BAD_LV_PREFIX) :]
        return LV_FLAG + rest
    if "?" not in old:
        return None
    s = old.replace(" ?? ", SEP)
    s = re.sub(r"^\?+\s*", "", s)
    if s.startswith("Latvia "):
        return LV_FLAG + s
    if s.startswith("Relay LV"):
        return LV_FLAG + s
    # Amsterdam / Relay AMS — plain text (matches internal docs table)
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    c = PanelClient()
    hosts = c.get_or_raise("/api/hosts")["response"]
    if not isinstance(hosts, list):
        raise SystemExit(f"unexpected hosts payload: {type(hosts)}")

    plan: list[tuple[str, str, str]] = []
    for h in hosts:
        uid = h.get("uuid")
        old = h.get("remark") or ""
        new = fix_remark(old)
        if new and new != old:
            plan.append((uid, old, new))

    if not plan:
        print("OK: no corrupted host remarks")
        return 0

    print(f"hosts to fix: {len(plan)}")
    for uid, old, new in plan:
        print(f"  {uid[:8]}  {old!r}")
        print(f"         -> {new!r}")

    if not args.apply:
        print("dry-run: pass --apply to PATCH /api/hosts")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    snap = SNAPSHOT_DIR / f"hosts-remarks-before-encoding-fix-{ts}.json"
    snap.write_text(
        json.dumps({"hosts": hosts}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"snapshot: {snap}")

    ok = 0
    for uid, _old, new in plan:
        code, body = c.patch("/api/hosts", body={"uuid": uid, "remark": new})
        if code not in (200, 201, 204):
            raise SystemExit(f"PATCH {uid} HTTP {code}: {body!s}"[:500])
        got = c.get_or_raise(f"/api/hosts/{uid}")["response"].get("remark")
        if got != new:
            raise SystemExit(f"verify failed {uid}: {got!r} != {new!r}")
        ok += 1
    print(f"OK: patched {ok} host remarks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
