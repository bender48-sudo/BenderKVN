#!/usr/bin/env python3
"""P1-RED-DNS-01 / P4-DNS-04: DNS delegation + critical host resolution (run on LV or locally)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
INVENTORY = Path(__file__).resolve().parent / "dns_critical_inventory.json"


def _norm_ns(name: str) -> str:
    name = name.strip().lower()
    if name and not name.endswith("."):
        name += "."
    return name


def _dig(args: list[str], resolver: str = "8.8.8.8") -> list[str]:
    cmd = ["dig", "+short", *args, f"@{resolver}"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if proc.returncode != 0:
        raise RuntimeError(f"dig failed ({proc.returncode}): {' '.join(args)}: {proc.stderr.strip()}")
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    return lines


def _load_inventory() -> dict:
    data = json.loads(INVENTORY.read_text(encoding="utf-8"))
    if len(data.get("registrars", [])) < 2:
        raise ValueError("inventory: need >=2 registrar entries")
    return data


def _hosts_from_site_urls() -> list[str]:
    sys.path.insert(0, str(ROOT / "ops"))
    import site_urls  # noqa: E402

    hosts: list[str] = []
    for url in (
        site_urls.PANEL_URL,
        site_urls.SUB_PUBLIC_ORIGIN,
        *site_urls.SUB_ALT_PUBLIC_ORIGINS,
        site_urls.status_mirror_url(),
    ):
        h = urlparse(url).hostname
        if h and h not in hosts:
            hosts.append(h)
    return hosts


def main() -> int:
    inv = _load_inventory()
    ok = True
    print("=== DNS delegation probe (P1-RED-DNS-01) ===")

    site_hosts = _hosts_from_site_urls()
    inv_hosts = [h["fqdn"] for h in inv.get("critical_hosts", []) if h.get("must_resolve")]
    for fqdn in sorted(set(site_hosts + inv_hosts)):
        try:
            ans = _dig(["A", fqdn])
        except Exception as exc:
            print(f"FAIL: {fqdn} A: {exc}", file=sys.stderr)
            ok = False
            continue
        if not ans:
            print(f"FAIL: {fqdn} — no A record", file=sys.stderr)
            ok = False
        else:
            print(f"OK: {fqdn} -> {', '.join(ans[:3])}")

    for zone in inv.get("zones", []):
        apex = zone["apex"]
        exp_ns = {_norm_ns(x) for x in zone.get("expected_ns", [])}
        try:
            got = {_norm_ns(x) for x in _dig(["NS", apex])}
        except Exception as exc:
            print(f"FAIL: {apex} NS: {exc}", file=sys.stderr)
            ok = False
            continue
        if len(got) < 2:
            print(f"FAIL: {apex} — fewer than 2 NS ({got})", file=sys.stderr)
            ok = False
        elif exp_ns and got != exp_ns:
            print(f"WARN: {apex} NS drift expected={sorted(exp_ns)} got={sorted(got)}")
        else:
            print(f"OK: {apex} NS {sorted(got)}")

        try:
            dnskey = _dig(["DNSKEY", apex])
        except Exception:
            dnskey = []
        ds = []
        try:
            ds = _dig(["DS", apex])
        except Exception:
            pass
        sec = bool(dnskey or ds)
        want = zone.get("dnssec_enabled", False)
        if sec:
            print(f"OK: {apex} DNSSEC records present")
        elif want:
            print(f"FAIL: {apex} DNSSEC required but no DNSKEY/DS", file=sys.stderr)
            ok = False
        else:
            print(f"NOTE: {apex} DNSSEC not enabled (target: {zone.get('dnssec_runbook', 'runbook')})")

    ids = {r["id"] for r in inv.get("registrars", [])}
    print(f"OK: inventory registrars ({len(ids)}): {', '.join(sorted(ids))}")
    backup = inv.get("backup_apex", {})
    if backup.get("registrar_id") not in ids:
        print("FAIL: backup_apex.registrar_id missing from registrars", file=sys.stderr)
        ok = False

    if ok:
        print("DNS_DELEGATION_OK")
        return 0
    print("DNS_DELEGATION_FAIL", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
