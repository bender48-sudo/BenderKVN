#!/usr/bin/env python3
"""VPN-AUD-280: post-apply check after relay-NL :443 inject (VPN-AUD-279).

Usage:
    python ops/verify_relay_nl_443_live.py
    python ops/verify_relay_nl_443_live.py --ssh-gate
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
ROOT = _OPS.parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from balancer_selectors import (  # noqa: E402
    INTL_RELAY_NL_443_SELECTOR,
    RELAY6_SELECTOR,
    is_stealth_split_relay_nl_443_profile,
)
from panel_client import PanelClient  # noqa: E402
from patch_add_relay_nl_443_hosts import is_relay_nl_443  # noqa: E402

MIN_INJECT = 16
MIN_RELAY_NL_HOSTS = 6


def _ssh_gate() -> tuple[int, str]:
    remote = "set -a; . /etc/bvpn/ru-monitor.env; set +a; python3 /opt/scripts/vpn_verify_gate.py"
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=25", "bvpn-lv", remote],
        capture_output=True,
        text=True,
        timeout=240,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssh-gate", action="store_true", help="also run vpn_verify_gate on LV")
    args = ap.parse_args()

    errors: list[str] = []

    c = PanelClient()
    tpl = c.get_or_raise(f"/api/subscription-templates/{site_urls.REMNA_TEMPLATE_UUID}")["response"]
    doc = tpl["templateJson"]
    inj = doc.get("remnawave", {}).get("injectHosts", [{}])[0].get("selector", {}).get("values") or []
    print(f"injectHosts: {len(inj)} (want>={MIN_INJECT})")
    if len(inj) < MIN_INJECT:
        errors.append(f"injectHosts={len(inj)}")

    if not is_stealth_split_relay_nl_443_profile(doc):
        errors.append("template not stealth_split_relay_nl_443")
    else:
        bal = {b["tag"]: b for b in (doc.get("routing") or {}).get("balancers") or []}
        stealth_n = len((bal.get("Intl_Stealth") or {}).get("selector") or [])
        intl_n = len((bal.get("Intl_Direct") or {}).get("selector") or [])
        print(f"Intl_Stealth: {stealth_n} paths (want {len(RELAY6_SELECTOR)})")
        print(f"Intl_Direct: {intl_n} paths (want {len(INTL_RELAY_NL_443_SELECTOR)})")
        if stealth_n != len(RELAY6_SELECTOR):
            errors.append(f"stealth selector={stealth_n}")
        if intl_n != len(INTL_RELAY_NL_443_SELECTOR):
            errors.append(f"intl selector={intl_n}")

    hosts = c.get_or_raise("/api/hosts")["response"]
    rnl = [h for h in hosts if is_relay_nl_443(h) and not h.get("isDisabled")]
    print(f"relay-NL :443 enabled hosts: {len(rnl)} (want>={MIN_RELAY_NL_HOSTS})")
    if len(rnl) < MIN_RELAY_NL_HOSTS:
        errors.append(f"enabled relay-NL hosts={len(rnl)}")
    visible = [h for h in rnl if not h.get("isHidden")]
    if visible:
        errors.append(f"relay-NL must be isHidden for inject export, visible={len(visible)}")

    if args.ssh_gate:
        print("=== vpn_verify_gate (LV) ===")
        rc, out = _ssh_gate()
        print(out[-2000:] if len(out) > 2000 else out)
        if rc != 0 or "VPN_VERIFY_GATE_OK" not in out:
            errors.append("vpn_verify_gate LV")

    if errors:
        for e in errors:
            print(f"WARN: {e}", file=sys.stderr)
        print("RELAY_NL_443_LIVE_FAIL", file=sys.stderr)
        return 1

    print("RELAY_NL_443_LIVE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
