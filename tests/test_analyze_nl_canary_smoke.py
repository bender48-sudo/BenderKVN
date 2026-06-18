"""Tests for NL canary smoke guard — NL-DIRECT-BASIC-SMOKE-GUARD-001."""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
_FIX = Path(__file__).resolve().parent / "fixtures"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))
if str(_FIX.parent) not in sys.path:
    sys.path.insert(0, str(_FIX.parent))

from analyze_nl_canary_smoke import analyze_nl_canary_smoke_report  # noqa: E402
from nl_canary_profile_builder import PROFILE_LABEL_DIRECT_BASIC  # noqa: E402
from nl_canary_smoke_guard import (  # noqa: E402
    CLASS_NL_DIRECT_ROUTE_FAIL,
    CLASS_SPLIT_STEALTH_PARTIAL,
    INVALID_FORBIDDEN_APP,
    INVALID_ROUTING_OVERLAY,
    INVALID_WRONG_PROFILE,
    VERDICT_NOT_TESTED,
    VERDICT_PARTIAL,
    evaluate_nl_canary_smoke,
    external_routing_overlay_active,
    generator_smoke_metadata,
    profile_name_matches_variant,
)
from fixtures.nl_smoke_report12_fixture import (  # noqa: E402
    PROFILE_LABEL_LEGACY,
    build_report12_invalid_zip,
    write_report12_fixture,
)


@pytest.fixture
def report12_zip(tmp_path: Path) -> Path:
    p = tmp_path / "report12-invalid.zip"
    write_report12_fixture(p)
    return p


def test_generator_metadata_direct_basic():
    meta = generator_smoke_metadata("direct_basic")
    assert meta["expected_variant"] == "direct_basic"
    assert meta["requires_external_routing_overlay_off"] is True
    assert "Telegram" in meta["forbidden_apps_for_variant"]
    assert "smoke_targets" in meta
    assert "google.com" in str(meta["smoke_targets"]["nl_direct_proof"])


def test_external_routing_overlay_detected():
    assert external_routing_overlay_active(
        {"use_routing": True, "routing_profile": "BenderVPN RU"}
    )


def test_profile_name_matches_direct_basic():
    assert profile_name_matches_variant(PROFILE_LABEL_DIRECT_BASIC, "direct_basic")
    assert not profile_name_matches_variant(PROFILE_LABEL_LEGACY, "direct_basic")


def test_report12_classified_not_tested_invalid_smoke(report12_zip: Path):
    result = analyze_nl_canary_smoke_report(report12_zip, variant="direct_basic")
    guard = result["guard"]
    assert guard["ACCEPTABLE_SMOKE_INPUT"] is False
    assert guard["verdict"] == VERDICT_NOT_TESTED
    reasons = guard["invalid_reasons"]
    assert INVALID_WRONG_PROFILE in reasons
    assert INVALID_ROUTING_OVERLAY in reasons
    assert any(INVALID_FORBIDDEN_APP in r for r in reasons)


def test_wrong_profile_invalid():
    guard = evaluate_nl_canary_smoke(
        variant="direct_basic",
        profile_name=PROFILE_LABEL_LEGACY,
        profile={"relay2_proxy_count": 3, "balancer_names": ["Intl_Stealth"]},
        mode={"use_routing": False},
    )
    assert guard.acceptable_smoke_input is False
    assert INVALID_WRONG_PROFILE in guard.invalid_reasons


def test_overlay_enabled_invalid():
    guard = evaluate_nl_canary_smoke(
        variant="direct_basic",
        profile_name=PROFILE_LABEL_DIRECT_BASIC,
        profile={"relay2_proxy_count": 0, "balancer_names": ["Intl_Direct"]},
        mode={"use_routing": True, "routing_profile": "BenderVPN RU"},
    )
    assert guard.acceptable_smoke_input is False
    assert INVALID_ROUTING_OVERLAY in guard.invalid_reasons


def test_telegram_active_invalid_for_direct_basic():
    guard = evaluate_nl_canary_smoke(
        variant="direct_basic",
        profile_name=PROFILE_LABEL_DIRECT_BASIC,
        profile={"relay2_proxy_count": 0, "balancer_names": ["Intl_Direct"]},
        mode={"use_routing": False},
        app_log="User opened Telegram loading chats",
        tun_log="connection to telegram.org",
    )
    assert guard.acceptable_smoke_input is False
    assert any(INVALID_FORBIDDEN_APP in r for r in guard.invalid_reasons)


