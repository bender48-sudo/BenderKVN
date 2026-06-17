"""Synthetic tests for ops/analyze_happ_report_tun.py — no real reports."""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from analyze_happ_report_tun import (  # noqa: E402
    analyze_core_relay_direct_rules,
    analyze_error_endpoints,
    analyze_profile,
    analyze_report_zip,
    analyze_tun_log_stream,
    analyze_tun_sessions,
    categorize_endpoint,
    check_direct_ip_overlap,
    detect_final_state_overwrite,
    endpoint_token,
    estimate_bender_segment_stats,
    redact_text,
)


def _make_zip(files: dict[str, str]) -> Path:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    tmp = Path(__file__).parent / "_tmp_tun_report.zip"
    tmp.write_bytes(buf.getvalue())
    return tmp


def test_redact_pac_url():
    raw = "GET https://evil.example/pac?hash=abc&secret=xyz vless://x@h:443"
    out = redact_text(raw)
    assert "secret=xyz" not in out
    assert "vless://[REDACTED]" in out


def test_direct_ip_overlap_detected():
    cfg = {
        "outbounds": [
            {"tag": "proxy", "settings": {"vnext": [{"address": "203.0.113.10"}]}},
            {"tag": "direct", "protocol": "freedom"},
        ]
    }
    profile = {"directIp": ["203.0.113.10/32", "10.0.0.0/8"]}
    result = check_direct_ip_overlap(cfg, profile)
    assert result["relay_in_direct_ip"] is True
    assert result["overlap_count"] == 1
    assert result["geoip_ru_in_direct_ip"] is False


def test_geoip_ru_flagged_in_direct_ip():
    cfg = {"outbounds": [{"tag": "proxy", "settings": {"vnext": [{"address": "203.0.113.10"}]}}]}
    profile = {"directIp": ["geoip:ru", "10.0.0.0/8"]}
    result = check_direct_ip_overlap(cfg, profile)
    assert result["geoip_ru_in_direct_ip"] is True
    assert result["relay_in_direct_ip"] is False


def test_core_relay_direct_rules_expected():
    cfg = {
        "routing": {
            "rules": [
                {"outboundTag": "direct", "ip": ["203.0.113.10/32", "203.0.113.11/32"]},
                {"outboundTag": "direct", "domain": ["localhost"]},
            ]
        }
    }
    result = analyze_core_relay_direct_rules(cfg)
    assert result["core_relay_direct_expected"] is True
    assert result["core_relay_direct_ip_count"] == 2


def test_tun_log_distinguishes_directip_leak_vs_long_resets():
    leak_log = "\n".join(
        f"ERROR open connection to 203.0.113.10 using outbound/direct[direct]: dial tcp: i/o timeout"
        for _ in range(200)
    )
    reset_log = "\n".join(
        f"ERROR connection download closed: raw-read tcp forcibly closed by the remote host" for _ in range(200)
    )
    leak_stats = analyze_tun_log_stream(leak_log)
    reset_stats = analyze_tun_log_stream(reset_log)
    assert leak_stats["happ_directip_leak_signal"] is True
    assert reset_stats["long_connection_reset_signal"] is True
    assert reset_stats["happ_directip_leak_signal"] is False


def test_analyze_profile_candidate_d_shape():
    cfg = {
        "outbounds": [{"tag": t} for t in ("proxy", "proxy-2", "proxy-3", "proxy-4", "proxy-5", "proxy-6")]
        + [{"tag": "direct"}, {"tag": "block"}],
        "routing": {
            "balancers": [
                {"tag": "Intl_Direct", "selector": ["proxy"], "strategy": {"type": "random"}},
            ]
        },
        "dns": {"servers": ["1.1.1.1"], "queryStrategy": "UseIP"},
        "inbounds": [{"protocol": "socks", "port": 10808, "listen": "127.0.0.1"}],
    }
    sel = json.dumps({"selected": {"name": "BenderVPN Auto", "config": cfg}})
    prof = analyze_profile(sel)
    assert prof["import_ok"] is True
    assert prof["candidate_d_shape"] is True
    assert prof["balancer_names"] == ["Intl_Direct"]


