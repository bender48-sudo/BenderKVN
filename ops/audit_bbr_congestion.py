#!/usr/bin/env python3
"""Audit TCP congestion control (BBR + fq) on VPN nodes.

Exit 0 + BBR_AUDIT_OK when all reachable nodes use bbr + fq (or fq_codel).

Usage:
    python ops/audit_bbr_congestion.py --ssh --ssh-alias bvpn-relay bvpn-lv
    python ops/audit_bbr_congestion.py --ssh   # from LV: site.env relay keys
"""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from relay_latency_probe import _load_env, _relay_ssh_endpoints  # noqa: E402

GOOD_QDISC = {"fq", "fq_codel"}


def _parse_remote(out: str) -> dict:
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    cc = lines[0] if lines else ""
    qdisc = lines[1] if len(lines) > 1 else ""
    ok = cc == "bbr" and qdisc in GOOD_QDISC
    return {"tcp_congestion_control": cc, "default_qdisc": qdisc, "ok": ok}


def _ssh_alias(alias: str) -> tuple[dict, str]:
    remote = "sysctl -n net.ipv4.tcp_congestion_control && sysctl -n net.core.default_qdisc"
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", alias, remote]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return {}, "timeout"
    if proc.returncode != 0:
        return {}, (proc.stderr or proc.stdout or "ssh failed").strip()[:200]
    return _parse_remote(proc.stdout), ""


def _ssh_direct(host: str, port: int, user: str, key: str) -> tuple[dict, str]:
    if not Path(key).is_file():
        return {}, f"key missing: {key}"
    remote = "sysctl -n net.ipv4.tcp_congestion_control && sysctl -n net.core.default_qdisc"
    cmd = [
        "ssh", "-4", "-p", str(port), "-i", key,
        "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
        f"{user}@{host}", remote,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return {}, "timeout"
    if proc.returncode != 0:
        return {}, (proc.stderr or proc.stdout or "ssh failed").strip()[:200]
    return _parse_remote(proc.stdout), ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssh", action="store_true")
    ap.add_argument("--ssh-alias", nargs="*", default=[], metavar="ALIAS")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.ssh:
        print("Run: python ops/audit_bbr_congestion.py --ssh --ssh-alias bvpn-relay bvpn-lv")
        return 0

    results: list[dict] = []
    errors: list[str] = []

    print("=== BBR / fq audit ===")

    if args.ssh_alias:
        for alias in args.ssh_alias:
            data, err = _ssh_alias(alias)
            row = {"node": alias, **data, "error": err or None}
            results.append(row)
    else:
        cfg: dict[str, str] = {}
        for p in (Path("/etc/bvpn/ru-monitor.env"), _OPS / "site.env"):
            cfg.update(_load_env(p))
        endpoints = _relay_ssh_endpoints(cfg)
        if not endpoints:
            print("FAIL: no SSH endpoints (use --ssh-alias)", file=sys.stderr)
            return 1
        for label, host, port, user, key in endpoints:
            data, err = _ssh_direct(host, port, user, key)
            row = {"node": label, **data, "error": err or None}
            results.append(row)

    for row in results:
        label = row["node"]
        err = row.get("error")
        if err:
            errors.append(f"{label}: {err}")
            print(f"  {label}: FAIL ({err})")
        elif row.get("ok"):
            print(f"  {label}: bbr + {row.get('default_qdisc')}  [BBR_OK]")
        else:
            msg = f"cc={row.get('tcp_congestion_control')!r} qdisc={row.get('default_qdisc')!r}"
            errors.append(f"{label}: {msg}")
            print(f"  {label}: {msg}  [BBR_FIX_NEEDED]")

    if args.json:
        print(json.dumps({"results": results, "errors": errors}, indent=2))

    ok_n = sum(1 for r in results if r.get("ok"))
    if errors:
        print(f"\nWARN: {len(errors)} issue(s); {ok_n} node(s) BBR_OK")
        return 1
    if ok_n:
        print(f"\nBBR_AUDIT_OK ({ok_n} node(s))")
        return 0
    print("FAIL: no nodes probed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
