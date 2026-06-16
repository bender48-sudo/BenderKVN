"""Tests for shared legacy apply guard — VPN-AUTO-CUTTING-GUARD-001."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import vpn_apply_guard as g  # noqa: E402


def test_banner_does_not_raise_or_exit():
    buf = io.StringIO()
    g.print_guardrail_banner("scriptX", capacity_reducing=True, cron_managed=True, stream=buf)
    text = buf.getvalue()
    assert "GUARDRAIL" in text
    assert "scriptX" in text
    assert "must NOT silently reduce capacity" in text


def test_owner_approval_present_via_flag():
    assert g.owner_approval_present(True) is True


def test_owner_approval_present_via_env(monkeypatch):
    monkeypatch.setenv(g.APPROVAL_ENV, "1")
    assert g.owner_approval_present(False) is True


def test_owner_approval_absent(monkeypatch):
    monkeypatch.delenv(g.APPROVAL_ENV, raising=False)
    assert g.owner_approval_present(False) is False


def test_require_owner_approval_blocks_without_approval(monkeypatch):
    monkeypatch.delenv(g.APPROVAL_ENV, raising=False)
    buf = io.StringIO()
    with pytest.raises(SystemExit) as exc:
        g.require_owner_approval("scriptX", owner_approved=False, stream=buf)
    assert exc.value.code == 2
    assert "BLOCKED" in buf.getvalue()


def test_require_owner_approval_passes_with_flag():
    # should not raise
    g.require_owner_approval("scriptX", owner_approved=True)


def test_require_owner_approval_passes_with_env(monkeypatch):
    monkeypatch.setenv(g.APPROVAL_ENV, "1")
    g.require_owner_approval("scriptX", owner_approved=False)


def test_no_secrets_in_messages():
    note = g.guardrail_notice("scriptX", capacity_reducing=True, cron_managed=True)
    for bad in ("vless://", "vmess://", "token=", "/sub/", "publicKey", "privateKey"):
        assert bad not in note
