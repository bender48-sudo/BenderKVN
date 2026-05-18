#!/usr/bin/env python3
"""P1-ENG-04: no hardcoded AMS panel IP in handlers."""
from __future__ import annotations

import sys
from pathlib import Path

H = (Path(__file__).resolve().parent.parent / "bot_src" / "handlers.py").read_text(encoding="utf-8")


def main() -> int:
    if "168.100.11.140" in H:
        print("HANDLERS_IP_FAIL: hardcoded IP still in handlers.py", file=sys.stderr)
        return 1
    if "BACKUP_SERVER_IP" not in H and "AMS_PANEL_HOST_IP" not in H:
        print("HANDLERS_IP_FAIL: env-based IP missing", file=sys.stderr)
        return 1
    print("HANDLERS_IP_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
