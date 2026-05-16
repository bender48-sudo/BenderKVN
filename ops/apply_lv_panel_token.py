#!/usr/bin/env python3
"""Update PANEL_TOKEN / REMNA_API_TOKEN on LV from stdin (one line JWT)."""
from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

FILES = (
    Path("/etc/bvpn/balancer.env"),
    Path("/etc/bvpn/ru-monitor.env"),
)
KEYS = ("PANEL_TOKEN", "REMNA_API_TOKEN")


def patch_file(path: Path, token: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    shutil.copy2(path, path.with_name(f"{path.name}.before-token-{ts}"))
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in KEYS:
            if key not in seen:
                out.append(f"{key}={token}\n")
                seen.add(key)
            continue
        out.append(line if line.endswith("\n") else line + "\n")
    for key in KEYS:
        if key not in seen and path.name == "balancer.env":
            out.append(f"{key}={token}\n")
        elif key == "REMNA_API_TOKEN" and key not in seen and path.name == "ru-monitor.env":
            out.append(f"{key}={token}\n")
    path.write_text("".join(out), encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    token = sys.stdin.read().strip().strip('"').strip("'")
    if not token.startswith("eyJ"):
        print("ERROR: expected JWT on stdin", file=sys.stderr)
        return 1
    for p in FILES:
        if not p.exists():
            print(f"ERROR: missing {p}", file=sys.stderr)
            return 1
        patch_file(p, token)
        print(f"patched {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
