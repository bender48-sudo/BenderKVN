"""Tests for new-node registry entry preparer — NODE-ONBOARD-NEW-PROD-PATH-001."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from prepare_new_node_registry_entry import (  # noqa: E402
    PROD_REGISTRY,
    build_new_node_entry,
    main,
    validate_entry,
    write_entry,
)


def test_entry_is_staging_and_non_capacity():
    entry = build_new_node_entry(node_id="de-exit-1", country="DE")
    assert entry["status"] == "staging"
    assert entry["delivery_path_eligible"] is False
    assert entry["rollout"]["canary_percent"] == 0
    assert entry["rollout"]["allow_new_assignments"] is False


def test_entry_validates_clean():
    entry = build_new_node_entry(node_id="de-exit-1", country="DE")
    assert validate_entry(entry) == []


def test_rejects_lab_group():
    with pytest.raises(ValueError, match="not allowed"):
        build_new_node_entry(node_id="x", country="DE", groups=["LAB_OWNER"])


def test_rejects_fallback_group():
    with pytest.raises(ValueError, match="not allowed"):
        build_new_node_entry(node_id="x", country="DE", groups=["FALLBACK_MANUAL"])


def test_rejects_secret_looking_input():
    with pytest.raises(ValueError, match="secret"):
        build_new_node_entry(
            node_id="vless://abc", country="DE"
        )


def test_writes_only_to_given_dir(tmp_path):
    entry = build_new_node_entry(node_id="de-exit-1", country="DE")
    path = write_entry(entry, tmp_path)
    assert path.parent == tmp_path
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "status: staging" in text


def test_refuses_to_write_into_prod_registry_dir():
    entry = build_new_node_entry(node_id="de-exit-1", country="DE")
    with pytest.raises(ValueError, match="production registry"):
        write_entry(entry, PROD_REGISTRY.parent)


def test_no_secrets_in_output(tmp_path):
    entry = build_new_node_entry(node_id="de-exit-1", country="DE")
    path = write_entry(entry, tmp_path)
    text = path.read_text(encoding="utf-8")
    for bad in ("vless://", "vmess://", "token=", "/sub/", "publicKey", "privateKey"):
        assert bad not in text


def test_dry_run_writes_nothing(tmp_path, capsys):
    code = main(["--node-id", "de-exit-1", "--country", "DE", "--dry-run", "--out-dir", str(tmp_path)])
    assert code == 0
    assert not list(tmp_path.iterdir())
