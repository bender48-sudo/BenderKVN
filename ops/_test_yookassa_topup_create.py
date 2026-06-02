#!/usr/bin/env python3
import os
import sys
import uuid

from yookassa import Configuration, Payment
from shop_bot.yookassa_payment import yookassa_receipt

sid = os.environ.get("YOOKASSA_SHOP_ID", "").strip()
sec = os.environ.get("YOOKASSA_SECRET_KEY", "").strip()
if not sid or not sec:
    print("FAIL: missing YOOKASSA env", file=sys.stderr)
    raise SystemExit(1)
Configuration.account_id = sid
Configuration.secret_key = sec
amt = "200.00"
desc = "Пополнение баланса BenderVPN 200 ₽"
p = Payment.create(
    {
        "amount": {"value": amt, "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": "https://t.me/"},
        "capture": True,
        "description": desc,
        "receipt": yookassa_receipt(desc, amt, 1),
        "metadata": {"t": "topup", "user_id": 1, "amount": amt},
    },
    uuid.uuid4(),
)
print("TOPUP_PAYMENT_OK", p.id[:16])
