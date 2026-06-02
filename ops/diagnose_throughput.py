#!/usr/bin/env python3
"""Throughput diagnostic: find why 23 MB TG files take ~1 minute.

Phase 1 (always, no SSH needed):
  - Template config: selector composition, strategy, known issues
  - TCP latency probes to relay#1, relay#2, NL

Phase 2 (--ssh, requires shell access to relay):
  - Relay server CPU load, memory, TCP connection count
  - XRay process CPU usage
  - Live bandwidth test: 5 MB download from Cloudflare

Bottleneck labels printed in summary:
  RELAY_BW_CAP       - relay uplink saturated, explains slow TG files
  RELAY_BW_MARGINAL  - relay bandwidth marginal (1-3 MB/s)
  RELAY_CPU_BOUND    - XRay XTLS saturating relay CPU cores
  RELAY_OVERLOADED   - too many concurrent TCP sessions
  RELAY_LINK_OK      - relay is not the bottleneck, issue is elsewhere
  CONFIG_ISSUE       - routing misconfiguration found

Usage:
    python ops/diagnose_throughput.py
    python ops/diagnose_throughput.py --ssh
    python ops/diagnose_throughput.py --ssh --ssh-user root
    python ops/diagnose_throughput.py --json
"""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import time
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402
from relay_latency_probe import (  # noqa: E402
    RELAY1_IP,
    RELAY2_IP,
    RELAY_VPN_PORT,
    RelayIpProbe,
    _load_env,
    _relay_ssh_endpoints,
    probe_relay_ips,
)
from nl_reachability_probe_ru import NL_IP, NL_PORT  # noqa: E402
from balancer_selectors import (  # noqa: E402
    RELAY6_SELECTOR,
    NL_DIRECT_SELECTOR,
    INTL_RELAY_NL_SELECTOR,
    INTL_BALANCER_TAG,
    INTL_STEALTH_BALANCER_TAG,
    is_stealth_split_profile,
)

# ── thresholds ────────────────────────────────────────────────────────────────
BW_CAP_MBS = 1.0        # relay uplink saturated below this
BW_MARGINAL_MBS = 3.0   # marginal — explains TG slowness
BW_OK_MBS = 7.0         # relay is clearly not the bw bottleneck
LOAD_RATIO_HIGH = 1.5   # load_1m / cpu_count — CPU pressure
CONN_HIGH = 150         # TCP established — overloaded relay
XRAY_CPU_HIGH = 80.0    # XRay CPU% — XTLS-bound

FILE_MB = 23.0          # reference file size for time estimates


# ── Python script that runs on relay via SSH ──────────────────────────────────
_RELAY_HEALTH_PY = r"""
import json, subprocess, time, os, re

r = {}

try:
    with open('/proc/loadavg') as f:
        la = f.read().split()
    r['load_1m'] = float(la[0])
    r['load_5m'] = float(la[1])
    r['cpu_count'] = os.cpu_count() or 1
    r['load_ratio'] = round(r['load_1m'] / r['cpu_count'], 2)
except Exception as e:
    r['load_error'] = str(e)

try:
    meminfo = {}
    with open('/proc/meminfo') as f:
        for line in f:
            if ':' in line:
                k, v = line.split(':', 1)
                meminfo[k.strip()] = int(v.strip().split()[0])
    r['mem_total_mb'] = meminfo.get('MemTotal', 0) // 1024
    r['mem_avail_mb'] = meminfo.get('MemAvailable', 0) // 1024
except Exception as e:
    r['mem_error'] = str(e)

try:
    ss = subprocess.run(['ss', '-s'], capture_output=True, text=True, timeout=5)
    for line in ss.stdout.splitlines():
        if line.strip().startswith('TCP:'):
            r['ss_tcp_line'] = line.strip()
            m = re.search(r'estab\s+(\d+)', line)
            if m:
                r['tcp_established'] = int(m.group(1))
            break
except Exception as e:
    r['ss_error'] = str(e)

try:
    ps = subprocess.run(['ps', 'aux', '--no-headers'], capture_output=True, text=True, timeout=5)
    keywords = ('xray', 'sing-box', 'singbox', 'v2ray', 'happ')
    xray_lines = [l for l in ps.stdout.splitlines() if any(k in l.lower() for k in keywords)]
    r['xray_proc_count'] = len(xray_lines)
    if xray_lines:
        try:
            r['xray_cpu_pct'] = round(sum(float(l.split()[2]) for l in xray_lines if len(l.split()) > 3), 1)
        except Exception:
            pass
        r['xray_proc_sample'] = xray_lines[0].split()[-1] if xray_lines else ''
except Exception as e:
    r['ps_error'] = str(e)

try:
    dps = subprocess.run(
        ['docker', 'ps', '--format', '{{.Names}}|{{.Image}}'],
        capture_output=True, text=True, timeout=5,
    )
    if dps.returncode == 0 and dps.stdout.strip():
        r['docker_containers'] = [ln.strip() for ln in dps.stdout.splitlines() if ln.strip()][:5]
        if not r.get('xray_proc_count'):
            for name in r['docker_containers']:
                if any(k in name.lower() for k in ('xray', 'sing', 'v2ray', 'vpn', 'remna')):
                    r['xray_proc_count'] = 1
                    r['xray_proc_sample'] = f"docker:{name.split('|')[0]}"
                    break
except Exception:
    pass

try:
    dl = subprocess.run(
        ['curl', '-s', '-o', '/dev/null',
         '-w', '%{speed_download} %{http_code} %{time_total}',
         '--max-time', '20',
         'https://speed.cloudflare.com/__down?bytes=5000000'],
        capture_output=True, text=True, timeout=25,
    )
    if dl.returncode == 0 and dl.stdout.strip():
        parts = dl.stdout.strip().split()
        r['bw_mbs'] = round(float(parts[0]) / 1_000_000, 2) if parts else 0
        r['bw_http'] = parts[1] if len(parts) > 1 else 'err'
        r['bw_time_s'] = float(parts[2]) if len(parts) > 2 else 0
    else:
        r['bw_error'] = (dl.stderr or dl.stdout or 'curl failed').strip()[:200]
except Exception as e:
    r['bw_error'] = str(e)

print(json.dumps(r))
"""


