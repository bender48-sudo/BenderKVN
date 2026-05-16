"""Find where the 'BenderVPN Auto' string lives in the template / host data."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
snap = sorted((ROOT / ".secrets" / "snapshots").glob("panel-*.json"))[-1]
print(f"# {snap.name}")

data = json.loads(snap.read_text(encoding="utf-8"))


def walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        if "BenderVPN" in obj or "Bender" in obj:
            yield path, obj


for path, val in walk(data):
    print(f"{path}: {val!r}")
