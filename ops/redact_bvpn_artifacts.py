#!/usr/bin/env python3
"""One-off / repeatable redaction of accidental secrets in bvpn-artifacts/.

Replaces JWT-looking strings and Telegram bot-token patterns with placeholders.
Run from repo root:  python ops/redact_bvpn_artifacts.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "bvpn-artifacts"

JWT_RE = re.compile(
    r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b"
)
# Audit logs often truncate: "prefix=eyJhbGci…" or "prefix=eyJ….…"
# Truncated logs: "prefix=eyJhbGciOiJIUzI1NiIs..."
JWT_TRUNC = re.compile(r"eyJ[A-Za-z0-9_\-]{16,}(?:\.{3}|…)")
# HTML dumps: embedded base64 JSON starting with eyJ (subscription page diagnostics)
DATA_PANEL_ATTR = re.compile(
    r'data-panel="eyJ[A-Za-z0-9+/=\-_]{80,}"'
)
BOT_RE = re.compile(r"\b[0-9]{6,13}:[A-Za-z0-9_\-]{25,}\b")
EXTS = {".txt", ".md", ".sh", ".py", ".json", ".yaml", ".yml", ".html", ".diff"}


def scrub(s: str) -> tuple[str, int]:
    n = 0

    def jwt_sub(m: re.Match) -> str:
        nonlocal n
        n += 1
        return "<REDACTED_JWT>"

    def bot_sub(m: re.Match) -> str:
        nonlocal n
        n += 1
        return "<REDACTED_BOT_TOKEN>"

    def data_panel_sub(_m: re.Match) -> str:
        nonlocal n
        n += 1
        return 'data-panel="<REDACTED_PANEL_JSON>"'

    s = JWT_RE.sub(jwt_sub, s)

    def trunc_sub(_m: re.Match) -> str:
        nonlocal n
        n += 1
        return "<REDACTED_JWT>"

    s = JWT_TRUNC.sub(trunc_sub, s)
    s = BOT_RE.sub(bot_sub, s)
    s = DATA_PANEL_ATTR.sub(data_panel_sub, s)
    return s, n


def main() -> None:
    if not ART.is_dir():
        print("no bvpn-artifacts/")
        return
    total = 0
    touched = 0
    for path in sorted(ART.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in EXTS:
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new, n = scrub(raw)
        if n and new != raw:
            path.write_text(new, encoding="utf-8")
            print(f"{path.relative_to(ROOT)}  ({n} replacements)")
            total += n
            touched += 1
    print(f"done: {touched} files, {total} replacements")


if __name__ == "__main__":
    main()
