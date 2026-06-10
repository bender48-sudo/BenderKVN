#!/usr/bin/env python3
"""QA-GUARD-001: runtime_env safety guard regression checks."""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"


def _import_runtime_env():
    if str(BOT) not in sys.path:
        sys.path.insert(0, str(BOT))
    if "shop_bot" not in sys.modules:
        pkg = types.ModuleType("shop_bot")
        pkg.__path__ = [str(BOT)]  # type: ignore[attr-defined]
        sys.modules["shop_bot"] = pkg
    if "shop_bot.runtime_env" in sys.modules:
        return importlib.reload(sys.modules["shop_bot.runtime_env"])
    mod = importlib.import_module("runtime_env")
    sys.modules["shop_bot.runtime_env"] = mod
    return mod


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


def _run_guard_tests() -> None:
    re = _import_runtime_env()

    prev = _set_env(BVPN_ENV=None, BVPN_QA_DRY_RUN_REMNA=None, BVPN_QA_DRY_RUN_PAYMENTS=None)
    try:
        re = _import_runtime_env()
        assert re.get_bvpn_env().value == "production"
        assert re.is_production()
        assert not re.is_non_production()
        re.assert_remna_mutation_allowed("test")
        re.assert_yookassa_write_allowed("test")
    finally:
        _restore_env(prev)

    prev = _set_env(BVPN_ENV="staging", BVPN_QA_DRY_RUN_REMNA=None, BVPN_QA_DRY_RUN_PAYMENTS=None)
    try:
        re = _import_runtime_env()
        assert re.get_bvpn_env().value == "staging"
        assert re.is_non_production()
        re.require_non_production("should_not_raise")
        try:
            re.assert_remna_mutation_allowed("provision_key")
            raise AssertionError("Remna must be blocked in staging without dry-run")
        except re.QaGuardError:
            pass
        prev2 = _set_env(BVPN_QA_DRY_RUN_REMNA="1")
        try:
            re = _import_runtime_env()
            re.assert_remna_mutation_allowed("provision_key")
        finally:
            _restore_env(prev2)
    finally:
        _restore_env(prev)

    prev = _set_env(BVPN_ENV="local", BVPN_QA_DRY_RUN_PAYMENTS=None)
    try:
        re = _import_runtime_env()
        try:
            re.assert_yookassa_write_allowed("Payment.create")
            raise AssertionError("YooKassa must be blocked in local without dry-run")
        except re.QaGuardError:
            pass
        prev2 = _set_env(BVPN_QA_DRY_RUN_PAYMENTS="1")
        try:
            re = _import_runtime_env()
            re.assert_yookassa_write_allowed("Payment.create")
        finally:
            _restore_env(prev2)
    finally:
        _restore_env(prev)

    prev = _set_env(BVPN_ENV="test", BVPN_QA_TOOLS_ENABLED=None)
    try:
        re = _import_runtime_env()
        try:
            re.require_qa_tooling_enabled("seed")
            raise AssertionError("QA tools must require BVPN_QA_TOOLS_ENABLED")
        except re.QaGuardError:
            pass
        prev2 = _set_env(BVPN_QA_TOOLS_ENABLED="1")
        try:
            re = _import_runtime_env()
            re.require_qa_tooling_enabled("seed")
        finally:
            _restore_env(prev2)
    finally:
        _restore_env(prev)

    prev = _set_env(BVPN_ENV="production")
    try:
        re = _import_runtime_env()
        try:
            re.require_non_production("seed")
            raise AssertionError("QA tools must not run in production")
        except re.QaGuardError:
            pass
    finally:
        _restore_env(prev)

    with tempfile.TemporaryDirectory() as tmp:
        qa_db = Path(tmp) / "qa_shop_bot.db"
        prev = _set_env(
            BVPN_ENV="staging",
            BVPN_PROD_DB_PATH="/app/data/shop_bot.db",
            BVPN_QA_TOOLS_ENABLED="1",
        )
        try:
            re = _import_runtime_env()
            re.assert_db_path_allowed_for_qa(qa_db, "seed")
            try:
                re.assert_db_path_allowed_for_qa("/app/data/shop_bot.db", "seed")
                raise AssertionError("prod DB path must be rejected for QA")
            except re.QaGuardError:
                pass
        finally:
            _restore_env(prev)


def _static_checks() -> None:
    handlers = (BOT / "handlers.py").read_text(encoding="utf-8")
    remna = (BOT / "remnawave_api.py").read_text(encoding="utf-8")
    yk = (BOT / "yookassa_payment.py").read_text(encoding="utf-8")
    runtime = (BOT / "runtime_env.py").read_text(encoding="utf-8")
    for needle, label in (
        ("class BvpnEnvironment", "environment enum"),
        ("BVPN_ENV", "BVPN_ENV documented"),
        ("def payment_create", "yookassa payment_create guard"),
        ("assert_yookassa_write_allowed", "yookassa guard call"),
        ("assert_remna_mutation_allowed", "remna guard"),
        ("payment_create(", "handlers uses payment_create"),
        ("SHOP_BOT_DB_PATH", "isolated db path override"),
    ):
        blob = handlers + remna + yk + runtime
        if needle not in blob:
            raise AssertionError(f"static check failed: {label} ({needle!r})")


def main() -> int:
    _static_checks()
    _run_guard_tests()
    print("RUNTIME_ENV_GUARDS_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
