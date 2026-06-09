# AUDIT — Billing & Payment Commercial Readiness (BILL-001 / LAUNCH-003)

**Date:** 2026-06-10  
**Mode:** audit only · no deploy · no prod mutation · no billing job · no DB write  
**Branch:** `product-referral-cabinet-ui-v1` @ `92a249a`  
**Parent:** [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md) — G6 blocker  
**Product facts:** 6.67 ₽/day **account-level**; multi-device 6.67×N **not implemented**; legacy/manual bypass documented

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| **Is billing logic implemented?** | **Yes** — wallet top-up, daily debit, panel sync, profile classification, YooKassa webhook queue |
| **Is it commercially audited?** | **This pass** — static code + prior postdeploy smoke; **no live money-flow matrix on prod** |
| **G6 status after audit** | **PARTIAL** — architecture sound; **gaps in live proof, tests, reconciliation, refund path** |
| **Manual paid pilot (whitelist + owner reconciliation)** | **CONDITIONAL** — only with explicit controls (see §10) |
| **Automated paid pilot** | **NO-GO** |
| **Open paid launch** | **NO-GO** |

**Bottom line:** Core money path is **engineered with idempotency layers**, but **commercial readiness requires live smokes + reconciliation tooling + support runbooks** before automated paid traffic.

**BILL-FIX-001 (repo):** Reconcile script aligned to canonical `yk:{payment_id}` via `shop_bot/payment_idempotency.py`; default **dry-run**; legacy `yookassa:` skip preserved. **Prod not mutated** — do **not** run `--apply` on production without separate explicit approval.

---

## 2. Paid launch verdict

| Launch mode | Verdict | Condition |
|-------------|---------|-----------|
| **F&F / no payment** | **GO** | Trial path only |
| **Manual paid pilot** (owner verifies each payment) | **CONDITIONAL** | Whitelist ≤10 users; manual balance check; no reconcile script until key fix |
| **Automated paid pilot** (YooKassa self-serve top-up) | **NO-GO** | Missing live idempotency smokes + admin reconciliation |
| **Open paid launch** | **NO-GO** | + monitoring, CI, copy audit, dispute runbook |

---

## 3. Money-flow map

