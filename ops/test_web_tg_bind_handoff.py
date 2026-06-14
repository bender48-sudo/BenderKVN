#!/usr/bin/env python3
"""Static tests: portal → Telegram bind handoff UX (G4-TG-BIND-HANDOFF-FIX-001)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIND_JS = ROOT / "web" / "portal" / "assets" / "bind-handoff.js"
SETUP_JS = ROOT / "web" / "portal" / "assets" / "setup.js"
SETUP_HTML = ROOT / "web" / "portal" / "setup.html"
RU_JSON = ROOT / "web" / "portal" / "content" / "ru.json"

_SAMPLE_BIND_URL = "https://t.me/ExampleBindBot?start=bind_" + ("abcdef0123456789" * 2)
_SAMPLE_TOKEN = "abcdef0123456789" * 2

_SECRET_RE = re.compile(
    r"eyJ[A-Za-z0-9_-]{20,}|REMNA_API_TOKEN|BOT_TOKEN|sk_live_",
    re.I,
)

_FUNNEL_EVENTS = (
    "web_tg_bind_rendered",
    "web_tg_bind_open_clicked",
    "web_tg_bind_copy_clicked",
    "web_tg_bind_retry_clicked",
)

_NODE_EVAL = r"""
const fs = require("fs");
const bindPath = process.env.BVPN_BIND_JS;
const bindUrl = process.env.BVPN_BIND_URL;
const code = fs.readFileSync(bindPath, "utf8");
eval(code.replace(/typeof window !== "undefined" \? window : globalThis/g, "globalThis"));
const h = globalThis.BenderBindHandoff.parseBindUrl(bindUrl);
if (!h) { console.error("parse_fail"); process.exit(2); }
const preview = globalThis.BenderBindHandoff.formatStartCommandPreview(h.startCommand);
console.log(JSON.stringify({
  botUsername: h.botUsername,
  startPayload: h.startPayload,
  startCommand: h.startCommand,
  tokenPrefix: h.tokenPrefix,
  httpsUrl: h.httpsUrl,
  tgResolveUrl: h.tgResolveUrl,
  preview: preview,
}));
"""


def _run_node_parse(bind_url: str) -> dict:
    import os

    env = os.environ.copy()
    env["BVPN_BIND_JS"] = str(BIND_JS)
    env["BVPN_BIND_URL"] = bind_url
    out = subprocess.check_output(
        ["node", "-e", _NODE_EVAL],
        text=True,
        encoding="utf-8",
        timeout=15,
        env=env,
    )
    return json.loads(out.strip())


def test_bind_handoff_files_present() -> None:
    for path in (BIND_JS, SETUP_JS, SETUP_HTML, RU_JSON):
        assert path.is_file(), f"missing {path}"


def test_bind_url_start_parameter() -> None:
    parsed = _run_node_parse(_SAMPLE_BIND_URL)
    assert parsed["startPayload"] == f"bind_{_SAMPLE_TOKEN}"
    assert parsed["httpsUrl"] == _SAMPLE_BIND_URL
    assert "start=bind_" in parsed["httpsUrl"]
    assert parsed["tgResolveUrl"].startswith("tg://resolve?domain=")
    assert "start=bind_" in parsed["tgResolveUrl"]
    assert parsed["botUsername"] == "ExampleBindBot"


def test_fallback_start_command() -> None:
    parsed = _run_node_parse(_SAMPLE_BIND_URL)
    cmd = parsed["startCommand"]
    assert cmd == f"/start bind_{_SAMPLE_TOKEN}"
    preview = parsed["preview"]
    assert preview.startswith("/start bind_")
    assert preview.endswith("\u2026")
    assert _SAMPLE_TOKEN not in preview
    assert len(preview) < len(cmd)


def test_setup_js_wires_handoff_and_events() -> None:
    text = SETUP_JS.read_text(encoding="utf-8")
    for ev in _FUNNEL_EVENTS:
        assert ev in text, f"setup.js missing funnel event {ev!r}"
    assert "BenderBindHandoff" in text or "parseBindHandoff" in text
    assert "btn-copy-bind-start" in text
    assert "btn-bind-tg-retry" in text
    assert "openBindInTelegram" in text
    assert "/setup/api/funnel-event" in text
    assert _SECRET_RE.search(text) is None


def test_setup_html_bind_panel() -> None:
    html = SETUP_HTML.read_text(encoding="utf-8")
    for needle in (
        "bind-handoff.js",
        "btn-bind-tg",
        "btn-copy-bind-start",
        "btn-bind-tg-retry",
        "bind-tg-warning",
        "bind-tg-start-preview",
    ):
        assert needle in html, f"setup.html missing {needle!r}"
    assert _SECRET_RE.search(html) is None


def test_ru_json_bind_copy() -> None:
    doc = json.loads(RU_JSON.read_text(encoding="utf-8"))
    setup = doc.get("setup") or {}
    assert "bind_tg_warning" in setup
    assert "bind_tg_copy_start" in setup
    assert "bind_tg_retry" in setup
    assert "Telegram" in setup.get("bind_tg_lead", "")
    assert _SECRET_RE.search(RU_JSON.read_text(encoding="utf-8")) is None


def test_no_raw_token_in_telemetry_payload() -> None:
    text = SETUP_JS.read_text(encoding="utf-8")
    assert "JSON.stringify({ event: event })" in text
    assert "bind_token" not in text or "extra.bind_url" in text


def main() -> int:
    tests = [
        test_bind_handoff_files_present,
        test_bind_url_start_parameter,
        test_fallback_start_command,
        test_setup_js_wires_handoff_and_events,
        test_setup_html_bind_panel,
        test_ru_json_bind_copy,
        test_no_raw_token_in_telemetry_payload,
    ]
    for fn in tests:
        try:
            fn()
        except AssertionError as e:
            print(f"WEB_TG_BIND_HANDOFF_FAIL: {fn.__name__}: {e}", file=sys.stderr)
            return 1
    print("WEB_TG_BIND_HANDOFF_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
