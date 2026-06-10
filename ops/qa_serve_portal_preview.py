#!/usr/bin/env python3
"""Local portal preview server with QA fixture API (QA-PORTAL-FIXTURES-001).

Serves web/portal static files and stubs /setup/api/* using isolated QA DB.
Requires BVPN_ENV non-production + BVPN_QA_TOOLS_ENABLED=1.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"
PORTAL = ROOT / "web" / "portal"
PORT = int(os.getenv("BVPN_QA_PORTAL_PORT", "8765"))


def _load_fixtures():
    if str(OPS) not in sys.path:
        sys.path.insert(0, str(OPS))
    import qa_portal_fixtures as qpf

    return qpf


class QaPortalPreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PORTAL), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        return

    def translate_path(self, path: str) -> str:
        p = path.split("?", 1)[0].split("#", 1)[0]
        if p.startswith("/portal/"):
            p = p[len("/portal/") :]
        elif p.startswith("/start/") or p == "/start":
            p = "/index.html"
        elif p == "/setup" or p.startswith("/setup/"):
            if p.startswith("/setup/api"):
                return p
            p = "/setup.html"
        if not p or p == "/":
            p = "/index.html"
        if p.startswith("/setup/api"):
            return p
        return super().translate_path(p)

    def do_GET(self) -> None:
        if self._handle_api_get():
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self._handle_api_post():
            return
        self.send_error(404)

    def _handle_api_get(self) -> bool:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if path == "/setup/api/health":
            self._json(200, {"ok": True, "service": "qa_portal_preview"})
            return True
        return False

    def _handle_api_post(self) -> bool:
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/setup/api/"):
            path = "/" + path[len("/setup/api/") :].lstrip("/")
        path = path.rstrip("/") or "/"

        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "invalid_json"})
            return True

        qpf = _load_fixtures()

        if path == "/funnel-event":
            self._json(200, {"ok": True})
            return True

        if path == "/capacity":
            fx = (data.get("fixture") or data.get("qa_capacity_fixture") or "").strip()
            if not fx:
                qs = parse_qs(urlparse(self.path).query)
                fx = (qs.get("qa_capacity_fixture") or [""])[0]
            payload = qpf.CAPACITY_FIXTURES.get(fx) or qpf.CAPACITY_FIXTURES.get("slots_high")
            self._json(200, payload)
            return True

        if path == "/cabinet":
            try:
                qpf._ensure_guards(qpf._resolve_db_path(None))
                tid = data.get("telegram_id")
                doc = qpf.cabinet_api_response(
                    telegram_id=int(tid) if tid else None,
                    email=(data.get("email") or "").strip(),
                    customer_id=(data.get("customer_id") or "").strip(),
                    db_path=qpf._resolve_db_path(None),
                )
            except Exception as exc:
                self._json(403, {"ok": False, "error": str(exc)[:160]})
                return True
            code = 200 if doc.get("ok") else 404
            self._json(code, doc)
            return True

        if path == "/telegram-setup":
            try:
                tid = int(data.get("telegram_id"))
            except (TypeError, ValueError):
                self._json(400, {"ok": False, "error": "missing_telegram_id"})
                return True
            if tid <= 0:
                self._json(400, {"ok": False, "error": "missing_telegram_id"})
                return True
            sub = f"https://sandbox.invalid/sub/qa-{tid}"
            setup_page = f"https://sandbox.invalid/setup/qa-{tid}"
            self._json(
                200,
                {
                    "ok": True,
                    "setup_page_url": setup_page,
                    "setup_url": setup_page,
                    "sub_url": sub,
                    "qa_fixture": True,
                },
            )
            return True

        if path in ("/web-trial", "/web-trial-recover"):
            self._json(
                501,
                {
                    "ok": False,
                    "error": "qa_preview_only",
                    "message": "Seed web trial via qa_seed_scenarios; use cabinet by email",
                },
            )
            return True

        self._json(404, {"ok": False, "error": "not_found"})
        return True

    def _json(self, code: int, doc: dict) -> None:
        body = json.dumps(doc, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    qpf = _load_fixtures()
    db_path = qpf._resolve_db_path(None)
    qpf._ensure_guards(db_path)
    print(f"QA portal preview DB: {db_path}")
    print(f"SERVING {PORTAL} http://127.0.0.1:{PORT}/start/")
    print("API stub: /setup/api/cabinet /setup/api/capacity /setup/api/telegram-setup")
    with ThreadingHTTPServer(("127.0.0.1", PORT), QaPortalPreviewHandler) as httpd:
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
