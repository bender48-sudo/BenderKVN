#!/usr/bin/env python3
"""Happ importable profile validator — NL-CANARY-IMPORT-ARTIFACT-FIX-001.

Fail-closed: metadata/runbook JSON must NEVER pass as an importable Happ profile.
Accepts only known sing-box/Xray subscription shapes used in this repo.

HARD SAFETY:
    * Redacted summary only on stdout (counts/tags, no UUIDs/endpoints/tokens).
    * No network calls.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from subscription_fetch import (  # noqa: E402
    happ_batch_parseable,
    outbound_endpoint,
    xray_config_root,
)

from balancer_selectors import INTL_BALANCER_TAG, INTL_STEALTH_BALANCER_TAG  # noqa: E402
from nl_canary_profile_builder import (  # noqa: E402
    PROFILE_LABEL_DIRECT_BASIC,
    PROFILE_LABEL_SPLIT_STEALTH,
    google_routes_via_stealth,
    nl_proxy_tags,
    relay1_proxy_tags,
    relay2_proxy_tags,
)

# Metadata/runbook markers — presence of any ⇒ NOT importable.
METADATA_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_type",
        "criteria_scorecard",
        "criteria_standard",
        "smoke_checklist",
        "record_template",
        "synthetic_canary_preview",
        "traffic_smoke_status",
        "promotion_on_pass",
        "expected_behavior",
        "failure_export",
        "pass_criteria",
        "partial_criteria",
        "fail_criteria",
        "import_instructions",
        "remaining_blockers",
        "egress_independence",
        "independent_exit_paths_now",
        "candidate_counts_as_capacity",
        "do_not_import_this_file",
    }
)

METADATA_ARTIFACT_TYPE = "metadata_runbook_not_importable"

SECRET_PATTERNS = (
    (re.compile(r"vless://", re.I), "vless:// URL"),
    (re.compile(r"vmess://", re.I), "vmess:// URL"),
    (re.compile(r"https?://[^\s\"']+/api/sub/", re.I), "subscription URL"),
    (re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I), "UUID"),
)


@dataclass
class ProfileValidation:
    ok: bool
    kind: str  # importable_profile | metadata_runbook | invalid
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "kind": self.kind,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": self.summary,
        }


def _proxy_outbounds(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ob in cfg.get("outbounds") or []:
        if not isinstance(ob, dict):
            continue
        if ob.get("protocol") == "vless" and str(ob.get("tag") or "").startswith("proxy"):
            out.append(ob)
    return out


def is_metadata_runbook(doc: Any) -> bool:
    """True when doc looks like generator metadata, not a client VPN config."""
    if not isinstance(doc, dict):
        return False
    if doc.get("artifact_type") == METADATA_ARTIFACT_TYPE:
        return True
    if doc.get("do_not_import_this_file") is True:
        return True
    if doc.get("importable_profile") is False and "criteria_scorecard" in doc:
        return True
    hits = METADATA_TOP_LEVEL_KEYS & set(doc.keys())
    # Strong markers — any one is enough.
    strong = {
        "criteria_scorecard",
        "smoke_checklist",
        "record_template",
        "synthetic_canary_preview",
        "traffic_smoke_status",
    }
    if hits & strong:
        return True
    return False


def scan_commit_risk(raw: str) -> list[str]:
    """Detect patterns that must not be committed (for CI guard)."""
    hits: list[str] = []
    for pat, label in SECRET_PATTERNS:
        if pat.search(raw):
            hits.append(label)
    return hits


def validate_importable_profile(doc: Any, *, require_routing: bool = True) -> ProfileValidation:
    """Validate a Happ-importable Xray/sing-box profile shape."""
    if is_metadata_runbook(doc):
        return ProfileValidation(
            ok=False,
            kind="metadata_runbook",
            errors=["document is metadata/runbook JSON — DO NOT import into Happ"],
            summary={"importable": False},
        )

    try:
        cfg = xray_config_root(doc)
    except ValueError as exc:
        return ProfileValidation(
            ok=False,
            kind="invalid",
            errors=[str(exc)],
            summary={"importable": False},
        )

    errors: list[str] = []
    warnings: list[str] = []

    outbounds = cfg.get("outbounds")
    if not isinstance(outbounds, list) or not outbounds:
        errors.append("missing or empty outbounds[]")

    proxies = _proxy_outbounds(cfg)
    if not proxies:
        errors.append("no vless proxy outbounds (tag proxy*)")

    parseable = 0
    for ob in proxies:
        ok, err = happ_batch_parseable(ob)
        if ok:
            parseable += 1
        else:
            errors.append(f"{ob.get('tag')}: not Happ-parseable ({err})")

    routing = cfg.get("routing")
    if require_routing:
        if not isinstance(routing, dict):
            errors.append("missing routing object")
        else:
            balancers = routing.get("balancers")
            if not isinstance(balancers, list) or not balancers:
                errors.append("missing routing.balancers[]")

    remarks = str(cfg.get("remarks") or "")
    if "do not refresh" not in remarks.lower() and "canary" not in remarks.lower():
        warnings.append("remarks missing CANARY / do-not-refresh marker")

    node_labels: dict[str, int] = {}
    for ob in proxies:
        addr, port = outbound_endpoint(ob)
        label = "UNKNOWN"
        if addr:
            # Redacted bucket — never print raw address.
            from subscription_fetch import node_label  # noqa: WPS433

            label = node_label(addr, port)
        node_labels[label] = node_labels.get(label, 0) + 1

    summary = {
        "importable": not errors,
        "outbound_count": len(outbounds or []),
        "vless_proxy_count": len(proxies),
        "happ_parseable_vless": parseable,
        "has_routing": isinstance(routing, dict),
        "balancer_count": len((routing or {}).get("balancers") or [])
        if isinstance(routing, dict)
        else 0,
        "node_label_buckets": node_labels,
        "remarks_present": bool(remarks),
    }

    return ProfileValidation(
        ok=not errors,
        kind="importable_profile" if not errors else "invalid",
        errors=errors,
        warnings=warnings,
        summary=summary,
    )


def validate_nl_canary_variant(
    doc: Any,
    variant: str,
) -> ProfileValidation:
    """Validate NL canary importable profile against smoke expectations."""
    base = validate_importable_profile(doc)
    if not base.ok:
        return base

    cfg = xray_config_root(doc)
    errors = list(base.errors)
    warnings = list(base.warnings)
    remarks = str(cfg.get("remarks") or "")

    r1 = relay1_proxy_tags(cfg)
    if r1:
        errors.append(f"relay-1 outbounds must be absent in canary: {r1}")

    if google_routes_via_stealth(cfg):
        errors.append(
            "geosite:google routes via Intl_Stealth — invalid for NL direct smoke "
            "(Gmail success would not prove NL egress)"
        )

    rules = (cfg.get("routing") or {}).get("rules") or []
    if any(r.get("fallbackTag") == "direct" for r in rules):
        errors.append("fallbackTag=direct present")

    for rule in rules:
        if rule.get("outboundTag") == "direct" and isinstance(rule.get("ip"), list):
            for ip in rule["ip"]:
                if "geoip:ru" in str(ip).lower() and "direct" in str(rule.get("outboundTag", "")):
                    pass  # geoip:ru direct bypass is OK for RU sites
                if "geoip:private" in str(ip).lower():
                    pass

    nl_tags = nl_proxy_tags(cfg)
    if not nl_tags:
        errors.append("no NL direct outbounds")

    balancers = {b.get("tag"): b for b in (cfg.get("routing") or {}).get("balancers") or []}

    if variant == "direct_basic":
        if PROFILE_LABEL_DIRECT_BASIC not in remarks:
            errors.append("remarks must match DIRECT_BASIC label")
        if relay2_proxy_tags(cfg):
            errors.append("DIRECT_BASIC must not include relay-2 outbounds")
        if INTL_STEALTH_BALANCER_TAG in balancers:
            errors.append("DIRECT_BASIC must not include Intl_Stealth balancer")
        google_tag = None
        for rule in rules:
            doms = rule.get("domain") or []
            if any("geosite:google" in str(d) for d in doms):
                google_tag = rule.get("balancerTag") or rule.get("outboundTag")
        if google_tag != INTL_BALANCER_TAG:
            errors.append("geosite:google must route via Intl_Direct for DIRECT_BASIC")
        intl = balancers.get(INTL_BALANCER_TAG)
        if intl and list(intl.get("selector") or []) != nl_tags:
            errors.append("Intl_Direct selector must be NL tags only")

    elif variant == "split_stealth":
        if PROFILE_LABEL_SPLIT_STEALTH not in remarks:
            errors.append("remarks must match SPLIT_STEALTH label")
        r2 = relay2_proxy_tags(cfg)
        if not r2:
            errors.append("SPLIT_STEALTH requires relay-2 outbounds")
        stealth = balancers.get(INTL_STEALTH_BALANCER_TAG)
        if not stealth or list(stealth.get("selector") or []) != r2:
            errors.append("Intl_Stealth selector must match relay-2 tags only")
        intl = balancers.get(INTL_BALANCER_TAG)
        if intl and list(intl.get("selector") or []) != nl_tags:
            errors.append("Intl_Direct selector must match NL tags only")
        for rule in rules:
            if rule.get("balancerTag") != INTL_BALANCER_TAG:
                continue
            hay = " ".join(str(x) for x in (rule.get("domain") or [])).lower()
            for needle in ("telegram", "instagram", "facebook"):
                if needle in hay:
                    errors.append(f"stealth app {needle!r} must not route via Intl_Direct")

    elif variant == "legacy_bad":
        if google_routes_via_stealth(cfg):
            errors.append("legacy profile: google on stealth (expected fail for smoke)")

    base.errors = errors
    base.warnings = warnings
    base.ok = not errors
    base.summary["variant"] = variant
    base.summary["google_on_stealth"] = google_routes_via_stealth(cfg)
    base.summary["relay1_tags"] = r1
    return base


def validate_file(path: Path, *, require_routing: bool = True) -> ProfileValidation:
    raw = path.read_text(encoding="utf-8")
    doc = json.loads(raw)
    result = validate_importable_profile(doc, require_routing=require_routing)
    result.summary["path"] = str(path.name)
    return result


def print_summary(result: ProfileValidation) -> None:
    print(f"kind={result.kind} ok={result.ok}")
    for k, v in result.summary.items():
        print(f"  {k}: {v}")
    for w in result.warnings:
        print(f"  WARNING: {w}")
    for e in result.errors:
        print(f"  ERROR: {e}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Happ importable profile vs metadata JSON")
    parser.add_argument("path", type=Path, help="JSON file to validate")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--allow-no-routing",
        action="store_true",
        help="accept minimal profile without routing (tests only)",
    )
    parser.add_argument(
        "--variant",
        choices=("direct_basic", "split_stealth", "legacy_bad"),
        help="NL canary smoke variant validation",
    )
    args = parser.parse_args(argv)

    try:
        if args.variant:
            raw = args.path.read_text(encoding="utf-8")
            result = validate_nl_canary_variant(json.loads(raw), args.variant)
            result.summary["path"] = str(args.path.name)
        else:
            result = validate_file(args.path, require_routing=not args.allow_no_routing)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print_summary(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
