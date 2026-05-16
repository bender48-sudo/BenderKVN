"""Search the panel OpenAPI spec for internal-squad endpoints."""
from __future__ import annotations

import io
import json
import ssl
import sys
import urllib.request
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TOKEN = (ROOT / ".secrets" / "panel-token.txt").read_text(encoding="ascii").strip()
BASE = site_urls.PANEL_URL

ctx = ssl.create_default_context()

req = urllib.request.Request(f"{BASE}/openapi.json")
req.add_header("Authorization", f"Bearer {TOKEN}")
with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
    spec = json.loads(r.read().decode("utf-8"))

needle = sys.argv[1] if len(sys.argv) > 1 else "squad"
print(f"# searching for: {needle}")
for path, methods in spec.get("paths", {}).items():
    if needle.lower() not in path.lower():
        continue
    for method, info in methods.items():
        summary = info.get("summary") or info.get("operationId") or ""
        print(f"  {method.upper():6s} {path:60s} {summary}")
        if method.lower() in ("post", "patch", "put"):
            rb = info.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
            if "$ref" in rb:
                ref = rb["$ref"].split("/")[-1]
                schema = spec.get("components", {}).get("schemas", {}).get(ref, {})
                props = schema.get("properties", {})
                req_fields = schema.get("required", [])
                print(f"    body schema: {ref}")
                for prop, info2 in props.items():
                    t = info2.get("type") or info2.get("$ref", "?")
                    req_mark = " (req)" if prop in req_fields else ""
                    print(f"      {prop}: {t}{req_mark}")
