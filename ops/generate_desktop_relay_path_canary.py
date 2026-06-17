#!/usr/bin/env python3
"""Owner/staging desktop relay-path canary — CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-001.

Produces a redacted owner/staging plan that EXCLUDES the unstable relay path found
in report(10) and KEEPS the healthy relay path, while preserving BenderVPN Auto /
Candidate-D semantics and the stealth split.

HARD SAFETY (read before extending):
    * Does NOT mutate production, Remna, Caddy, subscription, template, or the registry file.
    * Writes ONLY redacted artifacts under .local/ (never committed).
    * Prints/writes endpoint identities ONLY as redacted tokens (ep_<hash>:port).
    * The actual importable JSON is built by the owner with the existing
      `ops/generate_happ_relay2_lab_profile.py` from their held subscription —
      this tool never touches real UUIDs/endpoints.

Output (default .local/):
    desktop_relay_path_canary.json
    desktop_relay_path_canary.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_OPS = Path(__file__).resolve().parent
ROOT = _OPS.parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from balancer_selectors import (  # noqa: E402
    INTL_BALANCER_TAG,
    INTL_STEALTH_BALANCER_TAG,
    RELAY1_SELECTOR,
    RELAY2_SELECTOR,
)
from relay_latency_probe import RELAY1_IP, RELAY2_IP  # noqa: E402
from validate_vpn_node_registry import DEFAULT_REGISTRY  # noqa: E402
from vpn_node_selector import load_validated_registry  # noqa: E402

DEFAULT_OUT_DIR = ROOT / ".local"

PROFILE_LABEL = (
    "BenderVPN Desktop Relay Path Canary — owner/staging only — "
    "excludes unstable relay path — do NOT refresh normal subscription"
)

IMPORT_INSTRUCTIONS = [
    "Keep your normal 'BenderVPN Auto' profile untouched (this is a NEW profile).",
    "Build the importable JSON locally from your held subscription:",
    "  python ops/generate_happ_relay2_lab_profile.py --from-json <owner_sub.json> "
    "--write-json .local/desktop_relay2_only.json",
    "In Happ, add a NEW profile and import .local/desktop_relay2_only.json.",
    "Name it exactly: 'BenderVPN Desktop Relay Path Canary'.",
    "DISABLE auto-update / subscription refresh on this profile.",
    "Connect in TUN; routing profile BenderVPN RU; system proxy OFF.",
    "Run a 10–15 min long-session test (Telegram + Google Docs/Gmail + a heavy site).",
]

ROLLBACK_INSTRUCTIONS = [
    "Switch back to the normal 'BenderVPN Auto' profile in the client.",
    "Delete the desktop canary profile if no longer needed.",
    "No server change was made by this tool; nothing to revert server-side.",
]

GUARANTEES = [
    "Excludes the unstable relay path (relay #1) from both Intl_Direct and Intl_Stealth.",
    "Keeps the healthy relay path (relay #2) for all international + stealth traffic.",
    "Preserves the stealth split (TG/Meta/IG stay on the stealth balancer).",
    "Removes relay #1 from in-core direct (anti-loop) rules; keeps relay #2 self-bypass.",
    "No geoip:ru in DirectIp; no relay IP leak into Happ DirectIp; no FallbackTag=direct.",
    "No flat Super_Balancer catch-all; no user-facing server picker.",
]


def _token(ip: str, port: str = "443") -> str:
    return f"ep_{hashlib.sha1(ip.encode('utf-8')).hexdigest()[:8]}:{port}"


def build_canary_plan(registry: dict[str, Any]) -> dict[str, Any]:
    bad_token = _token(RELAY1_IP)
    healthy_token = _token(RELAY2_IP)

    nodes = {n.get("node_id"): n for n in registry.get("nodes") or [] if isinstance(n, dict)}
    bad_node = nodes.get("ru-relay-1") or {}
    healthy_node = nodes.get("ru-relay-2") or {}

    return {
        "task": "CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-001",
        "label": PROFILE_LABEL,
        "owner_only": True,
        "do_not_refresh": True,
        "production_default_changed": False,
        "diagnostic_ab_not_guaranteed_fix": (
            bad_node.get("shared_upstream_group")
            and bad_node.get("shared_upstream_group") == healthy_node.get("shared_upstream_group")
        ),
        "bad_path": {
            "endpoint_token": bad_token,
            "exclude_outbounds": list(RELAY1_SELECTOR),
            "node_id": "ru-relay-1",
            "registry_monitor_status": (bad_node.get("health") or {}).get("monitor_status"),
            "registry_incident": bad_node.get("incident", False),
            "exclude_from_desktop_canary": bad_node.get("exclude_from_desktop_canary", False),
            "architecture_compliance": bad_node.get("architecture_compliance"),
            "shared_upstream_group": bad_node.get("shared_upstream_group"),
            "evidence": "report(10) ~80.3% of that client's resets (session/balancer-specific; server-side identical to relay2)",
        },
        "healthy_path": {
            "endpoint_token": healthy_token,
            "keep_outbounds": list(RELAY2_SELECTOR),
            "node_id": "ru-relay-2",
            "registry_monitor_status": (healthy_node.get("health") or {}).get("monitor_status"),
            "desktop_canary_path": healthy_node.get("desktop_canary_path", False),
            "architecture_compliance": healthy_node.get("architecture_compliance"),
            "shared_upstream_group": healthy_node.get("shared_upstream_group"),
        },
        "pin_balancers": [INTL_BALANCER_TAG, INTL_STEALTH_BALANCER_TAG],
        "guarantees": GUARANTEES,
        "build_tool": "ops/generate_happ_relay2_lab_profile.py",
        "import_instructions": IMPORT_INSTRUCTIONS,
        "rollback_instructions": ROLLBACK_INSTRUCTIONS,
        "server_repair_owner_phrase": "APPROVE DESKTOP RELAY SERVER REPAIR DEPLOY",
        "canary_import_owner_phrase": "APPROVE OWNER RELAY-PATH CANARY IMPORT",
    }


def format_markdown(plan: dict[str, Any]) -> str:
    bad = plan["bad_path"]
    good = plan["healthy_path"]
    lines = [
        f"# {plan['label']}",
        "",
        f"- task: {plan['task']}",
        f"- owner_only: {plan['owner_only']}",
        f"- do_not_refresh: {plan['do_not_refresh']}",
        f"- production_default_changed: {plan['production_default_changed']}",
        "",
        "## Exclude (unstable relay path)",
        "",
        f"- endpoint: `{bad['endpoint_token']}`",
        f"- node_id: {bad['node_id']} (monitor_status={bad['registry_monitor_status']}, incident={bad['registry_incident']})",
        f"- outbounds to drop: {', '.join(bad['exclude_outbounds'])}",
        f"- evidence: {bad['evidence']}",
        "",
        "## Keep (healthy relay path)",
        "",
        f"- endpoint: `{good['endpoint_token']}`",
        f"- node_id: {good['node_id']} (monitor_status={good['registry_monitor_status']})",
        f"- outbounds to keep: {', '.join(good['keep_outbounds'])}",
        f"- balancers pinned: {', '.join(plan['pin_balancers'])}",
        "",
        "## Guarantees",
        "",
    ]
    lines += [f"- {g}" for g in plan["guarantees"]]
    lines += ["", "## Build + import", "", f"Build tool: `{plan['build_tool']}`", ""]
    for i in plan["import_instructions"]:
        lines.append(f"1. {i}")
    lines += ["", "## Rollback", ""]
    lines += [f"- {r}" for r in plan["rollback_instructions"]]
    lines += [
        "",
        "## Owner approval phrases",
        "",
        f"- Import canary client-side: **{plan['canary_import_owner_phrase']}**",
        f"- Server-side xray restore on relay #1 (all-users prod action): **{plan['server_repair_owner_phrase']}**",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate owner/staging desktop relay-path canary plan (.local only)"
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="print summary; no files written")
    args = parser.parse_args(argv)

    try:
        registry = load_validated_registry(args.registry)
        plan = build_canary_plan(registry)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(PROFILE_LABEL)
    print(f"  exclude: {plan['bad_path']['endpoint_token']} ({', '.join(plan['bad_path']['exclude_outbounds'])})")
    print(f"  keep:    {plan['healthy_path']['endpoint_token']} ({', '.join(plan['healthy_path']['keep_outbounds'])})")
    print(f"  production_default_changed: {plan['production_default_changed']}")

    if args.dry_run:
        print("  dry-run: no files written")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "desktop_relay_path_canary.json"
    md_path = args.out_dir / "desktop_relay_path_canary.md"
    json_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(format_markdown(plan), encoding="utf-8")
    print(f"  wrote: {json_path}")
    print(f"  wrote: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
