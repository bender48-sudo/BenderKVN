#!/usr/bin/env python3
"""VPN-AUD-310: TCP latency probe to RU relay VPN IPs from RU vantage.

Reality inbounds reject generic TLS (TLSV1_ALERT_INTERNAL_ERROR) — we use
**tcp_connect_ms only**, not tls_handshake_ok.

Cross-probe: relay#1 measures relay#2 IP; relay#2 measures relay#1 IP — avoids
hairpin (same-host ~0ms) and matches RU user → relay RTT.

Usage:
    python ops/relay_latency_probe.py
    python ops/relay_latency_probe.py --json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

RELAY1_IP = site_urls.RU_RELAY_HOST
RELAY2_IP = "46.173.28.252"
RELAY_VPN_PORT = 443


@dataclass
class RelayIpProbe:
    ip: str
    ok: bool
    tcp_connect_ms: float | None
    tls_ok: bool
    error: str | None = None
    vantage: str = ""


def _load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _relay_ssh_endpoints(cfg: dict[str, str]) -> list[tuple[str, str, int, str, str]]:
    specs = (
        ("relay1", "RELAY_HOST", "RELAY_SSH_PORT", "RELAY_SSH_USER", "RELAY_SSH_KEY"),
        ("relay2", "RELAY2_HOST", "RELAY2_SSH_PORT", "RELAY2_SSH_USER", "RELAY2_SSH_KEY"),
    )
    defaults = {
        "RELAY_HOST": RELAY1_IP,
        "RELAY_SSH_PORT": "3344",
        "RELAY_SSH_USER": "bvpncheck",
        "RELAY_SSH_KEY": "/root/.ssh/id_ed25519",
        "RELAY2_HOST": RELAY2_IP,
        "RELAY2_SSH_PORT": "22",
        "RELAY2_SSH_USER": "bvpncheck",
        "RELAY2_SSH_KEY": "/root/.ssh/id_ed25519_relay2",
    }
    out: list[tuple[str, str, int, str, str]] = []
    for label, host_k, port_k, user_k, key_k in specs:
        host = os.environ.get(host_k) or cfg.get(host_k) or defaults.get(host_k)
        if not host:
            continue
        port = int(os.environ.get(port_k) or cfg.get(port_k) or defaults.get(port_k, "22"))
        user = os.environ.get(user_k) or cfg.get(user_k) or defaults.get(user_k, "bvpncheck")
        key = os.environ.get(key_k) or cfg.get(key_k) or defaults.get(key_k, "/root/.ssh/id_ed25519")
        out.append((label, host, port, user, key))
    return out


def _run_check_on_relay(
    relay_host: str,
    relay_port: int,
    relay_user: str,
    relay_key: str,
    targets: list[dict],
    timeout_sec: int = 60,
) -> tuple[list[dict], str]:
    if not Path(relay_key).is_file():
        return [], f"missing SSH key: {relay_key}"
    cmd = [
        "ssh",
        "-4",
        "-p",
        str(relay_port),
        "-i",
        relay_key,
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=15",
        "-o",
        "StrictHostKeyChecking=accept-new",
        f"{relay_user}@{relay_host}",
    ]
    proc = subprocess.run(
        cmd,
        input=json.dumps(targets),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:300]
        return [], f"SSH {relay_user}@{relay_host}:{relay_port} exit={proc.returncode}: {err}"
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return [], f"invalid check.py JSON: {e}"
    return list(data.get("results") or []), ""


def _tcp_ok(row: dict) -> tuple[bool, float | None, str | None]:
    if row.get("error") in ("connection refused", "connection reset", "timeout"):
        return False, row.get("tcp_connect_ms"), str(row["error"])
    tcp_ms = row.get("tcp_connect_ms")
    if tcp_ms is None:
        return False, None, str(row.get("error") or "no tcp_connect_ms")
    return True, float(tcp_ms), None


def probe_relay_ips(
    *,
    timeout_sec: int = 60,
) -> tuple[list[RelayIpProbe], str]:
    cfg: dict[str, str] = {}
    for p in (Path("/etc/bvpn/ru-monitor.env"), _OPS / "site.env"):
        cfg.update(_load_env(p))

    endpoints = _relay_ssh_endpoints(cfg)
    if len(endpoints) < 1:
        return [], "no relay SSH endpoints configured"

    # Cross-probe map: measure relay1 from relay2 vantage and vice versa.
    cross: dict[str, tuple[str, str]] = {
        RELAY1_IP: ("relay2", RELAY1_IP),
        RELAY2_IP: ("relay1", RELAY2_IP),
    }
    by_label = {label: (host, port, user, key) for label, host, port, user, key in endpoints}

    samples: dict[str, list[tuple[float, str]]] = {RELAY1_IP: [], RELAY2_IP: []}
    errors: list[str] = []

    for target_ip, (vantage_label, _) in cross.items():
        if vantage_label not in by_label:
            continue
        host, port, user, key = by_label[vantage_label]
        sni = cfg.get("RELAY_PROBE_SNI") or "ozon.ru"
        targets = [{"address": target_ip, "port": RELAY_VPN_PORT, "sni": sni}]
        rows, err = _run_check_on_relay(host, port, user, key, targets, timeout_sec=timeout_sec)
        if err:
            errors.append(f"{vantage_label}→{target_ip}: {err}")
            continue
        if not rows:
            errors.append(f"{vantage_label}→{target_ip}: empty results")
            continue
        ok, tcp_ms, terr = _tcp_ok(rows[0])
        if ok and tcp_ms is not None:
            samples[target_ip].append((tcp_ms, vantage_label))
            print(f"[probe] {vantage_label} → {target_ip}:{RELAY_VPN_PORT} tcp={tcp_ms}ms")
        else:
            errors.append(f"{vantage_label}→{target_ip}: {terr}")

    results: list[RelayIpProbe] = []
    for ip in (RELAY1_IP, RELAY2_IP):
        if samples[ip]:
            best_ms, vantage = min(samples[ip], key=lambda x: x[0])
            results.append(
                RelayIpProbe(
                    ip=ip,
                    ok=True,
                    tcp_connect_ms=best_ms,
                    tls_ok=False,
                    error=None,
                    vantage=vantage,
                )
            )
        else:
            results.append(
                RelayIpProbe(
                    ip=ip,
                    ok=False,
                    tcp_connect_ms=None,
                    tls_ok=False,
                    error="; ".join(e for e in errors if ip in e) or "no cross-probe sample",
                    vantage="",
                )
            )

    if errors and not any(r.ok for r in results):
        return results, "; ".join(errors)
    return results, ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    results, err = probe_relay_ips()
    if err and not any(r.ok for r in results):
        print(f"RELAY_LATENCY_PROBE_FAIL: {err}", file=sys.stderr)
        return 1

    payload = {
        "results": [
            {
                "ip": r.ip,
                "ok": r.ok,
                "tcp_connect_ms": r.tcp_connect_ms,
                "tls_ok": r.tls_ok,
                "error": r.error,
                "vantage": r.vantage,
            }
            for r in results
        ]
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for r in results:
            if r.ok:
                print(f"{r.ip}:{RELAY_VPN_PORT} OK tcp={r.tcp_connect_ms}ms via {r.vantage}")
            else:
                print(f"{r.ip}:{RELAY_VPN_PORT} FAIL ({r.error})")

    if sum(1 for r in results if r.ok) >= 2:
        print("RELAY_LATENCY_PROBE_OK")
        return 0
    print("RELAY_LATENCY_PROBE_WARN", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
