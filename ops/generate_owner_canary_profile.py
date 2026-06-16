#!/usr/bin/env python3
"""Owner-only canary profile generator — CLIENT-STABILITY-OWNER-CANARY-PROFILE-001.

Gives the owner a practical stability/speed isolation path WITHOUT changing any
production default.

HARD SAFETY (read before extending):
    * Does NOT mutate production.
    * Does NOT change the subscription generator defaults.
    * Does NOT write live Remna / subscription / Caddy templates.
    * Writes ONLY redacted local artifacts under .local/ (git-ignored by
      convention; never committed).
    * The redacted repo registry contains NO real endpoints/UUIDs/URLs, so this
      tool produces an owner-only PLAN + IMPORT RUNBOOK with placeholders and a
      required-owner-input section. It never prints or writes secrets.

Output (default .local/):
    owner_canary_profile.json
    owner_canary_profile.md

The profile is explicitly labelled owner-only and "do NOT refresh subscription"
because refreshing would re-pull the production default node set.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from validate_vpn_node_registry import DEFAULT_REGISTRY
from vpn_node_selector import _canary_eligible, _is_suspect, _node_groups, load_validated_registry

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = ROOT / ".local"

PROFILE_LABEL = "BenderVPN Owner Canary — do NOT refresh subscription"

OWNER_ONLY_WARNING = (
    "OWNER-ONLY stability isolation. This is NOT a production default and must "
    "not be mass-issued. Do NOT refresh the subscription on this profile — a "
    "refresh re-pulls the normal BenderVPN Auto node set."
)

IMPORT_INSTRUCTIONS = [
    "In Happ/Karing, add a NEW profile (do not overwrite the normal BenderVPN profile).",
    "Name it exactly: 'BenderVPN Owner Canary — do NOT refresh'.",
    "Paste the owner-held relay isolation config (see required_owner_input).",
    "DISABLE auto-update / auto-refresh for this profile.",
    "Connect and run the owner smoke (sleep/wake + active traffic) on this profile only.",
]

ROLLBACK_INSTRUCTIONS = [
    "Switch back to the normal 'BenderVPN' profile in the client.",
    "Delete the owner canary profile if no longer needed.",
    "No production change was made; nothing to revert on the server.",
]

REQUIRED_OWNER_INPUT = [
    "The owner-held isolation config string (relay2-only or new-node), kept "
    "locally in .secrets/diagnostics/ — NEVER pasted into git or chat.",
    "Confirmation the profile is added as NEW (not overwriting BenderVPN Auto).",
]


@dataclass
class CanaryCandidate:
    node_id: str
    role: str
    region: str
    country: str
    basis: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "role": self.role,
            "region": self.region,
            "country": self.country,
            "basis": self.basis,
        }


@dataclass
class OwnerCanaryProfile:
    label: str = PROFILE_LABEL
    owner_only: bool = True
    do_not_refresh: bool = True
    production_default_changed: bool = False
    candidates: list[CanaryCandidate] = field(default_factory=list)
    excluded: list[dict[str, str]] = field(default_factory=list)
    import_instructions: list[str] = field(default_factory=list)
    rollback_instructions: list[str] = field(default_factory=list)
    required_owner_input: list[str] = field(default_factory=list)
    warning: str = OWNER_ONLY_WARNING
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "owner_only": self.owner_only,
            "do_not_refresh": self.do_not_refresh,
            "production_default_changed": self.production_default_changed,
            "warning": self.warning,
            "candidates": [c.to_dict() for c in self.candidates],
            "excluded": self.excluded,
            "import_instructions": self.import_instructions,
            "rollback_instructions": self.rollback_instructions,
            "required_owner_input": self.required_owner_input,
            "dry_run": self.dry_run,
        }


def select_owner_canary_candidates(
    registry: dict[str, Any],
    *,
    include_nl: bool = False,
    owner_approval: bool = False,
) -> tuple[list[CanaryCandidate], list[dict[str, str]]]:
    """Pick stable owner-canary candidates, excluding suspect relay1.

    Returns (candidates, excluded_with_reasons).
    """
    candidates: list[CanaryCandidate] = []
    excluded: list[dict[str, str]] = []

    for node in registry.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("node_id", "?"))
        role = str(node.get("role", "?"))
        region = str(node.get("region", "?"))
        country = str(node.get("country", "?"))
        status = node.get("status")
        groups = _node_groups(node)

        # Exclude suspect (relay1) by default for owner canary — stability first.
        if _is_suspect(node):
            excluded.append({"node_id": node_id, "reason": "suspect; excluded for stability"})
            continue

        # Exclude blocked statuses outright.
        if status in {"failed", "decommissioned", "draining"}:
            excluded.append({"node_id": node_id, "reason": f"status={status}"})
            continue

        # Backup edge is not a delivery candidate.
        if role == "backup" or "FALLBACK_MANUAL" in groups:
            excluded.append({"node_id": node_id, "reason": "backup/fallback, not delivery"})
            continue

        # NL handling: only when registry says canary-ready AND owner approves.
        if country == "NL" and role == "exit":
            if include_nl and owner_approval and _canary_eligible(node):
                candidates.append(
                    CanaryCandidate(node_id, role, region, country, "NL canary-ready + owner approval")
                )
            else:
                excluded.append(
                    {"node_id": node_id, "reason": "NL not included (needs canary-ready + --include-nl + --owner-approval)"}
                )
            continue

        # Preferred owner-only stable candidate: the lab relay2 profile.
        if "LAB_OWNER" in groups and status in {"staging", "canary", "active"}:
            candidates.append(
                CanaryCandidate(node_id, role, region, country, "owner lab profile (relay2-only)")
            )
            continue

        # Any other staging/canary-ready node is a candidate.
        if status in {"staging", "canary"} or _canary_eligible(node):
            candidates.append(
                CanaryCandidate(node_id, role, region, country, f"status={status}/canary-ready")
            )
            continue

        # Active production exits are intentionally NOT used for owner isolation —
        # the point is to isolate AWAY from the suspect production pool.
        excluded.append(
            {"node_id": node_id, "reason": "active production default; not isolation candidate"}
        )

    return candidates, excluded


def build_owner_canary_profile(
    registry: dict[str, Any],
    *,
    include_nl: bool = False,
    owner_approval: bool = False,
    dry_run: bool = True,
) -> OwnerCanaryProfile:
    candidates, excluded = select_owner_canary_candidates(
        registry, include_nl=include_nl, owner_approval=owner_approval
    )
    return OwnerCanaryProfile(
        candidates=candidates,
        excluded=excluded,
        import_instructions=list(IMPORT_INSTRUCTIONS),
        rollback_instructions=list(ROLLBACK_INSTRUCTIONS),
        required_owner_input=list(REQUIRED_OWNER_INPUT),
        dry_run=dry_run,
    )


def format_profile_markdown(profile: OwnerCanaryProfile) -> str:
    lines = [
        f"# {profile.label}",
        "",
        f"> {profile.warning}",
        "",
        f"- owner_only: {profile.owner_only}",
        f"- do_not_refresh: {profile.do_not_refresh}",
        f"- production_default_changed: {profile.production_default_changed}",
        "",
        "## Candidates (owner-only isolation)",
        "",
        "| Node | Role | Geo | Basis |",
        "|------|------|-----|-------|",
    ]
    if profile.candidates:
        for c in profile.candidates:
            lines.append(f"| {c.node_id} | {c.role} | {c.region}/{c.country} | {c.basis} |")
    else:
        lines.append("| (none) | - | - | no safe candidate; see required_owner_input |")
    lines.append("")
    lines.append("## Excluded")
    lines.append("")
    for e in profile.excluded:
        lines.append(f"- {e['node_id']}: {e['reason']}")
    lines.append("")
    lines.append("## Import instructions")
    lines.append("")
    for i in profile.import_instructions:
        lines.append(f"1. {i}")
    lines.append("")
    lines.append("## Rollback")
    lines.append("")
    for r in profile.rollback_instructions:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("## Required owner input")
    lines.append("")
    for r in profile.required_owner_input:
        lines.append(f"- {r}")
    lines.append("")
    return "\n".join(lines)


def write_profile(profile: OwnerCanaryProfile, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "owner_canary_profile.json"
    md_path = out_dir / "owner_canary_profile.md"
    json_path.write_text(
        json.dumps(profile.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    md_path.write_text(format_profile_markdown(profile), encoding="utf-8")
    return [json_path, md_path]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate owner-only canary profile plan (.local only; no prod mutation)"
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan summary only; do not write files",
    )
    parser.add_argument(
        "--include-nl",
        action="store_true",
        help="Consider NL only if registry says canary-ready (needs --owner-approval)",
    )
    parser.add_argument(
        "--owner-approval",
        action="store_true",
        help="Owner approves NL inclusion if canary-ready",
    )
    args = parser.parse_args(argv)

    try:
        registry = load_validated_registry(args.registry)
        profile = build_owner_canary_profile(
            registry,
            include_nl=args.include_nl,
            owner_approval=args.owner_approval,
            dry_run=args.dry_run,
        )
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Console: redacted summary only (node IDs/roles/geo, never secrets).
    print(PROFILE_LABEL)
    print(f"  candidates: {[c.node_id for c in profile.candidates] or '[]'}")
    print(f"  excluded: {[e['node_id'] for e in profile.excluded] or '[]'}")
    print(f"  production_default_changed: {profile.production_default_changed}")

    if args.dry_run:
        print("  dry-run: no files written")
        return 0

    paths = write_profile(profile, args.out_dir)
    for p in paths:
        print(f"  wrote: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
