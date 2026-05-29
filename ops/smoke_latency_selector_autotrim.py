#!/usr/bin/env python3
"""Smoke VPN-AUD-310: relay latency probe + autotrim wiring."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"


def main() -> int:
    for name in (
        "relay_latency_probe.py",
        "latency_selector_autotrim.py",
        "balancer_selectors.py",
    ):
        p = OPS / name
        if not p.is_file():
            print(f"LATENCY_SELECTOR_SMOKE_FAIL: missing {name}", file=sys.stderr)
            return 1
        ast.parse(p.read_text(encoding="utf-8"))

    from balancer_selectors import (  # noqa: WPS433
        RELAY1_SELECTOR,
        RELAY2_SELECTOR,
        RELAY6_SELECTOR,
        allowed_relay_only_selectors,
        is_relay_only_profile,
    )

    allowed = allowed_relay_only_selectors()
    if RELAY6_SELECTOR not in allowed or len(RELAY1_SELECTOR) != 3:
        print("LATENCY_SELECTOR_SMOKE_FAIL: selector constants", file=sys.stderr)
        return 1

    proc = subprocess.run(
        [sys.executable, str(OPS / "verify_vpn_balancer_profile.py")],
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0 or "VPN_BALANCER_PROFILE_OK" not in out:
        print(out, file=sys.stderr)
        print("LATENCY_SELECTOR_SMOKE_FAIL: live profile", file=sys.stderr)
        return 1

    proc2 = subprocess.run(
        [sys.executable, str(OPS / "latency_selector_autotrim.py")],
        capture_output=True,
        text=True,
        timeout=180,
    )
    out2 = (proc2.stdout or "") + (proc2.stderr or "")
    print(out2.rstrip())
    if proc2.returncode != 0:
        print("LATENCY_SELECTOR_SMOKE_FAIL: autotrim dry-run", file=sys.stderr)
        return 1

    print("LATENCY_SELECTOR_SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
