#!/usr/bin/env python3
"""NL canary route-class taxonomy — NL-DIRECT-ROUTE-CLASS-FIX-001.

Explicit route classes for owner smoke so normal RU/direct-bypass traffic
cannot be mistaken for NL proof, and blocked-site expectations are unambiguous.

HARD SAFETY: no secrets, no network, no prod mutation.
"""
from __future__ import annotations

from typing import Any

from balancer_selectors import INTL_BALANCER_TAG, INTL_STEALTH_BALANCER_TAG

ROUTE_CLASS_DIRECT_BYPASS = "DIRECT_BYPASS_ALLOWED"
ROUTE_CLASS_NL_DIRECT = "NL_DIRECT_VALIDATION"
ROUTE_CLASS_STEALTH = "STEALTH_VALIDATION"
ROUTE_CLASS_BLOCKED_NL = "BLOCKED_SITE_NL_DIRECT"
ROUTE_CLASS_BLOCKED_STEALTH = "BLOCKED_SITE_STEALTH"

# RU/local markers carried in direct-bypass rules — do NOT prove VPN/NL success.
DIRECT_BYPASS_MARKERS = frozenset(
    {
        "geoip:ru",
        "geoip:private",
        "regexp:.*\\.ru$",
        "yandex.ru",
        "yandex.com",
        "vk.com",
        "mail.ru",
        "ozon.com",
        "avito.com",
        "gosuslugi.com",
    }
)

# Neutral intl targets that must route via Intl_Direct (NL) — explicit proof set.
NL_DIRECT_VALIDATION_GEOSITES = [
    "geosite:google",
    "geosite:youtube",
    "geosite:twitter",
]

NL_DIRECT_VALIDATION_DOMAINS = [
    "x.com",
    "openai.com",
    "chatgpt.com",
]

# Stealth-only media — must route via Intl_Stealth in split profile.
STEALTH_VALIDATION_GEOSITES = [
    "geosite:instagram",
    "geosite:facebook",
    "geosite:telegram",
    "geosite:whatsapp",
]

STEALTH_VALIDATION_DOMAINS = [
    "meta.com",
    "fbcdn.net",
    "cdninstagram.com",
    "telegram.org",
    "t.me",
    "telegram.me",
    "telesco.pe",
]

# Blocked-site classification for runbook (RU-blocked expectations).
BLOCKED_SITE_CLASS: dict[str, str] = {
    "telegram.org": ROUTE_CLASS_BLOCKED_STEALTH,
    "t.me": ROUTE_CLASS_BLOCKED_STEALTH,
    "instagram.com": ROUTE_CLASS_BLOCKED_STEALTH,
    "facebook.com": ROUTE_CLASS_BLOCKED_STEALTH,
    "meta.com": ROUTE_CLASS_BLOCKED_STEALTH,
    "whatsapp.com": ROUTE_CLASS_BLOCKED_STEALTH,
    "google.com": ROUTE_CLASS_BLOCKED_NL,
    "youtube.com": ROUTE_CLASS_BLOCKED_NL,
    "gmail.com": ROUTE_CLASS_BLOCKED_NL,
    "twitter.com": ROUTE_CLASS_BLOCKED_NL,
    "x.com": ROUTE_CLASS_BLOCKED_NL,
    "openai.com": ROUTE_CLASS_BLOCKED_NL,
}

# Owner smoke proof targets — never use direct-bypass sites as NL proof.
SMOKE_TARGETS_DIRECT_BASIC = {
    "nl_direct_proof": ["google.com search", "gmail.com", "youtube.com"],
    "forbidden": ["telegram", "instagram", "meta"],
    "not_nl_proof": ["yandex.ru", "vk.com", "mail.ru", "ozon.com"],
}

SMOKE_TARGETS_SPLIT_STEALTH = {
    "nl_direct_proof": ["google.com search", "youtube.com", "x.com", "openai.com"],
    "stealth_proof": ["telegram", "instagram", "facebook", "whatsapp"],
    "not_nl_proof": ["yandex.ru", "vk.com", "mail.ru", "ozon.com", "rutube.ru"],
    "not_vpn_proof": ["yandex.ru", "vk.com", "mail.ru", "ozon.com", "rutube.ru"],
}