# ── Phase 1: template config ──────────────────────────────────────────────────

def phase1_template(template_uuid: str) -> list[str]:
    out: list[str] = []
    try:
        c = PanelClient(timeout=30)
        tpl = c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]
        doc = tpl.get("templateJson") or {}
    except Exception as e:
        out.append(f"WARN: cannot fetch template: {e}")
        return out

    routing = doc.get("routing") or {}
    balancers = {b.get("tag"): b for b in routing.get("balancers") or []}
    rules = routing.get("rules") or []

    intl = balancers.get(INTL_BALANCER_TAG)
    stealth = balancers.get(INTL_STEALTH_BALANCER_TAG)
    if stealth and is_stealth_split_profile(doc):
        ssel = list(stealth.get("selector") or [])
        fsel = list(intl.get("selector") or []) if intl else []
        strat = (intl.get("strategy") or {}).get("type", "unknown") if intl else "?"
        out.append(
            f"stealth split: {INTL_STEALTH_BALANCER_TAG} relay×{len(ssel)} (TG/Meta); "
            f"{INTL_BALANCER_TAG} {len(fsel)} paths catch-all strategy={strat}"
        )
        relay_paths = [t for t in fsel if t in RELAY6_SELECTOR]
        nl_paths = [t for t in fsel if t in NL_DIRECT_SELECTOR]
        if fsel:
            nl_pct = len(nl_paths) / len(fsel) * 100
            relay_pct = len(relay_paths) / len(fsel) * 100
            out.append(
                f"  catch-all random: NL {nl_pct:.0f}% / relay {relay_pct:.0f}% "
                f"(TG/Meta always relay-only via {INTL_STEALTH_BALANCER_TAG})"
            )
        return out

    intl = balancers.get(INTL_BALANCER_TAG)
    if not intl:
        out.append("ERROR: Intl_Direct balancer missing — CONFIG_ISSUE")
        return out

    sel = list(intl.get("selector") or [])
    strat = (intl.get("strategy") or {}).get("type", "unknown")
    relay_paths = [t for t in sel if t in RELAY6_SELECTOR]
    nl_paths = [t for t in sel if t in NL_DIRECT_SELECTOR]

    out.append(f"Intl_Direct: {len(sel)} paths  strategy={strat}")
    out.append(f"  relay paths: {len(relay_paths)} / NL paths: {len(nl_paths)}")

    if strat == "random" and sel:
        nl_pct = len(nl_paths) / len(sel) * 100
        relay_pct = len(relay_paths) / len(sel) * 100
        out.append(
            f"  random → each TG connection: NL {nl_pct:.0f}% (fast ~9 MB/s) "
            f"or relay {relay_pct:.0f}% (speed TBD by relay bandwidth)"
        )
        out.append(
            f"  23 MB via NL ≈ 2-3 s  |  via relay ≈ ? s (run --ssh to measure)"
        )

    has_catchall = any(
        r.get("balancerTag") == INTL_BALANCER_TAG
        and r.get("network") == "tcp,udp"
        and not r.get("port")
        for r in rules
    )
    if not has_catchall:
        out.append("WARN: no tcp,udp catch-all → Intl_Direct; unmatched traffic may leak — CONFIG_ISSUE")

    if doc.get("burstObservatory") or doc.get("observatory"):
        out.append("WARN: observatory present — disabled intentionally (closed-pipe risk on RU)")

    if strat == "random":
        out.append(
            "NOTE: random strategy has no throughput awareness; a congested relay is used "
            "as often as a healthy one. autotrim only evicts on TCP connect failure, not slowness."
        )

    return out


