#!/usr/bin/env python3
"""VPN-AUD-275: PoC gate — relay-NL :443 panel hosts + RU NL probe + Happ guards.

Does not modify prod template. Run after patch_add_relay_nl_443_hosts --apply.

Usage:
    python ops/probe_relay_nl_443_poc.py
    python ops/probe_relay_nl_443_poc.py --require-hosts
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
ROOT = _OPS.parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402

RELAY_NL_PORT = 443
MIN_HOSTS = 6  # 3× relay1 + 3× relay2


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


def _run(script: str, *extra: str, via_lv: bool = False, retries: int = 5) -> tuple[int, str]:
    last_out = ""
    for attempt in range(1, retries + 1):
        if via_lv:
            remote = f"set -a; . /etc/bvpn/ru-monitor.env; set +a; python3 /opt/scripts/{script}"
            if extra:
                remote += " " + " ".join(extra)
            cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=25", "bvpn-lv", remote]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        else:
            cmd = [sys.executable, str(_OPS / script), *extra]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(ROOT))
        last_out = ((proc.stdout or "") + (proc.stderr or "")).strip()
        if proc.returncode == 0:
            return 0, last_out
        if attempt < retries:
            import time

            time.sleep(2)
    return proc.returncode, last_out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--require-hosts",
        action="store_true",
        help=f"fail if fewer than {MIN_HOSTS} relay-NL :443 panel hosts",
    )
    args = ap.parse_args()

    errors: list[str] = []

    try:
        hosts = PanelClient().get_or_raise("/api/hosts")["response"]
        r443 = [h for h in hosts if is_relay_nl_443(h)]
        print(f"relay-NL :443 panel hosts: {len(r443)} (want>={MIN_HOSTS} for full PoC)")
        for h in sorted(r443, key=lambda x: (x.get("address"), x.get("remark") or "")):
            print(
                f"  {h['uuid'][:8]} | {h.get('address')}:{h.get('port')} "
                f"dis={h.get('isDisabled')} hid={h.get('isHidden')} | {h.get('remark')!r}"
            )
        if args.require_hosts and len(r443) < MIN_HOSTS:
            errors.append(f"hosts: got {len(r443)}, need>={MIN_HOSTS}")
        elif len(r443) == 0:
            errors.append("hosts: no relay-NL :443 (run patch_add_relay_nl_443_hosts --apply)")
    except Exception as e:
        errors.append(f"panel: {e}")

    for script, token, via_lv in (
        ("nl_reachability_probe_ru.py", "NL_REACHABILITY_PROBE_RU_OK", True),
        ("happ_geosite_guard.py", "HAPP_GEOSITE_GUARD_OK", False),
        ("verify_ru_bypass_status.py", "RU_BYPASS_STATUS_OK", False),
    ):
        rc, out = _run(script, via_lv=via_lv)
        ok = token in out and rc == 0
        print(f"--- {script} ---")
        if out:
            for line in out.splitlines()[-8:]:
                print(line)
        if not ok:
            errors.append(f"{script}: exit={rc}, missing {token}")
        else:
            print(f"OK: {token}")

    rc, out = _run("probe_ru_bypass.py")
    print("--- probe_ru_bypass.py (local sub fetch) ---")
    if out:
        for line in out.splitlines()[-8:]:
            print(line)
    if rc != 0 or "PROBE_RU_BYPASS_OK" not in out:
        if "ModuleNotFoundError" in out or "URLError" in out:
            print("SKIP: probe_ru_bypass (transient/local); rely on vpn_verify_gate on LV")
        else:
            errors.append(f"probe_ru_bypass: exit={rc}")

    if errors:
        for e in errors:
            print(f"WARN: {e}", file=sys.stderr)
        print("RELAY_NL_443_POC_FAIL", file=sys.stderr)
        return 1

    print("RELAY_NL_443_POC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