def test_empty_zip_class_g():
    path = _make_zip({"readme.txt": "empty"})
    try:
        result = analyze_report_zip(path)
        assert result.tun_log_stats["error_like_lines"] == 0
        assert "track_a" in result.track_signals
    finally:
        path.unlink(missing_ok=True)


def test_detect_overwritten_final_state_safevpn():
    sel = json.dumps({"selected": {"name": "SafeVPN Proxy", "type": "proxy", "config": "{}"}})
    settings = json.dumps(
        {"Preferences": {"AdvancedSettings": {"tun": False, "systemProxy": True}}}
    )
    app_log = "12:01 disconnected BenderVPN Auto\n12:02 connected SafeVPN Proxy mode"
    guard = detect_final_state_overwrite(sel, settings, app_log)
    assert guard["final_selected_is_bender"] is False
    assert guard["usable_as_bender_profile_evidence"] is False
    assert guard["switched_away_detected"] is True
    assert guard["final_mode_proxy_not_tun"] is True


def test_detect_clean_bender_final_state():
    sel = json.dumps({"selected": {"name": "BenderVPN Auto", "config": "{}"}})
    settings = json.dumps({"Preferences": {"AdvancedSettings": {"tun": True, "systemProxy": False}}})
    guard = detect_final_state_overwrite(sel, settings, "connected BenderVPN Auto TUN")
    assert guard["final_selected_is_bender"] is True
    assert guard["usable_as_bender_profile_evidence"] is True
    assert guard["switched_away_detected"] is False


def test_bender_segment_hint_when_overwritten():
    guard = detect_final_state_overwrite(
        json.dumps({"selected": {"name": "SafeVPN"}}),
        "{}",
        "line1 connect BenderVPN\nline2 disconnect BenderVPN Auto\nline3 SafeVPN",
    )
    seg = estimate_bender_segment_stats(
        "line1 connect BenderVPN\nline2 disconnect BenderVPN Auto\nline3 SafeVPN",
        "",
        guard,
    )
    assert seg["bender_segment_available"] is True
    assert "export before switching" in seg["segment_hint"] or "lines 0" in seg["segment_hint"]


def test_analyze_zip_flags_overwritten_export():
    cfg = {
        "outbounds": [{"tag": t} for t in ("proxy", "proxy-2", "proxy-3", "proxy-4", "proxy-5", "proxy-6")]
        + [{"tag": "direct"}, {"tag": "block"}],
    }
    sel = json.dumps({"selected": {"name": "SafeVPN Proxy", "config": cfg}})
    settings = json.dumps(
        {"Preferences": {"AdvancedSettings": {"tun": False, "systemProxy": True}}}
    )
    path = _make_zip(
        {
            "versions.txt": "Happ 2.16.2",
            "settings.json": settings,
            "selected_server.json": sel,
            "routing.json": "{}",
            "application_log.txt": "disconnected BenderVPN Auto\nconnected SafeVPN",
            "happd.log": "",
            "tun_log.txt": "",
            "ipconfig all.txt": "",
            "route print.txt": "",
            "tasklist.txt": "",
        }
    )
    try:
        result = analyze_report_zip(path)
        assert result.final_state_guard["usable_as_bender_profile_evidence"] is False
        assert any("overwritten" in n.lower() for n in result.notes)
    finally:
        path.unlink(missing_ok=True)


def test_lab_relay2_profile_detection():
    cfg = {
        "outbounds": [
            {"tag": "proxy-4", "settings": {"vnext": [{"address": "203.0.113.20"}]}},
            {"tag": "proxy-5", "settings": {"vnext": [{"address": "203.0.113.20"}]}},
            {"tag": "proxy-6", "settings": {"vnext": [{"address": "203.0.113.20"}]}},
            {"tag": "direct"},
            {"tag": "block"},
        ],
        "routing": {
            "balancers": [
                {"tag": "Intl_Direct", "selector": {"outboundTags": ["proxy-4", "proxy-5", "proxy-6"]}},
            ]
        },
    }
    sel = json.dumps(
        {
            "selected": {
                "name": "BenderVPN Auto [LAB relay2-only — do NOT refresh sub]",
                "config": cfg,
            }
        }
    )
    prof = analyze_profile(sel)
    assert prof["relay1_proxy_count"] == 0
    assert prof["relay2_proxy_count"] == 3
    assert prof["lab_relay2_only"] is True