# ── Phase 2: SSH relay health ────────────────────────────────────────────────

def _run_ssh_health_alias(alias: str) -> tuple[dict, str]:
    """Connect via SSH config alias (e.g. bvpn-relay, bvpn-relay2)."""
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", alias, "python3", "-"]
    try:
        proc = subprocess.run(cmd, input=_RELAY_HEALTH_PY, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return {}, "SSH timeout (90s)"
    except FileNotFoundError:
        return {}, "ssh binary not found in PATH"
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:400]
        return {}, f"exit={proc.returncode}: {err}"
    try:
        return json.loads(proc.stdout), ""
    except json.JSONDecodeError as e:
        return {}, f"JSON parse error: {e} — got: {proc.stdout[:200]!r}"


def _run_ssh_health(host: str, port: int, user: str, key: str) -> tuple[dict, str]:
    if not Path(key).is_file():
        return {}, f"SSH key not found: {key}"
    cmd = [
        "ssh", "-4", "-p", str(port), "-i", key,
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=15",
        "-o", "StrictHostKeyChecking=accept-new",
        f"{user}@{host}",
        "python3", "-",
    ]
    try:
        proc = subprocess.run(
            cmd, input=_RELAY_HEALTH_PY, capture_output=True, text=True, timeout=90,
        )
    except subprocess.TimeoutExpired:
        return {}, "SSH timeout (90s)"
    except FileNotFoundError:
        return {}, "ssh binary not found in PATH"

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:400]
        return {}, f"exit={proc.returncode}: {err}"

    try:
        return json.loads(proc.stdout), ""
    except json.JSONDecodeError as e:
        return {}, f"JSON parse error: {e} — got: {proc.stdout[:200]!r}"


def _format_relay_health(label: str, data: dict) -> list[str]:
    out: list[str] = [f"--- {label} ---"]

    if not data:
        out.append("  NO DATA (SSH failed or restricted user)")
        return out

    load = data.get("load_1m")
    ratio = data.get("load_ratio")
    cpus = data.get("cpu_count", 1)
    if load is not None:
        flag = "HIGH — RELAY_CPU_BOUND" if ratio and ratio > LOAD_RATIO_HIGH else "OK"
        out.append(f"  load: {load} / {cpus} CPUs → ratio={ratio}  [{flag}]")

    mem_total = data.get("mem_total_mb")
    mem_avail = data.get("mem_avail_mb")
    if mem_total and mem_avail is not None:
        used_pct = (mem_total - mem_avail) / max(mem_total, 1) * 100
        out.append(f"  mem: {mem_avail} MB free / {mem_total} MB total ({used_pct:.0f}% used)")

    tcp_estab = data.get("tcp_established")
    ss_line = data.get("ss_tcp_line", "")
    if tcp_estab is not None:
        if tcp_estab > CONN_HIGH:
            flag = f"HIGH — RELAY_OVERLOADED ({tcp_estab} sessions)"
        elif tcp_estab > 60:
            flag = f"moderate ({tcp_estab} sessions)"
        else:
            flag = f"OK ({tcp_estab} sessions)"
        out.append(f"  TCP established: {tcp_estab}  [{flag}]")
        if ss_line:
            out.append(f"    {ss_line}")

    xray_cpu = data.get("xray_cpu_pct")
    xray_procs = data.get("xray_proc_count", 0)
    xray_name = data.get("xray_proc_sample", "")
    docker = data.get("docker_containers") or []
    if xray_procs:
        flag = "HIGH — RELAY_CPU_BOUND" if xray_cpu and xray_cpu > XRAY_CPU_HIGH else "OK"
        out.append(f"  XRay: {xray_procs} proc(s)  CPU={xray_cpu}%  [{flag}]  ({xray_name})")
    elif docker:
        out.append(f"  XRay: in docker ({', '.join(docker[:2])})")
    else:
        out.append("  XRay: process not found (check name — xray / sing-box / v2ray / docker)")

    bw = data.get("bw_mbs")
    bw_err = data.get("bw_error")
    bw_http = data.get("bw_http", "")
    bw_time = data.get("bw_time_s", 0)
    if bw is not None:
        estimate_s = FILE_MB / bw if bw > 0 else 9999
        if bw < BW_CAP_MBS:
            verdict = f"RELAY_BW_CAP — {bw} MB/s is severely low; relay uplink saturated"
        elif bw < BW_MARGINAL_MBS:
            verdict = f"RELAY_BW_MARGINAL — {bw} MB/s explains slow TG files (~{estimate_s:.0f}s per 23 MB)"
        elif bw < BW_OK_MBS:
            verdict = f"OK-ish — {bw} MB/s → 23 MB ≈ {estimate_s:.0f}s single hop"
        else:
            verdict = f"RELAY_LINK_OK — {bw} MB/s; relay bandwidth is NOT the bottleneck"
        out.append(f"  bandwidth (5MB Cloudflare, {bw_time:.1f}s): {bw} MB/s  [{verdict}]")
        if bw < BW_OK_MBS:
            out.append(
                f"  NOTE: relay→Cloudflare ≠ relay→LV throughput; "
                f"actual TG path: client→relay→LV→TG (2 hops add overhead)"
            )
    elif bw_err:
        out.append(f"  bandwidth test: FAILED — {bw_err}")

    return out