| Step | Code path | DB / state | External | Logs | Failure mode | Support action |
|------|-----------|------------|----------|------|--------------|----------------|
| **1. TG trial start** | `handlers.trial_period_handler` → `provision_key` 90d | `users.trial_used`, `vpn_keys` row | Remna panel | `log_action` trial | Panel timeout | Manual provision |
| **2. User opens top-up** | `show_topup_handler` → preset/custom | — | — | `topup_custom_amount` | `BOT_PAYMENTS_LIVE=0` hides pay | Enable env on AMS |
| **3. Payment created** | `pay_yookassa_topup_handler` → `Payment.create` metadata `t=topup` | — | YooKassa API | error log | Create fails → user message | Retry / support |
| **4. YooKassa callback** | Flask webhook → `PaymentWebhookQueue.submit` → `claim_webhook_delivery` | `webhook_deliveries` idempotency | YooKassa POST | duplicate/in_progress log | Queue DLQ `mark_webhook_failed` | Check webhook_deliveries; manual reconcile **carefully** |
| **5. Amount verify** | `verify_yookassa_amount` | — | — | mismatch error | Webhook rejected — **no credit** | Fix metadata; replay only via reconcile ops |
| **6. Balance credited** | `process_topup_payment` → `add_balance` | `users.balance` += amount | — | `topup` action | Credited even if sync fails | See step 7 |
| **7. Daily waive same day** | `waive_daily_charge_today` | `user_actions` `daily_balance:DATE` = `waived_topup` | — | — | — | — |
| **8. Panel sync** | `sync_panel_access_from_balance` → `sync_panel_from_balance` or new key | `vpn_keys.expiry`, Remna `expireAt` | Remna API | warning if local key update fails | **Balance credited, access not extended** — user sees ⚠️ in TG | Manual panel extend; `reconcile` not substitute |
| **9. Idempotency record** | `log_action(user_id, "yk:{payment_id}", amount)` | `user_actions` | — | duplicate ignored log | Duplicate webhook → **no second credit** | — |
| **10. Profile becomes wallet** | `subscription_profile.is_paid_wallet_user` (balance ≥6.67 OR `topup` action OR `total_spent>0`) | — | — | — | User with expired trial + no topup stays trial/silent | Top-up once |
| **11. Daily billing tick** | `scheduler._poll_vpn_user` (~5 min batch) → `process_daily_balance_user` | — | Remna `get_user_by_telegram_id` | `daily balance insufficient` | Scheduler exception → skip user this cycle | Check scheduler logs |
| **12. Legacy gate** | `access_profile` → `legacy` if panel year ≥2030 or >400d | — | Panel expireAt | — | **No daily debit** | Explain legacy in cabinet |
| **13. Daily debit** | `charge_daily_balance_if_due` | `users.balance` −6.67; `user_actions` `daily_balance:DATE` | — | `insufficient` | Balance &lt; 6.67 → no deduct, logged insufficient | User top-up |
| **14. Post-debit sync** | `sync_panel_from_balance` — `expireAt = now + floor(balance/6.67)` days | `vpn_keys[0]` only | Remna | — | Multi-key: only primary synced | Support |
| **15. Low balance notify** | `days_left_for_notifications` → wallet messages | `last_expiry_notified` | TG bot | notification log | User ignores → access lapses | Top-up CTA |
| **16. Expired wallet** | `balance_to_days=0` → panel expire near now | Cabinet `billing_profile=expired` | — | EXPIRED notify | VPN stops when panel expires | Top-up restores via step 6–8 |
| **17. Autopay bind/renew** | `yookassa_autopay` + scheduler `_yookassa_autopay_loop` | `yookassa_autopay_*` columns | YooKassa recurring | autopay error log | Card charge fails → autopay disabled + user msg | Re-bind card |
| **18. Legacy plan purchase** | `process_successful_payment` (non-topup metadata) | extend/new key + months | Remna | purchase log | Panel fail → user error | Manual; **+3d ref bonus still in code** |
| **19. Auto-renew legacy keys** | `scheduler._run_auto_renew_for_user` | `renewal_attempts` ledger | Remna | recovery refunded log | Stale pending → startup refund | ops smoke `AUTO_RENEW_BILLING_OK` |
| **20. Manual correction** | `set_balance` in database.py | direct SQL | — | — | **No productized admin UI** | DB/panel manual — high risk |
| **21. Refund** | Auto-renew stale recovery only | `RENEWAL_STATUS_REFUNDED` | — | `auto_renew_recovery` | **No YooKassa refund flow** | Manual owner + payment provider |

### Architecture diagram

```
[TG trial 90d] ──no debit──► [trial profile]
        │
        ▼ top-up (YooKassa/crypto/Stars)
[Payment.create] ──webhook──► [PaymentWebhookQueue]
        │                           │
        │                    verify_yookassa_amount
        │                           │
        ▼                           ▼
              process_topup_payment (idempotent yk:ID)
        │ add_balance + waive_daily + sync_panel
        ▼
[wallet profile] ◄── scheduler poll ──► charge_daily 6.67₽/UTC day
        │                                      │
        │ legacy panel (≥2030)                   ▼ insufficient
        └──────── SKIP debit ───────────► sync_panel (short expire)
```

---

## 4. Scenario matrix (S1–S18)

