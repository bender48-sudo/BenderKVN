#!/usr/bin/env python3
"""Mandatory post-change gate for VPN template/infra (VPN-AUD-101).

Exit 0 + VPN_VERIFY_GATE_OK when all checks pass.
"""
from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"


def run(cmd: list[str], label: str) -> int:
    print(f"--- {label} ---")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        print(f"FAIL: {label} exit {r.returncode}", file=sys.stderr)
    return r.returncode


def main() -> int:
    py = sys.executable
    steps = [
        ([py, str(OPS / "verify_vpn_balancer_profile.py")], "balancer profile"),
        ([py, str(OPS / "probe_subscription.py")], "probe subscription"),
        ([py, str(OPS / "diagnose_happ_import.py")], "happ import"),
        ([py, str(OPS / "transport_mux_audit.py")], "transport mux"),
        ([py, str(OPS / "smoke_ams_safe_deploy.py"), "--skip-sub-probe"], "ams safe deploy"),
    ]
    ha = OPS / "smoke_sub_page_ha.sh"
    if ha.is_file() and platform.system() != "Windows":
        steps.append((["bash", str(ha)], "sub page HA"))
    elif ha.is_file():
        print("SKIP: sub page HA (run on Linux/SSH: bash ops/smoke_sub_page_ha.sh)")

    for cmd, label in steps:
        if run(cmd, label) != 0:
            return 1

    print("VPN_VERIFY_GATE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
