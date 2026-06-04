#!/usr/bin/env python3
"""VPN-AUD-281: relay-NL :443 inject hosts must stay isHidden=True.

Remnawave only exports injectHosts UUIDs when hosts are hidden; VPN-AUD-279
mistakenly set isHidden=False on enable → live sub stuck at 10 proxies.

Usage:
    python ops/patch_relay_nl_inject_hidden.py
    python ops/patch_relay_nl_inject_hidden.py --apply
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402
from patch_add_relay_nl_443_hosts import is_relay_nl_443  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402


def _ssh(script: str, token: str) -> bool:
    remote = f"set -a; . /etc/bvpn/ru-monitor.env; set +a; python3 /opt/scripts/{script}"
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", "bvpn-lv", remote],
        capture_output=True,
        text=True,
        timeout=180,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out.rstrip())
    return proc.returncode == 0 and token in out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--skip-notify", action="store_true")
    args = ap.parse_args()

    c = PanelClient(timeout=120)
    hosts = c.get_or_raise("/api/hosts")["response"]
    targets = [h for h in hosts if is_relay_nl_443(h) and not h.get("isDisabled")]
    need = [h for h in targets if not h.get("isHidden")]
    print(f"relay-NL :443 enabled: {len(targets)}, need isHidden=True: {len(need)}")

    for h in need:
        remark = h.get("remark")
        if not args.apply:
            print(f"dry-run PATCH hidden: {remark!r}")
            continue
        code, body = c.patch(
            "/api/hosts",
            body={"uuid": h["uuid"], "isDisabled": False, "isHidden": True},
        )
        if code != 200:
            print(f"FAIL {h['uuid'][:8]} HTTP {code}: {body!s}"[:200], file=sys.stderr)
            return 1
        print(f"hidden: {remark!r}")
        time.sleep(0.3)

    if not need:
        print("OK: all relay-NL inject hosts already hidden")
    elif not args.apply:
        print("\nDry-run. Apply: python ops/patch_relay_nl_inject_hidden.py --apply")
        return 0

    if args.apply and not args.skip_notify:
        after_template_patch("patch_relay_nl_inject_hidden", push_ams=True)

    print("=== parity probe (LV) ===")
    if not _ssh("probe_injecthosts_sub_parity.py --via-lv", "INJECT_SUB_PARITY_OK"):
        return 1

    print("=== vpn_verify_gate (LV) ===")
    if not _ssh("vpn_verify_gate.py", "VPN_VERIFY_GATE_OK"):
        return 1

    print("VPN_AUD_281_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
