"""Tests for ops/mobile_log_fullday.py (CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-001)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from mobile_log_fullday import (  # noqa: E402
    analyze_fullday,
    assess_coverage,
    bucket_access_events,
    correlate_gaps_subscriptions,
    find_top_gaps,
    parse_access_events,
    parse_subscription_events,
    subscription_failure_bursts,
)

ACCESS_DAY = """\
2026/06/16 19:00:00.000000 from tcp:127.0.0.1:1000 accepted tcp:8.8.8.8:443 [socks >> proxy]
2026/06/16 19:00:06.000000 from tcp:127.0.0.1:1001 accepted tcp:8.8.8.8:443 [socks >> proxy-2]
2026/06/16 19:00:25.000000 from tcp:127.0.0.1:1002 accepted tcp:1.1.1.1:53 [socks >> proxy-3]
2026/06/16 19:01:30.000000 from tcp:127.0.0.1:1003 accepted tcp:149.154.1.1:5222 [socks >> proxy-4]
"""

SUB_DAY = """\
Tue Jun 16 19:00:10 GMT+03:00 2026 Sub BenderVPN automatic update started
Tue Jun 16 19:00:11 GMT+03:00 2026 Server response: 200 7351 symbols
Tue Jun 16 19:00:11 GMT+03:00 2026 Batch config result 1: ImportResult(count=0, status=null, lastParseError=UnknownContentType)
Tue Jun 16 19:00:11 GMT+03:00 2026 Append custom result: ImportResult(count=1, status=null, lastParseError=null)
Tue Jun 16 19:00:12 GMT+03:00 2026 Google file failed
Tue Jun 16 19:00:12 GMT+03:00 2026 Happ file failed
Tue Jun 16 19:00:12 GMT+03:00 2026 Fetch provider file error: Required value was null.
"""


def test_timeline_bucketing():
    events = parse_access_events(ACCESS_DAY)
    buckets = bucket_access_events(events, 5)
    assert buckets
    assert sum(b["flows"] for b in buckets.values()) == 4


def test_longest_gap_and_post_gap():
    events = parse_access_events(ACCESS_DAY)
    gaps = find_top_gaps(events, top_n=3)
    assert gaps
    assert gaps[0].seconds >= 19
    assert gaps[0].flows_10s >= 1


def test_subscription_sequence_detection():
    events = parse_subscription_events(SUB_DAY)
    kinds = [e.kind for e in events]
    assert "http_200" in kinds
    assert "unknown_content_type" in kinds
    assert "append_custom_bender" in kinds
    assert "google_file_failed" in kinds


def test_failure_burst_detection():
    events = parse_subscription_events(SUB_DAY)
    bursts = subscription_failure_bursts(events, window_min=5)
    assert bursts
    assert bursts[0]["count"] >= 2


def test_gap_subscription_correlation():
    access = parse_access_events(ACCESS_DAY)
    sub = parse_subscription_events(SUB_DAY)
    gaps = find_top_gaps(access)
    rows = correlate_gaps_subscriptions(gaps, sub, windows_min=(2, 5))
    assert any(r["sub_events"] > 0 for r in rows)


def test_partial_coverage_warning():
    events = parse_access_events(ACCESS_DAY)
    sub = parse_subscription_events(SUB_DAY)
    cov = assess_coverage(events, sub, "2026-06-16")
    assert any("partial" in w.lower() or "Partial" in w for w in cov.warnings)


def test_fullday_markdown_no_secrets():
    md, summary = analyze_fullday(
        day="2026-06-16",
        access_text=ACCESS_DAY,
        subscription_text=SUB_DAY,
        sources={"access": "/tmp/a.txt"},
    )
    assert "vless://" not in md
    assert summary["access_flows"] == 4
    assert summary["primary_next_surface"] == "CLIENT-MOBILE-OBSERVABILITY-001"
    assert "PENDING" in summary["mobile_smoke_pass"]
    assert re.search(r"[0-9a-f]{32}", md) is None


def test_fullday_json_serializable():
    _, summary = analyze_fullday(day="2026-06-16", access_text=ACCESS_DAY, subscription_text=SUB_DAY)
    json.dumps(summary)


def test_partial_coverage_warning_validate():
    from mobile_log_fullday import validate_export_files

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        acc = root / "access.txt"
        sub = root / "sub.txt"
        acc.write_text(ACCESS_DAY, encoding="utf-8")
        sub.write_text(SUB_DAY, encoding="utf-8")
        v = validate_export_files(day="2026-06-16", access_path=acc, subscription_path=sub)
        assert v["access"]["present"]
        assert v["coverage"]["access_percent_day"] < 5
        assert v["coverage"]["can_conclude_full_day_health"] is False
        assert any("partial" in w.lower() or "CANNOT" in w for w in v["coverage"]["warnings"])


def test_missing_access_warning():
    from mobile_log_fullday import validate_export_files

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        sub = Path(td) / "sub.txt"
        sub.write_text(SUB_DAY, encoding="utf-8")
        v = validate_export_files(day="2026-06-16", subscription_path=sub)
        assert "Missing access log" in " ".join(v["issues"])


def test_owner_note_parsing():
    from mobile_log_fullday import parse_owner_notes

    notes = parse_owner_notes(["2026-06-16 14:05 unstable"])
    assert notes[0]["raw"]
    assert "vless://" not in notes[0]["raw"]


def test_secret_scan_no_values_printed():
    from mobile_log_fullday import scan_text_for_secrets

    dirty = "see vless://secret@1.2.3.4:443 and done"
    found = scan_text_for_secrets(dirty)
    assert "vless_uri" in found
    assert "secret" not in str(found)


def test_observability_report_no_secrets():
    from mobile_log_fullday import build_observability_report, validate_export_files

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        acc = Path(td) / "a.txt"
        acc.write_text(ACCESS_DAY, encoding="utf-8")
        v = validate_export_files(day="2026-06-16", access_path=acc)
        md = build_observability_report(day="2026-06-16", validation=v)
        assert "vless://" not in md
        assert "OBSERVABILITY" in md or "observability" in md.lower()
