#!/usr/bin/env python3
"""Analyze Happ report.zip for TUN mode stability (CLIENT-STABILITY).

Read-only local tool — redacts secrets in all output.

Usage:
    python ops/analyze_happ_report_tun.py path/to/report.zip
    python ops/analyze_happ_report_tun.py path/to/report.zip --json
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"vless://[^\s\"']+", re.I), "vless://[REDACTED]"),
    (re.compile(r"https?://[^\s\"']*api/sub/[^\s\"']+", re.I), "https://[REDACTED]/api/sub/[REDACTED]"),
    (re.compile(r"https?://[^\s\"']*pac\?[^\s\"']+", re.I), "http://[REDACTED]/pac?[REDACTED]"),
    (re.compile(r"happ://[^\s\"']+", re.I), "happ://[REDACTED]"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{20,}"), "[REDACTED_JWT]"),
    (re.compile(r"secret=[^\s&\"']+", re.I), "secret=[REDACTED]"),
    (re.compile(r"hash=[^\s&\"']+", re.I), "hash=[REDACTED]"),
    (
        re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
        ),
        "[REDACTED_UUID]",
    ),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b"), "[IP]"),
]

ERROR_TYPE_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("io_timeout", re.compile(r"i/o timeout|deadline exceeded", re.I)),
    ("forcibly_closed", re.compile(r"forcibly closed|connection reset|broken pipe", re.I)),
    ("aborted_host", re.compile(r"aborted by the host|operation was aborted", re.I)),
    ("dns_error", re.compile(r"dns|lookup|resolve", re.I)),
    ("route_error", re.compile(r"route|routing", re.I)),
    ("tun_error", re.compile(r"tun|interface|happ-tun", re.I)),
    ("download_closed", re.compile(r"download.*closed|read.*closed", re.I)),
    ("upload_closed", re.compile(r"upload.*closed|write.*closed", re.I)),
]

TRACK_A_SIGNALS: list[tuple[str, re.Pattern[str], str]] = [
    ("tun_crash", re.compile(r"sing-box-tun.*exit|exit code 1|process.*crashed", re.I), "A"),
    ("interface_not_up", re.compile(r"not UP|interface.*not found|Cannot set DNS", re.I), "A"),
    ("daemon_stop", re.compile(r"service stopped|daemon.*stop|Failed to start TUN", re.I), "A"),
]

TRACK_E_SIGNALS: list[tuple[str, re.Pattern[str], str]] = [
    ("io_timeout_relay", re.compile(r"i/o timeout.*relay|timeout opening connection", re.I), "E"),
    ("remote_reset", re.compile(r"forcibly closed by remote", re.I), "E"),
    ("reality_tls", re.compile(r"REALITY|TLS handshake|certificate", re.I), "E"),
]

TRACK_H_SIGNALS: list[tuple[str, re.Pattern[str], str]] = [
    ("xray_captured", re.compile(r"outbound/direct.*relay|opening connection.*relay.*direct", re.I), "H"),
    ("loop_hint", re.compile(r"172\.18\.|docker|loopback.*relay", re.I), "H"),
]


def redact_text(text: str) -> str:
    out = text
    for pat, repl in REDACT_PATTERNS:
        out = pat.sub(repl, out)
    return out


def read_zip_text(zf: zipfile.ZipFile, basename: str, *, limit: int = 2_000_000) -> str:
    for name in zf.namelist():
        if name.replace("\\", "/").rstrip("/").endswith(basename):
            raw = zf.read(name)
            text = raw.decode("utf-8", errors="replace")
            if len(text) > limit:
                return text[:limit] + "\n... [truncated]"
            return text
    return ""


def extract_config(sel_doc: dict) -> tuple[dict, dict]:
    meta = sel_doc.get("selected") or sel_doc
    if not isinstance(meta, dict):
        return {}, {}
    cfg_raw = meta.get("config")
    if isinstance(cfg_raw, str):
        cfg = json.loads(cfg_raw)
    elif isinstance(cfg_raw, dict):
        cfg = cfg_raw
    else:
        cfg = sel_doc if "outbounds" in sel_doc else {}
    return meta, cfg


def analyze_profile(sel_raw: str) -> dict:
    out: dict = {}
    try:
        meta, cfg = extract_config(json.loads(sel_raw))
        out["profile_name"] = meta.get("name", "?")
        out["profile_type"] = meta.get("type", "?")
        outbounds = cfg.get("outbounds") or []
        tags = [ob.get("tag") or ob.get("name") or "?" for ob in outbounds]
        proxy_tags = [t for t in tags if re.match(r"proxy(-\d+)?$", t, re.I)]
        relay1 = sum(1 for t in proxy_tags if t in ("proxy", "proxy-2", "proxy-3"))  # first trio heuristic
        relay2 = sum(1 for t in proxy_tags if t in ("proxy-4", "proxy-5", "proxy-6"))
        nl = sum(1 for t in tags if re.search(r"\bnl\b|netherlands", t, re.I))
        lv = sum(1 for t in tags if re.search(r"\blv\b|latvia", t, re.I))
        routing = cfg.get("routing") or {}
        balancers = routing.get("balancers") or []
        if isinstance(balancers, list):
            bal_names = [b.get("tag", "?") if isinstance(b, dict) else str(b) for b in balancers]
        elif isinstance(balancers, dict):
            bal_names = list(balancers.keys())
        else:
            bal_names = []
        dns = cfg.get("dns") or {}
        servers = dns.get("servers") or []
        inbounds = cfg.get("inbounds") or []
        socks = [ib for ib in inbounds if (ib.get("protocol") or "").lower() in ("socks", "http")]
        out.update(
            {
                "outbound_count": len(outbounds),
                "proxy_outbound_count": len(proxy_tags),
                "relay1_proxy_count": relay1 if len(proxy_tags) == 6 else len(proxy_tags) // 2,
                "relay2_proxy_count": relay2 if len(proxy_tags) == 6 else len(proxy_tags) - len(proxy_tags) // 2,
                "nl_count": nl,
                "lv_count": lv,
                "balancer_names": bal_names,
                "dns_server_count": len(servers),
                "dns_query_strategy": dns.get("queryStrategy") or dns.get("strategy"),
                "inbound_count": len(inbounds),
                "local_socks_ports": [
                    ib.get("port") for ib in socks if ib.get("listen") in ("127.0.0.1", "::1", None)
                ],
                "candidate_d_shape": len(proxy_tags) == 6 and nl == 0 and lv == 0,
                "import_ok": len(outbounds) >= 6 and len(proxy_tags) >= 6,
            }
        )
    except (json.JSONDecodeError, TypeError) as e:
        out["parse_error"] = str(e)
    return out


def check_direct_ip_overlap(cfg: dict, routing_profile: dict | None) -> dict:
    """Detect relay server IPs listed in Happ routing directIp (Track D signal)."""
    if not routing_profile:
        return {"overlap_count": 0}
    direct_ips = {item.split("/")[0] for item in routing_profile.get("directIp") or []}
    relay_ips: set[str] = set()
    for ob in cfg.get("outbounds") or []:
        tag = ob.get("tag") or ""
        if not re.match(r"proxy(-\d+)?$", tag, re.I):
            continue
        s = ob.get("settings") or {}
        addr = s.get("address") or s.get("server")
        if not addr and s.get("vnext"):
            addr = s["vnext"][0].get("address")
        if addr:
            relay_ips.add(addr)
    overlap = relay_ips & direct_ips
    return {
        "direct_ip_count": len(direct_ips),
        "relay_server_ip_count": len(relay_ips),
        "overlap_count": len(overlap),
        "relay_in_direct_ip": bool(overlap),
    }


def analyze_tun_log_stream(text: str) -> dict:
    total_lines = 0
    error_lines = 0
    success_hints = 0
    err_by_type: Counter[str] = Counter()
    err_by_min: Counter[str] = Counter()
    relay1_err = relay2_err = direct_err = docker_err = 0
    outbound_direct_relay = 0
    time_pat = re.compile(r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}|\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})")
    relay1_pat = re.compile(r"relay\s*#?\s*1|Relay[_\s-]*1", re.I)
    relay2_pat = re.compile(r"relay\s*#?\s*2|Relay[_\s-]*2", re.I)

    for line in text.splitlines():
        total_lines += 1
        ll = line.lower()
        is_err = (
            " error" in ll
            or ll.startswith("error")
            or "fail" in ll
            or "forcibly closed" in ll
            or "i/o timeout" in ll
        )
        if "connected" in ll or "established" in ll:
            success_hints += 1
        if not is_err:
            continue
        error_lines += 1
        m = time_pat.search(line)
        if m:
            err_by_min[m.group(1)] += 1
        for name, pat in ERROR_TYPE_RULES:
            if pat.search(line):
                err_by_type[name] += 1
        if relay1_pat.search(line):
            relay1_err += 1
        elif relay2_pat.search(line):
            relay2_err += 1
        elif "172.18." in line or "docker" in ll:
            docker_err += 1
        elif "outbound/direct" in ll or "direct]" in ll:
            direct_err += 1
        if re.search(r"outbound/direct.*relay|opening connection.*relay", line, re.I):
            outbound_direct_relay += 1

    return {
        "total_lines": total_lines,
        "error_like_lines": error_lines,
        "success_hint_lines": success_hints,
        "errors_by_type": dict(err_by_type.most_common(15)),
        "errors_by_minute_top10": dict(err_by_min.most_common(10)),
        "relay1_errors": relay1_err,
        "relay2_errors": relay2_err,
        "direct_errors": direct_err,
        "docker_local_errors": docker_err,
        "outbound_direct_to_relay": outbound_direct_relay,
    }


def scan_signals(text: str, rules: list[tuple[str, re.Pattern[str], str]]) -> list[str]:
    hits = []
    for sig_id, pat, _ in rules:
        if pat.search(text):
            hits.append(sig_id)
    return hits


@dataclass
class TunAnalysisResult:
    zip_name: str
    versions: str
    mode: dict
    profile: dict
    routing_overlap: dict
    tun_lifecycle: dict
    tun_log_stats: dict
    track_signals: dict
    local_clues: dict
    timeline_events: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def analyze_report_zip(path: Path) -> TunAnalysisResult:
    with zipfile.ZipFile(path) as zf:
        versions = read_zip_text(zf, "versions.txt").strip()
        settings_raw = read_zip_text(zf, "settings.json")
        app_log = read_zip_text(zf, "application_log.txt")
        happd = read_zip_text(zf, "happd.log", limit=500_000)
        tun_log = read_zip_text(zf, "tun_log.txt", limit=5_000_000)
        sel_raw = read_zip_text(zf, "selected_server.json")
        route_raw = read_zip_text(zf, "routing.json")
        ipcfg = read_zip_text(zf, "ipconfig all.txt")
        routes = read_zip_text(zf, "route print.txt")
        tasklist = read_zip_text(zf, "tasklist.txt")

    mode: dict = {"tun": None, "system_proxy": None, "routing_profile": None}
    try:
        sj = json.loads(settings_raw)
        pref = sj.get("Preferences") or sj
        adv = pref.get("AdvancedSettings") or {}
        if adv.get("tun") is not None:
            mode["tun"] = adv.get("tun")
        if adv.get("systemProxy") is not None:
            mode["system_proxy"] = adv.get("systemProxy")
        tun_set = pref.get("TunnelSettings") or {}
        rt_set = tun_set.get("Routing") or {}
        if rt_set.get("selectedRoutingRule"):
            mode["routing_profile"] = rt_set.get("selectedRoutingRule")
        if rt_set.get("useRouting") is not None:
            mode["use_routing"] = rt_set.get("useRouting")
    except json.JSONDecodeError:
        mode["parse_error"] = True

    routing_profile: dict | None = None
    try:
        rt = json.loads(route_raw)
        routing_profile = rt.get("activeProfile") if isinstance(rt.get("activeProfile"), dict) else None
        mode["active_routing_profile_name"] = (
            routing_profile.get("name") if routing_profile else rt.get("activeProfile")
        )
        mode["routing_enabled"] = rt.get("routingEnabled")
    except json.JSONDecodeError:
        pass

    meta, cfg = {}, {}
    try:
        meta, cfg = extract_config(json.loads(sel_raw))
    except (json.JSONDecodeError, TypeError):
        pass
    profile = analyze_profile(sel_raw)
    routing_overlap = check_direct_ip_overlap(cfg, routing_profile)
    tun_stats = analyze_tun_log_stream(tun_log)

    tun_lifecycle = {
        "tun_crash": bool(re.search(r"sing-box-tun.*exit|exit code 1", happd + app_log, re.I)),
        "interface_not_up": bool(re.search(r"not UP after|interface not found|Cannot set DNS", happd + app_log, re.I)),
        "interface_up_ok": bool(re.search(r"interface UP|UP after|DNS.*set successfully|DNS 1\.1\.1\.1", happd + app_log, re.I)),
        "dns_set_ok": bool(re.search(r"DNS.*set successfully|set DNS.*1\.1\.1\.1", happd + app_log, re.I)),
        "dns_set_fail": bool(re.search(r"Cannot set DNS", happd + app_log, re.I)),
    }

    combined = happd + "\n" + app_log + "\n" + tun_log[:200_000]
    track_signals = {
        "track_a": scan_signals(combined, TRACK_A_SIGNALS),
        "track_e": scan_signals(combined, TRACK_E_SIGNALS),
        "track_h": scan_signals(combined, TRACK_H_SIGNALS),
    }

    local_clues = {
        "check_point_adapter": "check point" in ipcfg.lower(),
        "npcap_adapter": "npcap" in ipcfg.lower(),
        "happ_tun_in_ipconfig": "happ-tun" in ipcfg.lower() or "happ-tun" in ipcfg.lower(),
        "stale_proxy_backup": bool(re.search(r"Backed up proxy|localhost:1080|pac\?", app_log, re.I)),
        "urbanvpn_hint": "urban" in tasklist.lower(),
        "vpn_process_count": sum(
            1
            for line in tasklist.splitlines()
            if re.search(r"happ|sing-box|xray|checkpoint|openvpn|wireguard", line, re.I)
        ),
        "happ_tun_routes": sum(1 for line in routes.splitlines() if "happ" in line.lower()),
        "wifi_default_route": sum(1 for line in routes.splitlines() if "0.0.0.0" in line and "wifi" in line.lower()),
    }

    timeline: list[str] = []
    for line in app_log.splitlines():
        ll = line.lower()
        if any(
            k in ll
            for k in (
                "tun",
                "connect",
                "disconnect",
                "crash",
                "dns",
                "interface",
                "daemon",
                "start",
                "stop",
                "error",
                "proxy",
            )
        ):
            timeline.append(redact_text(line[:220]))
    for line in happd.splitlines():
        ll = line.lower()
        if any(k in ll for k in ("tun", "crash", "dns", "interface", "exit", "not up", "cannot set", "up after")):
            timeline.append(redact_text(line[:220]))

    notes: list[str] = []
    if tun_lifecycle["tun_crash"] and not tun_lifecycle["interface_up_ok"]:
        notes.append("Track A: TUN daemon/interface failure pattern")
    if tun_stats["error_like_lines"] > 500 and tun_lifecycle.get("interface_up_ok"):
        notes.append("Track E/H: TUN up but massive connection errors to relays")
    if tun_stats.get("outbound_direct_to_relay", 0) > 50:
        notes.append("Track H: Xray relay egress via outbound/direct captured by TUN — possible route loop")
    if routing_overlap.get("relay_in_direct_ip"):
        notes.append("Track D: relay server IPs in Happ routing directIp — outbound/direct to relays")
    if profile.get("import_ok"):
        notes.append("Profile integrity OK — not Track C")
    if local_clues["check_point_adapter"]:
        notes.append("Check Point VPN adapter present — Track F secondary factor")

    return TunAnalysisResult(
        zip_name=path.name,
        versions=redact_text(versions),
        mode=mode,
        profile=profile,
        routing_overlap=routing_overlap,
        tun_lifecycle=tun_lifecycle,
        tun_log_stats=tun_stats,
        track_signals=track_signals,
        local_clues=local_clues,
        timeline_events=timeline[:60],
        notes=notes,
    )


def result_to_dict(r: TunAnalysisResult) -> dict:
    return {
        "zip_name": r.zip_name,
        "versions": r.versions,
        "mode": r.mode,
        "profile": r.profile,
        "routing_overlap": r.routing_overlap,
        "tun_lifecycle": r.tun_lifecycle,
        "tun_log_stats": r.tun_log_stats,
        "track_signals": r.track_signals,
        "local_clues": r.local_clues,
        "timeline_events": r.timeline_events,
        "notes": r.notes,
    }


def print_human(r: TunAnalysisResult) -> None:
    print(f"TUN_ANALYSIS zip={r.zip_name}")
    print(f"versions: {r.versions}")
    print(f"mode: {json.dumps(r.mode, ensure_ascii=False)}")
    print(f"profile: {json.dumps(r.profile, ensure_ascii=False)}")
    print(f"routing_overlap: {json.dumps(r.routing_overlap, ensure_ascii=False)}")
    print(f"tun_lifecycle: {json.dumps(r.tun_lifecycle, ensure_ascii=False)}")
    print(f"tun_log_stats: {json.dumps(r.tun_log_stats, ensure_ascii=False, indent=2)}")
    print(f"track_signals: {json.dumps(r.track_signals, ensure_ascii=False)}")
    print(f"local_clues: {json.dumps(r.local_clues, ensure_ascii=False)}")
    print("timeline (first 30):")
    for ev in r.timeline_events[:30]:
        print(f"  | {ev}")
    for note in r.notes:
        print(f"NOTE: {note}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze Happ report.zip for TUN stability")
    ap.add_argument("report_zip", type=Path, nargs="+", help="One or more report.zip paths")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    results = []
    for p in args.report_zip:
        if not p.is_file():
            print(f"FAIL: missing {p}", file=sys.stderr)
            return 1
        results.append(analyze_report_zip(p.resolve()))

    if args.json:
        print(json.dumps([result_to_dict(r) for r in results], ensure_ascii=False, indent=2))
    else:
        for i, r in enumerate(results):
            if i:
                print("\n" + "=" * 60 + "\n")
            print_human(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
