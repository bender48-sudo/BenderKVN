# Runbook: go-live монетизации (P2-COM-MONETIZE)

**Задачи бэклога:** **`P2-COM-MONETIZE-01` … `04`**, перед массовым привлечением — **до** или **вместе с** **`P6-RED-PAY-01`**.

**Текущее состояние (репо):** **COM-MONETIZE go-live OK** (**2026-05-16**). Webhook-платежи: очередь + idempotency + DLQ (**P6-RED-PAY-01**, **`ops/deploy-bot-payment-webhook-ams.ps1`**, smoke **`ops/smoke_webhook_payment_idempotency_ams.py`**). Живой GTM-wiki — **Q015**.

---

## 1. Финальные цены (**P2-COM-MONETIZE-01**)

Модель: **не месячные тарифы**, а **пополнение баланса** по **6.67 ₽/день** (кому-то хватит на день, кому-то на год).

1. **`bot_src/config.py`**: **`DAILY_RATE`**, **`TOPUP_PRESETS`**, **`balance_to_days()`**; UI — «Пополнить баланс», кнопки вида **`200 ₽ — ~30 дн.`**.
2. Деплой: **`ops/deploy-bot-balance-model-ams.ps1`** (config, keyboards, handlers, database, scheduler).
3. Smoke TG: главное меню / аккаунт → баланс и ₽/день; пресеты пополнения без **1 ₽** и без привязки «1 месяц = N ₽».

**Done when:** на проде видна модель баланса и **6.67 ₽/день**; underpricing (тест **1 ₽**) отсутствует.

---

## 2. Платежи live (**P2-COM-MONETIZE-02**)

1. Подключить креды (YooKassa, Telegram Stars, crypto — см. **`bot_src/main.py`**) в **`/opt/remna-shop/.env`** на AMS.
2. Установить **`BOT_PAYMENTS_LIVE=1`** (или `true`) в env бота; **`docker compose up -d`** / restart **`remna-shop-bot`**.
3. Smoke каждого канала: тестовая покупка → webhook → продление **`expireAt`** в панели.
4. **`P6-RED-PAY-01`**: HTTP webhook → **`PaymentWebhookQueue`** (SQLite **`webhook_deliveries`**, статусы pending/done/failed=DLQ); повтор с тем же ключом → **200 duplicate**. Деплой: **`ops/deploy-bot-payment-webhook-ams.ps1`**.
5. **`P6-RED-PAY-02`**: Flask **`WEBHOOK_BIND_HOST=127.0.0.1`** (порт **1488** только с AMS, через nginx); **YooKassa** — API verify **`Payment.find_one`** перед начислением; **crypto/cryptobot** — заголовок **`X-Webhook-Secret`** / query **`secret`** = **`CRYPTO_WEBHOOK_SECRET`**. Smoke: **`ops/smoke_webhook_auth_ams.py`** → **`WEBHOOK_AUTH_OK`**.

**Done when:** минимум один канал оплаты проходит E2E на проде; повтор webhook не дублирует подписку; подделанный webhook → **403** без изменения баланса.

---

## 3. Legal и доверие (**P2-COM-MONETIZE-03**)

1. В админке бота (или env) задать **`TERMS_URL`**, **`PRIVACY_URL`**, **`SUPPORT_USER`**, **`CHANNEL_URL`**.
2. Сверить тексты с **`docs/FAQ.md`** (trial, RU-bypass, что не обещаем).
3. Пользователь видит ссылки в боте до оплаты.

**Done when:** нет заглушек «не установлена» в прод-сообщениях.

---

## 4. Чеклист перед рекламой (**P2-COM-MONETIZE-04**)

- [x] **`P2-OPS-AMS-SAFE-DEPLOY-01`** — gate в **`docs/RUNBOOK-AMS-SAFE-DEPLOY.md`** (урок **2026-05-17** §12); накат AMS compose только по чеклисту
- [x] **`P6-SCALE-04`**: green **`subscription_load_probe`** + edge RL/CDN (см. **`docs/RUNBOOK-P6-SUBSCRIPTION-EDGE.md`**, §12 **2026-05-16**)
- [x] **`P2-OPS-RESTORE-TEST-01`**: дата restore test в **`docs/RUNBOOK-BACKUP-REMNAWAVE.md` §4** (**2026-05-16**)
- [x] **`docs/GTM-GROWTH-OUTLINE.md`** — шаблон и пороги в репо; **живая wiki** (каналы, бюджет) — отдельно **Q015 GTM-WIKI-01** (вне git)
- [x] Пороги **`docs/COMMERCIAL-BACKLOG.md` §10.1** (2k / 8k users, RAM, sub 502 → стоп рекламы)

**Verify (AMS):** `docker exec remna-shop-bot python /tmp/smoke_commerce_golive_ams.py` → **`COM-MONETIZE_GO_LIVE_OK`**.

Строка в **`docs/COMMERCIAL-BACKLOG.md` §12`**: «COM-MONETIZE go-live OK», дата — **2026-05-16**.

---

## 5. Связанные файлы

- **`docs/COMMERCIAL-BACKLOG.md` §5.3** — таблица задач  
- **`docs/GTM-GROWTH-OUTLINE.md`**  
- **`docs/FAQ.md`** — пробный период  