def test_correct_profile_overlay_off_no_telegram_acceptable():
    guard = evaluate_nl_canary_smoke(
        variant="direct_basic",
        profile_name=PROFILE_LABEL_DIRECT_BASIC,
        profile={"relay2_proxy_count": 0, "balancer_names": ["Intl_Direct"]},
        mode={"use_routing": False},
        tun_lifecycle={"interface_up_ok": True, "dns_set_ok": True},
        tun_log_stats={"error_like_lines": 12, "success_hint_lines": 5},
        app_log="Google search opened Gmail ok",
        tun_log="connection to google.com established",
        allow_evaluation=True,
    )
    assert guard.acceptable_smoke_input is True
    assert guard.verdict in {"PASS", "PARTIAL", "FAIL"}


def test_validate_legacy_label_fails_direct_basic():
    from validate_happ_importable_profile import validate_nl_canary_variant  # noqa: E402

    doc = {
        "remarks": PROFILE_LABEL_LEGACY,
        "outbounds": [{"tag": "proxy", "protocol": "vless", "settings": {"vnext": [{"address": "203.0.113.1", "port": 443}]}}],
        "routing": {"balancers": [{"tag": "Intl_Stealth", "selector": ["proxy"]}], "rules": []},
    }
    val = validate_nl_canary_variant(doc, "direct_basic")
    assert not val.ok
    assert any("legacy" in e.lower() or "DIRECT_BASIC" in e for e in val.errors)


def test_fixture_zip_structure():
    data = build_report12_invalid_zip()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        assert any(n.endswith("selected_server.json") for n in names)
        sel = json.loads(zf.read([n for n in names if n.endswith("selected_server.json")][0]))
        assert "Independent Exit Canary" in sel["selected"]["name"]


def test_report13_split_stealth_overlay_not_tested(tmp_path: Path):
    """report(13): Split Stealth active + BenderVPN RU overlay still enabled +
    NL direct reset storm ⇒ NOT a clean NL acceptance smoke (overlay invalid)."""
    from fixtures.nl_smoke_report13_fixture import write_report13_fixture  # noqa: E402

    p = write_report13_fixture(tmp_path / "report13.zip")
    result = analyze_nl_canary_smoke_report(p, variant="split_stealth")
    guard = result["guard"]
    assert guard["ACCEPTABLE_SMOKE_INPUT"] is False
    assert guard["verdict"] == VERDICT_NOT_TESTED
    assert INVALID_ROUTING_OVERLAY in guard["invalid_reasons"]


def test_report14_split_stealth_partial_not_pass(tmp_path: Path):
    """report(14): clean profile input but NL direct/blocked path failed — PARTIAL not PASS."""
    from fixtures.nl_smoke_report14_fixture import write_report14_fixture  # noqa: E402
    from nl_canary_profile_builder import PROFILE_LABEL_SPLIT_STEALTH  # noqa: E402

    p = write_report14_fixture(tmp_path / "report14.zip")
    result = analyze_nl_canary_smoke_report(p, variant="split_stealth", evaluate=True)
    guard = result["guard"]
    assert guard["ACCEPTABLE_SMOKE_INPUT"] is True
    assert guard["verdict"] == VERDICT_PARTIAL
    assert guard["checks"]["session_classification"] == CLASS_SPLIT_STEALTH_PARTIAL
    assert guard["verdict"] != "PASS"
    notes = " ".join(guard.get("notes") or [])
    assert CLASS_NL_DIRECT_ROUTE_FAIL in notes or CLASS_SPLIT_STEALTH_PARTIAL in notes


def test_telegram_alive_alone_not_pass_split_stealth():
    guard = evaluate_nl_canary_smoke(
        variant="split_stealth",
        profile_name="BenderVPN NL Split Stealth Canary — owner only",
        profile={"relay2_proxy_count": 3, "balancer_names": ["Intl_Direct", "Intl_Stealth"]},
        mode={"use_routing": False},
        tun_lifecycle={"interface_up_ok": True, "dns_set_ok": True},
        tun_log_stats={"error_like_lines": 611},
        app_log="Telegram loading chats yandex.ru ok google.com did not load",
        tun_log="connection reset by peer",
        allow_evaluation=True,
    )
    assert guard.acceptable_smoke_input is True
    assert guard.verdict in {VERDICT_PARTIAL, "FAIL"}
    assert guard.verdict != "PASS"
