"""Tests for ops/validate_happ_importable_profile.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"
if str(OPS) not in sys.path:
    sys.path.insert(0, str(OPS))

from validate_happ_importable_profile import (  # noqa: E402
    is_metadata_runbook,
    validate_importable_profile,
    validate_nl_canary_variant,
)
from nl_canary_profile_builder import (  # noqa: E402
    PROFILE_LABEL_DIRECT_BASIC,
    build_nl_direct_basic_profile,
    build_nl_split_stealth_profile,
)
from subscription_fetch import NL_IP  # noqa: E402
from relay_latency_probe import RELAY2_IP  # noqa: E402


def _vless(tag: str, addr: str, port: int = 443) -> dict:
    return {
        "protocol": "vless",
        "tag": tag,
        "settings": {
            "vnext": [
                {
                    "address": addr,
                    "port": port,
                    "users": [{"id": "00000000-0000-0000-0000-000000000099"}],
                }
            ]
        },
        "streamSettings": {"network": "tcp"},
    }


def _minimal_importable_profile() -> dict:
    return {
        "remarks": "BenderVPN Independent Exit Canary — owner/staging only — do NOT refresh subscription",
        "outbounds": [
            _vless("proxy-7", NL_IP),
            _vless("proxy-8", NL_IP),
            _vless("proxy-4", RELAY2_IP),
            _vless("proxy-5", RELAY2_IP),
            {"protocol": "freedom", "tag": "direct"},
        ],
        "routing": {
            "balancers": [
                {"tag": "Intl_Direct", "selector": ["proxy-7", "proxy-8"]},
                {"tag": "Intl_Stealth", "selector": ["proxy-4", "proxy-5"]},
            ],
            "rules": [],
        },
    }


def test_metadata_runbook_rejected():
    meta = {
        "artifact_type": "metadata_runbook_not_importable",
        "criteria_scorecard": [],
        "smoke_checklist": [],
    }
    assert is_metadata_runbook(meta) is True
    result = validate_importable_profile(meta)
    assert result.ok is False
    assert result.kind == "metadata_runbook"


def test_synthetic_preview_rejected():
    meta = {"synthetic_canary_preview": {"go": True}, "task": "x"}
    assert is_metadata_runbook(meta) is True


def test_minimal_valid_profile_accepted():
    profile = _minimal_importable_profile()
    result = validate_importable_profile(profile)
    assert result.ok is True
    assert result.kind == "importable_profile"
    assert result.summary["vless_proxy_count"] == 4


def test_no_secrets_in_validation_summary(capsys):
    profile = _minimal_importable_profile()
    validate_importable_profile(profile)
    # Ensure we never echo UUID from fixture in summary keys only
    dumped = json.dumps(validate_importable_profile(profile).summary)
    assert "00000000-0000-0000-0000-000000000099" not in dumped
    assert NL_IP not in dumped


def test_nl_direct_basic_variant_passes():
    src = _minimal_importable_profile()
    src["remarks"] = PROFILE_LABEL_DIRECT_BASIC
    profile = build_nl_direct_basic_profile(src)
    result = validate_nl_canary_variant(profile, "direct_basic")
    assert result.ok is True
    assert result.summary.get("google_on_stealth") is False


def test_nl_split_stealth_variant_passes():
    src = _minimal_importable_profile()
    profile = build_nl_split_stealth_profile(src)
    result = validate_nl_canary_variant(profile, "split_stealth")
    assert result.ok is True


def test_google_on_stealth_fails_direct_basic():
    profile = _minimal_importable_profile()
    profile["remarks"] = PROFILE_LABEL_DIRECT_BASIC
    profile["routing"]["rules"] = [
        {"type": "field", "domain": ["geosite:google"], "balancerTag": "Intl_Stealth"},
    ]
    result = validate_nl_canary_variant(profile, "direct_basic")
    assert result.ok is False
    assert any("google" in e.lower() for e in result.errors)
