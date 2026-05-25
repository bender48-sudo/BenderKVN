# Фаза 9 — Bot CodeRabbit backlog (Q142–160)

**Аудит:** [`AUDIT-2026-05-BOT-CODERABBIT.md`](AUDIT-2026-05-BOT-CODERABBIT.md)  
**Очередь:** [`BACKLOG-QUEUE.md`](BACKLOG-QUEUE.md) — одна строка **`NEXT`**.

## Gate (после каждого Q с деплоем бота)

```bash
python -m py_compile bot_src/*.py bot_src/webhook_server/*.py
python ops/smoke_ams_safe_deploy.py --skip-sub-probe
# при Q142/Q146: ops/deploy-bot-handlers-ams.ps1 и/или deploy-bot-payment-webhook-ams.ps1
curl -sS http://127.0.0.1:1488/health   # на AMS после deploy
```

Специфичные smokes — в колонке **Verify** таблицы очереди.

---

## Q142 — P2-RED-BOT-RENEW-IDEM-01 (P0)

| | |
|--|--|
| **Done when** | Таблица `renewal_attempts` (attempt_id UUID, user_id, key_id, status, cost_rub, timestamps); перед списанием — `pending`; success/refunded/failed; при старте — recovery pending >5 min |
| **Verify** | `py_compile`; unit/log review; нет двойного списания при simulated crash |
| **Commit** | `fix: P2-RED-BOT-RENEW-IDEM-01 — renewal attempt ledger` |

---

## Q143 — P2-RED-BOT-MULTIKEY-01

| | |
|--|--|
| **Done when** | `scheduler.py`: автопродление для **каждого** ключа `get_user_keys`; отдельный cost/plan; одно сообщение-сводка; `log_action` per key |
| **Verify** | `py_compile`; code review multi-key loop |
| **Commit** | `fix: P2-RED-BOT-MULTIKEY-01 — renew all user keys` |

---

## Q144 — P2-RED-BOT-BACKOFF-01

| | |
|--|--|
| **Done when** | `_global_backoff_until`, `_consecutive_failures` в `remnawave_api.py`; `_check_backoff()`; после 3 fail → 30s pause; `health_check()` сбрасывает backoff |
| **Verify** | `py_compile`; optional `ops/smoke_remna_api_retry.py` still OK |
| **Commit** | `fix: P2-RED-BOT-BACKOFF-01 — global Remna circuit breaker` |

---

## Q145 — P2-RED-BOT-INBOUND-LOCK-01

| | |
|--|--|
| **Done when** | `asyncio.Lock` на refresh `_INBOUND_CACHE`; stale-within-grace при параллельном refresh |
| **Verify** | `py_compile` |
| **Commit** | `fix: P2-RED-BOT-INBOUND-LOCK-01 — inbound cache stampede lock` |

---

## Q146 — P2-RED-WEBHOOK-ASYNC-01

| | |
|--|--|
| **Done when** | Background event loop + `_run_async()` (30s timeout); заменить `asyncio.run` в `webhook_server/app.py` portal/trial routes |
| **Verify** | `py_compile`; `WEBHOOK_AUTH_OK` / portal trial smoke если есть |
| **Commit** | `fix: P2-RED-WEBHOOK-ASYNC-01 — dedicated asyncio loop for Flask` |

---

## Q147 — P2-OPS-DB-INDEX-01

| | |
|--|--|
| **Done when** | Indexes: `vpn_keys(user_id)`, `vpn_keys(expiry_date)`, `referrals(referrer_code)`, `user_actions(user_id)`; web_trial `customer_seq` + index; lookup без full scan |
| **Verify** | `py_compile`; `EXPLAIN QUERY PLAN` на типовых SELECT |
| **Commit** | `chore: P2-OPS-DB-INDEX-01 — sqlite indexes for hot paths` |

---

## Q148 — P2-OPS-DB-MIGRATE-01

| | |
|--|--|
| **Done when** | `schema_migrations` table; `_migrate_vN()` chain; транзакции; убрать silent `OperationalError: pass` для schema |
| **Verify** | `py_compile`; fresh DB + upgrade path |
| **Commit** | `chore: P2-OPS-DB-MIGRATE-01 — versioned schema migrations` |
| **Doc** | `docs/DATABASE-MIGRATIONS.md` |

---

## Q149 — P2-OPS-WEBTRIAL-POOL-01

| | |
|--|--|
| **Done when** | Pool 3–5 connections в `web_trial_db.py`; thread-safe checkout |
| **Verify** | `py_compile`; concurrent claim test если есть |
| **Commit** | `ops: P2-OPS-WEBTRIAL-POOL-01 — web trial sqlite pool` |

