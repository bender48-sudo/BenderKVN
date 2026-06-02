# Фаза 10 — Bot CodeRabbit раунд 2 (Q161–166)

**Аудит:** [`AUDIT-2026-05-BOT-CODERABBIT-02.md`](AUDIT-2026-05-BOT-CODERABBIT-02.md)  
**Очередь:** [`BACKLOG-QUEUE.md`](BACKLOG-QUEUE.md) — одна строка **`NEXT`**.

**Правило:** один Q → verify gate → deploy бота при изменении `bot_src` → коммит → стоп.

---

## Gate (после каждого Q с деплоем бота)

```bash
python -m py_compile bot_src/*.py bot_src/webhook_server/*.py
python ops/smoke_ams_safe_deploy.py --skip-sub-probe
curl -sS http://127.0.0.1:1488/health   # на AMS после deploy; после Q161 — с секретом/localhost policy
```

---

## Q161 — P2-RED-BOT-ENV-01 (Phase 1: Config & startup)

| | |
|--|--|
| **Done when** | `load_dotenv()` в **первых** строках `main.py` (до `shop_bot.config` и модулей с `os.getenv` на import); `validate_required_config()` в `config.py` (TELEGRAM_BOT_TOKEN, REMNAWAVE_*, PORTAL_* secrets, warn SUPPORT_GROUP_ID=0); `get_db_connection()` + `PRAGMA busy_timeout=5000` везде вместо голого `sqlite3.connect`; `/health` — `HEALTH_CHECK_SECRET` или localhost-only, ответ без внутренних stack trace |
| **Verify** | `py_compile`; локальный старт с пустым `.env` → явный exit; grep нет `sqlite3.connect(DB_FILE)` вне helper |
| **Commit** | `fix: P2-RED-BOT-ENV-01 — dotenv order, config validate, db busy_timeout, health hardening` |

**Подзадачи CR:** load_dotenv ordering · validate_required_config · busy_timeout per connection · secure /health.

---

## Q162 — P2-RED-BOT-INTEGRITY-01 (Phase 2: Reliability & integrity)

| | |
|--|--|
| **Done when** | Topup/payment path: атомарный `claim_webhook_delivery` **до** изменения баланса (как в `payment_queue`); `RemnaWaveAPI._fetch_json` через общий protected fetch/retry или класс deprecated; `_background_tasks` set для `create_task` (backup monitor и др.); `asyncio.Lock` на `_consecutive_failures` / `_global_backoff_until` |
| **Verify** | `py_compile`; `ops/smoke_payment_amount_verify.py` / webhook smokes если есть; code review topup idempotency |
| **Commit** | `fix: P2-RED-BOT-INTEGRITY-01 — payment TOCTOU, remna fetch, task refs, backoff lock` |

**Подзадачи CR:** payment TOCTOU · RemnaWaveAPI._fetch_json · backup task GC · global failure counter lock.

---

## Q163 — P2-RED-BOT-RENEW-NOTIFY-01 (Phase 3: Auto-renewal & notifications)

| | |
|--|--|
| **Done when** | Автопродление при **`days_left <= 1`** (не 0); сообщения «продлили заранее» vs «после expiry»; backup monitor: первая проверка сразу, `sleep` в конце цикла; `TelegramForbiddenError` в sub refresh → всё равно bump `sub_refresh_notified_generation`; max **5** попыток на 429 в notify rate limit |
| **Verify** | `py_compile`; log/table review renewal trigger; optional dry-run scheduler |
| **Commit** | `fix: P2-RED-BOT-RENEW-NOTIFY-01 — early renew, backup first run, blocked refresh, 429 cap` |

**Подзадачи CR:** renew before expiry · backup first iteration · blocked users · rate limit max retries.

---

## Q164 — P2-RED-BOT-SEC-02 (Phase 4: Security)

| | |
|--|--|
| **Done when** | JSON portal setup **без** поля `sub_url` (только signed setup URL); crypto webhook — secret **только** `X-Webhook-Secret`, без query; `bind_token_expires_at` (migration v5), TTL 24h при выдаче, reject expired в lookup |
| **Verify** | `py_compile`; grep ответов portal на `sub_url`; webhook test без `?secret=` |
| **Commit** | `security: P2-RED-BOT-SEC-02 — no sub_url leak, header-only webhook, bind token TTL` |

**Подзадачи CR:** portal sub_url · query secret · bind token expiry.

---

## Q165 — P2-OPS-SCHEMA-02 (Phase 5: Schema safety)

| | |
|--|--|
| **Done when** | `schema_version` с `PRIMARY KEY CHECK(id=1)`; `_set_version` без лишнего `commit` внутри `with conn`; migration v2/v5: `CREATE TABLE IF NOT EXISTS renewal_attempts` перед индексами; миграции идемпотентны на fresh DB |
| **Verify** | `py_compile`; fresh `:memory:` или temp file migrate 0→latest |
| **Commit** | `chore: P2-OPS-SCHEMA-02 — schema_version PK, migration tx, v2 guard` |

**Подзадачи CR:** schema_version integrity · double-commit · missing table guard.

---

## Q166 — P3-UX-BOT-POLISH-02 (Phase 6: UX & hygiene)

| | |
|--|--|
| **Done when** | Renewal msgs в `user_messages.py`; `KEY_EMAIL_DOMAIN` / `DEFAULT_SUPPORT_USERNAME` из config; удалён мёртвый код (ADMIN_ID, unreachable branches); `datetime.now(timezone.utc)` convention; prune `expiry_*_notified` старше 30d; **рабочая** клавиатура + handler toggle `auto_renew` |
| **Verify** | `py_compile`; меню «Автопродление» в боте; grep hardcoded `kitsura.fun` |
| **Commit** | `product: P3-UX-BOT-POLISH-02 — messages, config constants, autorenew toggle, tz, prune` |

**Подзадачи CR:** centralize messages · hardcoded domain · dead code · UTC · bot_settings TTL · autorenew keyboard.

---

## После Q166

Очередь агента снова пуста (кроме **Q120**, **Q032**). Повторный проход CodeRabbit — новый аудит-файл + фаза 11, не расширять Q161–166 задним числом.
