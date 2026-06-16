#!/usr/bin/env python3
"""Shared apply guard for legacy VPN patch scripts — VPN-AUTO-CUTTING-GUARD-001.

Fail-closed gate that legacy capacity-reducing patch scripts call at the start of
their ``--apply`` path so an accidental/manual apply cannot silently collapse the
production pool before the script is migrated to the inventory-driven
architecture.

SAFETY:
    * No network, no Remna/Caddy/template/subscription calls, no secrets.
    * Reads only a CLI flag and an env opt-in.
    * Banner-only helpers never change control flow; the require_* helper fails
      closed (exit 2) when approval is absent.

See docs/VPN_PRODUCTION_GUARDRAILS.md and docs/VPN_PATCH_SCRIPT_MIGRATION_MAP.md.
"""
from __future__ import annotations

import os
import sys

GUARDRAIL_DOC = "docs/VPN_PRODUCTION_GUARDRAILS.md"
MIGRATION_DOC = "docs/VPN_PATCH_SCRIPT_MIGRATION_MAP.md"
APPROVAL_ENV = "VPN_GUARDRAIL_OWNER_APPROVED"


def guardrail_notice(
    script_name: str, *, capacity_reducing: bool, cron_managed: bool = False
) -> str:
    kind = "CAPACITY-REDUCING" if capacity_reducing else "production-mutating"
    lines = [
        f"[GUARDRAIL] {script_name}: legacy {kind} patch script.",
        f"[GUARDRAIL] Core rule: stability must NOT silently reduce capacity. "
        f"See {GUARDRAIL_DOC}.",
        f"[GUARDRAIL] Migration target: {MIGRATION_DOC} (inventory-driven apply gate).",
    ]
    if cron_managed:
        lines.append(
            "[GUARDRAIL] cron-managed: control flow unchanged this sprint; "
            "P0 migration to central guardrail pending owner approval."
        )
    return "\n".join(lines)


def print_guardrail_banner(
    script_name: str,
    *,
    capacity_reducing: bool,
    cron_managed: bool = False,
    stream=None,
) -> None:
    """Print the guardrail banner to stderr (never alters stdout payloads)."""
    out = stream if stream is not None else sys.stderr
    out.write(guardrail_notice(
        script_name, capacity_reducing=capacity_reducing, cron_managed=cron_managed
    ) + "\n")


def owner_approval_present(cli_flag: bool = False) -> bool:
    return bool(cli_flag) or os.environ.get(APPROVAL_ENV) == "1"


def require_owner_approval(
    script_name: str,
    *,
    owner_approved: bool = False,
    capacity_reducing: bool = True,
    stream=None,
) -> None:
    """Fail closed unless owner approval is present (CLI flag or env opt-in)."""
    if owner_approval_present(owner_approved):
        return
    out = stream if stream is not None else sys.stderr
    out.write(
        "\n".join(
            [
                guardrail_notice(
                    script_name, capacity_reducing=capacity_reducing
                ),
                "[GUARDRAIL] BLOCKED: live apply requires explicit owner approval.",
                "[GUARDRAIL] Re-run with --owner-approved (after capturing a "
                f"rollback snapshot), or set {APPROVAL_ENV}=1 for owner-supervised use.",
                "[GUARDRAIL] Owner approval phrase: 'APPROVE LEGACY PATCH APPLY "
                f"{script_name}'.",
            ]
        )
        + "\n"
    )
    raise SystemExit(2)


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    print(guardrail_notice("vpn_apply_guard (self-test)", capacity_reducing=True))