def test_endpoint_token_is_redacted_and_deterministic():
    tok = endpoint_token("72.56.10.20", "443")
    assert tok == endpoint_token("72.56.10.20", "443")  # deterministic
    assert "72.56" not in tok  # no octets leaked
    assert "10.20" not in tok
    assert tok.startswith("ep_") and tok.endswith(":443")


def test_categorize_endpoint():
    assert categorize_endpoint("127.0.0.1", "10808") == "local_socks"
    assert categorize_endpoint("172.16.0.2", "26531") == "tun_gateway_or_private"
    assert categorize_endpoint("149.154.167.91", "443") == "telegram"
    assert categorize_endpoint("1.1.1.1", "53") == "dns"
    assert categorize_endpoint("203.0.113.10", "443") == "relay_or_web_tls"


def test_single_relay_endpoint_dominance_detected():
    bad_relay = "203.0.113.10"
    good_relay = "198.51.100.20"
    lines = []
    for i in range(300):
        lines.append(
            f"2026-06-17 14:35:{i % 60:02d} ERROR connection download closed: "
            f"raw-read tcp 172.16.0.2:2{i:04d}->{bad_relay}:443: forcibly closed by the remote host"
        )
    for i in range(5):
        lines.append(
            f"2026-06-17 14:36:{i:02d} ERROR connection download closed: "
            f"raw-read tcp 172.16.0.2:3{i:04d}->{good_relay}:443: forcibly closed by the remote host"
        )
    result = analyze_error_endpoints("\n".join(lines))
    assert result["single_endpoint_dominates"] is True
    assert result["top_error_endpoint_share"] >= 0.9
    assert result["top_error_endpoint_category"] == "relay_or_web_tls"
    assert result["top_error_endpoint"] == endpoint_token(bad_relay, "443")
    # no raw IP anywhere in serialized output
    blob = json.dumps(result)
    assert bad_relay not in blob
    assert good_relay not in blob


def test_no_single_dominance_when_spread():
    lines = []
    for octet in range(10, 30):
        for _ in range(3):
            lines.append(
                f"ERROR connection download closed: raw-read tcp 172.16.0.2:5000->"
                f"203.0.113.{octet}:443: forcibly closed by the remote host"
            )
    result = analyze_error_endpoints("\n".join(lines))
    assert result["single_endpoint_dominates"] is False
    assert result["top_error_endpoint_share"] < 0.5


def test_sessions_separate_fast_startup_from_historical_crash():
    app_log = (
        "[17.06 12:59:16] [TUN]: Tun started up in 996ms\n"
        "[17.06 22:32:42] [TUN]: Tun started up in 1371ms\n"
    )
    happd = (
        "old: [DaemonManager] Process 'sing-box-tun' finished with exit code 1\n"
        "old: sing-box-tun exit code 2\n"
        "later: [DaemonManager] Process 'sing-box-tun' finished with exit code 0\n"
    )
    sessions = analyze_tun_sessions(app_log, happd)
    assert sessions["fast_startup_count"] == 2
    assert sessions["current_session_fast"] is True
    assert sessions["historical_crash_count"] >= 2
    assert sessions["clean_stop_count"] == 1
    assert sessions["crashes_are_historical_only"] is True


def test_error_endpoints_empty_log():
    result = analyze_error_endpoints("")
    assert result["endpoint_error_total"] == 0
    assert result["single_endpoint_dominates"] is False
    assert result["top_error_endpoint"] is None


def test_sleep_wake_signals_detected():
    from analyze_happ_report_tun import scan_sleep_wake_signals

    app_log = (
        "[14.06 23:51:38] [CORE]: Sleep/wake detected via timer gap (1180815ms)\n"
        "[14.06 23:51:38] [TUN]: [CommunicationClient] Disconnected from happd daemon\n"
        "[14.06 23:57:57] [CORE]: Wake recovery: forcing subscription update\n"
    )
    sig = scan_sleep_wake_signals(app_log)
    assert sig["sleep_wake_detected"] is True
    assert sig["daemon_ipc_disconnect"] is True
    assert sig["wake_subscription_refresh"] is True
