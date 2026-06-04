#!/usr/bin/env python3
"""Mandatory post-change gate for VPN template/infra (VPN-AUD-101).

Exit 0 + VPN_VERIFY_GATE_OK when all checks pass.

Layers:
  1. Profile + policy (reliability)
  2. Live sub shape (simplicity — no dead xhttp, parseable Happ)
  3. RU path probes on LV only (speed — relay + NL TCP from RU)
  4. Autotrim dry-run (no surprise PATCH in gate)
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = Path(__file__).resolve().parent
# On bvpn-lv scripts live in /opt/scripts (not repo ops/); prefer script dir.
if not (OPS / "verify_vpn_balancer_profile.py").is_file() and (ROOT / "ops" / "verify_vpn_balancer_profile.py").is_file():
    OPS = ROOT / "ops"
RU_MONITOR_ENV = Path("/etc/bvpn/ru-monitor.env")


def run(cmd: list[str], label: str, *, optional: bool = False) -> int:
    print(f"--- {label} ---")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        msg = f"WARN: {label} exit {r.returncode}" if optional else f"FAIL: {label} exit {r.returncode}"
        print(msg, file=sys.stderr)
    return r.returncode


def _on_lv() -> bool:
    return RU_MONITOR_ENV.is_file() or bool(os.environ.get("VPN_VERIFY_ON_LV"))


def _load_lv_panel_env() -> None:
    """Same token source as run_latency_selector_autotrim.sh on bvpn-lv."""
    if not RU_MONITOR_ENV.is_file():
        return
    for line in RU_MONITOR_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key in ("PANEL_TOKEN", "REMNA_API_TOKEN") and val and not os.environ.get(key):
            os.environ[key] = val


def main() -> int:
    if _on_lv():
        _load_lv_panel_env()
    py = sys.executable
    parity_cmd = [py, str(OPS / "probe_injecthosts_sub_parity.py")]
    if not _on_lv():
        parity_cmd.append("--via-lv")
    steps: list[tuple[list[str], str, bool]] = [
        ([py, str(OPS / "verify_vpn_balancer_profile.py")], "balancer profile", False),
        ([py, str(OPS / "happ_geosite_guard.py")], "happ geosite guard", False),
        ([py, str(OPS / "audit_policy_latency.py")], "policy latency audit", False),
        (parity_cmd, "inject sub parity", False),
        ([py, str(OPS / "probe_subscription.py")], "probe subscription", False),
        ([py, str(OPS / "diagnose_happ_import.py")], "happ import", False),
    ]

    if _on_lv():
        steps.extend(
            [
                ([py, str(OPS / "relay_latency_probe.py")], "relay latency probe RU", False),
                ([py, str(OPS / "nl_reachability_probe_ru.py")], "NL reachability probe RU", True),
                ([py, str(OPS / "latency_selector_autotrim.py")], "selector autotrim dry-run", False),
            ]
        )
    else:
        print("SKIP: RU probes + autotrim (run ops/vpn_verify_gate.sh on bvpn-lv)")

    ha = OPS / "smoke_sub_page_ha.sh"
    if ha.is_file() and platform.system() != "Windows":
        steps.append((["bash", str(ha)], "sub page HA", True))

    for cmd, label, optional in steps:
        rc = run(cmd, label, optional=optional)
        if rc != 0 and not optional:
            return 1

    print("VPN_VERIFY_GATE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
