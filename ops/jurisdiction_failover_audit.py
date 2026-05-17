#!/usr/bin/env python3
"""P3-RED-JURIS-01: validate jurisdiction failover wiki + runbook + tabletop."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INVENTORY = Path(__file__).resolve().parent / "jurisdiction_failover_inventory.json"


def main() -> int:
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    errors: list[str] = []

    for rel in inv.get("required_docs", []):
        p = ROOT / rel
        if not p.is_file():
            errors.append(f"missing doc: {rel}")

    for rel, needles in inv.get("required_doc_sections", {}).items():
        p = ROOT / rel
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                errors.append(f"{rel}: missing section marker {needle!r}")

    runbook = ROOT / "docs" / "RUNBOOK-JURISDICTION-FAILOVER.md"
    if runbook.is_file():
        rb = runbook.read_text(encoding="utf-8")
        for link in inv.get("cross_links", []):
            if link not in rb:
                errors.append(f"runbook: missing cross-link {link!r}")

    incident = ROOT / "docs" / "RUNBOOK-INCIDENT.md"
    if incident.is_file() and "JURISDICTION-FAILOVER" not in incident.read_text(encoding="utf-8"):
        errors.append("RUNBOOK-INCIDENT: missing JURISDICTION-FAILOVER link")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print("JURIS_FAILOVER_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
