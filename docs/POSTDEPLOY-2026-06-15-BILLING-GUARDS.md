# Post-deploy: billing safety guards (AMS)

**Date:** 2026-06-15 (smoke update 2026-06-16)
**Branch:** `product-referral-cabinet-ui-v1` @ `118a61a`+
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

Re-check (2026-06-16): container `Up`, structural smoke **PASS**, `BOT_PAYMENTS_LIVE=true` (autopay batch **not** run).

### LIVE-TERMS-UX-SMOKE-001

| Layer | Status | Notes |
|-------|--------|-------|
| Offline handler harness | **PASS** | `ops/smoke_terms_guard_ux_offline.py` — cases 1–6 on QA DB; no Telegram/YooKassa/Remna persist |
| Live owner Telegram taps | **NOT RUN** | Requires owner test account taps; use matrix below + `ops/smoke_live_terms_guard_ams.py --check-user` after setting `BVPN_TERMS_SMOKE_TG_ID` on AMS (read-only) |

Owner manual matrix (stop before payment URL / trial provision):

1. Unaccepted user → `get_trial` → terms prompt; no key / no `trial_used`
2. Unaccepted → top-up → terms; no YooKassa payment
3. Unaccepted → enable autorenew → terms; no bind payment
4. Stale promo/wizard callback → terms first
5. Accept terms → trial/top-up entry → passes guard; **STOP** before pay/provision
6. Accepted user disable autorenew → no terms re-prompt

**Not run:** live trial grant on prod user; YooKassa charge; `BILL-SMOKE-001..004` full suite.

## Gates (unchanged)

- Small paid beta / automated paid pilot / commercial launch: **NO-GO** (BILL-SMOKE full suite, kopeks decision, G4 bind, capacity, client smokes).
