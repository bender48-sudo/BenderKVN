# Очередь исполнения (одна задача — один коммит)

**Назначение:** единственный список «что делать сейчас» для владельца и агента Cursor.  
**Не дублировать** параллельные ветки из §3 спринтов — здесь только **линейный** порядок.

**Правило работы**

1. Взять **ровно одну** строку со статусом **`NEXT`** (ниже).
2. Выполнить **Done when** из ссылки на задачу в **`docs/COMMERCIAL-BACKLOG.md`** / runbook.
3. Проверка (см. колонку **Verify**).
4. Обновить эту таблицу: **`NEXT` → `DONE`**, следующая **`TODO` → `NEXT`**; строка в **`COMMERCIAL-BACKLOG.md` §12**.
5. **Один коммит** в `main`, сообщение по шаблону **Commit**.
6. **Остановиться.** Следующую задачу — в **новой** сессии агента (владелец возвращается сам).

**Не начинать** следующую строку в том же чате без явной просьбы владельца.

---

## Текущая очередь (фаза роста → 10k, лето 2026)

| Q | ID | Статус | Done when (кратко) | Verify | Runbook / § |
|---|-----|--------|-------------------|--------|-------------|
| 001 | **P6-SCALE-04a** | **DONE** | Green probe при стабильных 200/304 | §12 **2026-05-16** | **`RUNBOOK-P6-SUBSCRIPTION-EDGE` §0 (a)** |
| 002 | **P6-SCALE-04b** | **NEXT** | CDN **или** Caddy rate-limit на краю подписки на **проде** | Sub smoke 200/304; конфиг edge задеплоен | **`RUNBOOK-P6-SUBSCRIPTION-EDGE` §2** |
| 003 | **P6-SCALE-04c** | TODO | Повтор **`subscription_load_probe`** после (b); p95/гистограмма в §12 | `python ops/subscription_load_probe.py --json` | **`RUNBOOK-P6-SUBSCRIPTION-EDGE` §0 (c)** |
| 004 | **P2-OPS-RESTORE-TEST-01** | TODO | Квартальный restore test; дата в runbook §4 + §12 | Изолированный Postgres, дамп с LV | **`RUNBOOK-BACKUP-REMNAWAVE` §4** |
| 005 | **P2-COM-MONETIZE-01** | TODO | Финальные цены на проде (не тест 1 ₽) | Меню тарифов в TG | **`RUNBOOK-COMMERCE-GO-LIVE` §1** |
| 006 | **P2-COM-MONETIZE-02** | TODO | **`BOT_PAYMENTS_LIVE=1`**, E2E один канал оплаты | Оплата → `expireAt` в панели | **`RUNBOOK-COMMERCE-GO-LIVE` §2** |
| 007 | **P2-COM-MONETIZE-03** | TODO | Legal URLs в боте без заглушек | Ссылки до оплаты | **`RUNBOOK-COMMERCE-GO-LIVE` §3** |
| 008 | **P2-COM-MONETIZE-04** | TODO | Go-live чеклист §4; строка §12 | Чеклист отмечен | **`RUNBOOK-COMMERCE-GO-LIVE` §4** |
| 009 | **P6-RED-PAY-01** | TODO | Idempotency + DLQ webhook бота | Повтор webhook не дублирует | **§5.1** |
| 010 | **P2-RED-SUB-01** | TODO | ≥2 origin подписки + мониторинг | Wiki/док | **§5.1** |
| 011 | **P2-RED-MUX-01** | TODO | ≥2 транспортных профиля в матрице | Доля на alt-профиле | **§5.1**, **`HAPP-MATRIX`** |
| 012 | **P6-RED-SUBHA-01** | TODO | Горизонталь sub-page или split host | Load test без деградации p95 | **§5.1** |
| 013 | **P6-SCALE-02** | TODO | Soft cap + правило 3-й ноды | **`NODE-POLICY-LV-NL`** | **§10.2** |
| 014 | **P6-SCALE-03** | TODO | Postgres индексы / `pg_stat_statements` | План обслуживания | **§10.2** |
| 015 | **GTM-WIKI-01** | TODO | Wiki по **`GTM-GROWTH-OUTLINE`**; URL в §1 бэклога | Owner заполнил вне git | **`GTM-GROWTH-OUTLINE`** |
| 016 | **P2-OPS-IMAGE-PIN-01** | TODO | Digest pin postgres/valkey/caddy/adguard | Нет `:latest` в tmpl | **§6** |
| 017+ | **P1-RED-*** / **P6-SCALE-05…07** | TODO | После **Q009–Q014** или **users > 2k** | — | **§11** бэклога |

**Gate (не отдельный Q):** любой накат AMS compose/env — только по **`RUNBOOK-AMS-SAFE-DEPLOY`** (**`P2-OPS-AMS-SAFE-DEPLOY-01`**, runbook в репо ✅).

**Параллельно (другой человек, не трогать NEXT):** **P4-DNS-01…03**.

---

## Шаблоны коммитов

| Q | Commit (пример) |
|---|-----------------|
| 002 | `ops: P6-SCALE-04b — edge CDN/RL на подписке (AMS/LV)` |
| 003 | `ops: P6-SCALE-04c — load probe после edge, журнал §12` |
| 004 | `ops: P2-OPS-RESTORE-TEST-01 — restore test Remnawave, дата в runbook` |
| 005 | `product: P2-COM-MONETIZE-01 — финальные цены в боте` |
| 006 | `product: P2-COM-MONETIZE-02 — BOT_PAYMENTS_LIVE, smoke оплаты` |
| 007 | `product: P2-COM-MONETIZE-03 — legal URLs в боте` |
| 008 | `product: P2-COM-MONETIZE-04 — go-live чеклист, §12` |

После коммита с закрытием задачи — в **`BACKLOG-QUEUE.md`**: сменить статусы и при необходимости добавить подстроку в §12 бэклога (в том же коммите).

---

## История смены NEXT

| Дата | Было NEXT | Стало |
|------|-----------|--------|
| 2026-05-16 | — | **Q002** (**P6-SCALE-04b**) после внедрения очереди |
