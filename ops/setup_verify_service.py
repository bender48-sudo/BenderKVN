#!/usr/bin/env python3
"""P3-FLOW-02: localhost verify API for /setup tokens (behind Caddy)."""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from portal_setup_token import verify_setup_token  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in ("/verify", "/verify/"):
            self._json(404, {"ok": False, "error": "not_found"})
            return
        qs = parse_qs(parsed.query)
        token = (qs.get("t") or [""])[0]
        if not token:
            self._json(400, {"ok": False, "error": "missing_token"})
            return
        try:
            info = verify_setup_token(token)
            self._json(200, {"ok": True, **info})
        except ValueError as e:
            self._json(403, {"ok": False, "error": str(e)})

    def _json(self, code: int, doc: dict) -> None:
        body = json.dumps(doc, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    host = os.environ.get("SETUP_VERIFY_BIND", "127.0.0.1")
    port = int(os.environ.get("SETUP_VERIFY_PORT", "8871"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"SETUP_VERIFY_LISTEN {host}:{port}", flush=True)
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
