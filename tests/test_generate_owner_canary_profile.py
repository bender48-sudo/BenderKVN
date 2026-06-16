"""Tests for owner canary profile generator — CLIENT-STABILITY-OWNER-CANARY-PROFILE-001."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from validate_vpn_node_registry import DEFAULT_REGISTRY  # noqa: E402
from vpn_node_selector import load_validated_registry  # noqa: E402
from generate_owner_canary_profile import (  # noqa: E402
    PROFILE_LABEL,
    build_owner_canary_profile,
    main,
    select_owner_canary_candidates,
    write_profile,
)


@pytest.fixture
def registry_doc():
    return load_validated_registry(DEFAULT_REGISTRY)


def test_excludes_suspect_relay1(registry_doc):
    candidates, excluded = select_owner_canary_candidates(registry_doc)
    cand_ids = {c.node_id for c in candidates}
    assert "ru-relay-1" not in cand_ids
    relay1_excl = [e for e in excluded if e["node_id"] == "ru-relay-1"]
    assert relay1_excl
    assert "suspect" in relay1_excl[0]["reason"].lower()


def test_lab_profile_is_candidate_not_production(registry_doc):
    profile = build_owner_canary_profile(registry_doc)
    cand_ids = {c.node_id for c in profile.candidates}
    assert "ru-relay-2-lab" in cand_ids
    # active production exits must NOT be isolation candidates
    assert "lv-exit-1" not in cand_ids
    assert profile.production_default_changed is False


def test_nl_excluded_without_approval(registry_doc):
    profile = build_owner_canary_profile(registry_doc, include_nl=True, owner_approval=False)
    cand_ids = {c.node_id for c in profile.candidates}
    assert "nl-node-1" not in cand_ids


def test_nl_excluded_even_with_flags_when_disabled(registry_doc):
    # NL is disabled in registry → not canary-ready → still excluded even with flags
    profile = build_owner_canary_profile(registry_doc, include_nl=True, owner_approval=True)
    cand_ids = {c.node_id for c in profile.candidates}
    assert "nl-node-1" not in cand_ids


def test_label_contains_do_not_refresh(registry_doc):
    profile = build_owner_canary_profile(registry_doc)
    assert "do NOT refresh" in profile.label
    assert profile.do_not_refresh is True
    assert profile.owner_only is True
    assert "OWNER-ONLY" in profile.warning


def test_writes_only_to_given_dir(tmp_path, registry_doc):
    profile = build_owner_canary_profile(registry_doc)
    paths = write_profile(profile, tmp_path)
    assert len(paths) == 2
    for p in paths:
        assert p.parent == tmp_path
        assert p.exists()
    data = json.loads((tmp_path / "owner_canary_profile.json").read_text(encoding="utf-8"))
    assert data["label"] == PROFILE_LABEL
    assert data["production_default_changed"] is False


def test_no_secrets_in_written_output(tmp_path, registry_doc):
    profile = build_owner_canary_profile(registry_doc)
    write_profile(profile, tmp_path)
    for name in ("owner_canary_profile.json", "owner_canary_profile.md"):
        text = (tmp_path / name).read_text(encoding="utf-8")
        for bad in ("vless://", "vmess://", "token=", "/sub/", "publicKey", "privateKey", "shortId"):
            assert bad not in text


def test_no_secrets_in_stdout(capsys):
    code = main(["--dry-run"])
    assert code == 0
    out = capsys.readouterr().out
    for bad in ("vless://", "vmess://", "token=", "/sub/", "publicKey", "privateKey"):
        assert bad not in out
    assert "do NOT refresh" in out


def test_dry_run_writes_nothing(tmp_path, capsys):
    code = main(["--dry-run", "--out-dir", str(tmp_path)])
    assert code == 0
    assert not list(tmp_path.iterdir())
