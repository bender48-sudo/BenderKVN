#!/usr/bin/env python3
"""O-VPN-002 / VPN-AUD-220: NL direct :443 reachability from RU (via relay check).

Uses cross-probe from relay#1 and relay#2 (TCP only — Reality rejects generic TLS).
Gate before adding NL to Intl_Direct selector.

Usage:
    python ops/nl_reachability_probe_ru.py
    python ops/nl_reachability_probe_ru.py --json
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from relay_latency_probe import (  # noqa: E402
    RELAY1_IP,
    RELAY2_IP,
    RELAY_VPN_PORT,
    RelayIpProbe,
    _load_env,
    _relay_ssh_endpoints,
    _run_check_on_relay,
    _tcp_ok,
)

NL_IP = "91.90.192.17"
NL_PORT = 443
# NL direct from RU: allow higher TCP than relay hairpin; reject obvious block/timeouts.
MAX_TCP_MS = 120.0


def probe_nl_from_ru(*, timeout_sec: int = 60) -> tuple[list[RelayIpProbe], str]:
    cfg: dict[str, str] = {}
    for p in (Path("/etc/bvpn/ru-monitor.env"), _OPS / "site.env"):
        cfg.update(_load_env(p))

    endpoints = _relay_ssh_endpoints(cfg)
    by_label = {label: (host, port, user, key) for label, host, port, user, key in endpoints}
    sni = cfg.get("NL_PROBE_SNI") or "www.microsoft.com"

    samples: list[tuple[float, str]] = []
    errors: list[str] = []

    for vantage_label, relay_host, relay_port, relay_user, relay_key in endpoints:
        targets = [{"address": NL_IP, "port": NL_PORT, "sni": sni}]
        rows, err = _run_check_on_relay(
            relay_host, relay_port, relay_user, relay_key, targets, timeout_sec=timeout_sec
        )
        if err:
            errors.append(f"{vantage_label}→{NL_IP}: {err}")
            continue
        if not rows:
            errors.append(f"{vantage_label}→{NL_IP}: empty results")
            continue
        ok, tcp_ms, terr = _tcp_ok(rows[0])
        if ok and tcp_ms is not None:
            samples.append((tcp_ms, vantage_label))
            print(f"[nl-probe] {vantage_label} → {NL_IP}:{NL_PORT} tcp={tcp_ms}ms")
        else:
            errors.append(f"{vantage_label}→{NL_IP}: {terr}")

    if not samples:
        return [
            RelayIpProbe(
                ip=NL_IP,
                ok=False,
                tcp_connect_ms=None,
                tls_ok=False,
                error="; ".join(errors) or "no samples",
            )
        ], "; ".join(errors)

    best_ms, vantage = min(samples, key=lambda x: x[0])
    ok = best_ms <= MAX_TCP_MS
    result = RelayIpProbe(
        ip=NL_IP,
        ok=ok,
        tcp_connect_ms=best_ms,
        tls_ok=False,
        error=None if ok else f"tcp {best_ms}ms > {MAX_TCP_MS}ms max",
        vantage=vantage,
    )
    return [result], ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-ms", type=float, default=MAX_TCP_MS)
    args = ap.parse_args()

    max_ms = args.max_ms
    results, err = probe_nl_from_ru()
    r = results[0]
    ok = r.ok and (r.tcp_connect_ms is None or r.tcp_connect_ms <= max_ms)
    if r.ok and r.tcp_connect_ms is not None and r.tcp_connect_ms > max_ms:
        ok = False
        r = RelayIpProbe(
            ip=r.ip,
            ok=False,
            tcp_connect_ms=r.tcp_connect_ms,
            tls_ok=False,
            error=f"tcp {r.tcp_connect_ms}ms > {max_ms}ms max",
            vantage=r.vantage,
        )
    payload = {
        "nl_ip": NL_IP,
        "nl_port": NL_PORT,
        "ok": ok,
        "tcp_connect_ms": r.tcp_connect_ms,
        "vantage": r.vantage,
        "max_tcp_ms": max_ms,
        "error": r.error or err,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif ok:
        print(f"{NL_IP}:{NL_PORT} OK tcp={r.tcp_connect_ms}ms via {r.vantage} (max {max_ms}ms)")
    else:
        print(f"{NL_IP}:{NL_PORT} FAIL ({r.error or err})", file=sys.stderr)

    if ok:
        print("NL_REACHABILITY_PROBE_RU_OK")
        return 0
    print("NL_REACHABILITY_PROBE_RU_FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
