#!/usr/bin/env python3
"""VPN-AUD-271b: disable legacy RELAY→NL :9443 panel hosts (not in injectHosts).

Dry-run by default. Sets isDisabled=true on NL hosts with port 9443 or Relay+NL remark.

Usage:
    python ops/disable_relay_nl_legacy_hosts.py
    python ops/disable_relay_nl_legacy_hosts.py --apply
"""
from __future__ import annotations

import argparse
import io
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

RELAY_NL_PORT = 9443
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / ".secrets" / "snapshots"


def is_legacy_relay_nl(host: dict) -> bool:
    """Panel hosts: Relay→NL terminate on RU relay IP, port 9443 (removed from injectHosts gen=29)."""
    remark = str(host.get("remark") or "")
    if "Relay" not in remark or "Netherlands" not in remark:
        return False
    try:
        if int(host.get("port") or 0) == RELAY_NL_PORT:
            return True
    except (TypeError, ValueError):
        pass
    if "9443" in remark:
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    c = PanelClient()
    hosts = c.get_or_raise("/api/hosts")["response"]
    if not isinstance(hosts, list):
        hosts = hosts.get("hosts", hosts.get("items", []))

    targets = [h for h in hosts if is_legacy_relay_nl(h) and not h.get("isDisabled")]
    already = [h for h in hosts if is_legacy_relay_nl(h) and h.get("isDisabled")]

    print(f"legacy RELAY→NL hosts: {len(targets)} to disable, {len(already)} already disabled")
    for h in targets:
        print(f"  {h.get('uuid')} | {h.get('remark')!r} port={h.get('port')}")

    if not targets:
        print("RELAY_NL_LEGACY_DISABLE_OK (nothing to do)")
        return 0

    if not args.apply:
        print("Dry-run. Apply: python ops/disable_relay_nl_legacy_hosts.py --apply")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"hosts-before-relay-nl-disable-{time.strftime('%Y%m%d_%H%M%S')}.json"
    import json

    snap.write_text(
        json.dumps({"hosts": [h for h in hosts if is_legacy_relay_nl(h)]}, indent=2),
        encoding="utf-8",
    )
    print(f"snapshot: {snap.name}")

    ok = 0
    for h in targets:
        uuid = h["uuid"]
        code, body = c.patch("/api/hosts", body={"uuid": uuid, "isDisabled": True})
        if code == 200 and (body.get("response") or {}).get("isDisabled"):
            ok += 1
        else:
            print(f"FAIL patch {uuid}: HTTP {code}", file=sys.stderr)
    print(f"disabled {ok}/{len(targets)}")
    if ok == len(targets):
        print("RELAY_NL_LEGACY_DISABLE_OK")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