| ID | Scenario | Policy | Code behavior | Tests | Prod evidence | Risk | Paid blocker? | Required fix/test |
|----|----------|--------|---------------|-------|---------------|------|---------------|-------------------|
| **S1** | New TG trial, no payment | 90d, no balance debit | `trial` profile; no `process_daily_balance_user` debit | Unit trial ✅ | P1-CAB smoke trial PASS | Low | No | — |
| **S2** | Trial tops up successfully | Balance += amount; access from balance | `process_topup_payment` full path | **None** | Not re-run this pass | Med | **Yes** until smoke | `BILL-SMOKE-001` live top-up test |
| **S3** | Trial → wallet after top-up | Wallet billing starts | `is_paid_wallet_user` true after topup | Unit wallet ✅ | — | Low | No | — |
| **S4** | Wallet, balance ≥ 6.67 | Daily debit once/day | `charge_daily_balance_if_due` → charged | **None** | — | Med | **Yes** until smoke | `BILL-SMOKE-002` debit idempotency |
| **S5** | Wallet below 6.67 | No deduct; access winds down | `insufficient` + `sync_panel` → 0 days | **None** | — | Med | Partial | Smoke + cabinet copy |
| **S6** | Balance zero/negative | Expired profile | `balance_to_days=0`; panel synced | Unit expired ✅ | — | Med | Partial | — |
| **S7** | Expired tops up again | Access restored from balance | `sync_panel_access_from_balance`; may `provision_key` if no keys | **None** | — | Med | **Yes** | `BILL-SMOKE-003` recovery |
| **S8** | Duplicate YooKassa callback | Single credit | `yk:{id}` in `user_actions`; webhook queue duplicate | **None** | — | **High** if broken | **Yes** | `BILL-SMOKE-004` duplicate POST |
| **S9** | Failed/cancelled payment | No credit | Non-succeeded events ignored in `_handle_yookassa` | **None** | — | Low | No | Smoke cancelled event |
| **S10** | Payment OK, Remna sync fails | Balance credited; user warned | Returns `synced=False`; TG ⚠️ message | **None** | — | **High** | **Yes** | Alert + support runbook |
| **S11** | Billing job missed a day | Next tick catches up? | **Only one debit per UTC day** — missed day = **no retroactive multi-debit** | **None** | — | **High** | **Yes** | Document policy; optional catch-up design |
| **S12** | Billing job runs twice same day | Single debit | `has_action(daily_balance:DATE)` → already | **None** | — | Low | No | Unit test needed |
| **S13** | Legacy 2099 + balance | No drain | `legacy` profile skips `process_daily_balance_user` | Unit legacy ✅ | Prior AMS owner sample | Low UX | No | Cabinet legacy note ✅ deployed |
| **S14** | Multiple vpn_keys | 1× daily rate | Debits once; `sync_panel` uses `keys[0]` | Unit anomaly ✅ | — | Med fair-use | Partial | Admin procedure |
| **S15** | Active config, no balance | Expired when panel lapses | wallet→expired when inactive keys | Unit | — | Med | Partial | — |
| **S16** | Refund/manual adjustment | Support path | `set_balance` DB only; no YooKassa refund API | **None** | — | **High** | **Yes** | Admin tool + audit log |
| **S17** | Autopay bind/renew | Optional 200₽/30d | Credits via topup webhook; scheduler charges card | Static smoke ✅ | — | Med | Partial | Live autopay smoke |
| **S18** | Web/email trial pays/binds | 1d web; bind to TG | Web trial separate surrogate; wallet top-up on TG id after bind | Bind **FAIL** | POSTDEPLOY §9 | **High** | **Yes** if web growth | TG bind fix first |

---

## 5. Prod read-only aggregates

**Status:** **Not collected in this pass.**

| Reason | Detail |
|--------|--------|
| No safe read-only aggregate script in repo | Would require new AMS SQL or SSH session |
| Audit mode constraint | No DB write; no billing job trigger; no callback replay |
| Prior redacted sample | [`AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md`](AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md) §7 — one legacy owner: balance 186.66 ₽, 2 daily debits May 2026, then legacy bypass |

**Recommended next (read-only):** `ops/audit_billing_aggregates_ams.py` — counts only:

- users by inferred profile (trial/wallet/legacy/expired)
- `balance > 0`, `balance < 6.67`
- `user_actions` topup count 30d
- `webhook_deliveries` failed count 30d
- duplicate `yk:` keys (should be 0)

No user IDs in output.

---

## 6. Test coverage audit

### Existing

| Asset | Coverage |
|-------|----------|
| `tests/test_portal_cabinet_billing.py` | `build_billing_fields` — trial/wallet/legacy/expired; `build_configuration_fields`; snapshot compat |
| `ops/smoke_autorenew_billing.py` | Static code order: deduct before provision_key |
| `ops/smoke_yookassa_ams.py` / `smoke_yookassa_local.py` | Webhook auth / config presence |
| `ops/smoke_p1_cab_001_ams.py` | Cabinet API billing_profile fields (legacy+trial) |
| `ops/smoke_p1_cab_001_profiles_ams.py` | Profile smokes (partial) |
| COMMERCIAL-BACKLOG | Historical `WEBHOOK_AUTH_OK`, `AUTO_RENEW_BILLING_OK`, `PAYMENT_AMOUNT_VERIFY_OK` |

