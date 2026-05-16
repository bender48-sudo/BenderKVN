# Runbook: go-live монетизации (P2-COM-MONETIZE)

**Задачи бэклога:** **`P2-COM-MONETIZE-01` … `04`**, перед массовым привлечением — **до** или **вместе с** **`P6-RED-PAY-01`**.

**Текущее состояние (репо):** **`BOT_PAYMENTS_LIVE`** пустой в **`compose/ams/remna-shop/bot.env.tmpl`**; **`bot_src/config.py`** — **1 месяц = 50 ₽** (прод AMS **2026-05-16**, **`ops/deploy-bot-config-ams.ps1`**); **`TERMS_URL` / `PRIVACY_URL` / `SUPPORT_USER`** — заглушки (**Q007**).

---

## 1. Финальные цены (**P2-COM-MONETIZE-01**)

1. Согласовать с владельцем продукта цены в **`bot_src/config.py`** → **`PLANS`** и **`TRAFFIC_PACKS`** (убрать тест **1 ₽** на 1 месяц, если не акция).
2. Деплой бота на AMS: **`docs/DEPLOY.md` §4.3.1** / **`ops/deploy-bot-handlers-ams.ps1`** (+ при изменении только config — пересборка image или копирование env).
3. Проверить отображение в TG: меню тарифов, профиль, напоминания scheduler.

**Done when:** на проде отображаются согласованные цены; нет случайного underpricing.

---

## 2. Платежи live (**P2-COM-MONETIZE-02**)

1. Подключить креды (YooKassa, Telegram Stars, crypto — см. **`bot_src/main.py`**) в **`/opt/remna-shop/.env`** на AMS.
2. Установить **`BOT_PAYMENTS_LIVE=1`** (или `true`) в env бота; **`docker compose up -d`** / restart **`remna-shop-bot`**.
3. Smoke каждого канала: тестовая покупка → webhook → продление **`expireAt`** в панели.
4. Перед пиком продаж — закрыть или начать **`P6-RED-PAY-01`** (idempotency, DLQ).

**Done when:** минимум один канал оплаты проходит E2E на проде; повтор webhook не дублирует подписку.

---

## 3. Legal и доверие (**P2-COM-MONETIZE-03**)

1. В админке бота (или env) задать **`TERMS_URL`**, **`PRIVACY_URL`**, **`SUPPORT_USER`**, **`CHANNEL_URL`**.
2. Сверить тексты с **`docs/FAQ.md`** (trial, RU-bypass, что не обещаем).
3. Пользователь видит ссылки в боте до оплаты.

**Done when:** нет заглушек «не установлена» в прод-сообщениях.

---

## 4. Чеклист перед рекламой (**P2-COM-MONETIZE-04**)

- [ ] **`P2-OPS-AMS-SAFE-DEPLOY-01`** — runbook известен команде
- [x] **`P6-SCALE-04`**: green **`subscription_load_probe`** + edge RL/CDN (см. **`docs/RUNBOOK-P6-SUBSCRIPTION-EDGE.md`**, §12 **2026-05-16**)
- [x] **`P2-OPS-RESTORE-TEST-01`**: дата restore test в **`docs/RUNBOOK-BACKUP-REMNAWAVE.md` §4** (**2026-05-16**)
- [ ] **`docs/GTM-GROWTH-OUTLINE.md`** — wiki заполнен, owner GTM
- [ ] Пороги §10.1 понятны (план апгрейда AMS при **2k** users)

Строка в **`docs/COMMERCIAL-BACKLOG.md` §12`**: «COM-MONETIZE go-live OK», дата.

---

## 5. Связанные файлы

- **`docs/COMMERCIAL-BACKLOG.md` §5.3** — таблица задач  
- **`docs/GTM-GROWTH-OUTLINE.md`**  
- **`docs/FAQ.md`** — пробный период  
