"""Shared helpers: LV down → NL-only subscription template (injectHosts + balancers)."""
from __future__ import annotations

import copy
from typing import Any

from balancer_selectors import (  # noqa: E402
    INTL_BALANCER_TAG,
    INTL_STEALTH_BALANCER_TAG,
    is_relay_only_profile,
    is_stealth_split_profile,
)
from subscription_fetch import AMS_IP, LV_IP, NL_IP, RELAY_IP  # noqa: E402
from trim_injecthosts_no_xhttp import is_xhttp_host  # noqa: E402

STATE_FILE_NAME = "lv_nl_failover_state.json"
BALANCER_TAGS_TRAFFIC = ("Super_Balancer", INTL_BALANCER_TAG, INTL_STEALTH_BALANCER_TAG)


def is_lv_node(node: dict) -> bool:
    name = str(node.get("name") or "").lower()
    addr = str(node.get("address") or node.get("host") or "")
    if addr == LV_IP:
        return True
    return "latvia" in name or name.startswith("lv")


def is_nl_node(node: dict) -> bool:
    name = str(node.get("name") or "").lower()
    addr = str(node.get("address") or node.get("host") or "")
    if addr == NL_IP:
        return True
    return "netherlands" in name or name.endswith("-nl") or " nl" in f" {name} "


def is_relay_node(node: dict) -> bool:
    addr = str(node.get("address") or node.get("host") or "")
    if addr == RELAY_IP:
        return True
    name = str(node.get("name") or "").lower()
    return "relay" in name or "ru-" in name


def lv_nodes_healthy(nodes: list[dict]) -> tuple[bool, str]:
    lv = [n for n in nodes if is_lv_node(n) and not n.get("isDisabled")]
    if not lv:
        return False, "no LV prod node in panel"
    connected = [n for n in lv if n.get("isConnected")]
    if not connected:
        names = ", ".join(n.get("name") or "?" for n in lv)
        return False, f"LV node(s) not connected: {names}"
    return True, "LV connected"


def nl_nodes_healthy(nodes: list[dict]) -> tuple[bool, str]:
    nl = [n for n in nodes if is_nl_node(n) and not n.get("isDisabled")]
    if not nl:
        return False, "no NL prod node in panel"
    connected = [n for n in nl if n.get("isConnected")]
    if not connected:
        names = ", ".join(n.get("name") or "?" for n in nl)
        return False, f"NL node(s) not connected: {names}"
    return True, f"NL ok ({len(connected)} connected)"


def proxy_tags_for_count(n: int) -> list[str]:
    if n < 1:
        raise ValueError("need at least one injectHost for NL failover")
    tags = ["proxy"]
    for i in range(2, n + 1):
        tags.append(f"proxy-{i}")
    return tags


def collect_nl_inject_uuids(
    hosts: list[dict], nodes_by_uuid: dict[str, dict]
) -> tuple[list[str], list[str]]:
    """Return (uuids, log lines) for NL direct hosts only (no relay, no xhttp)."""
    log: list[str] = []
    candidates: list[tuple[int, str, dict]] = []
    for h in hosts:
        uid = str(h.get("uuid") or "")
        if not uid:
            continue
        if is_xhttp_host(h):
            continue
        node_ids = h.get("nodes") or []
        if not node_ids:
            continue
        node = nodes_by_uuid.get(str(node_ids[0]), {})
        if node.get("isDisabled") or not node.get("isConnected"):
            continue
        if is_relay_node(node) or is_lv_node(node) or not is_nl_node(node):
            continue
        port = int(h.get("port") or 0)
        remark = str(h.get("remark") or "")
        candidates.append((port, uid, h))
        log.append(f"  NL host {uid[:8]}… port={port} remark={remark[:40]!r}")

    if not candidates:
        return [], log + ["ERROR: zero NL hosts eligible for injectHosts"]

    # Prefer :443 before :9443 for stable tag order
    candidates.sort(key=lambda t: (0 if t[0] == 443 else 1, t[0], t[1]))
    uuids = [uid for _, uid, _ in candidates]
    log.append(f"selected {len(uuids)} NL injectHosts")
    return uuids, log


def detect_template_profile(doc: dict) -> str:
    balancers = {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}
    if is_stealth_split_profile(doc):
        return "stealth_split"
    if is_relay_only_profile(doc):
        return "relay_only"
    if balancers.get("Super_Balancer") and balancers.get(INTL_BALANCER_TAG):
        return "super_intl"
    if balancers.get(INTL_BALANCER_TAG):
        return "intl_only"
    return "unknown"


