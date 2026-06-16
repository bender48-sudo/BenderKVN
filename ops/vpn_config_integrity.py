#!/usr/bin/env python3
"""Central VPN config integrity verifier — VPN-CONFIG-INTEGRITY-VERIFIER-001.

Proves UUID <-> host <-> selector <-> node_id correspondence so that:
    * count-only parity (e.g. "16 injectHosts == 16 proxy outbounds") is NEVER
      treated as sufficient;
    * a selector tag cannot reference a slot/outbound that does not exist;
    * legacy positional proxy-N tags must not exceed the actual inject slot count;
    * an already-applied claim must prove enabled hosts + injectHosts + selectors
      all align, not just that counts match.

HARD SAFETY:
    * Pure validation. No network, no Remna/Caddy/template/subscription writes,
      no secrets. Operates on in-memory dicts passed by callers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntegrityResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "checked": self.checked,
        }


def _inject_uuids(doc: dict) -> list[str]:
    try:
        sel = doc["remnawave"]["injectHosts"][0]["selector"]
    except (KeyError, IndexError, TypeError):
        return []
    return [str(x) for x in (sel.get("values") or [])]


def _proxy_tags(n: int) -> set[str]:
    if n <= 0:
        return set()
    tags = {"proxy"}
    for i in range(2, n + 1):
        tags.add(f"proxy-{i}")
    return tags


def verify_proxy_tags_within_slots(doc: dict) -> list[str]:
    """Legacy positional proxy-N tags must not exceed actual inject slot count."""
    errors: list[str] = []
    inject = _inject_uuids(doc)
    allowed = _proxy_tags(len(inject))
    balancers = (doc.get("routing") or {}).get("balancers") or []
    for bal in balancers:
        btag = str(bal.get("tag") or "?")
        for sel in bal.get("selector") or []:
            st = str(sel)
            if st.startswith("proxy") and st not in allowed:
                errors.append(
                    f"balancer {btag} references {st} but only {len(inject)} "
                    f"inject slots exist (positional proxy-N over-reach)"
                )
    return errors


def verify_inject_hosts_known(
    doc: dict, hosts_by_uuid: dict[str, dict]
) -> list[str]:
    errors: list[str] = []
    for uid in _inject_uuids(doc):
        if uid not in hosts_by_uuid:
            errors.append(f"inject UUID {uid[:8]}… has no panel host record")
    return errors


def verify_inject_hosts_enabled(
    doc: dict, hosts_by_uuid: dict[str, dict]
) -> list[str]:
    """An injected host must be enabled (not isDisabled). Disabled-but-injected
    is the classic 'already-applied returned OK but path is dead' failure."""
    errors: list[str] = []
    for uid in _inject_uuids(doc):
        h = hosts_by_uuid.get(uid)
        if h is None:
            continue
        if h.get("isDisabled"):
            errors.append(f"inject UUID {uid[:8]}… maps to disabled host (dead path)")
    return errors


def verify_hosts_node_mapping(
    uuids: list[str],
    hosts_by_uuid: dict[str, dict],
    expected_node_ids: set[str] | None,
    nodes_by_uuid: dict[str, dict] | None = None,
) -> list[str]:
    """Each host UUID must map to an intended node_id group (not 'last 6 UUIDs')."""
    errors: list[str] = []
    if expected_node_ids is None:
        return errors
    nodes_by_uuid = nodes_by_uuid or {}
    for uid in uuids:
        h = hosts_by_uuid.get(uid)
        if not h:
            errors.append(f"UUID {uid[:8]}… not a known host (cannot prove node mapping)")
            continue
        node_refs = h.get("nodes") or []
        matched = False
        for nref in node_refs:
            pn = nodes_by_uuid.get(str(nref), {})
            name = str(pn.get("name") or "").lower()
            for nid in expected_node_ids:
                key = str(nid).lower()
                if key in name or key.replace("-", "") in name.replace("-", ""):
                    matched = True
                    break
            if matched:
                break
        if not matched and expected_node_ids:
            errors.append(
                f"UUID {uid[:8]}… does not map to any intended node group "
                f"(by-assumption ordering rejected)"
            )
    return errors


def verify_selector_outbound_mapping(
    selector_tags: list[str],
    known_outbound_tags: set[str],
) -> list[str]:
    """Every selector target must map to a known outbound tag (model-based path)."""
    errors: list[str] = []
    for tag in selector_tags:
        if str(tag) not in known_outbound_tags:
            errors.append(f"selector references unknown outbound tag {tag!r}")
    return errors


def verify_outbound_nodes_active(
    outbound_to_node: dict[str, dict],
) -> list[str]:
    """For production, an outbound's node must not be disabled/suspect."""
    errors: list[str] = []
    for tag, node in outbound_to_node.items():
        status = node.get("status")
        if status in {"disabled", "failed", "decommissioned", "draining"}:
            errors.append(f"outbound {tag} references {status} node (not prod-eligible)")
    return errors


def verify_template_integrity(
    doc: dict,
    *,
    hosts_by_uuid: dict[str, dict] | None = None,
    expected_node_ids: set[str] | None = None,
    nodes_by_uuid: dict[str, dict] | None = None,
    require_enabled: bool = True,
) -> IntegrityResult:
    """Top-level template integrity (count-only is never sufficient)."""
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []

    checked.append("proxy_tags_within_slots")
    errors.extend(verify_proxy_tags_within_slots(doc))

    if hosts_by_uuid is not None:
        checked.append("inject_hosts_known")
        errors.extend(verify_inject_hosts_known(doc, hosts_by_uuid))
        if require_enabled:
            checked.append("inject_hosts_enabled")
            errors.extend(verify_inject_hosts_enabled(doc, hosts_by_uuid))
        if expected_node_ids is not None:
            checked.append("hosts_node_mapping")
            errors.extend(
                verify_hosts_node_mapping(
                    _inject_uuids(doc), hosts_by_uuid, expected_node_ids, nodes_by_uuid
                )
            )

    return IntegrityResult(ok=not errors, errors=errors, warnings=warnings, checked=checked)


def assert_already_applied(
    doc: dict,
    required_uuids: list[str],
    hosts_by_uuid: dict[str, dict],
) -> IntegrityResult:
    """Prove an 'already applied' state: all required UUIDs are injected AND their
    hosts are enabled. Returns ok=False if any required path is missing/disabled."""
    errors: list[str] = []
    inject = set(_inject_uuids(doc))
    for uid in required_uuids:
        if uid not in inject:
            errors.append(f"required UUID {uid[:8]}… not present in injectHosts")
            continue
        h = hosts_by_uuid.get(uid)
        if h is None:
            errors.append(f"required UUID {uid[:8]}… has no host record")
        elif h.get("isDisabled"):
            errors.append(f"required UUID {uid[:8]}… host is disabled (not truly applied)")
    return IntegrityResult(
        ok=not errors,
        errors=errors,
        checked=["already_applied_proves_enabled_and_injected"],
    )
