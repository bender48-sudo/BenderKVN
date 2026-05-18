"""Auto-renew billing (P6-RED-PAY-03): deduct balance before panel extend."""
from __future__ import annotations

from shop_bot.config import DAILY_RATE, PLANS


def plan_renew_cost(plan_id: str) -> tuple[float, int, int]:
    """Return (cost_rub, months, extend_days) for legacy plan id on key."""
    _name, price_rub, months = PLANS.get(plan_id or "buy_1_month", (None, None, 1))
    months_i = int(months or 1)
    extend_days = months_i * 30
    if price_rub is not None:
        cost = float(price_rub)
    else:
        cost = extend_days * DAILY_RATE
    return cost, months_i, extend_days


def balance_covers_renew(balance: float, cost_rub: float) -> bool:
    return cost_rub > 0 and balance >= cost_rub
