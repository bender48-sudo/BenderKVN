#!/usr/bin/env python3
"""P2-OPS-TRANSPORT-HEALTH-01: alert on skewed transport profile mix in live subs."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sample", type=int, default=20)
    p.add_argument("--max-dominance-pct", type=float, default=80.0)
    p.add_argument("--min-profile-pct", type=float, default=1.0)
    p.add_argument("--alert-cmd", default="", help="shell command if unhealthy (optional)")
    args = p.parse_args()

    cmd = [
        sys.executable,
        str(ROOT / "ops" / "transport_mux_audit.py"),
        "--sample",
        str(args.sample),
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print("TRANSPORT_HEALTH_FAIL: invalid JSON from mux audit", file=sys.stderr)
        return 2

    sampled = report.get("sampled") or 0
    if sampled <= 0:
        print("TRANSPORT_HEALTH_FAIL: no samples", file=sys.stderr)
        return 3

    primary_pct = 100.0 * (report.get("has_primary_pct") or 0) / 100.0
    alt_pct = 100.0 * (report.get("has_alt_pct") or 0) / 100.0
    xhttp_pct = 100.0 * (report.get("has_xhttp_pct") or 0) / 100.0
    profiles = {
        "primary": report.get("has_primary_pct", 0),
        "alt": report.get("has_alt_pct", 0),
        "xhttp": report.get("has_xhttp_pct", 0),
    }
    issues: list[str] = []
    for name, pct in profiles.items():
        if pct < args.min_profile_pct:
            issues.append(f"{name} under {args.min_profile_pct}% ({pct}%)")
        if pct > args.max_dominance_pct:
            issues.append(f"{name} over {args.max_dominance_pct}% ({pct}%)")

    health = {
        "ok": not issues and bool(report.get("ok")),
        "sampled": sampled,
        "profiles_pct": profiles,
        "issues": issues,
        "mux_report": report,
    }
    print(json.dumps(health, ensure_ascii=False, indent=2))

    if health["ok"]:
        print("TRANSPORT_PROFILE_HEALTH_OK")
        return 0

    print("TRANSPORT_PROFILE_HEALTH_WARN", file=sys.stderr)
    if args.alert_cmd.strip():
        subprocess.run(args.alert_cmd, shell=True, check=False)
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
