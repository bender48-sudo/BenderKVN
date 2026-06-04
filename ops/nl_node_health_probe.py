#!/usr/bin/env python3
"""NL production node baseline: panel stats + RU TCP probe + optional SSH health.

Answers: is NL connected, used, reachable from RU, BBR/remnanode OK?

Usage:
    python ops/nl_node_health_probe.py
    python ops/nl_node_health_probe.py --ssh-via-lv
    python ops/nl_node_health_probe.py --json
"""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402

NL_IP = "91.90.192.17"
LV_IP = "176.126.162.158"
RELAY_NL_PORT = 9443
NL_DIRECT_PORT = 443

_REMOTE_HEALTH = r"""
import json, subprocess, re
out = {}
try:
    out["hostname"] = subprocess.check_output(["hostname"], text=True).strip()
except Exception as e:
    out["hostname_error"] = str(e)
for cmd, key in [
    (["uptime"], "uptime"),
    (["free", "-h"], "free_h"),
    (["nproc"], "cpu_count"),
]:
    try:
        out[key] = subprocess.check_output(cmd, text=True, timeout=10).strip()
    except Exception as e:
        out[key + "_error"] = str(e)
try:
    r = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
        capture_output=True, text=True, timeout=15,
    )
    out["docker_ps"] = r.stdout.strip().splitlines()
except Exception as e:
    out["docker_ps_error"] = str(e)
try:
    r = subprocess.run(
        ["docker", "stats", "remnanode", "--no-stream", "--format",
         "{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"],
        capture_output=True, text=True, timeout=20,
    )
    if r.returncode == 0:
        parts = (r.stdout or "").strip().split("\t")
        out["remnanode_stats"] = {
            "cpu_pct": parts[0] if parts else None,
            "mem": parts[1] if len(parts) > 1 else None,
            "net_io": parts[2] if len(parts) > 2 else None,
        }
    else:
        out["remnanode_stats_error"] = (r.stderr or r.stdout or "")[:200]
except Exception as e:
    out["remnanode_stats_error"] = str(e)
try:
    cc = subprocess.check_output(["sysctl", "-n", "net.ipv4.tcp_congestion_control"], text=True).strip()
    qd = subprocess.check_output(["sysctl", "-n", "net.core.default_qdisc"], text=True).strip()
    out["bbr"] = {"cc": cc, "qdisc": qd, "ok": cc == "bbr" and qd in ("fq", "fq_codel")}
except Exception as e:
    out["bbr_error"] = str(e)
try:
    r = subprocess.run(["ss", "-s"], capture_output=True, text=True, timeout=10)
    m = re.search(r"TCP:\s+(\d+).*estab\s+(\d+)", r.stdout or "")
    if m:
        out["tcp_total"] = int(m.group(1))
        out["tcp_estab"] = int(m.group(2))
except Exception as e:
    out["ss_error"] = str(e)
print(json.dumps(out))
"""


def _panel_nl_report(c: PanelClient) -> dict:
    nodes = c.get_or_raise("/api/nodes")["response"]
    if not isinstance(nodes, list):
        nodes = nodes.get("nodes", nodes.get("items", []))
    nl_nodes = [n for n in nodes if NL_IP in str(n.get("address", ""))]
    lv_nodes = [n for n in nodes if LV_IP in str(n.get("address", ""))]

    hosts = c.get_or_raise("/api/hosts")["response"]
    if not isinstance(hosts, list):
        hosts = hosts.get("hosts", hosts.get("items", []))

    nl_hosts = [h for h in hosts if str(h.get("address") or "") == NL_IP]
    inject = []
    try:
        tid = site_urls.REMNA_TEMPLATE_UUID
        t = c.get_or_raise(f"/api/subscription-templates/{tid}")["response"]
        doc = t.get("templateJson") or {}
        vals = (
            (doc.get("remnawave") or {}).get("injectHosts") or [{}]
        )[0].get("selector", {}).get("values") or []
        hm = {h["uuid"]: h for h in hosts}
        for u in vals:
            h = hm.get(u, {})
            if str(h.get("address") or "") == NL_IP:
                inject.append(
                    {
                        "port": h.get("port"),
                        "remark": h.get("remark"),
                        "in_inject": True,
                    }
                )
    except Exception as e:
        inject = [{"error": str(e)}]

    def _node_row(n: dict) -> dict:
        tb = n.get("trafficUsedBytes") or 0
        return {
            "name": n.get("name"),
            "connected": n.get("isConnected"),
            "disabled": n.get("isDisabled"),
            "users_online": n.get("usersOnline"),
            "traffic_gb": round(int(tb) / (1024**3), 2),
        }

    direct_443 = [
        h
        for h in nl_hosts
        if int(h.get("port") or 0) == NL_DIRECT_PORT and "Direct" in (h.get("remark") or "")
    ]
    def _legacy_relay_nl(h: dict) -> bool:
        remark = str(h.get("remark") or "")
        if "Relay" not in remark or "Netherlands" not in remark:
            return False
        try:
            return int(h.get("port") or 0) == RELAY_NL_PORT or "9443" in remark
        except (TypeError, ValueError):
            return "9443" in remark

    relay_9443 = [h for h in hosts if _legacy_relay_nl(h)]
    relay_9443_active = [h for h in relay_9443 if not h.get("isDisabled")]

    lv_online = sum(int(n.get("usersOnline") or 0) for n in lv_nodes)
    nl_online = sum(int(n.get("usersOnline") or 0) for n in nl_nodes)
    lv_traffic = sum(int(n.get("trafficUsedBytes") or 0) for n in lv_nodes)
    nl_traffic = sum(int(n.get("trafficUsedBytes") or 0) for n in nl_nodes)
    total_traffic = lv_traffic + nl_traffic
    nl_share_pct = round(100.0 * nl_traffic / total_traffic, 2) if total_traffic else 0.0

    return {
        "nl_node": [_node_row(n) for n in nl_nodes],
        "lv_node": [_node_row(n) for n in lv_nodes],
        "nl_hosts_total": len(nl_hosts),
        "nl_direct_443": len(direct_443),
        "nl_relay_9443_legacy_total": len(relay_9443),
        "nl_relay_9443_legacy_active": len(relay_9443_active),
        "nl_in_inject_hosts": len(inject),
        "inject_nl": inject,
        "session_ratio_nl_vs_lv": (
            f"{nl_online} online NL vs {lv_online} online LV (panel inbounds)"
        ),
        "traffic_share_nl_pct": nl_share_pct,
    }


