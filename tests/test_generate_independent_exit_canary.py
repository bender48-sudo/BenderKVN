"""Tests for ops/generate_independent_exit_canary.py — NL two-profile fix."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"
if str(OPS) not in sys.path:
    sys.path.insert(0, str(OPS))

from generate_independent_exit_canary import (  # noqa: E402
    ARTIFACT_FIX_TASK_ID,
    METADATA_FILENAME,
    METADATA_WARNING,
    NL_FIX_TASK_ID,
    RUNBOOK_FILENAME,
    build_artifact,
    build_metadata_document,
    try_generate_importable_profiles,
)
from nl_canary_profile_builder import (  # noqa: E402
    PROFILE_LABEL_DIRECT_BASIC,
    PROFILE_LABEL_SPLIT_STEALTH,
    build_nl_direct_basic_profile,
    build_nl_split_stealth_profile,
    google_routes_via_stealth,
)
from validate_happ_importable_profile import (  # noqa: E402
    is_metadata_runbook,
    validate_nl_canary_variant,
)
from vpn_node_selector import load_validated_registry  # noqa: E402
from subscription_fetch import NL_IP  # noqa: E402
from relay_latency_probe import RELAY1_IP, RELAY2_IP  # noqa: E402


def _owner_source_with_nl() -> dict:
    return {
        "remarks": "owner source",
        "outbounds": [
            {
                "protocol": "vless",
                "tag": "proxy-7",
                "settings": {
                    "vnext": [
                        {
                            "address": NL_IP,
                            "port": 443,
                            "users": [{"id": "00000000-0000-0000-0000-000000000001"}],
                        }
                    ]
                },
                "streamSettings": {"network": "tcp"},
            },
            {
                "protocol": "vless",
                "tag": "proxy-8",
                "settings": {
                    "vnext": [
                        {
                            "address": NL_IP,
                            "port": 443,
                            "users": [{"id": "00000000-0000-0000-0000-000000000002"}],
                        }
                    ]
                },
                "streamSettings": {"network": "tcp"},
            },
            {
                "protocol": "vless",
                "tag": "proxy-4",
                "settings": {
                    "vnext": [
                        {
                            "address": RELAY2_IP,
                            "port": 443,
                            "users": [{"id": "00000000-0000-0000-0000-000000000003"}],
                        }
                    ]
                },
                "streamSettings": {"network": "tcp"},
            },
            {
                "protocol": "vless",
                "tag": "proxy-5",
                "settings": {
                    "vnext": [
                        {
                            "address": RELAY2_IP,
                            "port": 443,
                            "users": [{"id": "00000000-0000-0000-0000-000000000004"}],
                        }
                    ]
                },
                "streamSettings": {"network": "tcp"},
            },
            {"protocol": "freedom", "tag": "direct"},
        ],
        "routing": {
            "balancers": [
                {"tag": "Intl_Direct", "selector": ["proxy-4", "proxy-5"]},
                {"tag": "Intl_Stealth", "selector": ["proxy-4", "proxy-5"]},
            ],
            "rules": [],
        },
    }


def test_metadata_envelope_not_importable():
    registry = load_validated_registry()
    artifact = build_artifact(registry, "nl-node-1")
    import_status = {"status": "IMPORTABLE_PROFILE_NOT_GENERATED_MISSING_OWNER_CONFIG", "generated": False}
    meta = build_metadata_document(artifact, import_status)
    assert meta["artifact_type"] == "metadata_runbook_not_importable"
    assert meta["importable_profile"] is False
    assert meta["do_not_import_this_file"] is True
    assert METADATA_WARNING in meta["warning"]
    assert meta["artifact_fix_task"] == ARTIFACT_FIX_TASK_ID
    assert meta["nl_fix_task"] == NL_FIX_TASK_ID
    assert meta["runbook_file"] == f".local/{RUNBOOK_FILENAME}"
    assert is_metadata_runbook(meta) is True


def test_direct_basic_profile_routes_google_via_nl():
    src = _owner_source_with_nl()
    profile = build_nl_direct_basic_profile(src)
    result = validate_nl_canary_variant(profile, "direct_basic")
    assert result.ok is True
    assert google_routes_via_stealth(profile) is False
    assert PROFILE_LABEL_DIRECT_BASIC in profile["remarks"]
    bal = {b["tag"]: b for b in profile["routing"]["balancers"]}
    assert list(bal["Intl_Direct"]["selector"]) == ["proxy-7", "proxy-8"]
    assert "Intl_Stealth" not in bal


def test_split_stealth_profile_excludes_google_from_stealth():
    src = _owner_source_with_nl()
    profile = build_nl_split_stealth_profile(src)
    result = validate_nl_canary_variant(profile, "split_stealth")
    assert result.ok is True
    assert google_routes_via_stealth(profile) is False
    assert PROFILE_LABEL_SPLIT_STEALTH in profile["remarks"]
    bal = {b["tag"]: b for b in profile["routing"]["balancers"]}
    assert list(bal["Intl_Direct"]["selector"]) == ["proxy-7", "proxy-8"]
    assert list(bal["Intl_Stealth"]["selector"]) == ["proxy-4", "proxy-5"]


def test_legacy_google_on_stealth_fails_validation():
    src = _owner_source_with_nl()
    bad = build_nl_split_stealth_profile(src)
    bad["routing"]["rules"].insert(
        0,
        {
            "type": "field",
            "domain": ["geosite:google"],
            "balancerTag": "Intl_Stealth",
        },
    )
    result = validate_nl_canary_variant(bad, "direct_basic")
    assert result.ok is False
    assert any("google" in e.lower() for e in result.errors)


def test_relay1_excluded_from_direct_basic_and_passes_validation():
    src = _owner_source_with_nl()
    src["outbounds"].append(
        {
            "protocol": "vless",
            "tag": "proxy-1",
            "settings": {
                "vnext": [
                    {
                        "address": RELAY1_IP,
                        "port": 443,
                        "users": [{"id": "00000000-0000-0000-0000-000000000099"}],
                    }
                ]
            },
            "streamSettings": {"network": "tcp"},
        }
    )
    profile = build_nl_direct_basic_profile(src)
    result = validate_nl_canary_variant(profile, "direct_basic")
    assert result.ok is True
    assert result.summary.get("relay1_tags") == []


def test_relay1_in_profile_fails_validation():
    src = _owner_source_with_nl()
    profile = build_nl_direct_basic_profile(src)
    profile["outbounds"].append(
        {
            "protocol": "vless",
            "tag": "proxy-bad",
            "settings": {
                "vnext": [
                    {
                        "address": RELAY1_IP,
                        "port": 443,
                        "users": [{"id": "00000000-0000-0000-0000-000000000099"}],
                    }
                ]
            },
            "streamSettings": {"network": "tcp"},
        }
    )
    result = validate_nl_canary_variant(profile, "direct_basic")
    assert result.ok is False
    assert any("relay-1" in e for e in result.errors)


def test_try_generate_missing_owner_config(tmp_path, monkeypatch):
    monkeypatch.setattr("generate_independent_exit_canary._load_owner_config", lambda: (None, None))
    status = try_generate_importable_profiles(tmp_path)
    assert status["generated"] is False
    assert "MISSING_OWNER_CONFIG" in status["status"]
    assert status["owner_smoke_status"] == "FAIL_PROFILE_ROUTING_PROTOCOL"


def test_artifact_traffic_smoke_fail_status():
    registry = load_validated_registry()
    artifact = build_artifact(registry, "nl-node-1")
    # After report(13) NL-direct fragment fix: client profile corrected, gate
    # waits for a fresh clean Direct Basic smoke (not a standing FAIL).
    assert artifact["traffic_smoke_status"] == "WAITING_CLEAN_DIRECT_BASIC_SMOKE"


def test_artifact_filenames_constants():
    assert RUNBOOK_FILENAME.endswith("_RUNBOOK.md")
    assert METADATA_FILENAME.endswith("_METADATA.json")
    assert "IMPORTABLE" not in METADATA_FILENAME
