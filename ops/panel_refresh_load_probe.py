#!/usr/bin/env python3
"""Simulate N subscription refresh GETs (P6-SCALE-05 «refresh × N»).

Fetches ACTIVE users from panel API, then parallel HTTPS GETs to
``{SUB_PUBLIC_ORIGIN}/api/sub/{shortUuid}`` — same path Happ uses on refresh.

Example::

  python ops/panel_refresh_load_probe.py --concurrency 25 --total 100
  python ops/panel_refresh_load_probe.py --json --max-bad-http-rate 0.02

Exit 1 on hard errors or rates above thresholds (same family as subscription_load_probe).
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
from panel_client import PanelClient  # noqa: E402


def _fwd() -> dict[str, str]:
    return {"X-Forwarded-Proto": "https", "X-Forwarded-For": "127.0.0.1"}


def fetch_short_uuids(client: PanelClient, limit: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    start = 0
    size = min(100, max(limit, 10))
    while len(out) < limit:
        code, data = client.get(f"/api/users?size={size}&start={start}", extra_headers=_fwd())
        if code != 200:
            raise RuntimeError(f"GET users HTTP {code}: {data!s}"[:400])
        chunk = (data.get("response") or {}).get("users") or []
        if not isinstance(chunk, list):
            break
        for u in chunk:
            if (u.get("status") or "").upper() != "ACTIVE":
                continue
            sid = (u.get("shortUuid") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            out.append(sid)
            if len(out) >= limit:
                break
        if len(chunk) < size:
            break
        start += size
        if start > 5000:
            break
    return out


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
            headers={"User-Agent": "Happ/1.9.4 (iOS)"},
        )
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            code = resp.getcode()
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:  # noqa: BLE001
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
    ap.add_argument("--origin", default=None, help="sub origin (default SUB_PUBLIC_ORIGIN)")
    ap.add_argument("--concurrency", type=int, default=20)
    ap.add_argument("--total", type=int, default=80, help="total refresh GETs (N)")
    ap.add_argument("--users-sample", type=int, default=40, help="max distinct shortUuid from panel")
    ap.add_argument("--timeout", type=float, default=25.0)
    ap.add_argument("--jitter-ms", type=float, default=30.0)
    ap.add_argument("--max-error-rate", type=float, default=0.05)
    ap.add_argument("--max-bad-http-rate", type=float, default=0.02)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.concurrency < 1 or args.total < 1:
        print("concurrency and total must be >= 1", file=sys.stderr)
        return 2

    origin = (args.origin or site_urls.SUB_PUBLIC_ORIGIN).rstrip("/")
    client = PanelClient()
    short_ids = fetch_short_uuids(client, args.users_sample)
    if not short_ids:
        print("FAIL: no ACTIVE shortUuid from panel", file=sys.stderr)
        return 1

    urls = [f"{origin}/api/sub/{sid}" for sid in short_ids]
    print(f"refresh_pool={len(urls)} origin={origin}", file=sys.stderr)

    latencies: list[float] = []
    hard_errors = 0
    bad_http = 0
    code_hist: Counter[int] = Counter()
    http_codes: list[int] = []

    def job(i: int) -> tuple[float, int | None, str | None]:
        url = urls[i % len(urls)]
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
    err_rate = hard_errors / args.total
    bad_http_rate = bad_http / len(http_codes) if http_codes else 1.0
    ok_http = sum(1 for c in http_codes if c in (200, 304))

    summary = {
        "probe": "panel_refresh_load",
        "origin": origin,
        "refresh_pool": len(urls),
        "concurrency": args.concurrency,
        "total": args.total,
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "max_ms": round(mx, 2),
        "hard_errors": hard_errors,
        "http_200_304": ok_http,
        "bad_http_rate": round(bad_http_rate, 4),
        "error_rate": round(err_rate, 4),
        "http_status_histogram": {str(k): v for k, v in sorted(code_hist.items())},
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            f"PANEL_REFRESH_LOAD total={args.total} c={args.concurrency} "
            f"pool={len(urls)} p50={p50:.0f}ms p95={p95:.0f}ms p99={p99:.0f}ms "
            f"hard_err={hard_errors} bad_http_rate={bad_http_rate:.2%} "
            f"hist={dict(sorted(code_hist.items()))}"
        )

    if err_rate > args.max_error_rate:
        print(f"FAIL: error_rate {err_rate:.2%}", file=sys.stderr)
        return 1
    if bad_http_rate > args.max_bad_http_rate:
        print(f"FAIL: bad_http_rate {bad_http_rate:.2%}", file=sys.stderr)
        return 1
    print("PANEL_REFRESH_LOAD_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
