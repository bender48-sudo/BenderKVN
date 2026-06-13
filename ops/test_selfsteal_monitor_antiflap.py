#!/usr/bin/env python3
"""MONITOR-FLAP-001 / MONITOR-FLAP-TUNE-001: selfsteal-monitor anti-flap regression tests."""
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


def _load_selfsteal():
    _stub_fcntl()
    path = ROOT / "selfsteal-monitor.py"
    spec = importlib.util.spec_from_file_location("selfsteal_monitor", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["selfsteal_monitor"] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_cycle(mod, prev_state, results, *, is_first_run=False, **kwargs):
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    defaults = {
        "fail_streak_need": mod.DEFAULT_FAIL_STREAK,
        "ok_streak_need": mod.DEFAULT_OK_STREAK,
        "re_alert_cooldown_sec": mod.DEFAULT_RE_ALERT_COOLDOWN_SEC,
        "recover_notify_min_sec": mod.DEFAULT_RECOVER_NOTIFY_MIN_SEC,
        "retried_warn_log_sec": mod.DEFAULT_RETRIED_WARN_LOG_SEC,
    }
    defaults.update(kwargs)
    return mod.process_node_checks(
        "latvia",
        results,
        prev_state,
        now_ts,
        is_first_run,
        **defaults,
    )


def _critical_result(sni, code=0):
    return {
        "sni": sni,
        "code": code,
        "level": "critical",
        "reason": "no response (HTTP 000)",
        "retried": True,
    }


def _ok_result(sni, code=200):
    return {
        "sni": sni,
        "code": code,
        "level": "ok",
        "reason": None,
        "retried": False,
    }


def test_single_http_zero_does_not_page_immediately():
    mod = _load_selfsteal()
    results = [_critical_result("www.microsoft.com")]
    state, down, recovered, logs = _run_cycle(mod, {}, results)
    assert down == []
    assert recovered == []
    key = "latvia:www.microsoft.com"
    assert state[key]["fail_streak"] == 1
    assert state[key]["alerting"] is False
    assert any("suppressed" in ln or "warning" in ln for ln in logs)


def test_down_only_after_fail_streak_threshold():
    mod = _load_selfsteal()
    prev = {}
    down_all = []
    for _ in range(mod.DEFAULT_FAIL_STREAK):
        state, down, _, _ = _run_cycle(
            mod, prev, [_critical_result("id.x5.ru")], fail_streak_need=3
        )
        prev = state
        down_all.extend(down)
    assert len(down_all) == 1
    assert state["latvia:id.x5.ru"]["alerting"] is True


def test_recovered_only_after_ok_streak_threshold():
    mod = _load_selfsteal()
    prev = {
        "latvia:id.x5.ru": {
            "status": "critical",
            "alerting": True,
            "fail_streak": 3,
            "ok_streak": 0,
            "last_change": "2026-06-01T00:00:00Z",
        }
    }
    recovered_all = []
    for _ in range(mod.DEFAULT_OK_STREAK):
        state, down, recovered, _ = _run_cycle(
            mod, prev, [_ok_result("id.x5.ru")], ok_streak_need=2
        )
        prev = state
        recovered_all.extend(recovered)
    assert down == []
    assert len(recovered_all) == 1
    assert state["latvia:id.x5.ru"]["alerting"] is False


def test_flap_does_not_spam_every_cycle():
    mod = _load_selfsteal()
    prev = {}
    telegram_down = 0
    for i in range(6):
        bad = [_critical_result("www.microsoft.com")]
        good = [_ok_result("www.microsoft.com")]
        results = bad if i % 2 == 0 else good
        state, down, recovered, _ = _run_cycle(mod, prev, results)
        telegram_down += len(down) + len(recovered)
        prev = state
    assert telegram_down <= 2


def test_cdn_quorum_does_not_page_immediately():
    mod = _load_selfsteal()
    results = [
        _critical_result("www.microsoft.com"),
        _critical_result("www.apple.com"),
    ]
    state, down, recovered, logs = _run_cycle(mod, {}, results)
    assert down == []
    assert recovered == []
    assert any("quorum blip" in ln for ln in logs)
    assert state["latvia:www.microsoft.com"]["alerting"] is False


def test_non_cdn_quorum_still_pages():
    mod = _load_selfsteal()
    results = [
        _critical_result("id.x5.ru"),
        _critical_result("eh.vk.com"),
    ]
    state, down, recovered, logs = _run_cycle(mod, {}, results)
    assert len(down) == 2
    assert any("quorum" in item.get("page_reason", "") for item in down)
    assert recovered == []


def test_cdn_sustained_failure_still_pages():
    mod = _load_selfsteal()
    prev = {}
    down_all = []
    for _ in range(mod.DEFAULT_FAIL_STREAK):
        state, down, _, logs = _run_cycle(
            mod,
            prev,
            [_critical_result("www.microsoft.com"), _critical_result("www.apple.com")],
        )
        prev = state
        down_all.extend(down)
    assert len(down_all) >= 1
    assert any(
        "sustained fail (CDN)" in item.get("page_reason", "") for item in down_all
    )
    assert state["latvia:www.microsoft.com"]["alerting"] is True


def test_retried_warning_throttled_per_hour():
    mod = _load_selfsteal()
    recent = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prev = {
        "latvia:api.github.com": {
            "status": "ok",
            "alerting": False,
            "fail_streak": 0,
            "ok_streak": 1,
            "retry_count": 6,
            "last_retried_warn_log": recent,
            "last_change": "2026-06-01T00:00:00Z",
        }
    }
    result = {
        "sni": "api.github.com",
        "code": 200,
        "level": "ok",
        "reason": None,
        "retried": True,
    }
    _, _, _, logs = _run_cycle(mod, prev, [result], retried_warn_log_sec=3600)
    assert not any("retried" in ln for ln in logs)


def test_retried_warning_logs_after_cooldown():
    mod = _load_selfsteal()
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    prev = {
        "latvia:api.github.com": {
            "status": "ok",
            "alerting": False,
            "fail_streak": 0,
            "ok_streak": 1,
            "retry_count": 6,
            "last_retried_warn_log": old,
            "last_change": "2026-06-01T00:00:00Z",
        }
    }
    result = {
        "sni": "api.github.com",
        "code": 200,
        "level": "ok",
        "reason": None,
        "retried": True,
    }
    _, _, _, logs = _run_cycle(mod, prev, [result], retried_warn_log_sec=3600)
    assert any("retried" in ln for ln in logs)


def test_legacy_state_backward_compatible():
    mod = _load_selfsteal()
    legacy = {
        "latvia:www.microsoft.com": {
            "status": "critical",
            "last_check": "2026-06-01T00:00:00Z",
            "last_change": "2026-06-01T00:00:00Z",
            "code": 0,
            "reason": "no response (HTTP 000)",
            "retried": True,
            "retry_count": 1,
        }
    }
    norm = mod.normalize_prev_entry(legacy["latvia:www.microsoft.com"])
    assert norm["fail_streak"] == 1
    assert norm["alerting"] is True
    state, down, _, _ = _run_cycle(
        mod, legacy, [_ok_result("www.microsoft.com")], ok_streak_need=2
    )
    assert "latvia:www.microsoft.com" in state
    assert state["latvia:www.microsoft.com"]["ok_streak"] == 1


def test_cooldown_blocks_realert_after_recovery():
    mod = _load_selfsteal()
    cooldown_until = (
        datetime.now(timezone.utc) + timedelta(seconds=900)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    prev = {
        "latvia:id.x5.ru": {
            "status": "ok",
            "alerting": False,
            "fail_streak": 0,
            "ok_streak": 0,
            "cooldown_until": cooldown_until,
            "last_change": "2026-06-01T00:00:00Z",
        }
    }
    for _ in range(3):
        state, down, _, logs = _run_cycle(
            mod, prev, [_critical_result("id.x5.ru")]
        )
        prev = state
    assert down == []
    assert any("cooldown" in ln for ln in logs)


def main() -> int:
    test_single_http_zero_does_not_page_immediately()
    test_down_only_after_fail_streak_threshold()
    test_recovered_only_after_ok_streak_threshold()
    test_flap_does_not_spam_every_cycle()
    test_cdn_quorum_does_not_page_immediately()
    test_non_cdn_quorum_still_pages()
    test_cdn_sustained_failure_still_pages()
    test_retried_warning_throttled_per_hour()
    test_retried_warning_logs_after_cooldown()
    test_legacy_state_backward_compatible()
    test_cooldown_blocks_realert_after_recovery()
    print("SELFSTEAL_MONITOR_ANTIFLAP_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
