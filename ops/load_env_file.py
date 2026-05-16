#!/usr/bin/env python3
"""Load KEY=value lines from an env-style file (# comments; stripped quotes).

Starter for **P5-ENG-02** — скрипты могут прочитать `*.env` без bash `source`.
Не парсит многострочные значения; строки после `#` в конце считаются комментарием
только если `#` первый символ строки после trim (как минимально для cron env)."""

from __future__ import annotations

import sys
from pathlib import Path


def load_env_file(path: Path | str) -> dict[str, str]:
    raw = Path(path).read_text(encoding="utf-8")
    env: dict[str, str] = {}
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, rest = line.split("=", 1)
        k = key.strip()
        val = rest.split("#", 1)[0].strip() if "#" in rest else rest.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        env[k] = val
    return env


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] != "get":
        print("Usage: python load_env_file.py get <path> <KEY>", file=sys.stderr)
        sys.exit(2)
    path, key = Path(sys.argv[2]), sys.argv[3]
    env = load_env_file(path)
    if key not in env:
        print(f"Missing {key}", file=sys.stderr)
        sys.exit(1)
    sys.stdout.buffer.write(env[key].encode("utf-8", errors="surrogateescape") + b"\n")


if __name__ == "__main__":
    main()
