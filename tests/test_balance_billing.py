"""Offline unit tests for balance/day-rate billing math (BILL-UT-001 scope).

``config`` imports only ``shop_bot.public_urls`` (stdlib), so it loads without
aiogram. These tests lock the honest day-rate behaviour (e.g. 200 RUB ~= 29 days,
not 30) and the floor semantics, so copy and math cannot silently drift apart.
No live calls.
"""

from __future__ import annotations

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

from shop_bot.config import (  # noqa: E402
    DAILY_RATE,
    TOPUP_PRESETS,
    balance_to_days,
    topup_button_label,
)


class TestDailyRate(unittest.TestCase):
    def test_daily_rate_value(self) -> None:
        self.assertEqual(DAILY_RATE, 6.67)


class TestBalanceToDays(unittest.TestCase):
    def test_below_one_day_is_zero(self) -> None:
        self.assertEqual(balance_to_days(0), 0)
        self.assertEqual(balance_to_days(6.66), 0)

    def test_exactly_one_day(self) -> None:
        self.assertEqual(balance_to_days(6.67), 1)

    def test_floor_behavior(self) -> None:
        # 50 / 6.67 = 7.49 -> 7 whole days
        self.assertEqual(balance_to_days(50), 7)

    def test_200_is_honest_29_not_30(self) -> None:
        # CB-4 truth check: 200 / 6.67 = 29.98 -> floor 29. Copy must not claim 30.
        self.assertEqual(balance_to_days(200), 29)

    def test_2000_is_about_ten_months(self) -> None:
        self.assertEqual(balance_to_days(2000), 299)

    def test_monotonic_non_decreasing(self) -> None:
        prev = -1
        for rub in range(0, 2001, 50):
            d = balance_to_days(rub)
            self.assertGreaterEqual(d, prev)
            prev = d


class TestTopupLabels(unittest.TestCase):
    def test_label_matches_balance_to_days(self) -> None:
        for _key, (_name, _price, amount) in TOPUP_PRESETS.items():
            label = topup_button_label(amount)
            self.assertIn(str(balance_to_days(amount)), label)

    def test_200_preset_label_says_29(self) -> None:
        self.assertIn("29", topup_button_label(200))


if __name__ == "__main__":
    unittest.main()
