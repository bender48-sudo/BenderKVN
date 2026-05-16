#!/usr/bin/env python3
"""Lightweight subscription-edge load probe (P6-SCALE-04).

Parallel HTTPS GETs to the public sub smoke URL (same family as monitor /
capacity_snapshot). No secrets — URL from --url or ops/site_urls.py.

Example::

  python ops/subscription_load_probe.py --concurrency 25 --total 150
  python ops/subscription_load_probe.py --url https://example:2053/api/sub/SHORTID --json

Exit 1 if any request hard-fails (TLS/DNS) or if error_rate exceeds --max-error-rate.
"""
from __future__ import annotations

import argparse
import json
import random
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "ops") not in sys.path:
    sys.path.insert(0, str(ROOT / "ops"))

import site_urls  # noqa: E402


def _one_get(url: str, timeout: float, jitter_ms: float) -> tuple[float, int | None, str | None]:
    if jitter_ms > 0:
        time.sleep(random.random() * jitter_ms / 1000.0)
    ctx = ssl.create_default_context()
    t0 = time.perf_counter()
    err: str | None = None
    code: int | None = None
    try:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": "BenderVPN-sub-load-probe/1.0"},
        )
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            code = resp.getcode()
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:  # noqa: BLE001 — aggregate for probe
        err = f"{type(e).__name__}: {e}"[:200]
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return elapsed_ms, code, err


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    i = int(round((len(sorted_vals) - 1) * p))
    return sorted_vals[max(0, min(i, len(sorted_vals) - 1))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--url",
        help="Full HTTPS URL to GET (default: site_urls.sub_monitor_probe_url())",
    )
    ap.add_argument("--concurrency", type=int, default=20, help="parallel workers")
    ap.add_argument("--total", type=int, default=100, help="total GET requests")
    ap.add_argument("--timeout", type=float, default=25.0, help="per-request timeout")
    ap.add_argument(
        "--jitter-ms",
        type=float,
        default=50.0,
        help="random delay 0..jitter before each request (spread load)",
    )
    ap.add_argument(
        "--max-error-rate",
        type=float,
        default=0.05,
        help="fail if (tcp/tls errors) / total > this (default 0.05)",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    url = args.url or site_urls.sub_monitor_probe_url()
    if args.concurrency < 1 or args.total < 1:
        print("concurrency and total must be >= 1", file=sys.stderr)
        return 2

    latencies: list[float] = []
    http_codes: list[int] = []
    hard_errors = 0
    bad_http = 0
    code_hist: Counter[int] = Counter()

    def job(_i: int) -> tuple[float, int | None, str | None]:
        return _one_get(url, args.timeout, args.jitter_ms)

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = [ex.submit(job, i) for i in range(args.total)]
        for fut in as_completed(futs):
            ms, code, err = fut.result()
            latencies.append(ms)
            if err:
                hard_errors += 1
                continue
            if code is not None:
                http_codes.append(code)
                code_hist[code] += 1
                if code not in (200, 304):
                    bad_http += 1

    lat_sorted = sorted(latencies)
    p50 = _percentile(lat_sorted, 0.50)
    p95 = _percentile(lat_sorted, 0.95)
    p99 = _percentile(lat_sorted, 0.99)
    mx = lat_sorted[-1] if lat_sorted else 0.0

    err_rate = hard_errors / args.total if args.total else 0.0
    ok_http = sum(1 for c in http_codes if c in (200, 304))
    http_ok_rate = ok_http / len(http_codes) if http_codes else 0.0

    summary = {
        "url": url,
        "concurrency": args.concurrency,
        "total": args.total,
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "max_ms": round(mx, 2),
        "hard_errors": hard_errors,
        "http_status_histogram": {str(k): v for k, v in sorted(code_hist.items())},
        "http_codes_count": len(http_codes),
        "http_200_304_rate": round(http_ok_rate, 4) if http_codes else None,
        "not_200_304": bad_http,
        "error_rate": round(err_rate, 4),
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"url={url}")
        print(
            f"total={args.total} concurrency={args.concurrency} "
            f"p50={p50:.1f}ms p95={p95:.1f}ms p99={p99:.1f}ms max={mx:.1f}ms"
        )
        print(
            f"hard_errors={hard_errors} not_200_304={bad_http} "
            f"status_histogram={dict(sorted(code_hist.items()))} "
            f"http_200_304={ok_http}/{len(http_codes)} tcp_tls_error_rate={err_rate:.2%}"
        )

    if err_rate > args.max_error_rate:
        print(
            f"FAIL: error_rate {err_rate:.2%} > max {args.max_error_rate:.2%}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