### Missing (paid pilot blockers)

| ID | Test | Priority |
|----|------|----------|
| **BILL-UT-001** | `charge_daily_balance_if_due` — charged / already / insufficient / skipped | P0 |
| **BILL-UT-002** | `process_topup_payment` duplicate `yk:` idempotency | P0 |
| **BILL-UT-003** | `waive_daily_charge_today` prevents second debit | P1 |
| **BILL-UT-004** | `verify_yookassa_amount` mismatch rejects | P1 |
| **BILL-SMOKE-001** | Controlled AMS top-up → balance + panel extend | P0 |
| **BILL-SMOKE-002** | Duplicate webhook POST → single credit | P0 |
| **BILL-SMOKE-003** | Expired wallet user top-up → access restored | P1 |
| **BILL-SMOKE-004** | `BOT_PAYMENTS_LIVE=0` → no debit | P1 |
| **BILL-SMOKE-005** | Wallet user `insufficient` → panel days → 0 | P1 |

---

## 7. Risk matrix

| Risk | Severity | Evidence | Impact | Mitigation | Paid blocker? | Open blocker? |
|------|----------|----------|--------|------------|---------------|---------------|
| **Double credit via reconcile script** | ~~**P0**~~ **Fixed in repo** | Was `yookassa:{id}` vs webhook `yk:{id}` | Duplicate balance if reconcile run after webhook | **BILL-FIX-001** — `payment_idempotency.py`; dry-run default | No (if fixed deployed) | No (if fixed deployed) |
| **Duplicate webhook double credit** | P1 | `process_topup_payment` + `claim_webhook_delivery` | Unlikely if queue works | `BILL-SMOKE-002` | **Yes** until smoke | Yes |
| **Balance credited, access not extended** | **P0** | `process_topup_payment` adds balance before sync; returns False on sync fail | Paid user, no VPN | Support runbook; alert on sync fail | **Yes** | **Yes** |
| **Missed billing day (no catch-up)** | P1 | Idempotent per day only; no backfill | Under-billing | Policy doc; monitor scheduler | Partial | Yes |
| **Legacy user balance confusion** | P2 | Legacy bypass + balance display | Trust | P1-CAB legacy note ✅ | No | Partial |
| **Multi-key single debit** | P2 | Policy OK; fairness risk | Abuse | Admin review anomaly flag | Partial | Yes |
| **No YooKassa refund path** | **P0** | No refund API in codebase | Disputes manual | Admin procedure + owner | **Yes** | **Yes** |
| **No reconciliation admin view** | P1 | No bot admin payment list | Slow dispute resolution | P1-ADM-003 | **Yes** | **Yes** |
| **Hidden +3d referral on legacy purchase** | P2 | `process_successful_payment` first_purchase | Policy PT-07 breach on old plan path | Gate/remove P1-REF-002 | Partial | Yes |
| **Payment webhook DLQ silent** | P1 | `mark_webhook_failed` — no alert doc | Lost payments | Monitor `webhook_deliveries` | **Yes** | **Yes** |
| **Autopay 200₽/30d vs 6.67/day messaging** | P2 | Different UX model | User confusion | Copy alignment | Partial | Partial |
| **BOT_PAYMENTS_LIVE misconfig** | P1 | All billing skipped if false | No revenue / wrong state | Deploy checklist | **Yes** | **Yes** |
| **Secret exposure in logs** | P2 | `payload_redact.py` exists | Compliance | Log audit | Partial | Yes |

### 7.1 Reconcile idempotency mismatch — **BILL-FIX-001 (repo fixed)**

**Was:** reconcile used `yookassa:{pid}` while webhook recorded `yk:{pid}`.

**Fix:** `shop_bot/payment_idempotency.py` — `yookassa_topup_action_key()`; reconcile + webhook queue share it; legacy `yookassa:` rows still skip reconcile.

**Still required before prod reconcile:** deploy fix to AMS; explicit owner approval for `--apply`; live smokes BILL-SMOKE-001..004.

---

## 8. Required fixes/tests (ordered)

