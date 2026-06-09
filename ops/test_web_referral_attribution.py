#!/usr/bin/env python3
"""P1-REF-001: web email referral attribution regression checks."""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"


def _bootstrap_shop_bot(workdir: str) -> None:
    os.chdir(workdir)
    if str(BOT) not in sys.path:
        sys.path.insert(0, str(BOT))

    pkg = types.ModuleType("shop_bot")
    pkg.__path__ = [str(BOT)]  # type: ignore[attr-defined]
    sys.modules["shop_bot"] = pkg

    public_urls = importlib.import_module("public_urls")
    sys.modules["shop_bot.public_urls"] = public_urls
    pkg.public_urls = public_urls

    config = importlib.import_module("config")
    sys.modules["shop_bot.config"] = config
    pkg.config = config

    dm = types.ModuleType("shop_bot.data_manager")
    sys.modules["shop_bot.data_manager"] = dm
    pkg.data_manager = dm

    database = importlib.import_module("database")
    sys.modules["shop_bot.data_manager.database"] = database
    dm.database = database

    schema_migrations = importlib.import_module("schema_migrations")
    sys.modules["shop_bot.schema_migrations"] = schema_migrations
    pkg.schema_migrations = schema_migrations

    modules_pkg = types.ModuleType("shop_bot.modules")
    sys.modules["shop_bot.modules"] = modules_pkg
    pkg.modules = modules_pkg

    remnawave = types.ModuleType("shop_bot.modules.remnawave_api")
    remnawave.provision_key = AsyncMock()
    remnawave.get_user_by_email = AsyncMock(return_value=None)
    remnawave.get_user_by_telegram_id = AsyncMock(return_value=None)
    remnawave.remna_client_session = AsyncMock()
    remnawave._fetch_json = AsyncMock(return_value={})
    sys.modules["shop_bot.modules.remnawave_api"] = remnawave
    modules_pkg.remnawave_api = remnawave

    web_trial_db = importlib.import_module("web_trial_db")
    sys.modules["shop_bot.web_trial_db"] = web_trial_db
    pkg.web_trial_db = web_trial_db

    web_referral = importlib.import_module("web_referral")
    sys.modules["shop_bot.web_referral"] = web_referral
    pkg.web_referral = web_referral

    web_tg_bind = importlib.import_module("web_tg_bind")
    sys.modules["shop_bot.web_tg_bind"] = web_tg_bind
    pkg.web_tg_bind = web_tg_bind

    portal_web_trial = importlib.import_module("portal_web_trial")
    sys.modules["shop_bot.portal_web_trial"] = portal_web_trial
    pkg.portal_web_trial = portal_web_trial


def _close_web_trial_pool() -> None:
    from shop_bot.web_trial_db import _pool  # noqa: PLC2701

    if _pool is None:
        return
    while True:
        try:
            conn = _pool.get_nowait()
        except Exception:
            break
        conn.close()
    import shop_bot.web_trial_db as wtd

    wtd._pool = None


def _static_checks() -> None:
    webhook = (BOT / "webhook_server" / "app.py").read_text(encoding="utf-8")
    trial = (BOT / "portal_web_trial.py").read_text(encoding="utf-8")
    bind = (BOT / "web_tg_bind.py").read_text(encoding="utf-8")
    referral = (BOT / "web_referral.py").read_text(encoding="utf-8")

    for needle, label in (
        ('ref_code = (data.get("ref_code")', "webhook ref_code extract"),
        ("issue_web_trial(email, phone, ref_code)", "webhook passes ref_code"),
        ("ref_code: str | None = None", "issue_web_trial signature"),
        ("apply_web_referral(ref_code, web_uid)", "trial links referral"),
        ("UPDATE referrals SET referred_user_id", "bind migrates referrals"),
        ("normalize_portal_ref_code", "referral normalizer"),
    ):
        if needle not in (webhook + trial + bind + referral):
            raise AssertionError(f"static check failed: {label} ({needle!r})")

    if "grant_referrer_bonus" in trial:
        raise AssertionError("portal_web_trial must not grant referral bonus")


def _db_tests(workdir: str) -> None:
    _bootstrap_shop_bot(workdir)
    from shop_bot.data_manager.database import (
        ensure_user_ref_code,
        get_user,
        initialize_db,
        register_user_if_not_exists,
    )
    from shop_bot.web_referral import apply_web_referral, normalize_portal_ref_code
    from shop_bot.web_tg_bind import merge_web_user_to_telegram
    from shop_bot.web_trial_db import record_web_trial_claim, reserve_web_trial_email

    initialize_db()

    assert normalize_portal_ref_code("  abcDEF12  ") == "abcDEF12"
    assert normalize_portal_ref_code("ref_tokenX") == "tokenX"
    assert normalize_portal_ref_code("") is None
    assert normalize_portal_ref_code("bad code!") is None

    register_user_if_not_exists(111, "referrer")
    ref = ensure_user_ref_code(111)
    assert ref

    web_uid = -999888777
    assert reserve_web_trial_email("merge@test.com", web_uid)
    register_user_if_not_exists(web_uid, "webtrial")
    assert apply_web_referral(ref, web_uid)
    record_web_trial_claim("merge@test.com", web_uid, "panel@test.com", None)
    row = get_user(web_uid)
    assert row and row.get("referred_by") == ref
    assert not apply_web_referral(ref, web_uid)

    register_user_if_not_exists(222, "tguser")
    result = merge_web_user_to_telegram(web_uid, 222, "tguser")
    assert result.get("ok"), result
    tg = get_user(222)
    assert tg and tg.get("referred_by") == ref
    assert get_user(web_uid) is None


async def _trial_integration(workdir: str) -> None:
    _bootstrap_shop_bot(workdir)
    from shop_bot.data_manager.database import (
        ensure_user_ref_code,
        get_user,
        initialize_db,
        register_user_if_not_exists,
    )
    from shop_bot.portal_web_trial import issue_web_trial

    initialize_db()
    register_user_if_not_exists(333, "ref2")
    ref2 = ensure_user_ref_code(333)

    fake_expire = "2099-12-31T00:00:00.000Z"
    with patch(
        "shop_bot.portal_web_trial.provision_key",
        new_callable=AsyncMock,
        return_value=("uri", fake_expire, "uuid-1", "https://example/sub"),
    ):
        out = await issue_web_trial("newuser@example.com", None, ref_code=ref2)

    assert out.get("ok"), out
    assert out.get("referral_linked") is True
    assert out.get("days") == 1
    em_uid = out.get("web_user_id")
    assert em_uid
    row = get_user(int(em_uid))
    assert row and row.get("referred_by") == ref2


def main() -> int:
    _static_checks()
    orig_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _db_tests(tmp)
            _close_web_trial_pool()
            asyncio.run(_trial_integration(tmp))
            _close_web_trial_pool()
        finally:
            os.chdir(orig_cwd)
    print("WEB_REFERRAL_ATTRIBUTION_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
