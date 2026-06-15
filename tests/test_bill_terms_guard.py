"""Offline structural tests for billing safety guards.

BILL-TERMS-GUARD-001 + TRIAL-GRANT-ATOMIC-001 + BILL-TERMS-GUARD-002.

`bot_src/handlers.py` imports aiogram/aiohttp/qrcode which are not installed in
the unit-test environment, so (like ``test_yookassa_topup_idempotency`` does) we
inspect the source with ``ast`` instead of importing the module. ``ast`` parses
without executing imports, which keeps these tests fast, offline, and free of any
live Telegram / YooKassa / Remna calls.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_HANDLERS = _REPO / "bot_src" / "handlers.py"

# Money / trial / wizard / promo / autopay-bind entry callbacks that must enforce
# terms acceptance before doing anything (BILL-TERMS-GUARD-001 + 002).
_GUARDED_HANDLERS = (
    "trial_period_handler",
    "connect_vpn_wizard_start",
    "connect_vpn_wizard_device",
    "connect_vpn_wizard_chat",
    "show_topup_handler",
    "topup_select_handler",
    "topup_custom_handler",
    "pay_yookassa_topup_handler",
    "choose_payment_method_handler",
    "create_yookassa_payment_handler",
    "create_crypto_payment_handler",
    "buy_traffic_pack",
    "toggle_autorenew_handler",
    "enter_promo_start",
)

_GUARD_NAME = "_ensure_terms_callback"


def _module() -> ast.Module:
    return ast.parse(_HANDLERS.read_text(encoding="utf-8"))


def _functions(tree: ast.Module) -> dict[str, ast.AST]:
    found: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.setdefault(node.name, node)
    return found


def _call_names(node: ast.AST) -> list[tuple[str, int]]:
    """Return (callee_name, lineno) for every call inside node."""
    calls: list[tuple[str, int]] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            if isinstance(func, ast.Name):
                calls.append((func.id, sub.lineno))
            elif isinstance(func, ast.Attribute):
                calls.append((func.attr, sub.lineno))
    return calls


def _first_statement_line(node: ast.AST) -> int | None:
    body = getattr(node, "body", None)
    if not body:
        return None
    first = body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        if body[1:]:
            return body[1].lineno
    return first.lineno


class TestTermsGuardExists(unittest.TestCase):
    def setUp(self) -> None:
        self.funcs = _functions(_module())

    def test_callback_terms_guard_defined(self) -> None:
        self.assertIn(
            _GUARD_NAME,
            self.funcs,
            "callback terms guard helper must exist for inline money/trial paths",
        )

    def test_guard_resolves_identity_from_callback_user(self) -> None:
        guard = self.funcs[_GUARD_NAME]
        src = ast.get_source_segment(_HANDLERS.read_text(encoding="utf-8"), guard)
        self.assertIsNotNone(src)
        # Identity must come from callback.from_user (callback.message.from_user is
        # the bot), otherwise the gate checks the wrong account.
        self.assertIn("callback.from_user.id", src)

    def test_accepted_users_pass_through_without_prompt(self) -> None:
        guard = self.funcs[_GUARD_NAME]
        src = ast.get_source_segment(_HANDLERS.read_text(encoding="utf-8"), guard)
        self.assertIsNotNone(src)
        self.assertIn('user_data.get("agreed_to_terms")', src)
        self.assertIn("return True", src)


class TestGuardedHandlers(unittest.TestCase):
    def setUp(self) -> None:
        self.funcs = _functions(_module())

    def test_all_money_handlers_present(self) -> None:
        for name in _GUARDED_HANDLERS:
            self.assertIn(name, self.funcs, f"missing handler {name}")

    def test_money_handlers_call_terms_guard(self) -> None:
        for name in _GUARDED_HANDLERS:
            node = self.funcs[name]
            callees = {c for c, _ in _call_names(node)}
            self.assertIn(
                _GUARD_NAME,
                callees,
                f"{name} must enforce terms via {_GUARD_NAME} before acting",
            )

    def test_guard_is_early_in_handler(self) -> None:
        """Stale keyboards must hit the guard before any side effect."""
        # toggle_autorenew: disable path is intentionally unguarded; enable/bind gated later.
        skip_early = {"toggle_autorenew_handler"}
        for name in _GUARDED_HANDLERS:
            if name in skip_early:
                continue
            node = self.funcs[name]
            calls = _call_names(node)
            guard_lines = [ln for c, ln in calls if c == _GUARD_NAME]
            self.assertTrue(guard_lines, f"{name} missing terms guard")
            first_body = _first_statement_line(node)
            self.assertIsNotNone(first_body)
            # Guard must be among the first statements (after imports inside fn).
            self.assertLessEqual(
                min(guard_lines),
                first_body + 8,
                f"{name} must call terms guard near the top (stale keyboard bypass)",
            )

    def test_guard_runs_before_payment_creation(self) -> None:
        """The terms guard must precede any Payment.create call in pay handlers."""
        for name in ("create_yookassa_payment_handler", "pay_yookassa_topup_handler"):
            node = self.funcs[name]
            calls = _call_names(node)
            guard_lines = [ln for c, ln in calls if c == _GUARD_NAME]
            pay_lines = [ln for c, ln in calls if c == "create"]
            # Payment.create() -> attr "create"
            self.assertTrue(guard_lines, f"{name} missing terms guard")
            self.assertTrue(pay_lines, f"{name} expected to create a payment")
            self.assertLess(
                min(guard_lines),
                min(pay_lines),
                f"{name} must check terms before creating a payment",
            )

    def test_toggle_autorenew_guard_before_bind_payment(self) -> None:
        node = self.funcs["toggle_autorenew_handler"]
        calls = _call_names(node)
        guard_lines = [ln for c, ln in calls if c == _GUARD_NAME]
        bind_lines = [ln for c, ln in calls if c == "create_bind_payment"]
        self.assertTrue(guard_lines, "toggle_autorenew must be terms-gated")
        self.assertTrue(bind_lines, "toggle_autorenew may create bind payment")
        self.assertLess(
            min(guard_lines),
            min(bind_lines),
            "terms guard must precede create_bind_payment in toggle_autorenew",
        )


class TestTrialGrantAtomic(unittest.TestCase):
    def setUp(self) -> None:
        self.funcs = _functions(_module())
        self.trial = self.funcs["trial_period_handler"]

    def test_trial_used_set_after_key_persisted(self) -> None:
        calls = _call_names(self.trial)
        add_key = [ln for c, ln in calls if c == "add_new_key"]
        set_trial = [ln for c, ln in calls if c == "set_trial_used"]
        self.assertTrue(add_key, "trial must persist a key via add_new_key")
        self.assertTrue(set_trial, "trial must set the trial_used flag")
        self.assertGreater(
            min(set_trial),
            min(add_key),
            "set_trial_used must run AFTER add_new_key so a crash never leaves "
            "trial_used=1 without a key",
        )

    def test_no_early_reset_in_trial_handler(self) -> None:
        callees = {c for c, _ in _call_names(self.trial)}
        self.assertNotIn(
            "reset_trial_used",
            callees,
            "trial flag is now set only after success, so reset_trial_used must "
            "not run in the trial handler (it could hand out a second trial)",
        )


if __name__ == "__main__":
    unittest.main()