def _windows_ssh_fallbacks() -> list[tuple[str, str, int, str, str]]:
    """Direct SSH when ~/.ssh/config aliases are missing (Windows dev box)."""
    home = Path.home() / ".ssh"
    specs = [
        ("relay1", RELAY1_IP, 3344, "root", home / "selectel_relay"),
        ("relay2", RELAY2_IP, 22, "root", home / "timeweb_relay"),
    ]
    out: list[tuple[str, str, int, str, str]] = []
    for label, host, port, user, key in specs:
        if key.is_file():
            out.append((label, host, port, user, str(key)))
    return out


def phase2_ssh(ssh_user: str, ssh_aliases: list[str]) -> list[str]:
    out: list[str] = []

    # Mode A: explicit SSH config aliases (Windows-friendly, e.g. bvpn-relay)
    if ssh_aliases:
        seen_hosts: set[str] = set()
        for alias in ssh_aliases:
            print(f"  [{alias}] SSH via config alias ...")
            data, err = _run_ssh_health_alias(alias)
            if err:
                out.append(f"WARN: {alias} SSH failed: {err}")
                out.append(f"  Check: ssh {alias} 'uptime && ss -s && ps aux | grep -i xray'")
            else:
                out.extend(_format_relay_health(alias, data))
                seen_hosts.add(alias)
        # Fallback: probe relay2 by IP if alias missing/failed and key exists
        for label, host, port, user, key in _windows_ssh_fallbacks():
            if label == "relay1" and "bvpn-relay" in seen_hosts:
                continue
            if label == "relay2" and ("bvpn-relay2" in seen_hosts or any("relay2" in s for s in seen_hosts)):
                continue
            if any(host in s for s in seen_hosts):
                continue
            if ssh_user:
                user = ssh_user
            print(f"  [{label}] SSH fallback {user}@{host}:{port} ...")
            data, err = _run_ssh_health(host, port, user, key)
            if err:
                out.append(f"WARN: {label} SSH failed: {err}")
            else:
                out.extend(_format_relay_health(label, data))
        return out

    # Mode B: site.env / AMS-centric key paths
    cfg: dict[str, str] = {}
    for p in (Path("/etc/bvpn/ru-monitor.env"), _OPS / "site.env"):
        cfg.update(_load_env(p))

    endpoints = _relay_ssh_endpoints(cfg)
    if not endpoints:
        endpoints = [(lbl, h, p, u, k) for lbl, h, p, u, k in _windows_ssh_fallbacks()]
    if not endpoints:
        out.append("ERROR: no relay SSH endpoints configured.")
        out.append("  From Windows, use: --ssh --ssh-alias bvpn-relay bvpn-relay2")
        out.append("  (requires SSH config aliases in ~/.ssh/config — see ssh/config.example)")
        return out

    for label, host, port, user, key in endpoints:
        if ssh_user:
            user = ssh_user
        print(f"  [{label}] SSH {user}@{host}:{port} ...")
        data, err = _run_ssh_health(host, port, user, key)
        if err:
            out.append(f"WARN: {label} SSH failed: {err}")
            out.append(f"  Manual: ssh -p {port} -i {key} {user}@{host} 'uptime && ss -s && ps aux | grep -i xray'")
        else:
            out.extend(_format_relay_health(label, data))

    return out


