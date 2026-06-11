"""Synthetic tests for ops/analyze_happ_report_proxy.py — no real reports."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
import sys

if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from analyze_happ_report_proxy import analyze_report_zip, redact_text  # noqa: E402


def _make_zip(files: dict[str, str]) -> Path:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    tmp = Path(__file__).parent / "_tmp_proxy_report.zip"
    tmp.write_bytes(buf.getvalue())
    return tmp


def test_redact_subscription_url():
    raw = "GET https://example.com/api/sub/abc123def vless://uuid@host:443?x=1"
    out = redact_text(raw)
    assert "api/sub/abc123" not in out
    assert "vless://[REDACTED]" in out


def test_class_c_unknown_content_type():
    path = _make_zip(
        {
            "subscription_log.txt": (
                "ImportResult(count=0, lastParseError=UnknownContentType)\n"
                "*** Subscription BenderVPN with 0 servers: ***\n"
            ),
            "versions.txt": "Happ 2.16.2\nXray 26.3.27\n",
        }
    )
    try:
        result = analyze_report_zip(path)
        assert "C" in result.classifications
        ids = {s.signal_id for s in result.signals}
        assert "unknown_content_type" in ids
        assert "zero_servers" in ids
    finally:
        path.unlink(missing_ok=True)


def test_class_a_localhost_dns():
    path = _make_zip(
        {
            "error_log.txt": "failed to query DNS for localhost address\n",
            "happd.log": "Cannot set DNS on interface\n",
        }
    )
    try:
        result = analyze_report_zip(path)
        assert result.classifications[0] in ("A", "G") or "A" in result.classifications
        assert any(s.signal_id == "localhost_dns" or s.signal_id == "dns_failure" for s in result.signals)
    finally:
        path.unlink(missing_ok=True)


def test_redacted_json_output():
    path = _make_zip(
        {
            "subscription_log.txt": "fetch https://k9x2m1.example/api/sub/secret-token-xyz\n",
        }
    )
    try:
        result = analyze_report_zip(path)
        for s in result.signals:
            for line in s.sample_lines:
                assert "secret-token" not in line
                assert "api/sub/secret" not in line
    finally:
        path.unlink(missing_ok=True)


def test_empty_zip_class_g():
    path = _make_zip({"readme.txt": "empty report"})
    try:
        result = analyze_report_zip(path)
        assert result.classifications == ["G"]
        assert "No known log files" in result.notes[0]
    finally:
        path.unlink(missing_ok=True)
