#!/usr/bin/env python3
"""Prepare a redacted new-node registry entry — NODE-ONBOARD-NEW-PROD-PATH-001.

Generates a STAGING, redacted registry entry for a new production-path node into
.local/ (git-ignored by convention). It NEVER writes the production registry.

HARD SAFETY:
    * Output goes ONLY to .local/ (or an explicit --out-dir for tests).
    * Writing to the production registry is intentionally NOT implemented.
    * Inputs are scanned for secret-looking values and rejected (no UUIDs, no
      vless/vmess URLs, no tokens/keys in node_id/provider_label).
    * Generated node is staging / canary_percent=0 / delivery_path_eligible=false
      so it cannot count as capacity or be selected for production.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from validate_vpn_node_registry import (
    GROUPS,
    scan_secrets,
    validate_registry,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = ROOT / ".local"

# Production registry path is referenced ONLY to refuse writing to it.
PROD_REGISTRY = ROOT / "ops" / "config" / "vpn_node_registry.yaml"

FORBIDDEN_GROUPS_FOR_NEW_PROD = frozenset({"LAB_OWNER", "FALLBACK_MANUAL"})


def build_new_node_entry(
    *,
    node_id: str,
    country: str,
    region: str = "EU",
    role: str = "exit",
    provider_label: str = "redacted-vps-new",
    groups: list[str] | None = None,
) -> dict[str, Any]:
    if groups is None:
        groups = ["INTL_DIRECT_ACTIVE"]

    # Reject secret-looking inputs.
    joined = " ".join([node_id, country, region, role, provider_label, *groups])
    secret_hits = scan_secrets(joined)
    if secret_hits:
        raise ValueError("secret-looking input rejected: " + "; ".join(secret_hits))

    for g in groups:
        if g not in GROUPS:
            raise ValueError(f"invalid group {g!r}; expected one of {sorted(GROUPS)}")
        if g in FORBIDDEN_GROUPS_FOR_NEW_PROD:
            raise ValueError(f"group {g!r} not allowed for a new production path")

    return {
        "node_id": node_id,
        "display_name": f"New production exit {node_id} (staging — pending acceptance)",
        "region": region,
        "country": country,
        "city": "redacted",
        "provider_label": provider_label,
        "role": role,
        "status": "staging",
        "delivery_path_eligible": False,
        "groups": list(groups),
        "capacity": {
            "max_active_configs": None,
            "max_concurrent_sessions": None,
            "max_mbps": None,
            "reserved_headroom_percent": 40,
        },
        "health": {
            "monitor_status": "unknown",
            "last_smoke_status": "pending",
            "last_smoke_at": None,
            "last_owner_test_status": "pending",
            "last_owner_test_at": None,
        },
        "rollout": {
            "cohort_weight": 0,
            "canary_percent": 0,
            "allow_new_assignments": False,
            "drain_after": None,
        },
        "client_support": {
            "happ_supported": "pending",
            "karing_supported": False,
            "v2rayn_supported": False,
            "mobile_supported": False,
        },
        "owner_approval_required": True,
        "notes": (
            "New candidate production path. Provider/DC/ASN must differ from "
            "lv-exit-1. Promote to active + delivery_path_eligible=true ONLY after "
            "acceptance P0 PASS + owner sign-off."
        ),
    }


def entry_to_yaml(entry: dict[str, Any]) -> str:
    header = (
        "# Generated staging node entry (redacted) — NODE-ONBOARD-NEW-PROD-PATH-001\n"
        "# Do NOT paste secrets. Do NOT write into ops/config/vpn_node_registry.yaml\n"
        "# directly; promotion is a separate owner-approved task.\n"
    )
    body = yaml.safe_dump([entry], sort_keys=False, allow_unicode=True)
    return header + body


def validate_entry(entry: dict[str, Any]) -> list[str]:
    """Validate the entry within a minimal registry doc; return errors."""
    doc = {
        "schema_version": 1,
        "capacity_policy": {"delivery_path_gate_300": 2},
        "nodes": [entry],
    }
    raw = yaml.safe_dump(doc)
    errors, _ = validate_registry(doc, raw)
    return errors


def write_entry(entry: dict[str, Any], out_dir: Path) -> Path:
    if out_dir.resolve() == PROD_REGISTRY.parent.resolve():
        raise ValueError("refusing to write into the production registry directory")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"new_node_registry_entry_{entry['node_id']}.yaml"
    path.write_text(entry_to_yaml(entry), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare redacted staging node entry (.local only; never prod registry)"
    )
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--country", required=True, help="ISO country bucket (non-secret)")
    parser.add_argument("--region", default="EU")
    parser.add_argument("--role", default="exit", choices=["exit", "relay"])
    parser.add_argument("--provider-label", default="redacted-vps-new")
    parser.add_argument(
        "--groups",
        nargs="+",
        default=["INTL_DIRECT_ACTIVE"],
        help="Registry group(s); LAB_OWNER/FALLBACK_MANUAL not allowed",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="Print only; do not write")
    args = parser.parse_args(argv)

    try:
        entry = build_new_node_entry(
            node_id=args.node_id,
            country=args.country,
            region=args.region,
            role=args.role,
            provider_label=args.provider_label,
            groups=args.groups,
        )
        errors = validate_entry(entry)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if errors:
        print("ERROR: generated entry failed validation:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"prepared staging entry: {entry['node_id']} "
          f"(status={entry['status']}, delivery_path_eligible={entry['delivery_path_eligible']})")

    if args.dry_run:
        print(entry_to_yaml(entry))
        print("dry-run: no files written")
        return 0

    path = write_entry(entry, args.out_dir)
    print(f"wrote: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