| Order | ID | Surface | Why |
|-------|-----|---------|-----|
| 1 | ~~**BILL-FIX-001**~~ | `payment_idempotency.py` + reconcile | **DONE in repo** — deploy + approval before `--apply` |
| 2 | **BILL-UT-001/002** | `tests/test_balance_billing.py` | Daily debit + topup idempotency unit tests |
| 3 | **BILL-SMOKE-001..004** | `ops/smoke_billing_commercial_ams.py` | Live money-path proof on smoke users |
| 4 | **BILL-RUNBOOK-001** | docs | Payment succeeded, access not extended |
| 5 | **P1-ADM-003** | admin | Payment/topup lookup by TG ID + last actions |
| 6 | **BILL-AGG-001** | ops read-only | Profile/balance aggregates (no PII) |
| 7 | **P1-REF-002** | bot | Remove/gate +3d referral purchase bonus |
| 8 | **BILL-MON-001** | ops | Alert on `webhook_deliveries` failed / sync fail rate |

**Not in scope:** 6.67×N multi-device billing; new product features.

---

## 9. Support / reconciliation requirements

Before **automated paid pilot**, support must be able to:

| Capability | Today | Required |
|------------|-------|----------|
| Find user by Telegram ID | Manual DB | Admin command |
| See balance + billing_profile | Cabinet API ✅ | — |
| See last topup / daily debits | `user_actions` manual SQL | Admin view |
| See webhook idempotency status | `webhook_deliveries` manual | Admin view |
| Extend access after payment sync fail | Manual Remna panel | Runbook |
| Refund / balance correction | `set_balance` raw SQL | Logged admin action |
| Prove duplicate was not double-paid | `yk:` action row | Reconciliation export |

---

## 10. Go / no-go recommendation

### Manual paid pilot

**CONDITIONAL YES** only if **all**:

1. Owner whitelist ≤10 paying users
2. Owner manually verifies each YooKassa payment in provider dashboard
3. Cross-check `user_actions` topup + balance before declaring success
4. **Do not** run `reconcile_yookassa_topups_ams.py` until BILL-FIX-001
5. Support runbook for S10 (sync fail) in hand
6. `BOT_PAYMENTS_LIVE=1` confirmed on AMS

### Automated paid pilot

**NO-GO** until:

- BILL-SMOKE-001..004 PASS on AMS
- BILL-UT-001..002 in CI
- P1-ADM-003 reconciliation view
- BILL-RUNBOOK-001 published
- BILL-FIX-001 deployed

### Open paid launch

**NO-GO** — additionally G9 monitoring, G11 CI, G10 copy, dispute/refund policy.

---

## 11. Exact next prompts / surfaces

1. **BILL-FIX-001** — *«Fix reconcile_yookassa idempotency key to match yk: prefix»*
2. **BILL-UT-001** — *«Add unit tests for charge_daily_balance_if_due and topup idempotency»*
3. **BILL-SMOKE-001** — *«Create ops/smoke_billing_commercial_ams.py read-only + controlled top-up verify»*
4. **BILL-RUNBOOK-001** — *«Write runbook: payment made but VPN not active»*
5. **P1-ADM-003** — *«Admin: show user balance, topups, daily debits, last webhook»*
6. **BILL-AGG-001** — *«Read-only AMS billing aggregate script (counts only)»*

---

## 12. References

| Doc / code | Role |
|------------|------|
| `bot_src/balance_billing.py` | Daily debit + panel sync |
| `bot_src/subscription_profile.py` | legacy/wallet/trial classification |
| `bot_src/handlers.py` | `process_topup_payment`, YooKassa create |
| `bot_src/webhook_server/payment_queue.py` | Webhook idempotency queue |
| `bot_src/scheduler.py` | Daily billing trigger |
| `bot_src/portal_cabinet.py` | Cabinet billing_profile |
| `ops/reconcile_yookassa_topups_ams.py` | **Risk:** key mismatch |
| [`POSTDEPLOY-2026-06-10-P1-CAB-001.md`](POSTDEPLOY-2026-06-10-P1-CAB-001.md) | Cabinet deploy |
| [`RUNBOOK-COMMERCE-GO-LIVE.md`](RUNBOOK-COMMERCE-GO-LIVE.md) | Historical go-live |
| [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) | PT-08, PT-09 |

**Status:** BILL-001 audit complete · **no implementation** · **no prod mutation**
