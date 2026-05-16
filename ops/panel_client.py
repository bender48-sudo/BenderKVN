"""Tiny shared HTTP client for Remnawave panel API.

Why it exists:
  Until now ops scripts copy-pasted ssl.CERT_NONE + curl -sk patterns.
  The panel uses a valid Let's Encrypt certificate — there is no reason
  to skip TLS validation. This module provides a safe default:
    - verify TLS via system CA
    - check_hostname=True
    - reasonable timeout
    - JSON helpers
    - structured errors with truncated bodies

Usage:
    from ops.panel_client import PanelClient
    c = PanelClient()
    code, data = c.get("/api/nodes")
    code, data = c.patch("/api/subscription-templates", body=tpl)

Token resolution order:
  1. argument PanelClient(token=...)
  2. env PANEL_TOKEN
  3. file <repo>/.secrets/panel-token.txt
"""
from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import site_urls  # noqa: F401  — loads optional ops/site.env (setdefaults)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TOKEN_FILE = REPO_ROOT / ".secrets" / "panel-token.txt"
DEFAULT_PANEL_URL = site_urls.PANEL_URL
DEFAULT_TIMEOUT = 30


def _load_token(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    env = os.environ.get("PANEL_TOKEN")
    if env:
        return env.strip()
    return DEFAULT_TOKEN_FILE.read_text(encoding="ascii").strip()


class PanelError(RuntimeError):
    def __init__(self, code: int, body: Any):
        super().__init__(f"panel HTTP {code}: {str(body)[:300]}")
        self.code = code
        self.body = body


class PanelClient:
    def __init__(
        self,
        base_url: str = DEFAULT_PANEL_URL,
        token: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.base = base_url.rstrip("/")
        self._token = _load_token(token)
        self.timeout = timeout
        # Strict TLS context (system CA + hostname check). Explicit so
        # that future "let's just skip verification" changes are visible.
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = True
        self._ctx.verify_mode = ssl.CERT_REQUIRED

    def _request(
        self,
        method: str,
        path: str,
        body: Any | None = None,
        raw_body: bytes | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[int, Any]:
        url = self.base + path if path.startswith("/") else f"{self.base}/{path}"

        data: bytes | None
        ct: str | None
        if raw_body is not None:
            data = raw_body
            ct = None
        elif body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            ct = "application/json; charset=utf-8"
        else:
            data = None
            ct = None

        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        if ct:
            req.add_header("Content-Type", ct)
        for k, v in (extra_headers or {}).items():
            req.add_header(k, v)

        try:
            with urllib.request.urlopen(req, context=self._ctx, timeout=self.timeout) as resp:
                raw = resp.read()
                if not raw:
                    return resp.status, None
                try:
                    return resp.status, json.loads(raw.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return resp.status, {"raw": raw.decode("utf-8", errors="replace")}
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = {"raw": raw.decode("utf-8", errors="replace")}
            return e.code, payload

    # --- thin verbs ---
    def get(self, path: str, **kw: Any) -> tuple[int, Any]:
        return self._request("GET", path, **kw)

    def post(self, path: str, body: Any | None = None, **kw: Any) -> tuple[int, Any]:
        return self._request("POST", path, body=body, **kw)

    def patch(self, path: str, body: Any | None = None, **kw: Any) -> tuple[int, Any]:
        return self._request("PATCH", path, body=body, **kw)

    def put(self, path: str, body: Any | None = None, **kw: Any) -> tuple[int, Any]:
        return self._request("PUT", path, body=body, **kw)

    def delete(self, path: str, **kw: Any) -> tuple[int, Any]:
        return self._request("DELETE", path, **kw)

    # --- raise variants for callers that prefer exceptions ---
    def get_or_raise(self, path: str, **kw: Any) -> Any:
        code, data = self.get(path, **kw)
        if code != 200:
            raise PanelError(code, data)
        return data

    def patch_or_raise(self, path: str, body: Any | None = None, **kw: Any) -> Any:
        code, data = self.patch(path, body=body, **kw)
        if code not in (200, 201, 204):
            raise PanelError(code, data)
        return data
