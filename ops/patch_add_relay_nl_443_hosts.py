#!/usr/bin/env python3
"""VPN-AUD-275: create RELAY→NL :443 panel hosts (PoC, not in injectHosts).

Mirrors legacy :9443 hosts (same NL inbound/SNI) on relay#1 and relay#2 at :443.
Hosts are **isHidden + isDisabled** until inject/balancer staging (runbook §NO-GO Stealth).

Does **not** PATCH subscription template.

Usage:
    python ops/patch_add_relay_nl_443_hosts.py
    python ops/patch_add_relay_nl_443_hosts.py --apply
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

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"

RELAY1_IP = site_urls.RU_RELAY_HOST
RELAY2_IP = "46.173.28.252"
RELAY_NL_PORT = 443
LEGACY_NL_PORT = 9443


def is_legacy_relay_nl_9443(host: dict) -> bool:
    remark = str(host.get("remark") or "")
    if "Relay" not in remark or "Netherlands" not in remark:
        return False
    try:
        return int(host.get("port") or 0) == LEGACY_NL_PORT
    except (TypeError, ValueError):
        return "9443" in remark


def _relay_nl_remark(remark: str) -> bool:
    return "Relay" in remark and ("Netherlands" in remark or "Relay NL" in remark or "Relay2 NL" in remark)


def is_relay_nl_443(host: dict) -> bool:
    remark = str(host.get("remark") or "")
    if not _relay_nl_remark(remark):
        return False
    try:
        return int(host.get("port") or 0) == RELAY_NL_PORT
    except (TypeError, ValueError):
        return False


def _sni_suffix(remark: str) -> str:
    if "·" in remark:
        return remark.split("·", 1)[-1].strip()
    return remark


def create_host(c: PanelClient, src: dict, *, address: str, relay_tag: str) -> str:
    suffix = _sni_suffix(src.get("remark") or "")
    remark = f"🇳🇱 Relay NL · {suffix}" if relay_tag == "1" else f"🇳🇱 Relay2 NL · {suffix}"
    body = {
        "remark": remark,
        "address": address,
        "port": RELAY_NL_PORT,
        "sni": src.get("sni"),
        "fingerprint": src.get("fingerprint") or "chrome",
        "isDisabled": True,
        "isHidden": True,
        "inbound": copy.deepcopy(src.get("inbound") or {}),
        "nodes": list(src.get("nodes") or []),
        "sockoptParams": copy.deepcopy(src.get("sockoptParams") or {}),
    }
    code, resp = c.post("/api/hosts", body=body)
    if code not in (200, 201):
        raise RuntimeError(f"POST host HTTP {code}: {resp!s}"[:300])
    uuid = resp["response"]["uuid"]
    print(f"created {uuid[:8]} | {remark} | {address}:{RELAY_NL_PORT}")
    return uuid


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    c = PanelClient(timeout=120)
    hosts = c.get_or_raise("/api/hosts")["response"]
    legacy = [h for h in hosts if is_legacy_relay_nl_9443(h)]
    legacy.sort(key=lambda x: x.get("remark") or "")
    if len(legacy) < 3:
        print(f"FAIL: need 3 legacy relay-NL :9443 hosts, got {len(legacy)}", file=sys.stderr)
        return 1

    existing = [h for h in hosts if is_relay_nl_443(h)]
    by_key = {(h.get("address"), h.get("sni")): h for h in existing}

    plan: list[tuple[str, dict, str]] = []
    for src in legacy:
        plan.append((RELAY1_IP, src, "1"))
        plan.append((RELAY2_IP, src, "2"))

    print(f"legacy :9443 templates: {len(legacy)}")
    print(f"existing relay-NL :443: {len(existing)}")
    to_create = []
    for addr, src, tag in plan:
        key = (addr, src.get("sni"))
        if key in by_key:
            h = by_key[key]
            print(f"OK exists: {h.get('remark')!r} @ {addr}:{RELAY_NL_PORT}")
        else:
            to_create.append((addr, src, tag))
            print(f"dry-run create: Relay{tag} NL · {_sni_suffix(src.get('remark') or '')} @ {addr}:{RELAY_NL_PORT}")

    if not to_create:
        print("RELAY_NL_443_HOSTS_OK (nothing to create)")
        return 0

    if not args.apply:
        print(f"\nDry-run: would create {len(to_create)} host(s).")
        print("Apply: python ops/patch_add_relay_nl_443_hosts.py --apply")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"hosts-before-relay-nl-443-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(
        json.dumps({"legacy": legacy, "existing_443": existing}, indent=2),
        encoding="utf-8",
    )
    print(f"snapshot: {snap.name}")

    created = 0
    for addr, src, tag in to_create:
        create_host(c, src, address=addr, relay_tag=tag)
        created += 1
    print(f"created {created} relay-NL :443 host(s) (hidden+disabled)")
    print("RELAY_NL_443_HOSTS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
