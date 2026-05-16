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
| 002 | **P6-SCALE-04b** | **DONE** | CDN **или** Caddy rate-limit на краю подписки на **проде** | Sub smoke **200**; Caddy RL на **bvpn-lv** §12 **2026-05-16** | **`RUNBOOK-P6-SUBSCRIPTION-EDGE` §2** |
| 003 | **P6-SCALE-04c** | **DONE** | Повтор **`subscription_load_probe`** после (b); p95/гистограмма в §12 | §12 **2026-05-16**: 120×**200**, p95≈**1.83s** | **`RUNBOOK-P6-SUBSCRIPTION-EDGE` §0 (c)** |
| 004 | **P2-OPS-RESTORE-TEST-01** | **DONE** | Квартальный restore test; дата в runbook §4 + §12 | §4/§12 **2026-05-16**, 36 tables | **`RUNBOOK-BACKUP-REMNAWAVE` §4** |
| 005 | **P2-COM-MONETIZE-01** | **DONE** | Финальные цены на проде (не тест 1 ₽) | AMS **`buy_1_month` 50 ₽** §12 | **`RUNBOOK-COMMERCE-GO-LIVE` §1** |
| 006 | **P2-COM-MONETIZE-02** | **DONE** | **`BOT_PAYMENTS_LIVE=1`**, E2E один канал оплаты | AMS Stars smoke §12 **2026-05-16** | **`RUNBOOK-COMMERCE-GO-LIVE` §2** |
| 007 | **P2-COM-MONETIZE-03** | **DONE** | Legal URLs в боте без заглушек | AMS telegra.ph + @support §12 | **`RUNBOOK-COMMERCE-GO-LIVE` §3** |
| 008 | **P2-COM-MONETIZE-04** | **DONE** | Go-live чеклист §4; строка §12 | COM-MONETIZE go-live OK §12 | **`RUNBOOK-COMMERCE-GO-LIVE` §4** |
| 009 | **P6-RED-PAY-01** | **DONE** | Idempotency + DLQ webhook бота | smoke WEBHOOK_PAY §12 | **§5.1** |
| 010 | **P2-RED-SUB-01** | **DONE** | ≥2 origin подписки + мониторинг | p4n7q+k9x2m1 §12 | **§5.1**, **`RUNBOOK-P6-SUBSCRIPTION-MULTI-ORIGIN`** |
| 011 | **P2-RED-MUX-01** | **DONE** | ≥2 транспортных профиля в матрице | alt_ob_share 56% §12 | **§5.1**, **`TRANSPORT-MUX-MATRIX`** |
| 012 | **P6-RED-SUBHA-01** | **DONE** | Горизонталь sub-page или split host | split-host :3010/:3011, HA probe OK §12 | **§5.1**, **`RUNBOOK-P6-SUBSCRIPTION-HA`** |
| 013 | **P6-SCALE-02** | **DONE** | Soft cap + правило 3-й ноды | **`NODE-POLICY-LV-NL`** §12 | **§10.2** |
| 014 | **P6-SCALE-03** | **DONE** | Postgres индексы / `pg_stat_statements` | **`RUNBOOK-P6-POSTGRES-MAINTENANCE`** §12 | **§10.2** |
| 015 | **GTM-WIKI-01** | **DONE** | Wiki по **`GTM-GROWTH-OUTLINE`**; URL в §1 бэклога | шаблон + **`GTM-WIKI.md`** §12 | **`RUNBOOK-GTM-WIKI`** |
| 016 | **P2-OPS-IMAGE-PIN-01** | **DONE** | Digest pin postgres/valkey/caddy/adguard | `check_compose_image_pins.py` OK §12 | **§6**, **`IMAGE-PINS.md`** |
| 017 | **P6-SCALE-06** | **DONE** | RU-monitor цикл **< 5 мин**; лог **`duration_sec`** | probe **`RU_MONITOR_CYCLE_OK`** §12 | **`RUNBOOK-P6-RU-MONITOR-SCALE`** |
| 018 | **P6-SCALE-05** | **NEXT** | API панели: refresh × N; Redis eviction | прогон refresh × N | **§11** |
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
| 009 | `ops: P6-RED-PAY-01 — webhook idempotency + DLQ` |
| 010 | `ops: P2-RED-SUB-01 — multi-origin подписки + drift probe` |
| 011 | `docs: P2-RED-MUX-01 — transport matrix + mux audit` |
| 012 | `ops: P6-RED-SUBHA-01 — split-host sub-page :3010/:3011 + HA load probe` |
| 013 | `docs: P6-SCALE-02 — soft cap policy + capacity_snapshot alerts` |
| 014 | `ops: P6-SCALE-03 — Postgres maintenance plan + backup window + audit` |
| 015 | `docs: GTM-WIKI-01 — GTM wiki template + registry + runbook` |
| 016 | `ops: P2-OPS-IMAGE-PIN-01 — digest pin postgres/valkey/adguard + IMAGE-PINS` |
| 017 | `ops: P6-SCALE-06 — ru-monitor cycle duration log + probe; GTM owner gate closed` |

После коммита с закрытием задачи — в **`BACKLOG-QUEUE.md`**: сменить статусы и при необходимости добавить подстроку в §12 бэклога (в том же коммите).

---

## История смены NEXT

| Дата | Было NEXT | Стало |
|------|-----------|--------|
| 2026-05-16 | — | **Q002** (**P6-SCALE-04b**) после внедрения очереди |
| 2026-05-16 | **Q002** P6-SCALE-04b | **Q003** P6-SCALE-04c |
| 2026-05-16 | **Q003** P6-SCALE-04c | **Q004** P2-OPS-RESTORE-TEST-01 |
| 2026-05-16 | **Q004** P2-OPS-RESTORE-TEST-01 | **Q005** P2-COM-MONETIZE-01 |
| 2026-05-16 | **Q005** P2-COM-MONETIZE-01 | **Q006** P2-COM-MONETIZE-02 |
| 2026-05-16 | **Q006** P2-COM-MONETIZE-02 | **Q007** P2-COM-MONETIZE-03 |
| 2026-05-16 | **Q007** P2-COM-MONETIZE-03 | **Q008** P2-COM-MONETIZE-04 |
| 2026-05-16 | **Q008** P2-COM-MONETIZE-04 | **Q009** P6-RED-PAY-01 |
| 2026-05-16 | **Q009** P6-RED-PAY-01 | **Q010** P2-RED-SUB-01 |
| 2026-05-16 | **Q010** P2-RED-SUB-01 | **Q011** P2-RED-MUX-01 |
| 2026-05-16 | **Q011** P2-RED-MUX-01 | **Q012** P6-RED-SUBHA-01 |
| 2026-05-16 | **Q012** P6-RED-SUBHA-01 | **Q013** P6-SCALE-02 |
| 2026-05-16 | **Q013** P6-SCALE-02 | **Q014** P6-SCALE-03 |
| 2026-05-16 | **Q014** P6-SCALE-03 | **Q015** GTM-WIKI-01 |
| 2026-05-16 | **Q015** GTM-WIKI-01 | **Q016** P2-OPS-IMAGE-PIN-01 |
| 2026-05-16 | **Q016** P2-OPS-IMAGE-PIN-01 | **Q017** §11 (P1-RED / P6-SCALE-05…) |
| 2026-05-16 | **Q017** P6-SCALE-06 (+ GTM gate) | **Q018** P6-SCALE-05 |
