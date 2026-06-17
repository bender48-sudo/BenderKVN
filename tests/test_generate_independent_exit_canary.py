"""Tests for ops/generate_independent_exit_canary.py — artifact naming fix."""
from __future__ import annotations

import json
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
    RUNBOOK_FILENAME,
    build_artifact,
    build_metadata_document,
    build_nl_independent_exit_canary_profile,
    try_generate_importable_profile,
    validate_nl_canary_profile,
)
from validate_happ_importable_profile import is_metadata_runbook  # noqa: E402
from vpn_node_selector import load_validated_registry  # noqa: E402
from subscription_fetch import NL_IP  # noqa: E402
from relay_latency_probe import RELAY2_IP  # noqa: E402


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
    assert is_metadata_runbook(meta) is True


def test_build_nl_canary_profile_pins_selectors():
    src = _owner_source_with_nl()
    profile = build_nl_independent_exit_canary_profile(src)
    assert validate_nl_canary_profile(profile) == []
    bal = {b["tag"]: b for b in profile["routing"]["balancers"]}
    assert list(bal["Intl_Direct"]["selector"]) == ["proxy-7", "proxy-8"]
    assert list(bal["Intl_Stealth"]["selector"]) == ["proxy-4", "proxy-5"]


def test_try_generate_missing_owner_config(tmp_path, monkeypatch):
    for p in (
        ROOT / ".secrets" / "nl_owner_direct_config.json",
        ROOT / ".secrets" / "owner_sub.json",
    ):
        if p.exists():
            monkeypatch.setattr("generate_independent_exit_canary._load_owner_config", lambda: (None, None))
            break
    else:
        monkeypatch.setattr("generate_independent_exit_canary._load_owner_config", lambda: (None, None))
    status = try_generate_importable_profile(tmp_path)
    assert status["generated"] is False
    assert "MISSING_OWNER_CONFIG" in status["status"]


def test_artifact_filenames_constants():
    assert RUNBOOK_FILENAME.endswith("_RUNBOOK.md")
    assert METADATA_FILENAME.endswith("_METADATA.json")
    assert "IMPORTABLE" not in METADATA_FILENAME
