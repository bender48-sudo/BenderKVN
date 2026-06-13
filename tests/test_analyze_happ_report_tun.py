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
    analyze_profile,
    analyze_report_zip,
    analyze_tun_log_stream,
    check_direct_ip_overlap,
    detect_final_state_overwrite,
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
