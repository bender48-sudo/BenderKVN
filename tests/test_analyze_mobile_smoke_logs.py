"""Tests for ops/analyze_mobile_smoke_logs.py."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from analyze_mobile_smoke_logs import (  # noqa: E402
    analyze,
    build_markdown,
    classify_root_cause_tracks,
    compute_gap_counts,
    parse_access_log,
    parse_adb_log,
    parse_subscription_log,
    redact,
    recommend_verdict_support,
)

ACCESS_SAMPLE = """\
2026/06/13 20:40:56.754199 from tcp:127.0.0.1:34284 accepted tcp:149.154.167.41:5222 [socks -> proxy]
2026/06/13 20:40:56.934712 from tcp:127.0.0.1:34296 accepted tcp:216.239.36.223:443 [socks -> proxy-5]
2026/06/13 20:40:57.355899 from tcp:127.0.0.1:34320 accepted tcp:31.13.72.53:443 [socks -> proxy-4]
2026/06/13 20:41:01.672935 from tcp:127.0.0.1:34490 accepted tcp:87.240.137.130:443 [socks -> direct]
2026/06/13 20:41:05.061558 from tcp:127.0.0.1:47936 accepted tcp:213.180.193.115:443 [socks -> direct]
"""

SUB_SAMPLE = """\
Sat Jun 13 19:35:55 GMT+03:00 2026 Server response: 200 7351 symbols
Sat Jun 13 19:35:55 GMT+03:00 2026 Batch config result 1: ImportResult(count=0, status=null, lastParseError=UnknownContentType)
Sat Jun 13 19:35:55 GMT+03:00 2026 Fetch provider file error: Required value was null
Sat Jun 13 19:35:55 GMT+03:00 2026 Google file failed
Sat Jun 13 19:35:55 GMT+03:00 2026 Happ file failed
Sat Jun 13 19:35:55 GMT+03:00 2026 Sub BenderVPN update started
Sat Jun 13 19:35:55 GMT+03:00 2026 Append custom result (use case): ImportResult(count=1, status=null, lastParseError=null)
Sat Jun 13 19:35:55 GMT+03:00 2026 Sub BenderVPN successfully updated (1)
Sat Jun 13 19:35:55 GMT+03:00 2026 Sub BenderVPN servers: 1 servers
"""

SUB_SAFE_SAMPLE = """\
Sat Jun 16 10:00:00 GMT+03:00 2026 Sub SafeVPN update started
Sat Jun 16 10:00:01 GMT+03:00 2026 Append custom result: ImportResult(count=5, status=null, lastParseError=null)
"""

GAP_SAMPLE = """\
2026/06/16 19:00:00.000000 from tcp:127.0.0.1:1000 accepted tcp:8.8.8.8:443 [socks >> proxy]
2026/06/16 19:00:06.000000 from tcp:127.0.0.1:1001 accepted tcp:8.8.8.8:443 [socks >> proxy-2]
2026/06/16 19:00:25.000000 from tcp:127.0.0.1:1002 accepted tcp:8.8.8.8:443 [socks >> proxy-3]
"""

ADB_SAMPLE = """\
06-13 23:44:11.996 W/tun2socks(12421): WARNING(tun2socks): BProcessInfo_QueryByBAddr: findConnectionOwner returned NULL
06-13 23:44:11.996 E/tun2socks(12421): ERROR(tun2socks): APPDETECT UDP: IP: 87.245.220.78:443 Failed to find conection
06-13 23:44:13.478 E/tun2socks(12421): ERROR(tun2socks): APPDETECT UDP: IP: 216.239.34.223:443 Failed to find conection
"""


def test_access_log_proxy_direct_split():
    stats = parse_access_log(ACCESS_SAMPLE)
    assert stats.total_accepted == 5
    assert stats.direct == 2
    assert sum(stats.proxy_routes.values()) == 3
    assert stats.class_proxy.get("telegram_hint") == 1
    assert stats.class_proxy.get("google_hint") == 1
    assert stats.class_direct.get("ru_hint") == 2


def test_subscription_unknown_content_type_with_append_ok():
    stats = parse_subscription_log(SUB_SAMPLE)
    assert stats.server_response_200 == 1
    assert stats.unknown_content_type == 1
    assert stats.append_custom_ok == 1
    assert stats.append_custom_bender == 1
    assert stats.required_value_null == 1
    assert stats.google_file_failed == 1
    assert stats.happ_file_failed == 1
    assert stats.import_verdict == "parse_noise_but_custom_import_ok"


def test_subscription_safevpn_append_count5():
    stats = parse_subscription_log(SUB_SAFE_SAMPLE)
    assert stats.append_custom_count5 == 1
    assert stats.append_custom_safe == 1


def test_access_log_double_arrow_route():
    line = "2026/06/16 19:00:00.000000 from tcp:127.0.0.1:1000 accepted tcp:8.8.8.8:443 [socks >> proxy-4]"
    stats = parse_access_log(line)
    assert stats.total_accepted == 1
    assert stats.proxy_routes["proxy-4"] == 1


def test_gap_detection():
    stats = parse_access_log(GAP_SAMPLE)
    assert stats.gap_counts[5] == 2
    assert stats.gap_counts[15] == 1
    assert stats.gap_counts[30] == 0


def test_classification_tracks_present():
    access = parse_access_log(ACCESS_SAMPLE)
    sub = parse_subscription_log(SUB_SAMPLE)
    tracks = classify_root_cause_tracks(access, sub)
    assert any("sleep/wake" in t["track"].lower() for t in tracks)
    assert any(t["verdict"] == "CONFIRMED" for t in tracks)


def test_adb_appdetect_warnings():
    stats = parse_adb_log(ADB_SAMPLE)
    assert stats.appdetect_udp_failed == 2
    assert stats.appdetect_null_owner == 1
    assert stats.classification == "low_frequency_likely_non_blocking"


def test_redaction_no_secrets_in_output():
    dirty = (
        "vless://uuid@1.2.3.4:443?security=reality "
        "https://example.com/api/sub/short123 "
        "f7b4bd49f8f84dff81dd152306dbc2aa"
    )
    clean = redact(dirty)
    assert "vless://uuid" not in clean
    assert "short123" not in clean
    assert "f7b4bd49f8f84dff81dd152306dbc2aa" not in clean


def test_markdown_output_has_no_forbidden_patterns():
    access = parse_access_log(ACCESS_SAMPLE)
    sub = parse_subscription_log(SUB_SAMPLE)
    adb = parse_adb_log(ADB_SAMPLE)
    md = build_markdown(access, sub, adb, {"access_log": "/tmp/access.txt"})
    assert "vless://" not in md
    assert "/api/sub/" not in md
    assert "PENDING" in md
    assert re.search(r"[0-9a-f]{32}", md) is None


def test_analyze_integration(tmp_path: Path):
    acc = tmp_path / "access.txt"
    acc.write_text(ACCESS_SAMPLE, encoding="utf-8")
    md, summary = analyze(access_path=acc)
    assert summary["connectivity"] == "limited_traffic_observed"
    assert summary["mobile_smoke_pass"].startswith("PENDING")
    assert "Routing evidence" in md
