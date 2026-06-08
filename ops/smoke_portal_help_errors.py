#!/usr/bin/env python3
"""P3-FLOW-08: human-readable errors page on portal (/start/help/errors/)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ERRORS_INDEX = ROOT / "web" / "portal" / "help" / "errors" / "index.html"
REQUIRED_IDS = {
    "service_unavailable",
    "trial_used",
    "rate_limited",
    "link_expired",
    "subscription_refresh",
}


def _http_body(url: str, timeout: float = 25.0) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "BVPN-smoke/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, body
    except OSError:
        return 0, ""


def _http_ok(url: str, timeout: float = 25.0) -> bool:
    code, _ = _http_body(url, timeout=timeout)
    return 200 <= code < 300


def main() -> int:
    if not ERRORS_INDEX.is_file():
        print("PORTAL_HELP_ERRORS_FAIL: missing help/errors/index.html", file=sys.stderr)
        return 1

    ru = json.loads((ROOT / "web" / "portal" / "content" / "ru.json").read_text(encoding="utf-8"))
    items = (ru.get("user_errors") or {}).get("items") or []
    ids = {it.get("id") for it in items if isinstance(it, dict)}
    if ids != REQUIRED_IDS:
        print(f"PORTAL_HELP_ERRORS_FAIL: expected ids {REQUIRED_IDS}, got {ids}", file=sys.stderr)
        return 1

    pl = (ROOT / "bot_src" / "portal_links.py").read_text(encoding="utf-8")
    kb = (ROOT / "bot_src" / "keyboards.py").read_text(encoding="utf-8")
    if "public_errors_url" not in pl:
        print("PORTAL_HELP_ERRORS_FAIL: portal_links missing public_errors_url", file=sys.stderr)
        return 1
    if "public_errors_url(" not in kb:
        print("PORTAL_HELP_ERRORS_FAIL: keyboards missing errors link", file=sys.stderr)
        return 1

    if "errors.js" not in ERRORS_INDEX.read_text(encoding="utf-8"):
        print("PORTAL_HELP_ERRORS_FAIL: index.html missing errors.js", file=sys.stderr)
        return 1

    sys.path.insert(0, str(ROOT / "ops"))
    try:
        import site_urls

        base = site_urls.public_errors_url()
        code, body = _http_body(base)
        if not (200 <= code < 300):
            print(f"PORTAL_HELP_ERRORS_FAIL: HTTP not OK {base}", file=sys.stderr)
            return 1
        if "errors.js" not in body or 'id="errors-list"' not in body:
            print(
                "PORTAL_HELP_ERRORS_FAIL: pretty URL must serve errors page, not landing",
                file=sys.stderr,
            )
            return 1
        if not _http_ok(site_urls.public_errors_url("rate_limited")):
            print("PORTAL_HELP_ERRORS_FAIL: deep link HTTP not OK", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"PORTAL_HELP_ERRORS_FAIL: probe {exc}", file=sys.stderr)
        return 1

    print("PORTAL_HELP_ERRORS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
