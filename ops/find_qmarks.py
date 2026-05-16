"""Find all '?' clusters in the latest panel snapshot — locate broken UTF-8."""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
snap_dir = ROOT / ".secrets" / "snapshots"
latest = sorted(snap_dir.glob("panel-*.json"))[-1]
print(f"# snapshot: {latest.name}")

data = json.loads(latest.read_text(encoding="utf-8"))


def walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        if re.search(r"\?{2,}", obj):
            yield path, obj


for path, val in walk(data):
    print(f"{path}: {val!r}")
