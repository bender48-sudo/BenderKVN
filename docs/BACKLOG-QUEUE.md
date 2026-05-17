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

## Текущая очередь

### Фаза 1 — рост → 10k (лето 2026) — **закрыта**

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
| 018 | **P6-SCALE-05** | **DONE** | API панели: refresh × N; Redis eviction | **100×200** p95≈**1.4s**; Valkey **allkeys-lru** §12 | **`RUNBOOK-P6-PANEL-API-SCALE`** |
| 019 | **P6-SCALE-07** | **DONE** | Поддержка: шаблоны + SLA при росте очереди | **`SUPPORT_QUEUE_OK`** §12 | **`RUNBOOK-P6-SUPPORT-SCALE`** |
| 020 | **P2-RED-BOOT-01** | **DONE** | Резервный канал статуса (не только TG) | **`STATUS_CHANNELS_OK`** §12 | **`RUNBOOK-P2-STATUS-BOOT-CHANNEL`** |
| 021 | **P2-RED-TLS-01** | **DONE** | Квартальный обзор sing-box / uTLS / ECH | **`TLS-QUARTERLY-2026-Q2`** + audit OK §12 | **`TLS-CLIENT-STACK-REVIEW`** |
| 022 | **P6-RED-PG-01** | **DONE** | Postgres read replicas / pool limit / load test | **PG_STAMPEDE_LOAD_OK** §12 | **`RUNBOOK-P6-POSTGRES-RED`** |

### Фаза 2 — Red team (P1-RED) + платежи + путь к 30k

**Старт:** после закрытия Q022 (**2026-05-17**). **Фаза 2 закрыта** (**2026-05-17**, Q031). Следующий **NEXT** — из §3/§9 бэклога или новая строка в этой таблице.

| Q | ID | Статус | Done when (кратко) | Verify | Runbook / § |
|---|-----|--------|-------------------|--------|-------------|
| 023 | **P2-OPS-AMS-SAFE-DEPLOY-01** | **DONE** | Чеклист gate + smoke pre/post наката AMS; урок **502 2026-05-17** в runbook | **AMS_SAFE_DEPLOY_OK** §12 | **`RUNBOOK-AMS-SAFE-DEPLOY`**, **§6** |
| 024 | **P6-RED-PAY-02** | **DONE** | Webhook: YooKassa API verify + IP/proxy; Flask **127.0.0.1:1488**; crypto secret | **WEBHOOK_AUTH_OK** §12 | **§5.1**, **`RUNBOOK-COMMERCE-GO-LIVE` §2** |
| 025 | **P1-RED-SSH-01** | **DONE** | Per-host ключи LV/AMS/NL; legacy shared key снят; audit с панели + workstation | **SSH_AUDIT_OK** §12 | **§5.1**, **`SSH-KEY-INVENTORY`** |
| 026 | **P1-RED-DNS-01** | **DONE** | ≥2 регистратора в wiki; DNSSEC runbook; probe делегирования на LV | **DNS_DELEGATION_OK** §12 | **§5.1**, **`DNS-CRITICAL-NAMES`** |
| 027 | **P1-RED-DATA-01** | **DONE** | LUKS2 том Postgres AMS; ключ в Bitwarden; probe + safe-deploy | **POSTGRES_CRYPT_OK** §12 | **`POSTGRES-ENCRYPTION-AMS`** |
| 028 | **P1-RED-SEC-01** | **DONE** | Broker TTL+audit; ru-monitor + balancer на LV | **SHORT_LIVED_TOKEN_OK** §12 | **`RUNBOOK-SHORT-LIVED-CREDS`** |
| 029 | **P3-RED-MIN-01** | **DONE** | Политика + инвентарь полей; redact webhook; audit | **DATA_MINIMIZATION_OK** §12 | **`DATA-MINIMIZATION-POLICY`** |
| 030 | **P3-RED-JURIS-01** | **DONE** | Wiki + runbook VPS/PSP; tabletop шаблон; audit | **JURIS_FAILOVER_OK** §12 | **`JURISDICTION-FAILOVER-WIKI`** |
| 031 | **P5-COM-01** | **DONE** | HTML `/status` на k9x2m1; incidents.json; cron | **PUBLIC_STATUS_PAGE_OK** §12 | **`RUNBOOK-PUBLIC-STATUS-PAGE`** |

**Gate (не отдельный Q):** любой накат AMS compose/env — только по **`RUNBOOK-AMS-SAFE-DEPLOY`** (закрепляется **Q023**).

