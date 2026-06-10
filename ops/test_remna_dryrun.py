#!/usr/bin/env python3
"""QA-REMNA-DRYRUN-001: dry-run Remna provider regression checks."""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"


def _bootstrap_shop_bot() -> None:
    if str(BOT) not in sys.path:
        sys.path.insert(0, str(BOT))
    if "shop_bot" not in sys.modules:
        pkg = types.ModuleType("shop_bot")
        pkg.__path__ = [str(BOT)]  # type: ignore[attr-defined]
        sys.modules["shop_bot"] = pkg


def _set_env(**kwargs: str | None) -> dict[str, str | None]:
    prev: dict[str, str | None] = {}
    for key, value in kwargs.items():
        prev[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    return prev


def _restore_env(prev: dict[str, str | None]) -> None:
    for key, value in prev.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _reload_modules():
    _bootstrap_shop_bot()
    for name in ("runtime_env", "remna_dryrun", "remnawave_api"):
        full = f"shop_bot.{name}"
        if full in sys.modules:
            importlib.reload(sys.modules[full])
        else:
            mod = importlib.import_module(name)
            sys.modules[full] = mod
    return (
        sys.modules["shop_bot.runtime_env"],
        sys.modules["shop_bot.remna_dryrun"],
        sys.modules["shop_bot.remnawave_api"],
    )


def _static_checks() -> None:
    dryrun_src = (BOT / "remna_dryrun.py").read_text(encoding="utf-8")
    remna_src = (BOT / "remnawave_api.py").read_text(encoding="utf-8")
    for needle, label in (
        ("def should_use_remna_dry_run", "dry-run gate"),
        ("def dryrun_provision_key", "dryrun provision_key"),
        ("sandbox.invalid", "sandbox host only"),
        ("should_use_remna_dry_run()", "wired in remnawave_api"),
        ("dryrun_provision_key", "provision_key dry-run branch"),
        ("dryrun_add_extra_traffic", "add_extra_traffic dry-run branch"),
    ):
        if needle not in (dryrun_src + remna_src):
            raise AssertionError(f"static check failed: {label} ({needle!r})")
    for bad in ("https://kitsura", "@kitsura.fun", "REMNA_API_TOKEN", "www.yandex.ru"):
        if bad in dryrun_src:
            raise AssertionError(f"dry-run module must not embed production-like value: {bad!r}")
    if "sandbox.invalid" not in dryrun_src:
        raise AssertionError("dry-run must use sandbox.invalid host")


async def _async_tests() -> None:
    _re, dryrun, remna = _reload_modules()

    prev = _set_env(BVPN_ENV="production", BVPN_QA_DRY_RUN_REMNA="1")
    try:
        _re, dryrun, remna = _reload_modules()
        assert not dryrun.should_use_remna_dry_run()
    finally:
        _restore_env(prev)

    prev = _set_env(BVPN_ENV="staging", BVPN_QA_DRY_RUN_REMNA=None)
    try:
        _re, _, remna = _reload_modules()
        try:
            await remna.provision_key("blocked@example.com", days=3)
            raise AssertionError("staging without dry-run flag must be blocked")
        except _re.QaGuardError:
            pass
    finally:
        _restore_env(prev)

    prev = _set_env(BVPN_ENV="test", BVPN_QA_DRY_RUN_REMNA="1")
    try:
        _re, dryrun, remna = _reload_modules()
        assert dryrun.should_use_remna_dry_run()

        session_mock = AsyncMock()
        session_mock.__aenter__ = AsyncMock(side_effect=AssertionError("real Remna session must not open"))
        session_mock.__aexit__ = AsyncMock(return_value=False)

        with patch.object(remna, "remna_client_session", return_value=session_mock):
            uri, expire_iso, vless_uuid, sub_url = await remna.provision_key(
                "qa-user@example.com",
                days=7,
                telegram_id="900000001",
            )

        assert uri and expire_iso and vless_uuid and sub_url
        dryrun.assert_dummy_response_safe(uri, sub_url)
        assert "qa-user" in uri or "qa-" in uri
        assert expire_iso.endswith("Z")

        with patch.object(remna, "remna_client_session", return_value=session_mock):
            ok = await remna.add_extra_traffic("qa-user@example.com", 100, telegram_id="900000001")
        assert ok is True

        with patch.object(remna, "remna_client_session", return_value=session_mock):
            exp = await remna.set_user_access_days("900000001", 14, email="qa-user@example.com")
        assert exp and exp.endswith("Z")
    finally:
        _restore_env(prev)

    uri2, _, uuid2, sub2 = dryrun.dryrun_provision_key("qa-user@example.com", days=7)
    uri3, _, uuid3, sub3 = dryrun.dryrun_provision_key("qa-user@example.com", days=7)
    assert uuid2 == uuid3
    dryrun.assert_dummy_response_safe(uri2, sub2)


def main() -> int:
    _static_checks()
    asyncio.run(_async_tests())
    print("REMNA_DRYRUN_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
