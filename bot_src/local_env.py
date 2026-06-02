"""Load gitignored local env files from repo root (dev / owner keys only)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent

_LOCAL_ENV_FILES = (
    ".env",
    ".secrets/vault.env",
    ".secrets/yookassa.env",
)

# YooKassa export from ЛК (often pasted as several lines, no KEY=).
_YOOKASSA_KEY_FILENAMES = (
    "secret_key 2",
    "secret_key 2.txt",
)


def _parse_yookassa_keyfile(path: Path) -> None:
    try:
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError:
        return
    if not lines:
        return

    if any("=" in ln for ln in lines):
        load_dotenv(path)
        return

    for ln in lines:
        if ln.startswith(("live_", "test_")):
            os.environ.setdefault("YOOKASSA_SECRET_KEY", ln)
        elif ln.isdigit() and 4 <= len(ln) <= 12:
            os.environ.setdefault("YOOKASSA_SHOP_ID", ln)


def load_local_env() -> None:
    for rel in _LOCAL_ENV_FILES:
        path = _REPO_ROOT / rel
        if path.is_file():
            load_dotenv(path)

    for name in _YOOKASSA_KEY_FILENAMES:
        path = _REPO_ROOT / name
        if path.is_file():
            _parse_yookassa_keyfile(path)


def repo_root() -> Path:
    return _REPO_ROOT
