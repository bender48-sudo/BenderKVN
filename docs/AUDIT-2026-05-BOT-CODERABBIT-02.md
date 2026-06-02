# Аудит бота — CodeRabbit раунд 2 (2026-05-25)

**Источник:** Coding Plan CodeRabbit (6 фаз: Config → Integrity → Renew/Notify → Security → Schema → UX).  
**Сверка:** `bot_src/` (деплой как `shop_bot` на AMS), фаза 9 **Q142–160** ([`AUDIT-2026-05-BOT-CODERABBIT.md`](AUDIT-2026-05-BOT-CODERABBIT.md)).

**Исполнение:** линейно **`docs/BACKLOG-QUEUE.md`** фаза 10 (**Q161–166**), детали — [`AGENT-PHASE10-BOT-CODERABBIT-BACKLOG.md`](AGENT-PHASE10-BOT-CODERABBIT-BACKLOG.md).

**Ожидание:** ответ Claude — сверить триаж ниже; не дублировать закрытое без проверки кода.

---

## Design choices (зафиксировать в репо)

| Тема | Решение | Примечание |
|------|---------|------------|
| Async DB | `asyncio.to_thread()` на hot-path SQLite | Не полный `aiosqlite` в Q161–166 |
| Автопродление | `days_left <= 1` (за сутки до expiry) | Сейчас в коде **`days_left <= 0`** (`scheduler.py`) |
| `load_dotenv` | Вызов **до** импортов, читающих `os.environ` | Сейчас `load_dotenv()` внутри `main()` **после** `from shop_bot.config import …` |

---

## Сводка триажа

| Вердикт | Фаза CR | Комментарий |
|---------|---------|-------------|
| **Новое (Q161–166)** | 1, 3, 4, 5, 6 (частично) | См. таблицы ниже |
| **Частично / хвост** | 2 | Topup TOCTOU ≠ renewal ledger Q142; Lock на backoff-счётчики |
| **Уже Q142–160** | 2 (часть) | renewal ledger, multi-key, backoff, webhook loop, migrations, sub cache, refresh batch |
| **Уже Q063–078 / Q024** | 4 | portal resolve без `sub_url`; webhook hardening — проверить query `secret` |
| **Параллельно владелец** | — | Q120, Q032; encoding sub-page — отдельная ветка |

---

## Фаза 1 — Configuration & startup (→ **Q161**)

| Задача CR | Статус | Доказательство / хвост |
|-----------|--------|------------------------|
| `load_dotenv()` до импортов | **P1 новое** | `main.py`: `load_dotenv()` в `main()` после `from shop_bot.config import …` |
| `validate_required_config()` | **P1 новое** | Нет fail-fast на пустые секреты при старте |
| `busy_timeout` на каждое соединение | **P1 новое** | `web_trial_db.py` — PRAGMA есть; `database.py` / `handlers.py:1218` — прямой `connect` |
| `/health` без утечки | **P2 новое** | Сверить с **Q134**; добавить `HEALTH_CHECK_SECRET` или localhost-only |

---

## Фаза 2 — Reliability & data integrity (→ **Q162**)

| Задача CR | Статус | Доказательство / хвост |
|-----------|--------|------------------------|
| Topup TOCTOU | **P0 новое** | `payment_queue` использует `claim_webhook_delivery`; **topup** в `handlers.py` — отдельный путь, сверить атомарность |
| `RemnaWaveAPI._fetch_json` | **P1 новое** | Класс vs module-level protected fetch |
| Backup task GC | **P2 новое** | `create_task` без ссылки на task set |
| Lock на `_consecutive_failures` | **P2 хвост Q144** | Backoff есть; Lock на RMW — нет |

---

## Фаза 3 — Auto-renewal & notifications (→ **Q163**)

| Задача CR | Статус | Доказательство / хвост |
|-----------|--------|------------------------|
| Renew при `days_left <= 1` | **P1 новое** | `scheduler.py:364` — **`<= 0`** |
| Backup loop: sleep в конце цикла | **P2 новое** | Первый backup через 1 ч после старта |
| Blocked user + sub refresh | **P1 новое** | `TelegramForbiddenError` → всё равно `update_sub_refresh_notified_generation` |
| Max retries на 429 | **P2 новое** | Бесконечный цикл в rate-limit helper |

---

## Фаза 4 — Security (→ **Q164**)

| Задача CR | Статус | Доказательство / хвост |
|-----------|--------|------------------------|
| Убрать `sub_url` из portal setup API | **P1 новое** | `portal_browser_resolve` уже без sub_url; **`portal_telegram_setup`**, **`portal_web_trial`** — проверить |
| Webhook secret только header | **P1 новое** | `webhook_server/auth.py` — `?secret=` fallback |
| TTL `bind_token` 24h | **P1 новое** | Миграция v5 + проверка в `get_claim_by_bind_token` |

---

## Фаза 5 — Schema & migrations (→ **Q165**)

| Задача CR | Статус | Доказательство / хвост |
|-----------|--------|------------------------|
| `schema_version` PK | **P1 хвост Q148** | Одна строка version без `CHECK(id=1)` |
| Убрать лишний `commit` в `_set_version` | **P2 новое** | Транзакция мигратора |
| v2 index без таблицы | **P2 новое** | `renewal_attempts` на fresh DB |

---

## Фаза 6 — Code quality & UX (→ **Q166**)

| Задача CR | Статус | Доказательство / хвост |
|-----------|--------|------------------------|
| Сообщения renewal в `user_messages` | **P2 новое** | Inline f-strings в `scheduler.py` |
| `KEY_EMAIL_DOMAIN` / support username | **P2 новое** | Hardcode в `handlers.py`, `support_handler.py` |
| Dead code | **P3 новое** | `ADMIN_ID`, X-Real-IP branch, reply private check |
| UTC datetimes | **P2 хвост Q065** | Унификация `timezone.utc` |
| Prune `bot_settings` expiry flags | **P2 новое** | Рост без TTL |
| Клавиатура автопродления | **P1 новое** | Stub vs реальный toggle в продукте |

---

## Verify gate (фаза 10)

```bash
python -m py_compile bot_src/*.py bot_src/webhook_server/*.py
python ops/smoke_ams_safe_deploy.py --skip-sub-probe
# после Q164: smoke webhook / portal без sub_url в JSON
# после Q163: log review scheduler renewal at days_left==1
```

Деплой бота: **`ops/deploy-bot-handlers-ams.ps1`** / **`deploy-bot-payment-webhook-ams.ps1`** по затронутым путям.

---

## Связь с ответом Claude

Когда придёт ответ Claude — обновить эту таблицу (**Подтверждено / Отклонено / Дубль Qxxx**) и при необходимости дробить Q161–166; **не менять NEXT** без согласования с владельцем.