def _run_nl_reachability() -> tuple[bool, str]:
    script = _OPS / "nl_reachability_probe_ru.py"
    if not script.is_file():
        return False, "missing nl_reachability_probe_ru.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(_OPS.parent),
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"
    out = (proc.stdout or "") + (proc.stderr or "")
    ok = "NL_REACHABILITY_PROBE_RU_OK" in out
    return ok, out.strip()[-500:]


def _ssh_nl_via_lv() -> tuple[dict | None, str]:
    """LV jump: requires bvpn_nl key on LV at /root/.ssh/bvpn_nl."""
    remote = (
        "ssh -o BatchMode=yes -o ConnectTimeout=15 -i /root/.ssh/bvpn_nl "
        f"-p 3333 root@{NL_IP} python3 -"
    )
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=25", "bvpn-lv", remote]
    try:
        proc = subprocess.run(
            cmd,
            input=_REMOTE_HEALTH,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return None, str(e)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:400]
        return None, err
    try:
        return json.loads(proc.stdout), ""
    except json.JSONDecodeError as e:
        return None, f"json: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssh-via-lv", action="store_true", help="docker/BBR on NL via LV jump")
    ap.add_argument(
        "--require-ru-probe",
        action="store_true",
        help="fail if nl_reachability cannot run (needs relay SSH keys on LV)",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report: dict = {"nl_ip": NL_IP}
    errors: list[str] = []

    try:
        c = PanelClient()
        report["panel"] = _panel_nl_report(c)
    except Exception as e:
        errors.append(f"panel: {e}")
        report["panel"] = None

    reach_ok, reach_tail = _run_nl_reachability()
    report["ru_tcp_probe_ok"] = reach_ok
    ru_skipped = (not reach_ok) and "missing SSH key" in reach_tail
    report["ru_tcp_skipped"] = ru_skipped
    if not reach_ok and not ru_skipped:
        errors.append(f"ru_tcp: {reach_tail}")
    elif ru_skipped and not args.require_ru_probe:
        print("  RU TCP :443 probe: SKIP (run on bvpn-lv for full check)")

    if args.ssh_via_lv:
        ssh_data, ssh_err = _ssh_nl_via_lv()
        report["ssh_nl"] = ssh_data
        if ssh_err:
            errors.append(f"ssh_nl: {ssh_err}")
        elif ssh_data and not (ssh_data.get("bbr") or {}).get("ok"):
            errors.append(
                f"bbr: cc={ssh_data.get('bbr', {}).get('cc')} qdisc={ssh_data.get('bbr', {}).get('qdisc')}"
            )

    p = report.get("panel") or {}
    nl_connected = any(n.get("connected") for n in (p.get("nl_node") or []))
    has_inject = (p.get("nl_in_inject_hosts") or 0) >= 4

    print("=== NL node health baseline ===")
    if p:
        for n in p.get("nl_node") or []:
            print(
                f"  panel NL: connected={n.get('connected')} users_online={n.get('users_online')} "
                f"traffic_gb={n.get('traffic_gb')}"
            )
        for n in p.get("lv_node") or []:
            print(
                f"  panel LV: connected={n.get('connected')} users_online={n.get('users_online')} "
                f"traffic_gb={n.get('traffic_gb')}"
            )
        print(f"  NL traffic share vs LV (lifetime bytes): {p.get('traffic_share_nl_pct')}%")
        print(f"  injectHosts NL entries: {p.get('nl_in_inject_hosts')}")
        print(
            f"  legacy relay→NL :9443 hosts: {p.get('nl_relay_9443_legacy_total')} total, "
            f"{p.get('nl_relay_9443_legacy_active')} still enabled"
        )
    if not ru_skipped:
        print(f"  RU TCP :443 probe: {'OK' if reach_ok else 'FAIL'}")
    if report.get("ssh_nl"):
        s = report["ssh_nl"]
        print(f"  SSH NL hostname: {s.get('hostname')}")
        rs = s.get("remnanode_stats") or {}
        if rs:
            print(f"  remnanode: CPU={rs.get('cpu_pct')} mem={rs.get('mem')} net={rs.get('net_io')}")
        bbr = s.get("bbr") or {}
        print(f"  BBR: {bbr.get('cc')} qdisc={bbr.get('qdisc')} ok={bbr.get('ok')}")

    ru_ok = reach_ok or (ru_skipped and not args.require_ru_probe)
    gate_ok = nl_connected and has_inject and ru_ok and not errors

    if args.json:
        report["errors"] = errors
        report["ok"] = gate_ok
        print(json.dumps(report, indent=2, ensure_ascii=False))

    if errors:
        for e in errors:
            print(f"WARN: {e}", file=sys.stderr)
    if gate_ok:
        print("NL_NODE_HEALTH_OK")
        return 0
    print("NL_NODE_HEALTH_FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
