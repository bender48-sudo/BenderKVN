# POSTDEPLOY — BILL-FIX-001 YooKassa reconcile idempotency

**Date:** 2026-06-09 ~22:15 UTC (AMS `20260609-221550`)  
**Target:** AMS `168.100.11.140` · **`remna-shop-bot`**  
**Approval:** Owner — push + controlled deploy BILL-FIX-001 only  
**Repo commit pushed:** `8b9923e` — `fix(billing): align yookassa reconcile idempotency key`  
**Rollback:** Not used (backups available)  
**Related:** [`AUDIT-2026-06-10-BILLING-PAYMENT-COMMERCIAL-READINESS.md`](AUDIT-2026-06-10-BILLING-PAYMENT-COMMERCIAL-READINESS.md) §7.1

---

## 1. Deploy scope (actual)

| File | Host path | Container path | Action |
|------|-----------|----------------|--------|
| `bot_src/payment_idempotency.py` | `/opt/remna-shop/src/shop_bot/payment_idempotency.py` | `/app/src/shop_bot/payment_idempotency.py` | **New** — canonical `yk:` helper |
| `bot_src/webhook_server/payment_queue.py` | `/opt/remna-shop/src/shop_bot/webhook_server/payment_queue.py` | `/app/src/shop_bot/webhook_server/payment_queue.py` | **Updated** — imports shared helper |
| `ops/reconcile_yookassa_topups_ams.py` | `/opt/remna-shop/ops/reconcile_yookassa_topups_ams.py` | `/app/ops/reconcile_yookassa_topups_ams.py` | **New on AMS** — dry-run default; legacy skip |

**Not touched:** Remna panel/users, Caddy, template PATCH, broadcast, mass-refresh, billing job, DB migration, portal static, other bot handlers, YooKassa write endpoints, callback replay, reconcile `--apply`.

---

## 2. Backups / rollback

| Asset | Backup path |
|-------|-------------|
| `payment_queue.py` (host) | `/opt/remna-shop/src/shop_bot/webhook_server/payment_queue.py.before-bill-fix-001-20260609-221550` |
| `payment_idempotency.py` | *(none — file did not exist pre-deploy)* |
| `reconcile_yookassa_topups_ams.py` | *(none — file did not exist pre-deploy)* |

**Rollback (manual):**

```bash
# AMS host
cp /opt/remna-shop/src/shop_bot/webhook_server/payment_queue.py.before-bill-fix-001-20260609-221550 \
   /opt/remna-shop/src/shop_bot/webhook_server/payment_queue.py
rm -f /opt/remna-shop/src/shop_bot/payment_idempotency.py
rm -f /opt/remna-shop/ops/reconcile_yookassa_topups_ams.py

docker cp /opt/remna-shop/src/shop_bot/webhook_server/payment_queue.py \
   remna-shop-bot:/app/src/shop_bot/webhook_server/payment_queue.py
docker exec remna-shop-bot rm -f /app/src/shop_bot/payment_idempotency.py
docker exec remna-shop-bot rm -f /app/ops/reconcile_yookassa_topups_ams.py
docker restart remna-shop-bot
```

---

## 3. Container / startup

| Check | Result |
|-------|--------|
| `remna-shop-bot` before deploy | **running** |
| `remna-shop-bot` after restart | **running** |
| Flask webhook port 1488 | **started** — no import traceback |
| `payment_queue` import in container | **PASS** |
| Secrets in log tail | **None observed** |

---

## 4. Canonical idempotency verification

| Check | Expected | Result |
|-------|----------|--------|
| `yookassa_topup_action_key()` present | yes | **yes** — `/app/src/shop_bot/payment_idempotency.py` |
| Canonical key format | `yk:{payment_id}` | **verified** — container returned `yk:test` |
| Webhook path uses shared helper | yes | **yes** — `payment_queue.py` imports `yookassa_topup_action_key` |
| Reconcile writes `yookassa:{id}` | no | **no write path** — legacy prefix read/skip only |
| Reconcile default mode | dry-run | **yes** — stderr `DRY_RUN` without `--apply` |
| `--apply` required for credits | yes | **yes** — `--help` documents `--apply` |

---

## 5. Tests / smokes run

### Local (pre-push)

| Command | Result |
|---------|--------|
| `python -m py_compile` (3 deploy files) | **PASS** |
| `python -m unittest tests.test_yookassa_topup_idempotency -v` | **10/10 PASS** |
| `python -m unittest tests.test_portal_cabinet_billing -v` | **12/12 PASS** |
| `git diff --check origin/product-referral-cabinet-ui-v1..HEAD` | **PASS** |

### AMS (post-deploy, read-only)

| Command | Result |
|---------|--------|
| `docker exec remna-shop-bot python -m py_compile` (3 files) | **PASS** |
| Canonical key import smoke | **PASS** (`yk:test`) |
| `payment_queue` import smoke | **PASS** |
| `reconcile_yookassa_topups_ams.py --help` | **PASS** |
| Reconcile dry-run execution | **SKIPPED** — would call YooKassa `Payment.list` (external read API); not required for this deploy |
| Log tail (30 lines) | **PASS** — clean startup after restart |

---

## 6. Explicit no-mutation confirmation

| Action | Executed? |
|--------|-----------|
| `reconcile_yookassa_topups_ams.py --apply` | **No** |
| Billing job / daily debit trigger | **No** |
| YooKassa write endpoints | **No** |
| Callback replay | **No** |
| Balance changes | **No** — no write commands run |
| Remna / Caddy / template PATCH | **No** |
| Broadcast / mass-refresh | **No** |

**Balance mutation check:** No aggregate before/after run; confirmation is procedural — no `--apply`, no billing job, no reconcile execution, no callback replay.

---

## 7. Push record

| Item | Value |
|------|-------|
| Branch | `product-referral-cabinet-ui-v1` |
| Pushed range | `209939a..8b9923e` |
| Post-push HEAD | local = origin = `8b9923e` |
| CI/auto-deploy triggered by push | **No** — manual scp + docker cp only |

---

## 8. Remaining paid blockers (unchanged)

1. **BILL-SMOKE-001** — controlled AMS top-up → balance + panel extend  
2. **BILL-SMOKE-002** — duplicate webhook POST → single credit  
3. **BILL-SMOKE-003** — expired wallet user top-up → access restored  
4. **BILL-SMOKE-004** — insufficient balance / `BOT_PAYMENTS_LIVE=0` debit guard  
5. **BILL-RUNBOOK-001** — payment succeeded but access not extended  
6. **P1-ADM-003** — admin payment/topup lookup  
7. **BILL-MON-001** — billing/payment monitoring  
8. Reconciliation admin view / export  

**G6 billing gate:** still **PARTIAL** until BILL-SMOKE-001..004 PASS.

---

## 9. Next recommended surface (do not start here)

- **BILL-UT-001/002** — unit tests for daily debit + topup idempotency in CI  
- **BILL-SMOKE-001** — prepare `ops/smoke_billing_commercial_ams.py` (owner-approved controlled users only)
