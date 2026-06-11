#!/usr/bin/env python3
"""MONITOR-FLAP-001 / OPS-ALERT-HYGIENE-001: ru-monitor cert digest tests."""
from __future__ import annotations

import importlib.util
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _stub_fcntl():
    if "fcntl" not in sys.modules:
        fcntl_stub = types.ModuleType("fcntl")
        fcntl_stub.LOCK_EX = 2
        fcntl_stub.LOCK_NB = 4
        fcntl_stub.LOCK_UN = 8
        fcntl_stub.flock = lambda *a, **k: None
        sys.modules["fcntl"] = fcntl_stub


def _load_ru_monitor():
    _stub_fcntl()
    path = ROOT / "ru-monitor.py"
    spec = importlib.util.spec_from_file_location("ru_monitor", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["ru_monitor"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_cdn_sni_classified():
    mod = _load_ru_monitor()
    assert mod.is_cdn_heavy_sni("www.microsoft.com")
    assert mod.is_cdn_heavy_sni("WWW.MICROSOFT.COM")
    assert not mod.is_cdn_heavy_sni("id.x5.ru")


def test_cert_digest_batched_message():
    mod = _load_ru_monitor()
    changes = [
        {
            "r": {"sni": "www.microsoft.com", "address": "1.2.3.4", "port": 443},
            "old_fp": "aaa111",
            "new_fp": "bbb222",
            "is_cdn": True,
        },
        {
            "r": {"sni": "id.x5.ru", "address": "5.6.7.8", "port": 443},
            "old_fp": "ccc333",
            "new_fp": "ddd444",
            "is_cdn": False,
        },
    ]
    msg = mod.format_cert_digest(changes)
    assert "certificate changes" in msg
    assert "Diagnostic" in msg or "informational" in msg
    assert "www.microsoft.com" in msg
    assert "id.x5.ru" in msg
    assert "[CDN]" in msg
    assert "[edge]" in msg
    assert "aaa111" in msg
    assert "ddd444" in msg


def test_cert_digest_cooldown():
    mod = _load_ru_monitor()
    now = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)
    recent = (now - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    old = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert not mod.cert_digest_allows(
        {"last_cert_digest": recent}, 3600, now=now
    )
    assert mod.cert_digest_allows({"last_cert_digest": old}, 3600, now=now)
    assert mod.cert_digest_allows({}, 3600, now=now)


def test_cert_digest_not_paging_style():
    mod = _load_ru_monitor()
    msg = mod.format_cert_digest([
        {
            "r": {"sni": "www.bing.com", "address": "9.9.9.9", "port": 443},
            "old_fp": "old",
            "new_fp": "new",
            "is_cdn": True,
        },
    ])
    assert "\U0001f6a8" not in msg  # no paging siren
    assert "\u2139" in msg or "certificate changes" in msg


def main() -> int:
    test_cdn_sni_classified()
    test_cert_digest_batched_message()
    test_cert_digest_cooldown()
    test_cert_digest_not_paging_style()
    print("RU_MONITOR_CERT_DIGEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
