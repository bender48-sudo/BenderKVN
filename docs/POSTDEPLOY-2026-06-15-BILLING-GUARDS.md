# Post-deploy: billing safety guards (AMS)

**Date:** 2026-06-15  
**Branch:** `product-referral-cabinet-ui-v1` @ `aaae0c8`  
**Target:** AMS `remna-shop-bot` (hot-patch, bot-only)  
**Scope:** BILL-TERMS-GUARD-001/002, TRIAL-GRANT-ATOMIC-001, BILL-WEBHOOK-CLAIM-TOCTOU-001, BILL-AUTOPAY-LIVE-GUARD-001  

## Deploy method

Minimal hot-patch (not full `deploy-bot-handlers-ams.ps1` — avoids `.env` Remna URL mutation and unrelated surfaces):

| File | Host path | Notes |
|------|-----------|-------|
| `handlers.py` | `/opt/remna-shop/src/shop_bot/bot/handlers.py` | Prod-compat: `Payment.create`, no `referral_invitee_*` import |
| `database.py` | `/opt/remna-shop/src/shop_bot/data_manager/database.py` | Atomic webhook claim |
| `yookassa_autopay_scheduler.py` | `/opt/remna-shop/src/shop_bot/yookassa_autopay_scheduler.py` | `BOT_PAYMENTS_LIVE` guard |

Rollback: restore `*.before-bill-guards-*` backups on AMS host + `docker cp` + `docker compose restart remna-shop-bot`.

## Incidents during deploy

1. **First handlers deploy** — `ImportError: payment_create` (branch handlers vs live `yookassa_payment.py`). Rolled back; fixed in `79fa7ce` (`Payment.create`).
2. **Second handlers deploy** — `ImportError: referral_invitee_first_purchase_bonus_days`. Rolled back; fixed in `aaae0c8` (invitee bonus gated off on hot-patch).

## Smoke

```bash
docker exec remna-shop-bot python /tmp/smoke_billing_guards_ams.py
# expect: BILLING_GUARDS_SMOKE_OK
```

Results (2026-06-15): `LEGAL_OK=True`, webhook claim atomic OK, autopay guard present, handlers guard markers OK, container `running`.

**Not run:** live terms UX on owner Telegram account; trial grant on live user; YooKassa charge; `BILL-SMOKE-001..004` full suite.

## Gates (unchanged)

- Small paid beta / automated paid pilot / commercial launch: **NO-GO** (BILL-SMOKE full suite, kopeks decision, G4 bind, capacity, client smokes).