# ── Summary ───────────────────────────────────────────────────────────────────

def _summarize(all_text: str, has_ssh: bool) -> list[str]:
    t = all_text.lower()
    findings: list[str] = []

    if "relay_bw_cap" in t:
        findings.append("RELAY_BW_CAP: relay uplink is saturated → upgrade relay VPS bandwidth tier")
    elif "relay_bw_marginal" in t:
        findings.append(
            "RELAY_BW_MARGINAL: relay is the TG file bottleneck. "
            "Options: add faster relay, or allow NL for large files (stealth trade-off)."
        )

    if "relay_cpu_bound" in t:
        findings.append("RELAY_CPU_BOUND: XRay XTLS saturating relay CPU → upgrade relay VPS or reduce user count")

    if "relay_overloaded" in t:
        findings.append("RELAY_OVERLOADED: relay handling too many concurrent sessions → add second relay or upgrade")

    if not findings and has_ssh:
        findings.append(
            "RELAY_LINK_OK: relay server is not obviously the bottleneck. "
            "Possible causes: LV→TG server path congestion, TG upload throttle from relay IP, "
            "or relay→LV backbone congestion (run mtr from relay to LV IP for packet loss)."
        )
    elif not findings and not has_ssh:
        findings.append(
            "Phase 2 not run. Re-run with --ssh from a machine with relay SSH access "
            "(AMS panel server or Windows with SSH key configured) to measure actual bandwidth."
        )

    findings.append(
        "\nQuick context: random balancer means each TG connection independently picks relay or NL. "
        "A single large-file upload stays on one path for its whole duration. "
        "If that path is relay at <1 MB/s, 23 MB takes >23s. "
        "Observatory (leastPing) would fix this but is disabled due to closed-pipe risk on RU (§0 P8)."
    )

    return findings


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ssh", action="store_true", help="Phase 2: SSH to relays, measure CPU + bandwidth")
    ap.add_argument("--ssh-user", default="", metavar="USER", help="Override SSH user (default from site.env)")
    ap.add_argument(
        "--ssh-alias", nargs="+", default=[], metavar="ALIAS",
        help="SSH config aliases to use instead of site.env keys (Windows-friendly). "
             "Example: --ssh-alias bvpn-relay bvpn-relay2",
    )
    ap.add_argument("--skip-template", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    all_lines: list[str] = []

    def emit(line: str = "") -> None:
        all_lines.append(line)
        if not args.json:
            print(line)

    emit("=== THROUGHPUT DIAGNOSTIC ===")
    emit(f"reference: {FILE_MB:.0f} MB file, target < 10 s (= {FILE_MB*1000/10/1000:.1f} MB/s needed)")

    if not args.skip_template:
        emit("\n── Phase 1: template config ──────────────────────")
        for line in phase1_template(args.template_uuid):
            emit(f"  {line}")

    emit("\n── Phase 1b: TCP latency probes ──────────────────")
    relay_probes, relay_err = probe_relay_ips()
    for r in relay_probes:
        if r.ok:
            emit(f"  relay {r.ip}:{RELAY_VPN_PORT}  tcp={r.tcp_connect_ms:.1f}ms  OK  (via {r.vantage})")
        else:
            emit(f"  relay {r.ip}:{RELAY_VPN_PORT}  FAIL  ({r.error})")
    if relay_err:
        emit(f"  relay probe warning: {relay_err}")

    if args.ssh:
        emit("\n── Phase 2: relay server health (SSH) ────────────")
        for line in phase2_ssh(args.ssh_user, args.ssh_alias):
            emit(f"  {line}")
    else:
        emit("\n  (skip Phase 2 — run with --ssh to measure relay CPU + bandwidth)")

    emit("\n── SUMMARY ───────────────────────────────────────")
    summary_lines = _summarize("\n".join(all_lines), has_ssh=args.ssh)
    for line in summary_lines:
        emit(line)

    if not args.ssh:
        emit("\nTo run bandwidth test on relay:")
        emit("  # Windows (SSH aliases from ssh/config.example configured):")
        emit("  python ops/diagnose_throughput.py --ssh --ssh-alias bvpn-relay bvpn-relay2")
        emit("  # From AMS server (has /root/.ssh keys):")
        emit("  python ops/diagnose_throughput.py --ssh")
        emit("  python ops/diagnose_throughput.py --ssh --ssh-user root")

    if args.json:
        print(json.dumps({"lines": all_lines, "summary": summary_lines}, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
