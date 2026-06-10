#!/usr/bin/env python3
"""QA-PAYMENT-DRYRUN-001: dry-run YooKassa provider regression checks."""
from __future__ import annotations

import importlib
import os
import sys
import types
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    for name in ("runtime_env", "yookassa_dryrun", "yookassa_payment"):
        full = f"shop_bot.{name}"
        if full in sys.modules:
            importlib.reload(sys.modules[full])
        else:
            mod = importlib.import_module(name)
            sys.modules[full] = mod
    return (
        sys.modules["shop_bot.runtime_env"],
        sys.modules["shop_bot.yookassa_dryrun"],
        sys.modules["shop_bot.yookassa_payment"],
    )


def _static_checks() -> None:
    dryrun_src = (BOT / "yookassa_dryrun.py").read_text(encoding="utf-8")
    pay_src = (BOT / "yookassa_payment.py").read_text(encoding="utf-8")
    for needle, label in (
        ("def should_use_payments_dry_run", "payments dry-run gate"),
        ("def dryrun_payment_create", "dryrun payment_create"),
        ("sandbox.invalid", "sandbox payment host"),
        ("should_use_payments_dry_run()", "wired in yookassa_payment"),
        ("class DryRunPayment", "dummy payment object"),
        ("confirmation_url", "redirect URL field"),
    ):
        if needle not in (dryrun_src + pay_src):
            raise AssertionError(f"static check failed: {label} ({needle!r})")
    for bad in ("https://yookassa.ru", "YOOKASSA_SECRET_KEY", "YOOKASSA_SHOP_ID"):
        if bad in dryrun_src:
            raise AssertionError(f"dry-run module must not embed production credential/host: {bad!r}")


def _run_tests() -> None:
    _re, dryrun, yk_pay = _reload_modules()

    prev = _set_env(BVPN_ENV="production", BVPN_QA_DRY_RUN_PAYMENTS="1")
    try:
        _re, dryrun, _ = _reload_modules()
        assert not dryrun.should_use_payments_dry_run()
    finally:
        _restore_env(prev)

    prev = _set_env(BVPN_ENV="staging", BVPN_QA_DRY_RUN_PAYMENTS=None)
    try:
        _re, _, yk_pay = _reload_modules()
        try:
            yk_pay.payment_create({"amount": {"value": "200.00", "currency": "RUB"}})
            raise AssertionError("staging without dry-run flag must be blocked")
        except _re.QaGuardError:
            pass
    finally:
        _restore_env(prev)

    prev = _set_env(BVPN_ENV="test", BVPN_QA_DRY_RUN_PAYMENTS="1")
    try:
        _re, dryrun, yk_pay = _reload_modules()
        assert dryrun.should_use_payments_dry_run()

        fake_payment = MagicMock()
        with patch("yookassa.Payment.create", fake_payment) as mock_create:
            payload = {
                "amount": {"value": "500.00", "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": "https://t.me/bot"},
                "capture": True,
                "description": "QA topup",
                "metadata": {"t": "topup", "user_id": 900000001, "amount": "500.00"},
            }
            idem = str(uuid.uuid4())
            payment = yk_pay.payment_create(payload, idem)

        mock_create.assert_not_called()
        assert payment.id.startswith("qa-pay-")
        assert payment.status == "pending"
        assert payment.amount["value"] == "500.00"
        assert payment.confirmation.confirmation_url.startswith("https://sandbox.invalid/pay/")
        dryrun.assert_dummy_payment_safe(payment)

        p2 = yk_pay.payment_create(payload, idem)
        assert p2.id == payment.id

        recurring_payload = {
            "amount": {"value": "200.00", "currency": "RUB"},
            "capture": True,
            "payment_method_id": "qa-pm-1",
            "description": "autopay",
            "metadata": {"t": "topup", "user_id": 1, "amount": "200.00"},
        }
        with patch("yookassa.Payment.create", mock_create):
            rec = yk_pay.payment_create(recurring_payload, "yk-autopay-1-202606")
        assert rec.id.startswith("qa-pay-")
        assert rec.confirmation is None
    finally:
        _restore_env(prev)


def main() -> int:
    _static_checks()
    _run_tests()
    print("YOOKASSA_DRYRUN_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
