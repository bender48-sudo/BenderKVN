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
    analyze_profile,
    analyze_report_zip,
    check_direct_ip_overlap,
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
