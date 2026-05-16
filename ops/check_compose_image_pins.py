#!/usr/bin/env python3
"""Fail if compose templates still use unpinned images (P2-OPS-IMAGE-PIN-01)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ROOT / "compose"

# image lines that must contain @sha256: (basename prefix before :latest or :tag)
REQUIRED_PINNED_PREFIXES = (
    "postgres:17.6",
    "valkey/valkey:8.1-alpine",
    "adguard/adguardhome",
)

IMAGE_LINE = re.compile(r"^\s*image:\s*(.+)\s*$", re.MULTILINE)


def main() -> int:
    failures: list[str] = []
    for path in sorted(COMPOSE.rglob("docker-compose.yml.tmpl")):
        if "_archive" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for m in IMAGE_LINE.finditer(text):
            ref = m.group(1).strip().strip("'\"")
            for prefix in REQUIRED_PINNED_PREFIXES:
                if ref.startswith(prefix) and "@sha256:" not in ref:
                    failures.append(f"{path.relative_to(ROOT)}: image: {ref}")
    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("IMAGE_PINS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