def _rule_hay(rule: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("domain", "ip", "protocol"):
        for v in rule.get(key) or []:
            parts.append(str(v).lower())
    return " ".join(parts)


def _marker_in_hay(marker: str, hay: str) -> bool:
    m = marker.lower()
    if m in hay:
        return True
    # geosite:google matches domain list containing geosite:google
    if m.startswith("geosite:") and m in hay:
        return True
    bare = m.split(":")[-1] if ":" in m else m
    return bare in hay


def resolve_marker_route(cfg: dict[str, Any], marker: str) -> str | None:
    """Return balancerTag or outboundTag for the first matching routing rule."""
    rules = (cfg.get("routing") or {}).get("rules") or []
    for rule in rules:
        if rule.get("network") == "tcp,udp" and not rule.get("domain") and not rule.get("ip"):
            # catch-all — only if no prior match; handled by caller walking in order
            continue
        hay = _rule_hay(rule)
        if _marker_in_hay(marker, hay):
            return rule.get("balancerTag") or rule.get("outboundTag")
    # catch-all fallback
    for rule in rules:
        if rule.get("network") == "tcp,udp":
            return rule.get("balancerTag") or rule.get("outboundTag")
    return None


def expected_route_class(marker: str) -> str | None:
    """Runbook expectation for a domain/geosite marker."""
    low = marker.lower()
    if low in BLOCKED_SITE_CLASS:
        return BLOCKED_SITE_CLASS[low]
    if low in DIRECT_BYPASS_MARKERS or low.endswith(".ru"):
        return ROUTE_CLASS_DIRECT_BYPASS
    if any(low == d.lower() for d in STEALTH_VALIDATION_DOMAINS) or any(
        low in g for g in STEALTH_VALIDATION_GEOSITES
    ):
        return ROUTE_CLASS_STEALTH
    if any(low in g for g in NL_DIRECT_VALIDATION_GEOSITES) or any(
        low == d.lower() for d in NL_DIRECT_VALIDATION_DOMAINS
    ):
        return ROUTE_CLASS_NL_DIRECT
    return None


def validate_route_classes(
    cfg: dict[str, Any],
    *,
    variant: str,
) -> list[str]:
    """Return validation errors for route-class consistency (empty = OK)."""
    errors: list[str] = []
    rules = (cfg.get("routing") or {}).get("rules") or []

    if not rules:
        errors.append("routing.rules missing — route classes undefined")
        return errors

    if variant == "direct_basic":
        for marker in NL_DIRECT_VALIDATION_GEOSITES:
            tag = resolve_marker_route(cfg, marker)
            if tag != INTL_BALANCER_TAG:
                errors.append(
                    f"NL_DIRECT_VALIDATION {marker!r} must route via {INTL_BALANCER_TAG}, got {tag!r}"
                )
        for marker in STEALTH_VALIDATION_GEOSITES + STEALTH_VALIDATION_DOMAINS:
            tag = resolve_marker_route(cfg, marker)
            if tag == INTL_STEALTH_BALANCER_TAG:
                errors.append(f"DIRECT_BASIC must not route stealth target {marker!r} via stealth")
        catch = resolve_marker_route(cfg, "example.com")
        if catch != INTL_BALANCER_TAG:
            errors.append(f"DIRECT_BASIC catch-all must route via {INTL_BALANCER_TAG}, got {catch!r}")

    elif variant == "split_stealth":
        # Explicit NL validation rule required (not only implicit catch-all).
        has_explicit_nl_rule = any(
            rule.get("balancerTag") == INTL_BALANCER_TAG
            and any(
                m in _rule_hay(rule)
                for m in NL_DIRECT_VALIDATION_GEOSITES + NL_DIRECT_VALIDATION_DOMAINS
            )
            for rule in rules
        )
        if not has_explicit_nl_rule:
            errors.append(
                "SPLIT_STEALTH lacks explicit NL_DIRECT_VALIDATION rule "
                f"({NL_DIRECT_VALIDATION_GEOSITES + NL_DIRECT_VALIDATION_DOMAINS})"
            )

        for marker in NL_DIRECT_VALIDATION_GEOSITES + NL_DIRECT_VALIDATION_DOMAINS:
            tag = resolve_marker_route(cfg, marker)
            if tag != INTL_BALANCER_TAG:
                errors.append(
                    f"NL_DIRECT_VALIDATION {marker!r} must route via {INTL_BALANCER_TAG}, got {tag!r}"
                )

        for marker in STEALTH_VALIDATION_GEOSITES + STEALTH_VALIDATION_DOMAINS:
            tag = resolve_marker_route(cfg, marker)
            if tag != INTL_STEALTH_BALANCER_TAG:
                errors.append(
                    f"STEALTH_VALIDATION {marker!r} must route via {INTL_STEALTH_BALANCER_TAG}, got {tag!r}"
                )

        for marker in DIRECT_BYPASS_MARKERS:
            # Only enforce when a direct rule explicitly mentions the marker.
            present = any(
                rule.get("outboundTag") == "direct" and _marker_in_hay(marker, _rule_hay(rule))
                for rule in rules
            )
            if not present:
                continue
            tag = resolve_marker_route(cfg, marker)
            if tag and tag != "direct":
                errors.append(
                    f"DIRECT_BYPASS {marker!r} must route via direct, got {tag!r}"
                )

        # Stealth must not swallow NL validation targets.
        for rule in rules:
            if rule.get("balancerTag") != INTL_STEALTH_BALANCER_TAG:
                continue
            hay = _rule_hay(rule)
            for marker in NL_DIRECT_VALIDATION_GEOSITES + NL_DIRECT_VALIDATION_DOMAINS:
                if _marker_in_hay(marker, hay):
                    errors.append(
                        f"NL validation target {marker!r} incorrectly listed in stealth rule"
                    )

    if not BLOCKED_SITE_CLASS:
        errors.append("BLOCKED_SITE_CLASS table empty")

    return errors


def route_class_metadata(variant: str) -> dict[str, Any]:
    """Embed in generator metadata / runbook."""
    return {
        "route_classes": {
            ROUTE_CLASS_DIRECT_BYPASS: sorted(DIRECT_BYPASS_MARKERS),
            ROUTE_CLASS_NL_DIRECT: NL_DIRECT_VALIDATION_GEOSITES + NL_DIRECT_VALIDATION_DOMAINS,
            ROUTE_CLASS_STEALTH: STEALTH_VALIDATION_GEOSITES + STEALTH_VALIDATION_DOMAINS,
            "blocked_site_classification": BLOCKED_SITE_CLASS,
        },
        "smoke_targets": (
            SMOKE_TARGETS_DIRECT_BASIC if variant == "direct_basic" else SMOKE_TARGETS_SPLIT_STEALTH
        ),
    }