**Параллельно (другой человек, не трогать NEXT):** **P4-DNS-01…06** (mobile bootstrap / whitelist SKU).

### Фаза 3 — продукт, флоу, GTM (после Q031)

**Старт:** после закрытия фазы 2 (**2026-05-17**).  
**Инструкции для агента:** **`docs/AGENT-FLOW-BACKLOG.md`** (портал = сайт + Mini App).  
**NEXT:** **Q039** (**P3-FLOW-04**).

| Q | ID | Статус | Done when (кратко) | Verify | Runbook / § |
|---|-----|--------|-------------------|--------|-------------|
| 032 | **P5-COM-02** | **TODO** | Возвраты при массовом дауне в оферте | Текст согласован владельцем | **`AGENT-FLOW-BACKLOG` §Q032** |
| 033 | **P3-FLOW-00** | **DONE** | Карта флоу: сайт = Mini App = бот | **USER_FLOW_JOURNEY_OK** §12 | **`USER-FLOW-JOURNEY.md`** |
| 034 | **P3-FLOW-14** | **DONE** | `web/portal/` + ru.json (iPhone/Android/Win/Mac, Happ) | **PORTAL_BUNDLE_OK** §12 | §Q034 |
| 035 | **P3-FLOW-01** | **DONE** | `/start` + `/portal` на LV; as-is бот в journey | **`PUBLIC_BOOTSTRAP_OK`** §12 | **`RUNBOOK-USER-BOOTSTRAP-SITE`** |
| 036 | **P3-FLOW-02** | **DONE** | `/setup/?t=` HMAC + QR + verify API | **`PORTAL_SETUP_PAGE_OK`** §12 | **`RUNBOOK-USER-BOOTSTRAP-SITE`** |
| 037 | **P3-FLOW-12** | **DONE** | Mini App = portal; Menu Button + WebApp | **`TELEGRAM_MINIAPP_PORTAL_OK`** §12 | **`RUNBOOK-TELEGRAM-MINIAPP`** |
| 038 | **P3-FLOW-03** | **DONE** | Бот: WebApp + браузер + setup; UI ≈ HITVPN | **`BOT_PORTAL_LINKS_OK`** §12 | §Q038 |
| 039 | **P3-FLOW-04** | **NEXT** | Мастер «Подключить VPN»; CTA → Mini App | Сценарий journey | §Q039 |
| 040 | **P3-FLOW-07** | **TODO** | FAQ/онбординг/ru.json — оплата live | Diff OK | **`FAQ.md`** |
| 041 | **P3-FLOW-05** | **TODO** | QR (бот + portal) | Скан → Happ | §7.1 |
| 042 | **P3-FLOW-06** | **TODO** | Видео/GIF на portal | Без VPN с телефона | §7.1 |
| 043 | **P3-FLOW-08** | **TODO** | Страница ошибок на portal | 5 кейсов | §7.1 |
| 044 | **P3-FLOW-09** | **TODO** | Ветки iPhone / Android / Win | ≤ 5 шагов | §7.1 |
| 045 | **P3-FLOW-13** | **TODO** | a11y portal | Lighthouse ≥ 95 | §7.1 |
| 046 | **P3-FLOW-10** | **TODO** | Метрики воронки | Wiki + §12 | §7.1 |
| 047 | **P3-FLOW-11** | **TODO** | Запасной домен bootstrap | Tabletop | §7.1 |

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
| 018 | `ops: P6-SCALE-05 — panel refresh load probe + Valkey allkeys-lru` |
| 019 | `ops: P6-SCALE-07 — support queue metric + SLA templates + bot timestamps` |
| 020 | `ops: P2-RED-BOOT-01 — HTTPS status JSON mirror + dual-channel smoke` |
| 021 | `docs: P2-RED-TLS-01 — quarterly TLS/sing-box review checklist + audit` |
| 022 | `ops: P6-RED-PG-01 — Postgres pool limits + stampede load probe` |
| 023 | `ops: P2-OPS-AMS-SAFE-DEPLOY-01 — gate smoke + runbook post-502 checklist` |
| 024 | `security: P6-RED-PAY-02 — webhook signature/allowlist + smoke` |
| 025 | `ops: P1-RED-SSH-01 — per-host SSH keys + inventory` |
| 026 | `ops: P1-RED-DNS-01 — multi-registrar DNS + DNSSEC wiki` |
| 027 | `ops: P1-RED-DATA-01 — Postgres volume encryption AMS` |
| 028 | `ops: P1-RED-SEC-01 — short-lived creds pilot (monitors)` |
| 029 | `docs: P3-RED-MIN-01 — data minimization policy + DB checklist` |
| 030 | `docs: P3-RED-JURIS-01 — jurisdiction failover runbook` |
| 031 | `product: P5-COM-01 — public incident status page` |
| 032 | `docs: P5-COM-02 — правила возвратов в оферте` |
| 033 | `docs: P3-FLOW-00 — user journey map + grandma-test criteria` |
| 034 | `product: P3-FLOW-14 — shared portal bundle (ru.json + base UI)` |
| 035 | `product: P3-FLOW-01 — bootstrap /start on LV + smoke` |
| 036 | `product: P3-FLOW-02 — setup page + signed token helper` |
| 037 | `product: P3-FLOW-12 — Telegram Mini App mirrors portal` |
| 038 | `product: P3-FLOW-03 — bot portal + setup links` |
| 039 | `product: P3-FLOW-04 — VPN setup wizard + Mini App CTA` |
| 040 | `docs: P3-FLOW-07 — FAQ/onboarding/portal payment copy sync` |
| 041 | `product: P3-FLOW-05 — subscription QR in bot and portal` |
| 042 | `product: P3-FLOW-06 — setup video on portal` |
| 043 | `product: P3-FLOW-08 — human-readable errors on portal` |
| 044 | `product: P3-FLOW-09 — device-specific portal branches` |
| 045 | `product: P3-FLOW-13 — portal a11y pass` |
| 046 | `ops: P3-FLOW-10 — funnel metrics hooks` |
| 047 | `docs: P3-FLOW-11 — backup bootstrap domain runbook` |

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
| 2026-05-16 | **Q018** P6-SCALE-05 | **Q019** P6-SCALE-07 |
| 2026-05-16 | **Q019** P6-SCALE-07 | **Q020** P2-RED-BOOT-01 |
| 2026-05-16 | **Q020** P2-RED-BOOT-01 | **Q021** P2-RED-TLS-01 |
| 2026-05-16 | **Q021** P2-RED-TLS-01 | **Q022** P6-RED-PG-01 |
| 2026-05-17 | **Q022** P6-RED-PG-01 | — (фаза 1 закрыта) |
| 2026-05-17 | — | **Q023** (**P2-OPS-AMS-SAFE-DEPLOY-01**) — фаза 2 Red team / 30k |
| 2026-05-17 | **Q023** P2-OPS-AMS-SAFE-DEPLOY-01 | **Q024** P6-RED-PAY-02 |
| 2026-05-17 | **Q024** P6-RED-PAY-02 | **Q025** P1-RED-SSH-01 |
| 2026-05-17 | **Q025** P1-RED-SSH-01 | **Q026** P1-RED-DNS-01 |
| 2026-05-17 | **Q026** P1-RED-DNS-01 | **Q027** P1-RED-DATA-01 |
| 2026-05-17 | **Q027** P1-RED-DATA-01 | **Q028** P1-RED-SEC-01 |
| 2026-05-17 | **Q028** P1-RED-SEC-01 | **Q029** P3-RED-MIN-01 |
| 2026-05-17 | **Q029** P3-RED-MIN-01 | **Q030** P3-RED-JURIS-01 |
| 2026-05-17 | **Q030** P3-RED-JURIS-01 | **Q031** P5-COM-01 |
| 2026-05-17 | **Q031** P5-COM-01 | — (**фаза 2 закрыта**) |
| 2026-05-17 | — | **Фаза 3** Q032–Q047; **`docs/AGENT-FLOW-BACKLOG.md`** |
| 2026-05-17 | — | **NEXT=Q033** (**P3-FLOW-00** journey map) |
| 2026-05-17 | **Q033** P3-FLOW-00 | **Q034** P3-FLOW-14 |
| 2026-05-17 | **Q034** P3-FLOW-14 | **Q035** P3-FLOW-01 |
| 2026-05-17 | **Q035** P3-FLOW-01 | **Q036** P3-FLOW-02 |
| 2026-05-17 | **Q036** P3-FLOW-02 | **Q037** P3-FLOW-12 |
| 2026-05-17 | **Q037** P3-FLOW-12 | **Q038** P3-FLOW-03 |
| 2026-05-17 | **Q038** P3-FLOW-03 | **Q039** P3-FLOW-04 |
