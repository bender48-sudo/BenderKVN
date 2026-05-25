# Аудит бота — CodeRabbit (2026-05-25)

**Источник:** диагностика CodeRabbit (5 фаз: Reliability → DB → Code → Speed → UX).  
**Сверка с репо:** `bot_src/`, фаза 8 **Q122–141** ([`AGENT-PHASE8-RELIABILITY-BACKLOG.md`](AGENT-PHASE8-RELIABILITY-BACKLOG.md)).

**Исполнение:** линейно **`docs/BACKLOG-QUEUE.md`** фаза 9 (**Q142–160**), детали — [`AGENT-PHASE9-BOT-CODERABBIT-BACKLOG.md`](AGENT-PHASE9-BOT-CODERABBIT-BACKLOG.md).

---

## Сводка триажа

| Вердикт | Кол-во | Комментарий |
|---------|--------|-------------|
| **Подтверждено (P0–P1)** | 12 | Есть в коде, риск денег/данных/каскадов |
| **Подтверждено (P2)** | 5 | Производительность, UX, техдолг |
| **Частично / уточнено** | 2 | Multi-key: триггер только `user_keys[0]`, но `provision` обновляет все ключи одним UUID |
| **Уже закрыто фазой 8** | 4 | Timeout, tenacity retry, shared session, WAL, scheduler gather, backup glob |
| **Дубль старого бэклога** | 2 | Inbound cache TTL (**Q076**), webhook payment idempotency (**Q009**) |

---

## Фаза 1 — Critical Reliability

| # | Находка | Статус | Доказательство в репо |
|---|---------|--------|------------------------|
| 1.1 | Idempotency auto-renew | **P0 подтверждено** | `scheduler.py`: `try_deduct_balance` → `provision_key` → refund при fail; нет `renewal_attempts`, нет recovery после crash между списанием и refund |
| 1.2 | Multi-key renewal | **P1 подтверждено** | `scheduler.py:139–140` — цикл автопродления только при `user_keys[0]`; отдельные ключи/планы не обрабатываются |
| 1.3 | Global backoff Remna API | **P1 подтверждено** | `remnawave_api.py`: есть **tenacity** (Q123), нет `_global_backoff_until` / circuit breaker |
| 1.4 | Inbound cache stampede | **P2 подтверждено** | `_INBOUND_CACHE` без `asyncio.Lock`; пересекается с **P5-ENG-03 / Q076** (TTL есть) |
| 1.5 | `asyncio.run` в Flask webhook | **P1 подтверждено** | `webhook_server/app.py:93,112,167` (+ probe paths); `payment_queue` уже использует `run_coroutine_threadsafe` |

---

## Фаза 2 — Database

| # | Находка | Статус | Доказательство |
|---|---------|--------|----------------|
| 2.1 | Индексы `vpn_keys`, `referrals`, `user_actions` | **P1 подтверждено** | `database.py` `initialize_db`: только индекс web_trial bind_token |
| 2.2 | Versioned migrations | **P1 подтверждено** | Множество `ALTER TABLE` + `except OperationalError: pass` |
| 2.3 | Web trial connection pool | **P2 подтверждено** | `web_trial_db.py`: новое соединение на вызов |
| 2.4 | `customer_seq` + indexed lookup | **P2 уточнение** | Проверить `get_claim_by_customer_id()` — full scan; добавить в Q147 |

---

## Фаза 3 — Code quality

| # | Находка | Статус | Доказательство |
|---|---------|--------|----------------|
| 3.1 | `get_setting` import в admin | **P1 подтверждено** | `admin_handlers.py:282` использует `get_setting`, в imports только `update_setting` |
| 3.2 | `**bold**` вместо HTML | **P2 подтверждено** | `admin_handlers.py:125,132,140` — parse mode HTML не задан |
| 3.3 | Mac App Store URL в wizard | **Проверить** | `vpn_setup_wizard.py` — в Q150 |
| 3.4 | Keyboard stubs | **P2 подтверждено** | `keyboards.py` «Legacy stubs» — 8+ функций → только back; `create_support_keyboard` **не** stub |
| 3.5 | Duplicate setup URL | **P2 подтверждено** | `handlers._wizard_setup_url` + `portal_telegram_setup.telegram_setup_for_user` |
| 3.6 | `user_messages` polish | **P3** | Плейсхолдеры, «ты», expired msg |

**Дополнительно (не в CR):** `process_support_user` валидирует support как URL (`admin_handlers.py:137`) — должно быть `@username`, не link.

---

## Фаза 4 — Speed

| # | Находка | Статус | Доказательство |
|---|---------|--------|----------------|
| 4.1 | Subscription URL cache | **P1 подтверждено** | Каждый QR/copy → `resolve_subscription_url()` → panel API |
| 4.2 | Sub-refresh batch 15 | **P2 подтверждено** | `subscription_refresh.py`: `SUB_REFRESH_BATCH = 15` |
| 4.3 | Scheduler jitter + backup split | **P2 частично** | Jitter sub-notify есть (`SUB_REFRESH_JITTER_MAX_SEC`); основной `CHECK_INTERVAL` фиксирован; backup в том же loop |

---

## Фаза 5 — UX

| # | Находка | Статус |
|---|---------|--------|
| 5.1 | Legal URLs fallback | **P2** — `start_handler` без graceful fallback |
| 5.2 | Wizard Mini App feedback | **P2** — `_wizard_setup_url` → `None` без текста |
| 5.3 | Support rate limit persist | **P2** — in-memory |
| 5.4 | SUPPORT_GROUP_ID silent drop | **Частично** — Q110 fail-fast prod; user reply при `0` всё ещё возможен |

---

## Не входит в фазу 9 (уже сделано / другой трек)

| ID | Тема |
|----|------|
| Q122–126 | Remna timeout, retry, jitter config, backup glob, aiohttp pool |
| Q127–129 | Scheduler gather, WAL, autorenew `days_left<=0` |
| Q009, Q063 | Webhook idempotency, auto-renew billing (без attempt ledger) |
| Q110 | SUPPORT_GROUP_ID prod gate |
| Q132+ | VPN template / TSPU (отдельно от бота) |

---

## Приоритет исполнения (фаза 9)

1. **Q142–Q146** — деньги, API storms, webhook threads.  
2. **Q147–Q149** — DB перед ростом базы.  
3. **Q150–Q153** — баги админки/UX копирайта.  
4. **Q154–Q156** — latency sub URL + notify scale.  
5. **Q157–Q160** — polish и support hardening.

**Verify после деплоя бота:** `py_compile`, `ops/smoke_ams_safe_deploy.py`, существующие payment/webhook smokes, `curl :1488/health`, при Q142 — сценарий auto-renew dry-run / log review.
