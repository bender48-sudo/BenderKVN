#!/usr/bin/env python3
"""P3-FLOW-02/WEB: setup verify + browser web trial (behind Caddy on LV)."""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import re

from portal_setup_token import sign_setup_token, verify_setup_token  # noqa: E402
import site_urls  # noqa: E402

_SHORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def _short_id_from_sub_url(sub_url: str) -> str | None:
    if not sub_url:
        return None
    seg = sub_url.rstrip("/").split("/")[-1].split("?")[0]
    if _SHORT_ID_RE.match(seg):
        return seg
    return None

_RATE: dict[str, list[float]] = {}
_RATE_LIMIT = int(os.environ.get("WEB_TRIAL_RATE_PER_HOUR", "5"))
_FUNNEL_LOG = Path(os.environ.get("BVPN_FUNNEL_LOG", "/var/log/bvpn-funnel.jsonl"))


def _funnel_log(event: str, meta: dict | None = None) -> None:
    doc = {"ts": int(time.time()), "event": event, "meta": meta or {}}
    line = json.dumps(doc, ensure_ascii=False) + "\n"
    try:
        _FUNNEL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_FUNNEL_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
_AMS_KEY = Path.home() / ".ssh" / "bvpn_ams_ed25519"
_AMS_HOST = os.environ.get("AMS_OPS_HOST", "168.100.11.140")
_AMS_PORT = os.environ.get("AMS_OPS_SSH_PORT", "3344")


def _client_ip(handler: BaseHTTPRequestHandler) -> str:
    fwd = handler.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return handler.client_address[0]


def _rate_ok(ip: str) -> bool:
    now = time.time()
    window = _RATE.get(ip, [])
    window = [t for t in window if now - t < 3600]
    if len(window) >= _RATE_LIMIT:
        _RATE[ip] = window
        return False
    window.append(now)
    _RATE[ip] = window
    return True


def _ams_portal_post(path: str, body: dict) -> dict:
    secret = os.environ.get("PORTAL_WEB_TRIAL_SECRET", "").strip()
    if not secret:
        raise ValueError("PORTAL_WEB_TRIAL_SECRET is not set")
    payload = json.dumps(body, ensure_ascii=False)
    pl = shlex.quote(payload)
    remote = (
        "curl -fsS -X POST "
        "-H 'Content-Type: application/json' "
        f"-H 'X-Portal-Web-Trial-Key: {secret}' "
        f"-d {pl} "
        f"http://127.0.0.1:1488{path}"
    )
    cmd = [
        "ssh",
        "-i",
        str(_AMS_KEY),
        "-p",
        str(_AMS_PORT),
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=40",
        f"root@{_AMS_HOST}",
        remote,
    ]
    out = subprocess.check_output(cmd, text=True, timeout=90)
    return json.loads(out.strip().splitlines()[-1])


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

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/funnel-event":
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                data = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._json(400, {"ok": False, "error": "invalid_json"})
                return
            ev = (data.get("event") or "").strip()[:64]
            if not ev or not re.match(r"^[a-z][a-z0-9_]{0,63}$", ev):
                self._json(400, {"ok": False, "error": "bad_event"})
                return
            _funnel_log(ev, {"ip_hash": hashlib.sha256(_client_ip(self).encode()).hexdigest()[:16]})
            self._json(200, {"ok": True})
            return
        if path == "/cabinet":
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                data = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._json(400, {"ok": False, "error": "invalid_json"})
                return
            try:
                body = {
                    "customer_id": (data.get("customer_id") or "").strip(),
                    "email": (data.get("email") or "").strip(),
                }
                raw_tid = data.get("telegram_id")
                if raw_tid is not None:
                    try:
                        tid = int(raw_tid)
                        if tid > 0:
                            body["telegram_id"] = tid
                    except (TypeError, ValueError):
                        pass
                ams = _ams_portal_post("/portal-cabinet", body)
            except Exception as e:
                self._json(502, {"ok": False, "error": str(e)[:120]})
                return
            code = 200 if ams.get("ok") else 404
            self._json(code, ams)
            return
        if path not in ("/web-trial", "/web-trial-recover"):
            self._json(404, {"ok": False, "error": "not_found"})
            return
        ip = _client_ip(self)
        if not _rate_ok(ip):
            self._json(429, {"ok": False, "error": "rate_limited"})
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "invalid_json"})
            return
        email = (data.get("email") or "").strip()
        phone = (data.get("phone") or "").strip()
        if not email or "@" not in email:
            self._json(400, {"ok": False, "error": "invalid_email"})
            return
        ams_path = "/portal-web-trial-recover" if path == "/web-trial-recover" else "/portal-web-trial"
        body = {"email": email}
        if ams_path == "/portal-web-trial":
            body["phone"] = phone
        try:
            ams = _ams_portal_post(ams_path, body)
        except subprocess.CalledProcessError as e:
            self._json(502, {"ok": False, "error": "upstream_failed", "detail": str(e)[:120]})
            return
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)[:200]})
            return
        if not ams.get("ok"):
            err = ams.get("error")
            if err == "trial_already_claimed":
                code = 409
            elif err == "not_found":
                code = 404
            else:
                code = 400
            self._json(code, ams)
            return
        sub_url = ams.get("sub_url") or ""
        sid = _short_id_from_sub_url(sub_url)
        if not sid:
            self._json(500, {"ok": False, "error": "bad_sub_url"})
            return
        token = sign_setup_token(sid)
        setup_url = site_urls.public_setup_url(token)
        out = {
            "ok": True,
            "sub_url": sub_url,
            "setup_url": setup_url,
            "token": token,
            "expire_at": ams.get("expire_at"),
            "days": ams.get("days"),
            "customer_id": ams.get("customer_id"),
        }
        for key in ("bind_url", "bind_token", "telegram_bound", "recovered"):
            if key in ams:
                out[key] = ams[key]
        self._json(200, out)

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
