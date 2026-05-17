#!/usr/bin/env python3
"""P3-FLOW-00: validate USER-FLOW-JOURNEY.md structure."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNEY = ROOT / "docs" / "USER-FLOW-JOURNEY.md"

REQUIRED = [
    "Персоны",
    "10 шагов",
    "Сайт",
    "Mini App",
    "Бот",
    "P1",
    "P2",
    "P3",
    "Windows",
    "Mac",
    "Happ",
    "As-is",
    "App Store",
    "Google Play",
    "бабушка-тест",
    "ONBOARDING.md",
    "FAQ.md",
    "/status",
]


def main() -> int:
    if not JOURNEY.is_file():
        print(f"FAIL: missing {JOURNEY}", file=sys.stderr)
        return 1
    text = JOURNEY.read_text(encoding="utf-8")
    errors: list[str] = []
    for needle in REQUIRED:
        if needle not in text:
            errors.append(f"missing section/marker: {needle!r}")
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("USER_FLOW_JOURNEY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
