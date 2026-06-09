"""BILL-FIX-001: YooKassa top-up idempotency key parity (webhook vs reconcile)."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_BOT_SRC = _REPO / "bot_src"
if str(_BOT_SRC) not in sys.path:
    sys.path.insert(0, str(_BOT_SRC))
if "shop_bot" not in sys.modules:
    _pkg = types.ModuleType("shop_bot")
    _pkg.__path__ = [str(_BOT_SRC)]  # type: ignore[attr-defined]
    sys.modules["shop_bot"] = _pkg

from shop_bot.payment_idempotency import (  # noqa: E402
    LEGACY_YOOKASSA_RECONCILE_PREFIX,
    YOOKASSA_TOPUP_ACTION_PREFIX,
    yookassa_topup_action_key,
)


def _reconcile_already_credited(user_id: int, payment_id: str, has_action) -> bool:
    """Mirror ops/reconcile_yookassa_topups_ams.py::_already_credited."""
    canonical = yookassa_topup_action_key(payment_id)
    if has_action(user_id, canonical):
        return True
    legacy = f"{LEGACY_YOOKASSA_RECONCILE_PREFIX}{payment_id}"
    return has_action(user_id, legacy)


class TestYookassaTopupActionKey(unittest.TestCase):
    def test_canonical_prefix(self) -> None:
        self.assertEqual(YOOKASSA_TOPUP_ACTION_PREFIX, "yk:")
        self.assertEqual(yookassa_topup_action_key("pay-abc-123"), "yk:pay-abc-123")

    def test_webhook_queue_uses_same_key(self) -> None:
        _ws = types.ModuleType("shop_bot.webhook_server")
        sys.modules["shop_bot.webhook_server"] = _ws
        _ws.__path__ = [str(_BOT_SRC / "webhook_server")]  # type: ignore[attr-defined]
        _dm = types.ModuleType("shop_bot.data_manager")
        sys.modules["shop_bot.data_manager"] = _dm
        _db = types.ModuleType("shop_bot.data_manager.database")
        for _fn in (
            "claim_webhook_delivery",
            "mark_webhook_done",
            "mark_webhook_failed",
            "mark_webhook_processing",
        ):
            setattr(_db, _fn, lambda *a, **k: None)
        sys.modules["shop_bot.data_manager.database"] = _db
        _dm.database = _db
        _pr = types.ModuleType("shop_bot.webhook_server.payload_redact")
        _pr.redact_webhook_payload = lambda source, payload: payload
        sys.modules["shop_bot.webhook_server.payload_redact"] = _pr
        _pav = types.ModuleType("shop_bot.webhook_server.payment_amount_verify")
        _pav.verify_yookassa_amount = lambda e: True
        _pav.verify_crypto_amount = lambda d: True
        sys.modules["shop_bot.webhook_server.payment_amount_verify"] = _pav

        from shop_bot.webhook_server.payment_queue import idempotency_key_yookassa

        event = {"object": {"id": "2d8f1c00-0001-5000-9000-1a2b3c4d5e6f"}}
        self.assertEqual(
            idempotency_key_yookassa(event),
            yookassa_topup_action_key("2d8f1c00-0001-5000-9000-1a2b3c4d5e6f"),
        )

    def test_empty_payment_id_raises(self) -> None:
        with self.assertRaises(ValueError):
            yookassa_topup_action_key("")

    def test_reconcile_script_uses_canonical_helper(self) -> None:
        text = (_REPO / "ops" / "reconcile_yookassa_topups_ams.py").read_text(encoding="utf-8")
        self.assertIn("yookassa_topup_action_key", text)
        self.assertIn("payment_idempotency", text)
        self.assertNotIn('f"yookassa:{pid}"', text)

    def test_reconcile_defaults_to_dry_run(self) -> None:
        text = (_REPO / "ops" / "reconcile_yookassa_topups_ams.py").read_text(encoding="utf-8")
        self.assertIn("--apply", text)
        self.assertIn("DRY_RUN", text)

    def test_legacy_prefix_documented(self) -> None:
        self.assertEqual(LEGACY_YOOKASSA_RECONCILE_PREFIX, "yookassa:")

    def test_canonical_yk_action_prevents_reconcile_double_credit(self) -> None:
        recorded = {"yk:pay-dup"}

        def has_action(_uid: int, key: str) -> bool:
            return key in recorded

        self.assertTrue(_reconcile_already_credited(1, "pay-dup", has_action))

    def test_legacy_yookassa_action_also_skips_reconcile(self) -> None:
        recorded = {"yookassa:pay-legacy"}

        def has_action(_uid: int, key: str) -> bool:
            return key in recorded

        self.assertTrue(_reconcile_already_credited(1, "pay-legacy", has_action))

    def test_uncredited_payment_not_skipped(self) -> None:
        def has_action(_uid: int, key: str) -> bool:
            return False

        self.assertFalse(_reconcile_already_credited(1, "pay-new", has_action))

    def test_process_topup_accepts_yk_prefix(self) -> None:
        text = (_REPO / "bot_src" / "handlers.py").read_text(encoding="utf-8")
        self.assertIn('"yk:"', text)
        self.assertIn("crypto:", text)


if __name__ == "__main__":
    unittest.main()
