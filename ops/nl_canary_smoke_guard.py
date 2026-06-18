#!/usr/bin/env python3
"""NL canary smoke preflight guard — NL-DIRECT-BASIC-SMOKE-GUARD-001.

Fail-fast validation before accepting owner NL Direct Basic smoke reports.
Read-only: no network, no prod mutation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from nl_canary_profile_builder import (
    PROFILE_LABEL_DIRECT_BASIC,
    PROFILE_LABEL_SPLIT_STEALTH,
)

PROFILE_LABEL_LEGACY = "BenderVPN NL Independent Exit Canary — owner only"

VARIANT_EXPECTED_PROFILE: dict[str, str] = {
    "direct_basic": PROFILE_LABEL_DIRECT_BASIC,
    "split_stealth": PROFILE_LABEL_SPLIT_STEALTH,
}

FORBIDDEN_APPS_DIRECT_BASIC = frozenset({"Telegram", "Instagram", "Meta"})

INVALID_WRONG_PROFILE = "INVALID_SMOKE_WRONG_PROFILE"
INVALID_ROUTING_OVERLAY = "INVALID_SMOKE_ROUTING_OVERLAY_ENABLED"
INVALID_FORBIDDEN_APP = "INVALID_SMOKE_FORBIDDEN_APP_TELEGRAM_IN_DIRECT_BASIC"
INVALID_RELAY_STEALTH_PATH = "INVALID_SMOKE_RELAY_STEALTH_DOMINANT"
INVALID_PROFILE_RELAY2 = "INVALID_SMOKE_DIRECT_BASIC_HAS_RELAY2"

VERDICT_NOT_TESTED = "NOT_TESTED_INVALID_SMOKE"
VERDICT_PASS = "PASS"
VERDICT_PARTIAL = "PARTIAL"
VERDICT_FAIL = "FAIL"

CLASS_SPLIT_STEALTH_PARTIAL = "SPLIT_STEALTH_PARTIAL"
CLASS_TELEGRAM_STEALTH_ALIVE = "TELEGRAM_STEALTH_ALIVE"
CLASS_NL_DIRECT_ROUTE_FAIL = "NL_DIRECT_OR_ROUTE_CLASS_FAIL"
CLASS_DIRECT_BYPASS_MASKS = "DIRECT_BYPASS_MASKS_SMOKE"

_EXTERNAL_OVERLAY_MARKERS = (
    "bendervpn ru",
    "bender vpn ru",
)

_TELEGRAM_PATTERNS = (
    re.compile(r"\btelegram\b", re.I),
    re.compile(r"\bt\.me\b", re.I),
    re.compile(r"149\.154\.", re.I),
    re.compile(r"91\.108\.", re.I),
)

_META_PATTERNS = (
    re.compile(r"\binstagram\b", re.I),
    re.compile(r"\bfacebook\b", re.I),
    re.compile(r"\bmeta\.com\b", re.I),
)

_BLOCKED_NL_PATTERNS = (
    re.compile(r"\bgoogle\.com\b", re.I),
    re.compile(r"\bgmail\b", re.I),
    re.compile(r"\byoutube\b", re.I),
    re.compile(r"\bx\.com\b", re.I),
    re.compile(r"\btwitter\b", re.I),
    re.compile(r"\bopenai\b", re.I),
)

_DIRECT_BYPASS_OK_PATTERNS = (
    re.compile(r"\byandex\b", re.I),
    re.compile(r"\bvk\.com\b", re.I),
    re.compile(r"\bmail\.ru\b", re.I),
    re.compile(r"\bozon\b", re.I),
    re.compile(r"\brutube\b", re.I),
    re.compile(r"\.ru\b", re.I),
)


@dataclass
class SmokeGuardResult:
    variant: str
    acceptable_smoke_input: bool
    invalid_reasons: list[str] = field(default_factory=list)
    verdict: str = VERDICT_NOT_TESTED
    checks: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": self.variant,
            "ACCEPTABLE_SMOKE_INPUT": self.acceptable_smoke_input,
            "invalid_reasons": self.invalid_reasons,
            "verdict": self.verdict,
            "checks": self.checks,
            "notes": self.notes,
        }


def _norm_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in {"true", "1", "yes"}:
        return True
    if s in {"false", "0", "no"}:
        return False
    return None


def external_routing_overlay_active(mode: dict[str, Any]) -> bool:
    """Happ TunnelSettings external routing overlay (BenderVPN RU etc.)."""
    use_routing = _norm_bool(mode.get("use_routing"))
    profile = str(mode.get("routing_profile") or mode.get("active_routing_profile_name") or "").strip()
    profile_l = profile.lower()
    if use_routing is True and profile:
        if any(m in profile_l for m in _EXTERNAL_OVERLAY_MARKERS):
            return True
        if "ru" in profile_l and "bender" in profile_l:
            return True
    if use_routing is True and mode.get("routing_enabled") is True:
        if profile and "bender" in profile_l:
            return True
    return False


def profile_name_matches_variant(profile_name: str | None, variant: str) -> bool:
    expected = VARIANT_EXPECTED_PROFILE.get(variant)
    if not expected:
        return False
    name = str(profile_name or "").strip()
    if not name:
        return False
    if name == expected:
        return True
    return expected.lower() in name.lower()


def is_legacy_profile_name(profile_name: str | None) -> bool:
    name = str(profile_name or "").strip().lower()
    return "independent exit canary" in name and "direct basic" not in name


def detect_session_signals(
    *,
    app_log: str = "",
    tun_log: str = "",
    tasklist: str = "",
) -> dict[str, bool]:
    """Classify owner session activity for route-class smoke interpretation."""
    combined = "\n".join((app_log, tun_log, tasklist))
    telegram_alive = any(p.search(combined) for p in _TELEGRAM_PATTERNS)
    stealth_meta = any(p.search(combined) for p in _META_PATTERNS)
    blocked_nl_attempted = any(p.search(combined) for p in _BLOCKED_NL_PATTERNS)
    blocked_nl_failed = bool(
        re.search(r"google.*(fail|reset|closed|error|did not)", combined, re.I)
        or re.search(r"gmail.*(fail|reset|closed|error|did not)", combined, re.I)
        or re.search(r"youtube.*(fail|reset|closed|error|did not)", combined, re.I)
        or re.search(r"instagram.*(fail|reset|closed|error|did not)", combined, re.I)
        or re.search(r"blocked.*(fail|reset|closed|error)", combined, re.I)
    )
    direct_bypass_ok = any(p.search(combined) for p in _DIRECT_BYPASS_OK_PATTERNS) and not blocked_nl_attempted
    return {
        "telegram_alive": telegram_alive,
        "stealth_meta_alive": stealth_meta,
        "blocked_nl_attempted": blocked_nl_attempted,
        "blocked_nl_failed": blocked_nl_failed,
        "direct_bypass_activity": direct_bypass_ok,
    }


def classify_split_stealth_session(
    *,
    tun_log_stats: dict[str, Any] | None,
    error_endpoints: dict[str, Any] | None,
    session_signals: dict[str, bool],
) -> tuple[str, list[str]]:
    """Return (classification, notes) for split_stealth owner sessions."""
    stats = tun_log_stats or {}
    err_eps = error_endpoints or {}
    err_lines = int(stats.get("error_like_lines") or 0)
    notes: list[str] = []

    telegram_alive = session_signals.get("telegram_alive") or session_signals.get("stealth_meta_alive")
    blocked_failed = session_signals.get("blocked_nl_failed") or (
        err_lines >= 300 and telegram_alive
    )
    nl_direct_dominant = (
        err_eps.get("top_error_endpoint_category") in {"relay_or_web_tls", "unknown"}
        and float(err_eps.get("top_error_endpoint_share") or 0) >= 0.35
        and err_lines >= 200
    )

    if telegram_alive:
        notes.append(CLASS_TELEGRAM_STEALTH_ALIVE)

    if session_signals.get("direct_bypass_activity") and not session_signals.get("blocked_nl_attempted"):
        notes.append(CLASS_DIRECT_BYPASS_MASKS)

    if blocked_failed or nl_direct_dominant:
        notes.append(CLASS_NL_DIRECT_ROUTE_FAIL)

    if telegram_alive and (blocked_failed or nl_direct_dominant):
        return CLASS_SPLIT_STEALTH_PARTIAL, notes

    if blocked_failed or nl_direct_dominant:
        return CLASS_NL_DIRECT_ROUTE_FAIL, notes

    return "", notes


def detect_forbidden_apps(
    *,
    app_log: str = "",
    tun_log: str = "",
    tasklist: str = "",
    profile: dict[str, Any] | None = None,
) -> dict[str, bool]:
    combined = "\n".join((app_log, tun_log, tasklist))
    telegram = any(p.search(combined) for p in _TELEGRAM_PATTERNS)
    meta = any(p.search(combined) for p in _META_PATTERNS)
    if profile:
        name = str(profile.get("profile_name") or "").lower()
        if "telegram" in name:
            telegram = True
        if any(x in name for x in ("instagram", "meta", "facebook")):
            meta = True
        if profile.get("relay2_proxy_count", 0) > 0 and variant_hint_direct_basic(profile):
            pass
    return {"telegram": telegram, "instagram_or_meta": meta}


def variant_hint_direct_basic(profile: dict[str, Any]) -> bool:
    name = str(profile.get("profile_name") or "").lower()
    return "direct basic" in name


def direct_basic_has_relay_stealth(profile: dict[str, Any]) -> bool:
    relay2 = int(profile.get("relay2_proxy_count") or 0)
    stealth_bal = any(
        "stealth" in str(b).lower()
        for b in (profile.get("balancer_names") or [])
    )
    lab_relay2 = bool(profile.get("lab_relay2_only"))
    return relay2 > 0 or stealth_bal or lab_relay2


def classify_invalid_reasons(
    *,
    variant: str,
    profile_name: str | None,
    profile: dict[str, Any],
    mode: dict[str, Any],
    forbidden_apps: dict[str, bool],
    error_endpoints: dict[str, Any] | None = None,
    tun_lifecycle: dict[str, Any] | None = None,
) -> list[str]:
    reasons: list[str] = []

    if not profile_name_matches_variant(profile_name, variant):
        if is_legacy_profile_name(profile_name) or (
            variant == "direct_basic" and PROFILE_LABEL_SPLIT_STEALTH in str(profile_name or "")
        ):
            reasons.append(INVALID_WRONG_PROFILE)
        elif profile_name:
            reasons.append(INVALID_WRONG_PROFILE)

    if external_routing_overlay_active(mode):
        reasons.append(INVALID_ROUTING_OVERLAY)

    if variant == "direct_basic":
        if forbidden_apps.get("telegram"):
            reasons.append(INVALID_FORBIDDEN_APP)
        if forbidden_apps.get("instagram_or_meta"):
            reasons.append(f"{INVALID_FORBIDDEN_APP}_META")
        if direct_basic_has_relay_stealth(profile):
            reasons.append(INVALID_PROFILE_RELAY2)

    if variant == "direct_basic" and error_endpoints:
        cat = str(error_endpoints.get("top_error_endpoint_category") or "")
        share = float(error_endpoints.get("top_error_endpoint_share") or 0)
        total = int(error_endpoints.get("endpoint_error_total") or 0)
        if total >= 200 and share >= 0.4:
            if cat in {"relay_or_web_tls", "telegram"} or profile.get("relay2_proxy_count", 0) > 0:
                reasons.append(INVALID_RELAY_STEALTH_PATH)

    return reasons


def evaluate_nl_canary_smoke(
    *,
    variant: str,
    profile_name: str | None,
    profile: dict[str, Any],
    mode: dict[str, Any],
    tun_lifecycle: dict[str, Any] | None = None,
    tun_log_stats: dict[str, Any] | None = None,
    error_endpoints: dict[str, Any] | None = None,
    app_log: str = "",
    tun_log: str = "",
    tasklist: str = "",
    allow_evaluation: bool = False,
) -> SmokeGuardResult:
    """Return guard verdict. Invalid smoke → NOT_TESTED_INVALID_SMOKE (never PASS/FAIL)."""
    forbidden = detect_forbidden_apps(
        app_log=app_log, tun_log=tun_log, tasklist=tasklist, profile=profile
    )
    session_signals = detect_session_signals(app_log=app_log, tun_log=tun_log, tasklist=tasklist)
    invalid_reasons = classify_invalid_reasons(
        variant=variant,
        profile_name=profile_name,
        profile=profile,
        mode=mode,
        forbidden_apps=forbidden,
        error_endpoints=error_endpoints,
        tun_lifecycle=tun_lifecycle,
    )

    tun = tun_lifecycle or {}
    stats = tun_log_stats or {}
    checks: dict[str, Any] = {
        "expected_profile_name": VARIANT_EXPECTED_PROFILE.get(variant),
        "active_profile_name": profile_name,
        "profile_name_ok": profile_name_matches_variant(profile_name, variant),
        "external_routing_overlay": external_routing_overlay_active(mode),
        "use_routing": mode.get("use_routing"),
        "selected_routing_rule": mode.get("routing_profile"),
        "forbidden_apps": forbidden,
        "tun_startup_healthy": bool(
            tun.get("interface_up_ok") or tun.get("dns_set_ok") or stats.get("success_hint_lines", 0) > 0
        ),
        "dns_set_ok": bool(tun.get("dns_set_ok")),
        "dns_set_fail": bool(tun.get("dns_set_fail")),
        "error_like_lines": stats.get("error_like_lines"),
        "relay2_proxy_count": profile.get("relay2_proxy_count"),
        "balancer_names": profile.get("balancer_names"),
        "top_error_endpoint_category": (error_endpoints or {}).get("top_error_endpoint_category"),
        "top_error_endpoint_share": (error_endpoints or {}).get("top_error_endpoint_share"),
        "session_signals": session_signals,
    }

    notes: list[str] = []
    acceptable = not invalid_reasons
    verdict = VERDICT_NOT_TESTED
    classification = ""

    if variant == "split_stealth" and acceptable:
        classification, class_notes = classify_split_stealth_session(
            tun_log_stats=stats,
            error_endpoints=error_endpoints,
            session_signals=session_signals,
        )
        checks["session_classification"] = classification or None
        notes.extend(class_notes)

    if not acceptable:
        notes.append(
            "Smoke input rejected — wrong profile, routing overlay, or forbidden apps. "
            "NL canary smoke was NOT tested; do not classify as NL PASS/FAIL."
        )
    elif allow_evaluation:
        err_lines = int(stats.get("error_like_lines") or 0)
        if variant == "split_stealth" and classification == CLASS_SPLIT_STEALTH_PARTIAL:
            verdict = VERDICT_PARTIAL
            notes.append(
                "Split Stealth PARTIAL: stealth/Telegram alive but NL-direct/blocked path failed. "
                "Normal RU/direct-bypass sites do not prove NL."
            )
        elif variant == "split_stealth" and classification == CLASS_NL_DIRECT_ROUTE_FAIL:
            verdict = VERDICT_FAIL
            notes.append("NL direct / blocked-site route class failed — not acceptance-ready.")
        elif err_lines > 800:
            verdict = VERDICT_FAIL
            notes.append("High error volume during otherwise valid smoke input.")
        elif err_lines > 300:
            verdict = VERDICT_PARTIAL
            if variant == "direct_basic":
                notes.append("Elevated errors — NL direct path unstable; not PASS.")
        elif variant == "direct_basic" and session_signals.get("direct_bypass_activity"):
            verdict = VERDICT_PARTIAL
            notes.append(CLASS_DIRECT_BYPASS_MASKS + ": only direct-bypass activity seen; use NL proof targets.")
        else:
            verdict = VERDICT_PASS
            notes.append("Smoke input acceptable; session metrics within expected bounds.")
    else:
        notes.append("Smoke input acceptable; run full evaluation with --evaluate.")

    return SmokeGuardResult(
        variant=variant,
        acceptable_smoke_input=acceptable,
        invalid_reasons=invalid_reasons,
        verdict=verdict if acceptable else VERDICT_NOT_TESTED,
        checks=checks,
        notes=notes,
    )


def generator_smoke_metadata(variant: str) -> dict[str, Any]:
    """Metadata fields embedded in generated canary artifacts."""
    from nl_canary_route_classes import route_class_metadata  # noqa: WPS433

    base = {
        "expected_profile_name": VARIANT_EXPECTED_PROFILE.get(variant),
        "expected_variant": variant,
        "forbidden_apps_for_variant": sorted(FORBIDDEN_APPS_DIRECT_BASIC)
        if variant == "direct_basic"
        else [],
        "requires_external_routing_overlay_off": True,
        "deprecated_legacy_profile_name": PROFILE_LABEL_LEGACY,
    }
    base.update(route_class_metadata(variant))
    return base
