"""Sample panel node stats every N seconds, log to CSV, report distribution.

Usage:
    python ops/load_monitor.py [--seconds 60] [--minutes 60] [--out PATH]

Writes one row per sample with columns:
    ts_iso, name, address, isConnected, usersOnline, trafficUsedBytes

After --minutes elapse (or on Ctrl-C), prints a per-node summary:
    samples count, mean usersOnline, total bytes delta, share %.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import signal
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from statistics import mean

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TOKEN = (ROOT / ".secrets" / "panel-token.txt").read_text(encoding="ascii").strip()
BASE = site_urls.PANEL_URL


def _ctx() -> ssl.SSLContext:
    # TLS verification ON: panel uses Let's Encrypt cert; system CA is enough.
    return ssl.create_default_context()


def fetch_nodes() -> list[dict]:
    req = urllib.request.Request(f"{BASE}/api/nodes")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, context=_ctx(), timeout=15) as r:
            return json.loads(r.read().decode("utf-8")).get("response", [])
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"fetch error: {e}")
        return []


def summarize(rows: list[dict]) -> None:
    by_name: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_name[r["name"]].append(r)

    print()
    print("=" * 78)
    print(f"{'node':18s} {'samples':>8s} {'mean_online':>12s} {'bytes_delta':>14s} {'share%':>8s}")
    deltas: dict[str, int] = {}
    total_delta = 0
    for name, items in by_name.items():
        items.sort(key=lambda x: x["ts"])
        first = int(items[0]["trafficUsedBytes"])
        last = int(items[-1]["trafficUsedBytes"])
        delta = max(0, last - first)
        deltas[name] = delta
        total_delta += delta
    for name, items in by_name.items():
        online_vals = [int(i["usersOnline"]) for i in items if i.get("usersOnline") is not None]
        m_online = mean(online_vals) if online_vals else 0.0
        d = deltas.get(name, 0)
        share = (d * 100.0 / total_delta) if total_delta > 0 else 0.0
        print(f"{name:18s} {len(items):>8d} {m_online:>12.2f} {d:>14d} {share:>7.2f}%")
    print("=" * 78)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=60, help="seconds between samples")
    ap.add_argument("--minutes", type=int, default=60, help="total duration in minutes")
    ap.add_argument("--out", type=Path, default=ROOT / ".secrets" / "snapshots" / "load-monitor.csv")
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    new = not args.out.exists()
    f = args.out.open("a", newline="", encoding="utf-8")
    writer = csv.writer(f)
    if new:
        writer.writerow(["ts_iso", "name", "address", "isConnected", "usersOnline", "trafficUsedBytes"])

    stop = {"flag": False}

    def _stop(signum, frame):
        stop["flag"] = True

    signal.signal(signal.SIGINT, _stop)

    deadline = time.time() + args.minutes * 60
    rows: list[dict] = []
    sample_idx = 0
    while not stop["flag"] and time.time() < deadline:
        sample_idx += 1
        nodes = fetch_nodes()
        ts = time.time()
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
        for n in nodes:
            row = {
                "ts": ts,
                "ts_iso": ts_iso,
                "name": n.get("name"),
                "address": n.get("address"),
                "isConnected": n.get("isConnected"),
                "usersOnline": n.get("usersOnline"),
                "trafficUsedBytes": n.get("trafficUsedBytes"),
            }
            rows.append(row)
            writer.writerow([
                row["ts_iso"], row["name"], row["address"],
                row["isConnected"], row["usersOnline"], row["trafficUsedBytes"],
            ])
        f.flush()
        online_line = " | ".join(
            f"{n.get('name')}={n.get('usersOnline')}(conn={n.get('isConnected')})"
            for n in nodes
        )
        print(f"[{ts_iso}] sample {sample_idx}: {online_line}")
        # Sleep but allow early stop
        slept = 0
        while slept < args.seconds and not stop["flag"] and time.time() < deadline:
            time.sleep(1)
            slept += 1

    f.close()
    summarize(rows)
    print(f"csv: {args.out}")


if __name__ == "__main__":
    main()
