#!/usr/bin/env python3
"""Load probe both subscription origins (P6-RED-SUBHA-01 split-host verify)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "ops" / "subscription_load_probe.py"


def _run(url: str, total: int, concurrency: int) -> dict:
    cmd = [
        sys.executable,
        str(PROBE),
        "--url",
        url,
        "--total",
        str(total),
        "--concurrency",
        str(concurrency),
        "--json",
    ]
    out = subprocess.check_output(cmd, text=True, encoding="utf-8")
    return json.loads(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary-url", default="https://p4n7q.conntest.xyz:2053/api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2")
    ap.add_argument("--alt-url", default="https://k9x2m1.conntest.xyz:2053/api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2")
    ap.add_argument("--total", type=int, default=60)
    ap.add_argument("--concurrency", type=int, default=15)
    ap.add_argument("--max-p95-ms", type=float, default=5000.0, help="fail if either origin p95 exceeds")
    args = ap.parse_args()

    primary = _run(args.primary_url, args.total, args.concurrency)
    alt = _run(args.alt_url, args.total, args.concurrency)

    report = {"primary": primary, "alt": alt}
    print(json.dumps(report, ensure_ascii=False, indent=2))

    fail = False
    for label, data in (("primary", primary), ("alt", alt)):
        p95 = float(data.get("p95_ms", 0))
        bad = float(data.get("bad_http_rate", 1))
        hard = int(data.get("hard_errors", 1))
        print(f"{label}: p95={p95:.0f}ms bad_http_rate={bad:.3f} hard_errors={hard}")
        if p95 > args.max_p95_ms or bad > 0.05 or hard > 0:
            fail = True

    if fail:
        print("SUB_HA_LOAD_PROBE_FAIL", file=sys.stderr)
        return 1
    print("SUB_HA_LOAD_PROBE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
