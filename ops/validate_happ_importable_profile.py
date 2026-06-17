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
    args = parser.parse_args(argv)

    try:
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
