#!/usr/bin/env python3
"""NL independent-exit canary profile builder — NL-INDEPENDENT-EXIT-FIX-001.

Builds two owner-only Happ importable profiles (local .local only):

  1. DIRECT_BASIC — NL outbounds only; Google/general via NL (protocol proof).
  2. SPLIT_STEALTH — NL Intl_Direct + relay-2 Intl_Stealth (TG/Meta only; no Google on stealth).

HARD SAFETY: no secrets in stdout; no prod mutation.
"""
from __future__ import annotations

import copy
from typing import Any

from balancer_selectors import INTL_BALANCER_TAG, INTL_STEALTH_BALANCER_TAG, NL_DIRECT_SELECTOR
from nl_canary_route_classes import (
    NL_DIRECT_VALIDATION_DOMAINS,
    NL_DIRECT_VALIDATION_GEOSITES,
    STEALTH_VALIDATION_DOMAINS,
    STEALTH_VALIDATION_GEOSITES,
)
from relay_latency_probe import RELAY1_IP, RELAY2_IP
from subscription_fetch import node_label, outbound_endpoint

PROFILE_LABEL_DIRECT_BASIC = "BenderVPN NL Direct Basic Canary — owner only"
PROFILE_LABEL_SPLIT_STEALTH = "BenderVPN NL Split Stealth Canary — owner only"

PROFILE_LABEL_LEGACY = "BenderVPN NL Independent Exit Canary — owner only"

DIRECT_BASIC_FILENAME = "independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json"
SPLIT_STEALTH_FILENAME = "independent_exit_nl_SPLIT_STEALTH_IMPORTABLE_PROFILE.json"
LEGACY_IMPORTABLE_FILENAME = "independent_exit_nl_canary_IMPORTABLE_PROFILE.json"

# Stealth-only media (must NOT include geosite:google — invalidates NL smoke).
STEALTH_MEDIA_GEOSITES = list(STEALTH_VALIDATION_GEOSITES)
STEALTH_MEDIA_DOMAINS = list(STEALTH_VALIDATION_DOMAINS)

STEALTH_MEDIA_IPS = [
    "149.154.0.0/16",
    "91.108.0.0/16",
    "185.60.64.0/22",
    "31.13.0.0/16",
    "31.13.64.0/18",
    "57.144.0.0/14",
]

# Explicit NL-direct proof targets for DIRECT_BASIC + SPLIT_STEALTH smoke.
NL_DIRECT_PROOF_GEOSITES = list(NL_DIRECT_VALIDATION_GEOSITES)
NL_DIRECT_PROOF_DOMAINS = list(NL_DIRECT_VALIDATION_DOMAINS)

# Markers that must never route via Intl_Direct in split profile.
STEALTH_SENSITIVE_IN_DIRECT = frozenset({"telegram", "instagram", "facebook", "meta.com"})


def _vless_proxies(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        o
        for o in cfg.get("outbounds") or []
        if isinstance(o, dict)
        and o.get("protocol") == "vless"
        and str(o.get("tag") or "").startswith("proxy")
    ]


