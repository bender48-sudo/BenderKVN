"""Apply-order + already-applied integrity tests for patch_add_relay_nl_443_inject.

VPN-CONFIG-STABILITY-SCALABILITY-STEALTH-SPRINT-001 Phase 5:
  * hosts must NOT be enabled before snapshot + verified template patch;
  * patch failure must not leave hosts enabled;
  * already-applied with count/selector match but disabled host must NOT return OK.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import patch_add_relay_nl_443_inject as mod  # noqa: E402
from balancer_selectors import (  # noqa: E402
    INTL_BALANCER_TAG,
    INTL_RELAY_NL_443_SELECTOR,
    INTL_RELAY_NL_SELECTOR,
    INTL_STEALTH_BALANCER_TAG,
    RELAY6_SELECTOR,
)
from vpn_config_integrity import assert_already_applied  # noqa: E402


def _relay_nl_host(i: int) -> dict:
    return {
        "uuid": f"relaynl-{i:04d}",
        "remark": f"\U0001F1F3\U0001F1F1 Relay NL \u00b7 sni{i}",
        "port": 443,
        "address": "10.0.1.1",
        "isDisabled": True,
        "isHidden": True,
        "nodes": ["node-relay"],
    }


def _base_inject(n: int) -> list[str]:
    return [f"base-{i:04d}" for i in range(n)]


def _stealth_split_doc(inject_vals: list[str]) -> dict:
    return {
        "remnawave": {"injectHosts": [{"selector": {"values": list(inject_vals)}}]},
        "routing": {
            "balancers": [
                {"tag": INTL_STEALTH_BALANCER_TAG, "selector": list(RELAY6_SELECTOR)},
                {"tag": INTL_BALANCER_TAG, "selector": list(INTL_RELAY_NL_SELECTOR)},
            ],
            "rules": [
                {"network": "tcp,udp", "balancerTag": INTL_BALANCER_TAG},
                {"balancerTag": INTL_STEALTH_BALANCER_TAG, "ip": ["geoip:telegram"]},
                {"balancerTag": INTL_STEALTH_BALANCER_TAG, "domain": ["geosite:meta"]},
            ],
        },
    }


class FakePanel:
    def __init__(self, doc, hosts):
        self._doc = doc
        self._hosts = {h["uuid"]: h for h in hosts}
        self.events: list[str] = []

    def get_or_raise(self, path):
        if path == "/api/hosts":
            return {"response": list(self._hosts.values())}
        if path.startswith("/api/subscription-templates"):
            return {"response": {"uuid": "tpl", "templateJson": self._doc,
                                 "viewPosition": 0, "templateType": "xray"}}
        raise AssertionError(f"unexpected GET {path}")

    def patch(self, path, body=None):
        if path == "/api/subscription-templates":
            self.events.append("patch_template")
            self._doc = body["templateJson"]
            return 200, {"ok": True}
        if path == "/api/hosts":
            self.events.append(f"enable_host:{body.get('uuid')}")
            h = self._hosts.get(body["uuid"])
            if h:
                h["isDisabled"] = body.get("isDisabled", h["isDisabled"])
                h["isHidden"] = body.get("isHidden", h.get("isHidden"))
            return 200, {"ok": True}
        raise AssertionError(f"unexpected PATCH {path}")


@pytest.fixture
def patched_env(monkeypatch):
    hosts = [_relay_nl_host(i) for i in range(6)]
    doc = _stealth_split_doc(_base_inject(10))
    panel = FakePanel(doc, hosts)
    monkeypatch.setattr(mod, "PanelClient", lambda *a, **k: panel)
    monkeypatch.setattr(mod, "_verify_gate", lambda *a, **k: True)
    monkeypatch.setattr(mod, "after_template_patch", lambda *a, **k: None)
    monkeypatch.setattr(mod, "SNAPSHOT_DIR", Path(mod.ROOT) / ".secrets" / "snapshots")
    return panel


def _run_apply(monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "patch_add_relay_nl_443_inject.py", "--apply", "--owner-approved", "--skip-pre-verify",
    ])
    return mod.main()


def test_apply_order_via_main(patched_env, monkeypatch):
    panel = patched_env
    rc = _run_apply(monkeypatch)
    assert rc == 0
    assert "patch_template" in panel.events
    patch_idx = panel.events.index("patch_template")
    enable_events = [i for i, e in enumerate(panel.events) if e.startswith("enable_host")]
    assert enable_events
    assert min(enable_events) > patch_idx, panel.events


def test_apply_blocked_without_owner_approval(patched_env, monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "patch_add_relay_nl_443_inject.py", "--apply", "--skip-pre-verify",
    ])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2
    # no host should have been enabled
    assert not any(e.startswith("enable_host") for e in patched_env.events)


def test_patch_failure_does_not_enable_hosts(patched_env, monkeypatch):
    panel = patched_env

    def failing_patch(path, body=None):
        if path == "/api/subscription-templates":
            panel.events.append("patch_template_fail")
            return 500, {"error": "boom"}
        raise AssertionError("hosts should not be patched after template failure")

    monkeypatch.setattr(panel, "patch", failing_patch)
    monkeypatch.setattr(sys, "argv", [
        "patch_add_relay_nl_443_inject.py", "--apply", "--owner-approved", "--skip-pre-verify",
    ])
    rc = mod.main()
    assert rc == 1
    assert not any(e.startswith("enable_host") for e in panel.events)


def test_already_applied_count_match_but_disabled_host_not_ok():
    inject = _base_inject(10) + [f"relaynl-{i:04d}" for i in range(6)]
    doc = _stealth_split_doc(inject)
    doc["routing"]["balancers"][1]["selector"] = list(INTL_RELAY_NL_443_SELECTOR)
    # host disabled → not truly applied even though injected
    hosts = {f"relaynl-{i:04d}": {"uuid": f"relaynl-{i:04d}", "isDisabled": True} for i in range(6)}
    res = assert_already_applied(doc, [f"relaynl-{i:04d}" for i in range(6)], hosts)
    assert res.ok is False
    assert any("disabled" in e for e in res.errors)
