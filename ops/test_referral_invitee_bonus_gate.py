#!/usr/bin/env python3
"""P1-REF-002: hidden invitee +3d legacy purchase bonus gated OFF; referrer +1m deferred."""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"


def _bootstrap_shop_bot(workdir: str) -> None:
    os.chdir(workdir)
    if str(BOT) not in sys.path:
        sys.path.insert(0, str(BOT))

    pkg = types.ModuleType("shop_bot")
    pkg.__path__ = [str(BOT)]  # type: ignore[attr-defined]
    sys.modules["shop_bot"] = pkg

    config = importlib.import_module("config")
    sys.modules["shop_bot.config"] = config
    pkg.config = config

    dm = types.ModuleType("shop_bot.data_manager")
    sys.modules["shop_bot.data_manager"] = dm
    pkg.data_manager = dm

    database = importlib.import_module("database")
    sys.modules["shop_bot.data_manager.database"] = database
    dm.database = database


def _static_checks() -> None:
    cfg_src = (BOT / "config.py").read_text(encoding="utf-8")
    handlers_src = (BOT / "handlers.py").read_text(encoding="utf-8")

    for needle, label in (
        ("REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED", "invitee bonus flag"),
        ("REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_DAYS", "invitee bonus days"),
        ("REFERRAL_REFERRER_FIRST_PAYMENT_REWARD_ENABLED", "referrer reward flag"),
        ("REFERRAL_REFERRER_FIRST_PAYMENT_REWARD_MONTHS", "referrer reward months"),
        ("def referral_invitee_first_purchase_bonus_days", "invitee bonus gate helper"),
        ("referral_invitee_first_purchase_bonus_days(referrer_code)", "handlers uses invitee gate"),
        ("REF-BONUS-001", "target referrer reward documented"),
    ):
        if needle not in (cfg_src + handlers_src):
            raise AssertionError(f"static check failed: {label} ({needle!r})")

    if 'days_to_add += 3' in handlers_src:
        raise AssertionError("handlers.py must not hardcode days_to_add += 3")

    if "REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED" not in cfg_src:
        raise AssertionError("config must define REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED")


def _gate_tests() -> None:
    from shop_bot.config import (
        REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_DAYS,
        REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED,
        REFERRAL_REFERRER_FIRST_PAYMENT_REWARD_ENABLED,
        REFERRAL_REFERRER_FIRST_PAYMENT_REWARD_MONTHS,
        referral_invitee_first_purchase_bonus_days,
    )

    assert REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED is False
    assert REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_DAYS == 3
    assert REFERRAL_REFERRER_FIRST_PAYMENT_REWARD_ENABLED is False
    assert REFERRAL_REFERRER_FIRST_PAYMENT_REWARD_MONTHS == 1
    assert referral_invitee_first_purchase_bonus_days("abc123") == 0
    assert referral_invitee_first_purchase_bonus_days(None) == 0
    assert referral_invitee_first_purchase_bonus_days("") == 0

    prev_enabled = os.environ.get("REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED")
    prev_days = os.environ.get("REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_DAYS")
    try:
        os.environ["REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED"] = "1"
        os.environ["REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_DAYS"] = "3"
        importlib.reload(importlib.import_module("shop_bot.config"))
        cfg = importlib.import_module("shop_bot.config")
        assert cfg.REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED is True
        assert cfg.referral_invitee_first_purchase_bonus_days("abc123") == 3

        os.environ["REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_DAYS"] = "0"
        importlib.reload(cfg)
        assert cfg.referral_invitee_first_purchase_bonus_days("abc123") == 0
    finally:
        if prev_enabled is None:
            os.environ.pop("REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED", None)
        else:
            os.environ["REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED"] = prev_enabled
        if prev_days is None:
            os.environ.pop("REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_DAYS", None)
        else:
            os.environ["REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_DAYS"] = prev_days
        importlib.reload(importlib.import_module("shop_bot.config"))


def _referral_counter_tests(workdir: str) -> None:
    _bootstrap_shop_bot(workdir)
    from shop_bot.data_manager.database import (
        count_referrals,
        ensure_user_ref_code,
        initialize_db,
        link_referral,
        register_user_if_not_exists,
    )

    initialize_db()
    register_user_if_not_exists(501, "inviter")
    ref = ensure_user_ref_code(501)
    assert ref

    register_user_if_not_exists(502, "invitee_a")
    register_user_if_not_exists(503, "invitee_b")
    assert link_referral(ref, 502)
    assert link_referral(ref, 503)
    assert count_referrals(ref) == 2

    register_user_if_not_exists(504, "solo")
    assert count_referrals(ensure_user_ref_code(504)) == 0


def main() -> int:
    _static_checks()
    orig_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _bootstrap_shop_bot(tmp)
            _gate_tests()
            _referral_counter_tests(tmp)
        finally:
            os.chdir(orig_cwd)
    print("REFERRAL_INVITEE_BONUS_GATE_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