def _balancers_to_patch(doc: dict, profile: str) -> list[str]:
    if profile == "stealth_split":
        return [INTL_BALANCER_TAG, INTL_STEALTH_BALANCER_TAG]
    if profile in ("relay_only", "intl_only"):
        return [INTL_BALANCER_TAG]
    return ["Super_Balancer", INTL_BALANCER_TAG]


def save_balancer_state(doc: dict, profile: str) -> dict[str, Any]:
    saved: dict[str, Any] = {}
    tags = _balancers_to_patch(doc, profile)
    for b in doc.get("routing", {}).get("balancers") or []:
        tag = b.get("tag")
        if tag in tags:
            saved[tag] = copy.deepcopy(b)
    return saved


def apply_nl_failover_to_doc(
    doc: dict, nl_uuids: list[str], *, saved: dict[str, Any] | None = None
) -> tuple[bool, list[str], dict[str, Any]]:
    """Mutate doc. Returns (changed, log, state_fragment)."""
    log: list[str] = []
    profile = detect_template_profile(doc)
    log.append(f"template profile: {profile}")

    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before_inj = list(sel.get("values") or [])
    if before_inj == nl_uuids:
        log.append(f"injectHosts already NL-only ({len(nl_uuids)})")
        inject_changed = False
    else:
        sel["values"] = list(nl_uuids)
        log.append(f"injectHosts {len(before_inj)} -> {len(nl_uuids)} (NL only)")
        inject_changed = True

    tags = proxy_tags_for_count(len(nl_uuids))
    log.append(f"balancer selector tags: {tags}")

    state = saved or {}
    if not state.get("saved_inject"):
        state["saved_inject"] = before_inj
    if not state.get("saved_balancers"):
        state["saved_balancers"] = save_balancer_state(doc, profile)
    state["profile"] = profile

    bal_changed = False
    for b in doc.get("routing", {}).get("balancers") or []:
        tag = b.get("tag")
        if tag not in _balancers_to_patch(doc, profile):
            continue
        old = list(b.get("selector") or [])
        if old != tags:
            b["selector"] = list(tags)
            log.append(f"{tag}: {len(old)} -> {len(tags)} paths (NL only)")
            bal_changed = True
        strat = b.setdefault("strategy", {})
        if strat.get("type") != "random":
            strat["type"] = "random"
            log.append(f"{tag}: strategy -> random")
            bal_changed = True
        if b.pop("fallbackTag", None):
            log.append(f"{tag}: removed fallbackTag")
            bal_changed = True

    return inject_changed or bal_changed, log, state


def restore_doc_from_state(doc: dict, state: dict[str, Any]) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False
    saved_inj = state.get("saved_inject")
    if saved_inj is not None:
        cur = list(doc["remnawave"]["injectHosts"][0]["selector"].get("values") or [])
        if cur != saved_inj:
            doc["remnawave"]["injectHosts"][0]["selector"]["values"] = list(saved_inj)
            log.append(f"injectHosts restored ({len(saved_inj)} UUIDs)")
            changed = True

    saved_bals = state.get("saved_balancers") or {}
    by_tag = {b.get("tag"): b for b in doc.get("routing", {}).get("balancers") or []}
    for tag, snap in saved_bals.items():
        if tag not in by_tag:
            continue
        if by_tag[tag] != snap:
            idx = next(
                i
                for i, b in enumerate(doc["routing"]["balancers"])
                if b.get("tag") == tag
            )
            doc["routing"]["balancers"][idx] = copy.deepcopy(snap)
            log.append(f"restored balancer {tag}")
            changed = True
    return changed, log


def analyze_live_sub(cfg: dict) -> dict[str, Any]:
    """Summarize subscription for verify/compare."""
    outbounds = cfg.get("outbounds") or []
    proxies = [o for o in outbounds if str(o.get("tag", "")).startswith("proxy")]
    by_addr: dict[str, int] = {}
    for o in proxies:
        v = (o.get("settings") or {}).get("vnext") or [{}]
        addr = str((v[0] if v else {}).get("address") or "?")
        by_addr[addr] = by_addr.get(addr, 0) + 1
    rules = (cfg.get("routing") or {}).get("rules") or []
    has_private_geo = any("geoip:private" in (r.get("ip") or []) for r in rules)
    return {
        "proxy_count": len(proxies),
        "by_addr": by_addr,
        "lv_count": by_addr.get(LV_IP, 0),
        "nl_count": by_addr.get(NL_IP, 0),
        "relay_count": by_addr.get(RELAY_IP, 0),
        "ams_count": by_addr.get(AMS_IP, 0),
        "has_geoip_private": has_private_geo,
        "rules_count": len(rules),
    }
