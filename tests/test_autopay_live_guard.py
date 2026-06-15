"""Offline structural test for the autopay live guard.

BILL-AUTOPAY-LIVE-GUARD-001. ``yookassa_autopay_scheduler`` imports aiogram, which
is not installed in the unit-test environment, so we inspect the source with
``ast`` (no execution, no live charges).
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_MOD = _REPO / "bot_src" / "yookassa_autopay_scheduler.py"


def _func(name: str) -> ast.AST:
    tree = ast.parse(_MOD.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found")


class TestAutopayLiveGuard(unittest.TestCase):
    def setUp(self) -> None:
        self.fn = _func("run_yookassa_autopay_batch")

    def test_guard_present_before_due_query(self) -> None:
        guard_line = None
        due_line = None
        for node in ast.walk(self.fn):
            if isinstance(node, ast.Name) and node.id == "BOT_PAYMENTS_LIVE":
                guard_line = node.lineno if guard_line is None else min(guard_line, node.lineno)
            if isinstance(node, ast.Call):
                func = node.func
                name = getattr(func, "id", None) or getattr(func, "attr", None)
                if name == "list_yookassa_autopay_due":
                    due_line = node.lineno if due_line is None else min(due_line, node.lineno)
        self.assertIsNotNone(guard_line, "BOT_PAYMENTS_LIVE guard missing")
        self.assertIsNotNone(due_line, "expected list_yookassa_autopay_due call")
        self.assertLess(
            guard_line,
            due_line,
            "BOT_PAYMENTS_LIVE must be checked before querying due charges",
        )

    def test_early_return_zero_when_not_live(self) -> None:
        # The guard branch must return (0) without charging.
        src = ast.get_source_segment(_MOD.read_text(encoding="utf-8"), self.fn)
        self.assertIsNotNone(src)
        self.assertIn("if not BOT_PAYMENTS_LIVE", src)
        self.assertIn("return 0", src)


if __name__ == "__main__":
    unittest.main()
