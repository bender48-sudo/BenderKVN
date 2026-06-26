"""BOT-QR-MISSING-KEY-UX-001: legacy key QR must not fail silently."""
from __future__ import annotations

import ast
import importlib
import sys
import types
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_BOT_SRC = _REPO / "bot_src"
_HANDLERS = _BOT_SRC / "handlers.py"


def _legacy_key_qr_error(inbound, connection_string: str | None) -> str | None:
    """Load helper from handlers.py without importing aiogram/yookassa."""
    if str(_BOT_SRC) not in sys.path:
        sys.path.insert(0, str(_BOT_SRC))
    user_messages = importlib.import_module("user_messages")
    tree = ast.parse(_HANDLERS.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_legacy_key_qr_error":
            ns: dict = {"user_messages": user_messages}
            exec(compile(ast.Module(body=[node], type_ignores=[]), "<handlers>", "exec"), ns)
            return ns["_legacy_key_qr_error"](inbound, connection_string)
    raise AssertionError("_legacy_key_qr_error not found in handlers.py")


def _show_qr_handler_source() -> ast.AsyncFunctionDef:
    tree = ast.parse(_HANDLERS.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "show_qr_handler":
            return node
    raise AssertionError("show_qr_handler not found")


class LegacyKeyQrErrorTests(unittest.TestCase):
    def test_ok_when_inbound_and_uri(self) -> None:
        user_messages = importlib.import_module("user_messages")
        self.assertIsNone(_legacy_key_qr_error(object(), "vless://x"))

    def test_inbound_missing(self) -> None:
        user_messages = importlib.import_module("user_messages")
        self.assertEqual(_legacy_key_qr_error(None, None), user_messages.ERR_INBOUND)

    def test_uri_missing(self) -> None:
        user_messages = importlib.import_module("user_messages")
        self.assertEqual(_legacy_key_qr_error(object(), None), user_messages.ERR_VLESS_BUILD)

    def test_uri_empty_string(self) -> None:
        user_messages = importlib.import_module("user_messages")
        self.assertEqual(_legacy_key_qr_error(object(), ""), user_messages.ERR_VLESS_BUILD)


class ShowQrHandlerStructureTests(unittest.TestCase):
    def test_handler_answers_on_qr_err(self) -> None:
        src = ast.unparse(_show_qr_handler_source())
        self.assertIn("_legacy_key_qr_error", src)
        self.assertIn("qr_err", src)
        self.assertIn("ERR_KEY_WRONG_USER", src)

    def test_no_silent_return_on_missing_inbound(self) -> None:
        """After inbound fetch, missing key must answer — not bare return."""
        src = ast.unparse(_show_qr_handler_source())
        idx = src.find("qr_err = _legacy_key_qr_error")
        self.assertGreater(idx, -1)
        tail = src[idx:]
        self.assertIn("if qr_err:", tail)
        self.assertIn("answer", tail)


if __name__ == "__main__":
    unittest.main()
