"""Tests for shadow-mode subscription assignment diff.

SUB-GEN-SELECTOR-INTEGRATION-001 (shadow) + SUB-GEN-SHADOW-REPORT-001.
Asserts the shadow tool stays dry-run, never claims to apply, emits only redacted
node IDs (no secrets), and computes correct add/remove diffs.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from validate_vpn_node_registry import DEFAULT_REGISTRY  # noqa: E402
from vpn_node_selector import load_validated_registry  # noqa: E402
from vpn_sub_assignment_shadow import (  # noqa: E402
    SHADOW_BANNER,
    build_shadow_report,
    derive_current_pool,
    format_shadow_report,
    main,
)

_REGISTRY = load_validated_registry(DEFAULT_REGISTRY)

# Secret-like patterns that must never appear in shadow output.
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_FORBIDDEN = ("vless://", "token=", "publicKey", "/sub/", "http://", "https://")


def test_derive_current_pool_excludes_lab_disabled_fallback():
    pool = derive_current_pool(_REGISTRY)
    assert "lv-exit-1" in pool
    assert "ru-relay-1" in pool
    assert "ru-relay-2" in pool
    assert "ru-relay-2-lab" not in pool  # LAB_OWNER
    assert "nl-node-1" not in pool  # disabled
    assert "ams-backup-edge" not in pool  # FALLBACK_MANUAL


def test_reports_are_always_dry_run_and_not_applied():
    for cohort in ("LAB_OWNER", "PUBLIC_PROD", "CANARY", "OWNER_FF", "FALLBACK_MANUAL"):
        r = build_shadow_report(cohort, _REGISTRY)
        assert r.dry_run is True
        assert r.applied is False


def test_public_prod_nogo_removes_all_and_not_apply_safe():
    r = build_shadow_report("PUBLIC_PROD", _REGISTRY)
    assert r.verdict == "NO-GO"
    assert r.selector_node_ids == []
    assert r.apply_safe is False
    assert "ru-relay-1" in r.removed


def test_owner_ff_drops_suspect_relay1():
    r = build_shadow_report("OWNER_FF", _REGISTRY)
    assert "ru-relay-1" in r.removed  # suspect excluded
    assert "lv-exit-1" in r.unchanged
    assert "ru-relay-2" in r.unchanged


def test_lab_owner_adds_lab_node():
    r = build_shadow_report("LAB_OWNER", _REGISTRY)
    assert r.selector_node_ids == ["ru-relay-2-lab"]
    assert "ru-relay-2-lab" in r.added


def test_owner_baseline_file_overrides_derived():
    r = build_shadow_report("OWNER_FF", _REGISTRY, baseline=["lv-exit-1"])
    assert r.baseline_source == "owner-provided baseline file"
    assert r.baseline_node_ids == ["lv-exit-1"]
    # ru-relay-2 is selected but not in baseline -> would_add
    assert "ru-relay-2" in r.added


def test_added_removed_are_disjoint():
    for cohort in ("LAB_OWNER", "PUBLIC_PROD", "CANARY", "OWNER_FF", "FALLBACK_MANUAL"):
        r = build_shadow_report(cohort, _REGISTRY)
        assert set(r.added).isdisjoint(set(r.removed))
        assert set(r.added).isdisjoint(set(r.unchanged))


def test_no_secrets_in_text_output():
    for cohort in ("LAB_OWNER", "PUBLIC_PROD", "OWNER_FF"):
        out = format_shadow_report(build_shadow_report(cohort, _REGISTRY))
        assert not _UUID_RE.search(out)
        for token in _FORBIDDEN:
            assert token not in out


def test_cli_json_is_redacted_and_dry_run(capsys):
    rc = main(["--cohort", "PUBLIC_PROD", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert data[0]["dry_run"] is True
    assert data[0]["applied"] is False
    assert not _UUID_RE.search(out)
    for token in _FORBIDDEN:
        assert token not in out


def test_cli_all_runs_every_cohort(capsys):
    rc = main(["--all"])
    assert rc == 0
    out = capsys.readouterr().out
    assert SHADOW_BANNER in out
    assert "cohort: PUBLIC_PROD" in out
    assert "cohort: LAB_OWNER" in out


def test_banner_is_ascii_only():
    # guard against mojibake in captured logs
    SHADOW_BANNER.encode("ascii")