---

## Q150 — P2-RED-BOT-ADMIN-FIX-01

| | |
|--|--|
| **Done when** | Import `get_setting` в `admin_handlers.py`; HTML `<b>` вместо `**`; Mac App Store URL в `vpn_setup_wizard.py`; `support_user` — username validation, не URL |
| **Verify** | `py_compile`; admin flow step 1 не падает |
| **Commit** | `fix: P2-RED-BOT-ADMIN-FIX-01 — admin imports and HTML` |

---

## Q151 — P2-CHORE-KEYBOARD-STUBS-01

| | |
|--|--|
| **Done when** | Аудит stubs в `keyboards.py`: restore / remove / document; callers без мёртвых кнопок |
| **Verify** | grep callers; manual menu smoke |
| **Commit** | `chore: P2-CHORE-KEYBOARD-STUBS-01 — keyboard stub cleanup` |

---

## Q152 — P2-RED-SETUP-URL-DEDUP-01

| | |
|--|--|
| **Done when** | `bot_src/setup_url_service.py` — единый `get_setup_url_for_user`; handlers + portal_telegram_setup |
| **Verify** | `py_compile`; wizard + portal setup same URL |
| **Commit** | `refactor: P2-RED-SETUP-URL-DEDUP-01 — shared setup URL service` |

---

## Q153 — P3-UX-MESSAGES-01

| | |
|--|--|
| **Done when** | `user_messages.py`: единый «ты»; `MSG_TRIAL_PORTAL_HINT`; expired subscription msg; параметризованный profile в `MSG_SUB_CONFIG_REFRESH` |
| **Verify** | grep review |
| **Commit** | `product: P3-UX-MESSAGES-01 — user message consistency` |

---

## Q154 — P2-RED-SUB-URL-CACHE-01

| | |
|--|--|
| **Done when** | `subscription_cache.py`: TTL 60s, lock, invalidate after provision/delete; `subscription_resolve` + `subscription_qr` |
| **Verify** | `py_compile`; log cache hit on repeat resolve |
| **Commit** | `perf: P2-RED-SUB-URL-CACHE-01 — subscription URL cache` |

---

## Q155 — P2-OPS-SUB-REFRESH-BATCH-01

| | |
|--|--|
| **Done when** | `SUB_REFRESH_BATCH` 50; rate limit 0.035s; backoff on 429 |
| **Verify** | `py_compile`; batch duration log |
| **Commit** | `ops: P2-OPS-SUB-REFRESH-BATCH-01 — sub refresh notify scale` |

---

## Q156 — P2-OPS-SCHED-JITTER-02

| | |
|--|--|
| **Done when** | Jitter `CHECK_INTERVAL_SECONDS + uniform(0,30)`; backup check — отдельная asyncio task |
| **Verify** | `py_compile`; **SCHEDULER_CYCLE** logs |
| **Commit** | `ops: P2-OPS-SCHED-JITTER-02 — scheduler jitter and backup task` |

---

## Q157 — P3-UX-LEGAL-FALLBACK-01

| | |
|--|--|
| **Done when** | `start_handler`: fallback terms/privacy + support CTA; defaults в `config.py`; admin warn log |
| **Verify** | `py_compile` |
| **Commit** | `product: P3-UX-LEGAL-FALLBACK-01 — onboarding legal fallback` |

---

## Q158 — P3-UX-WIZARD-FALLBACK-01

| | |
|--|--|
| **Done when** | `_wizard_setup_url` → `(url, reason)`; текст «веб-настройка недоступна» + QR path |
| **Verify** | wizard smoke |
| **Commit** | `product: P3-UX-WIZARD-FALLBACK-01 — setup wizard unavailable hint` |

---

## Q159 — P3-RED-SUPPORT-RATELIMIT-PERSIST-01

| | |
|--|--|
| **Done when** | `support_rate_limits` table; persist в `support_handler.py`; TTL cleanup |
| **Verify** | `py_compile` |
| **Commit** | `security: P3-RED-SUPPORT-RATELIMIT-PERSIST-01 — persist support rate limits` |

---

## Q160 — P3-RED-SUPPORT-SILENT-01

| | |
|--|--|
| **Done when** | `BOT_SUPPORT_ENABLED`; startup warn; user message «Поддержка временно недоступна» вместо silent drop |
| **Verify** | `py_compile`; SUPPORT_REPLY smoke if configured |
| **Commit** | `ops: P3-RED-SUPPORT-SILENT-01 — support unavailable user feedback` |