def nl_proxy_tags(cfg: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for ob in _vless_proxies(cfg):
        addr, port = outbound_endpoint(ob)
        tag = str(ob.get("tag") or "")
        if node_label(addr, port) == "NL" or tag in NL_DIRECT_SELECTOR:
            if addr and node_label(addr, port) != "NL" and tag not in NL_DIRECT_SELECTOR:
                continue
            tags.append(tag)
    return sorted(set(tags))


def relay2_proxy_tags(cfg: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for ob in _vless_proxies(cfg):
        addr, _ = outbound_endpoint(ob)
        if addr == RELAY2_IP:
            tags.append(str(ob.get("tag") or ""))
    return sorted(set(tags))


def relay1_proxy_tags(cfg: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for ob in _vless_proxies(cfg):
        addr, _ = outbound_endpoint(ob)
        if addr == RELAY1_IP:
            tags.append(str(ob.get("tag") or ""))
    return sorted(set(tags))


def _relay1_proxy_tags(cfg: dict[str, Any]) -> list[str]:
    return relay1_proxy_tags(cfg)


def _filter_outbounds(cfg: dict[str, Any], keep_tags: set[str]) -> None:
    new_outbounds: list[dict[str, Any]] = []
    for ob in cfg.get("outbounds") or []:
        if (
            isinstance(ob, dict)
            and ob.get("protocol") == "vless"
            and str(ob.get("tag") or "").startswith("proxy")
        ):
            if str(ob.get("tag") or "") not in keep_tags:
                continue
        new_outbounds.append(ob)
    cfg["outbounds"] = new_outbounds


def _scrub_direct_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep RU bypass / private direct rules; strip relay1 from direct IP lists."""
    kept: list[dict[str, Any]] = []
    for rule in rules:
        if rule.get("outboundTag") != "direct":
            continue
        r = copy.deepcopy(rule)
        if isinstance(r.get("ip"), list):
            r["ip"] = [
                ip
                for ip in r["ip"]
                if RELAY1_IP not in str(ip) and f"{RELAY1_IP}/32" not in str(ip)
            ]
        kept.append(r)
    return kept


def _block_bittorrent_rule() -> dict[str, Any]:
    return {"type": "field", "protocol": ["bittorrent", "utp"], "outboundTag": "block"}


def _set_balancers(
    cfg: dict[str, Any],
    *,
    intl_selector: list[str],
    stealth_selector: list[str] | None,
) -> None:
    routing = cfg.setdefault("routing", {})
    new_balancers: list[dict[str, Any]] = []
    for bal in routing.get("balancers") or []:
        tag = bal.get("tag")
        if tag == INTL_BALANCER_TAG:
            b = copy.deepcopy(bal)
            b["selector"] = list(intl_selector)
            b.setdefault("strategy", {})["type"] = "random"
            new_balancers.append(b)
        elif tag == INTL_STEALTH_BALANCER_TAG and stealth_selector is not None:
            b = copy.deepcopy(bal)
            b["selector"] = list(stealth_selector)
            b.setdefault("strategy", {})["type"] = "random"
            new_balancers.append(b)
    routing["balancers"] = new_balancers


def _rules_direct_basic(cfg: dict[str, Any], nl_tags: list[str]) -> list[dict[str, Any]]:
    src_rules = (cfg.get("routing") or {}).get("rules") or []
    rules = [_block_bittorrent_rule()]
    rules.append(
        {
            "type": "field",
            "domain": list(NL_DIRECT_PROOF_GEOSITES) + list(NL_DIRECT_PROOF_DOMAINS),
            "balancerTag": INTL_BALANCER_TAG,
        }
    )
    rules.extend(_scrub_direct_rules(src_rules))
    rules.append({"type": "field", "network": "tcp,udp", "balancerTag": INTL_BALANCER_TAG})
    return rules


def _rules_split_stealth(cfg: dict[str, Any], nl_tags: list[str], relay_tags: list[str]) -> list[dict[str, Any]]:
    src_rules = (cfg.get("routing") or {}).get("rules") or []
    rules = [_block_bittorrent_rule()]
    rules.append(
        {
            "type": "field",
            "ip": list(STEALTH_MEDIA_IPS),
            "balancerTag": INTL_STEALTH_BALANCER_TAG,
        }
    )
    rules.append(
        {
            "type": "field",
            "domain": list(STEALTH_MEDIA_GEOSITES) + list(STEALTH_MEDIA_DOMAINS),
            "balancerTag": INTL_STEALTH_BALANCER_TAG,
        }
    )
    # NL validation BEFORE direct-bypass scrub — source may list intl domains as direct.
    rules.append(
        {
            "type": "field",
            "domain": list(NL_DIRECT_PROOF_GEOSITES) + list(NL_DIRECT_PROOF_DOMAINS),
            "balancerTag": INTL_BALANCER_TAG,
        }
    )
    rules.extend(_scrub_direct_rules(src_rules))
    rules.append({"type": "field", "network": "tcp,udp", "balancerTag": INTL_BALANCER_TAG})
    return rules


def _strip_reality_fragment(cfg: dict[str, Any]) -> int:
    """Remove sockopt.fragment from REALITY outbounds.

    TLS fragmentation corrupts the REALITY ClientHello on the direct exit path:
    the session connects, survives a few seconds, then resets (report 13 NL
    direct reset storm while the relay2/stealth forwarder path stayed alive).
    The repo already strips this server-side (patch_remove_fragment_defaults);
    the canary builder previously copied it verbatim from the owner source.
    Returns the number of outbounds cleaned (for logging/tests).
    """
    cleaned = 0
    for ob in cfg.get("outbounds") or []:
        if not isinstance(ob, dict):
            continue
        ss = ob.get("streamSettings")
        if not isinstance(ss, dict) or ss.get("security") != "reality":
            continue
        sockopt = ss.get("sockopt")
        if isinstance(sockopt, dict) and "fragment" in sockopt:
            sockopt.pop("fragment", None)
            cleaned += 1
            if not sockopt:
                ss.pop("sockopt", None)
    return cleaned


def reality_fragment_outbounds(cfg: dict[str, Any]) -> list[str]:
    """Tags of REALITY outbounds that still carry sockopt.fragment (should be none)."""
    tags: list[str] = []
    for ob in cfg.get("outbounds") or []:
        if not isinstance(ob, dict):
            continue
        ss = ob.get("streamSettings")
        if not isinstance(ss, dict) or ss.get("security") != "reality":
            continue
        sockopt = ss.get("sockopt")
        if isinstance(sockopt, dict) and "fragment" in sockopt:
            tags.append(str(ob.get("tag") or "?"))
    return tags


def _finalize(cfg: dict[str, Any], remarks: str) -> dict[str, Any]:
    cfg.pop("observatory", None)
    cfg.pop("burstObservatory", None)
    _strip_reality_fragment(cfg)
    cfg["remarks"] = remarks
    return cfg


def build_nl_direct_basic_profile(cfg: dict[str, Any]) -> dict[str, Any]:
    """NL-only connectivity proof — Google/catch-all via NL; no stealth pool."""
    nl_tags = nl_proxy_tags(cfg)
    if not nl_tags:
        raise ValueError("source config has no NL direct vless outbounds")

    out = copy.deepcopy(cfg)
    _filter_outbounds(out, set(nl_tags))
    _set_balancers(out, intl_selector=nl_tags, stealth_selector=None)
    out.setdefault("routing", {})["rules"] = _rules_direct_basic(out, nl_tags)
    return _finalize(out, PROFILE_LABEL_DIRECT_BASIC)


def build_nl_split_stealth_profile(cfg: dict[str, Any]) -> dict[str, Any]:
    """NL Intl_Direct + relay-2 stealth; Google NOT on stealth."""
    nl_tags = nl_proxy_tags(cfg)
    relay_tags = relay2_proxy_tags(cfg)
    if not nl_tags:
        raise ValueError("source config has no NL direct vless outbounds")
    if not relay_tags:
        raise ValueError("source config has no relay-2 vless outbounds for stealth pool")

    out = copy.deepcopy(cfg)
    keep = set(nl_tags) | set(relay_tags)
    _filter_outbounds(out, keep)
    _set_balancers(out, intl_selector=nl_tags, stealth_selector=relay_tags)
    out.setdefault("routing", {})["rules"] = _rules_split_stealth(out, nl_tags, relay_tags)
    return _finalize(out, PROFILE_LABEL_SPLIT_STEALTH)


def build_nl_independent_exit_canary_profile(cfg: dict[str, Any]) -> dict[str, Any]:
    """Legacy single profile — kept for regression; prefer split variants."""
    return build_nl_split_stealth_profile(cfg)


def balancer_for_domain_marker(cfg: dict[str, Any], marker: str) -> str | None:
    """Return balancerTag/outboundTag for first rule matching marker in domain/ip."""
    for rule in (cfg.get("routing") or {}).get("rules") or []:
        hay = " ".join(str(x) for x in (rule.get("domain") or []) + (rule.get("ip") or [])).lower()
        if marker.lower() in hay:
            return rule.get("balancerTag") or rule.get("outboundTag")
    return None


def google_routes_via_stealth(cfg: dict[str, Any]) -> bool:
    tag = balancer_for_domain_marker(cfg, "geosite:google")
    return tag == INTL_STEALTH_BALANCER_TAG
