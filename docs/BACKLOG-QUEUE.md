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

**Карта документов:** **`docs/BACKLOG-MAP.md`** (иерархия, фазы, URL portal).

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

**Старт:** после закрытия Q022 (**2026-05-17**). **Фаза 2 закрыта** (**2026-05-17**, Q031). Дальше — **фаза 3** (таблица ниже).

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

### Фаза 3 — критичное → продукт → флоу (после Q031)

**Старт:** **2026-05-17**.

**Порядок агента (строго, без исключений):**

1. **Security** **Q063–Q078** (CodeRabbit; сначала критичное)
2. **Продукт / ТСПУ** **Q051–062**
3. **Флоу** **Q044–050**

**NEXT:** **Q064** (**P3-RED-SUP-01** — support reply authz).

| Кому | Документ |
|------|----------|
| **Агент — security (сейчас)** | **`docs/AUDIT-2026-05-SECURITY.md`** — Q063–Q078 |
| Агент — продукт (после **Q078**) | **`docs/AGENT-PRODUCT-BACKLOG.md`** — Q051–062 |
| Агент — флоу (после **Q062**) | **`docs/AGENT-FLOW-BACKLOG.md`** |
| Правила Cursor | **`sequential-backlog.mdc`**; после Q078 — **`product-backlog.mdc`**; после Q062 — **`flow-backlog.mdc`** |

| Блок | Q | Смысл |
|------|---|--------|
| Legal (владелец, не NEXT) | 032 | Возвраты — **TODO**; только владелец или по явной просьбе |
| MVP portal | 033–043 | **DONE** |
| **Security** | **063–078** | **Сейчас** — billing, support, webhooks, logs, … |
| **Продукт / ТСПУ** | **051–062** | Порт **8443**, v2rayN, VLESS, SNI, тиры (**`TSPU-OBSERVATIONS.md`**) |
| **Флоу** | **044–050** | Только после **Q062** |

| Q | ID | Статус | Done when (кратко) | Verify | Runbook / § |
|---|-----|--------|-------------------|--------|-------------|
| 032 | **P5-COM-02** | **TODO** | Возвраты в оферте (**владелец**; не в очереди агента) | Текст согласован владельцем | §9, **`AGENT-FLOW-BACKLOG` §Q032** |
| 033 | **P3-FLOW-00** | **DONE** | Карта флоу: сайт = Mini App = бот | **USER_FLOW_JOURNEY_OK** §12 | **`USER-FLOW-JOURNEY.md`** |
| 034 | **P3-FLOW-14** | **DONE** | `web/portal/` + ru.json (iPhone/Android/Win/Mac, Happ) | **PORTAL_BUNDLE_OK** §12 | §Q034 |
| 035 | **P3-FLOW-01** | **DONE** | `/start` + `/portal` на LV; as-is бот в journey | **`PUBLIC_BOOTSTRAP_OK`** §12 | **`RUNBOOK-USER-BOOTSTRAP-SITE`** |
| 036 | **P3-FLOW-02** | **DONE** | `/setup/?t=` HMAC + QR + verify API | **`PORTAL_SETUP_PAGE_OK`** §12 | **`RUNBOOK-USER-BOOTSTRAP-SITE`** |
| 037 | **P3-FLOW-12** | **DONE** | Mini App = portal; Menu Button + WebApp | **`TELEGRAM_MINIAPP_PORTAL_OK`** §12 | **`RUNBOOK-TELEGRAM-MINIAPP`** |
| 038 | **P3-FLOW-03** | **DONE** | Бот: WebApp + браузер + setup; UI ≈ HITVPN | **`BOT_PORTAL_LINKS_OK`** §12 | §Q038 |
| 039 | **P3-FLOW-04** | **DONE** | Мастер «Подключить VPN»; CTA → Mini App | **VPN_SETUP_WIZARD_OK** §12 | §Q039 |
| 040 | **P3-FLOW-07** | **DONE** | FAQ/онбординг/ru.json — оплата live | **PAYMENT_COPY_SYNC_OK** §12 | **`FAQ.md`** |
| 041 | **P3-FLOW-05** | **DONE** | QR (бот + portal) | **BOT_SUBSCRIPTION_QR_OK** / **PORTAL_SUBSCRIPTION_QR_OK** §12 | §7.1 |
| 042 | **P3-FLOW-06** | **DONE** | Видео/GIF на portal | **PORTAL_SETUP_VIDEO_OK** §12 | §7.1 |
| 043 | **P3-FLOW-08** | **DONE** | Страница ошибок на portal | **PORTAL_HELP_ERRORS_OK** §12 | §7.1 |
| 063 | **P6-RED-PAY-03** | **DONE** | Auto-renew: списание баланса / отказ + уведомление | **`AUTO_RENEW_BILLING_OK`** §12 | **`AUDIT-2026-05-SECURITY`**, `scheduler.py` |
| 064 | **P3-RED-SUP-01** | **NEXT** | Ответы из support group только **SUPPORT_STAFF_IDS** / admin | **`SUPPORT_REPLY_AUTHZ_OK`** | `support_handler.py` |
| 065 | **P2-OPS-SCHED-01** | **TODO** | Expiry notify: сравнение в **UTC** (aware datetime) | **`EXPIRY_TZ_OK`** | `scheduler.py` |
| 066 | **P1-RED-LOG-02** | **TODO** | **`log_skip`** `/api/sub/*` на **k9x2m1** | grep access-log без token path | **`RUNBOOK-CADDY-SUBSCRIPTION-LOGS`** |
| 067 | **P6-RED-PAY-04** | **TODO** | **CryptoBot POST** + `hmac.compare_digest` | **`CRYPTOBOT_WEBHOOK_POST_OK`** | `app.py` |
| 068 | **P6-RED-PAY-05** | **TODO** | **`WEBHOOK_TRUST_PROXY_HEADERS` default false** | **`WEBHOOK_XFF_HARDEN_OK`** | `auth.py` |
| 069 | **P1-RED-NET-01** | **TODO** | Panel **127.0.0.1:3000** в compose tmpl | external :3000 fail | `docker-compose.yml.tmpl` |
| 070 | **P6-RED-PAY-06** | **TODO** | Cross-check суммы платежа vs invoice | **`PAYMENT_AMOUNT_VERIFY_OK`** | `payment_queue.py` |
| 071 | **P6-RED-PAY-07** | **TODO** | CRITICAL log если `SKIP_API_VERIFY` на проде | smoke flag unset | `app.py` |
| 072 | **P3-RED-SETUP-01** | **TODO** | Caddy **rate_limit** `/setup/api/*` | burst → **429** | Caddy k9x2m1 |
| 073 | **P3-RED-SUP-02** | **TODO** | Rate limit user→support | flood test | `support_handler.py` |
| 074 | **P2-OPS-BACKUP-01** | **TODO** | Backup filename с **timestamp** | `backup_YYYYMMDD_*` | `handlers.py` |
| 075 | **P2-CHORE-SUP-01** | **TODO** | `support_handler` → `DB_FILE` из `database.py` | один путь | `support_handler.py` |
| 076 | **P5-ENG-03** | **TODO** | Lazy `REMNA_API_TOKEN` + inbound cache TTL | ротация без restart | `remnawave_api.py` |
| 077 | **P1-ENG-04** | **TODO** | Hardcoded IP в bot → env / `site_urls` | grep clean | `handlers.py` |
| 078 | **P2-OPS-REMNA-KEY-01** | **TODO** | Fail fast без `REMNA_PUBLIC_KEY` | smoke URI | `remnawave_api.py` |
| 051 | **P2-RED-EDGE-PORT-01** | **TODO** | **P0** Edge **2053→8443** | **`SUB_EDGE_PORT_OK`** | **`AGENT-PRODUCT-BACKLOG` §Q051** |
| 052 | **P1-PRO-CLIENT-V2RAYN-01** | **TODO** | **P1** v2rayN Win | **`V2RAYN_CLIENT_OK`** | **§Q052** |
| 053 | **P5-PROD-NATIVE-APP-01** | **TODO** | **P2** Brief iOS/Android | **`NATIVE-APP-BACKLOG.md`** | **§Q053** |
| 054 | **P2-RED-TSPU-VLESS-01** | **TODO** | **P1** Runbook VLESS / ТСПУ | **`TSPU_VLESS_PLAYBOOK_OK`** | **§Q054** |
| 055 | **P1-RED-TSPU-BLOCK-01** | **TODO** | **P1** Probe RU block | **`TSPU_BLOCK_PROBE_OK`** | **§Q055** |
| 056 | **P2-RED-VPN-INBOUND-PORT-01** | **TODO** | **P1** Inbound VPN ≠443 | **`VPN_INBOUND_PORT_OK`** | **§Q056** |
| 057 | **P2-RED-SELFSTEAL-REVIEW-01** | **TODO** | **P1** Selfsteal go/no-go | **`SELFSTEAL_REVIEW_OK`** | **§Q057** |
| 058 | **P2-RED-SNI-ROTATE-01** | **TODO** | **P0** SNI **yandex.ru** | **`SNI_ROTATE_OK`** | **§Q058** |
| 059 | **P1-RED-TSPU-THREAT-MODEL-01** | **TODO** | **P1** Wiki ТСПУ | **`TSPU-THREAT-MODEL.md`** | **§Q059** |
| 060 | **P4-DNS-07/08** | **TODO** | **P4** RF egress; **стоп** — согласовать с владельцем | Wiki/PoC | **§Q060** |
| 061 | **P1-RED-NODE-DNS-01** | **TODO** | **P1** DNS на нодах | **`NODE_DNS_RESOLVER_OK`** | **§Q061** |
| 062 | **P1-PRO-SUB-TIER-01** | **TODO** | **P0** 3 tier sub | **`SUB_TIER_PROFILES_OK`** | **§Q062** |
| 044 | **P3-FLOW-09** | **TODO** | **ФЛОУ** Ветки iPhone/Android/Win | ≤ 5 шагов | **`AGENT-FLOW-BACKLOG` §Q044** |
| 045 | **P3-FLOW-13** | **TODO** | a11y portal | Lighthouse ≥ 95 | §7.1 |
| 046 | **P3-FLOW-10** | **TODO** | Метрики воронки | Wiki + §12 | §7.1 |
| 047 | **P3-FLOW-11** | **TODO** | Запасной домен bootstrap | Tabletop | §7.1 |
| 048 | **P3-FLOW-15** | **TODO** | Баланс в веб-ЛК (read API; оплата после эквайринга) | **`PORTAL_CABINET_BALANCE_OK`** | §7.1, **`AGENT-FLOW-BACKLOG` §Q048** |
| 049 | **P3-FLOW-16** | **TODO** | Привязка TG ↔ web (`BVPN-ID` / email) | **`WEB_TG_BIND_OK`** | §7.1, **`USER-FLOW-JOURNEY`** §Web |
| 050 | **P3-FLOW-17** | **TODO** | Уведомления web-only (portal + опц. email) | **`WEB_NOTIFY_CHANNEL_OK`** | §7.1, **P2-RED-BOOT-01** |

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
| 051 | `ops: P2-RED-EDGE-PORT-01 — migrate public edge 2053 to 8443 (TSPU)` |
| 052 | `product: P1-PRO-CLIENT-V2RAYN-01 — Windows v2rayN compatibility` |
| 053 | `docs: P5-PROD-NATIVE-APP-01 — native app product brief` |
| 054 | `docs: P2-RED-TSPU-VLESS-01 — TSPU VLESS incident runbook` |
| 055 | `ops: P1-RED-TSPU-BLOCK-01 — RU block probe ports>990 SSL` |
| 056 | `ops: P2-RED-VPN-INBOUND-PORT-01 — VPN node inbound port migration` |
| 057 | `docs: P2-RED-SELFSTEAL-REVIEW-01 — decoy/selfsteal go-no-go` |
| 058 | `ops: P2-RED-SNI-ROTATE-01 — rotate Reality dest SNI off github cluster` |
| 059 | `docs: P1-RED-TSPU-THREAT-MODEL-01 — TSPU threat model wiki` |
| 060 | `docs: P4-DNS-07/08 — RF egress + whitelist IP source` |
| 061 | `ops: P1-RED-NODE-DNS-01 — node DNS resolver policy` |
| 062 | `product: P1-PRO-SUB-TIER-01 — turbo/wl-direct/wl-routed subscription tiers` |
| 063 | `security: P6-RED-PAY-03 — auto-renew balance deduction` |
| 064 | `security: P3-RED-SUP-01 — support reply staff allowlist` |
| 065 | `fix: P2-OPS-SCHED-01 — UTC-aware expiry notifications` |
| 066 | `ops: P1-RED-LOG-02 — log_skip on k9x2m1 sub origin` |
| 067 | `security: P6-RED-PAY-04 — cryptobot POST webhook + compare_digest` |
| 068 | `security: P6-RED-PAY-05 — webhook XFF trust default false` |
| 069 | `ops: P1-RED-NET-01 — bind panel port to loopback` |
| 070 | `security: P6-RED-PAY-06 — payment amount cross-validation` |
| 071 | `security: P6-RED-PAY-07 — alarm on YOOKASSA skip verify flag` |
| 072 | `ops: P3-RED-SETUP-01 — Caddy rate limit setup API` |
| 073 | `product: P3-RED-SUP-02 — support user message rate limit` |
| 074 | `ops: P2-OPS-BACKUP-01 — timestamped backup filenames` |
| 075 | `chore: P2-CHORE-SUP-01 — support handler DB path from database module` |
| 076 | `bot: P5-ENG-03 — lazy Remna token + inbound cache TTL` |
| 077 | `ops: P1-ENG-04 — externalize hardcoded infra IPs in bot` |
| 078 | `ops: P2-OPS-REMNA-KEY-01 — fail on missing REMNA public key` |
| 044 | `product: P3-FLOW-09 — device-specific portal branches` |
| 045 | `product: P3-FLOW-13 — portal a11y pass` |
| 046 | `ops: P3-FLOW-10 — funnel metrics hooks` |
| 047 | `docs: P3-FLOW-11 — backup bootstrap domain runbook` |
| 048 | `product: P3-FLOW-15 — portal cabinet balance read API` |
| 049 | `product: P3-FLOW-16 — web TG bind BVPN-ID` |
| 050 | `product: P3-FLOW-17 — web-only notifications channel` |

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
| 2026-05-17 | **Q039** P3-FLOW-04 | **Q040** P3-FLOW-07 |
| 2026-05-17 | **Q040** P3-FLOW-07 | **Q041** P3-FLOW-05 |
| 2026-05-17 | **Q041** P3-FLOW-05 | **Q042** P3-FLOW-06 |
| 2026-05-17 | **Q042** P3-FLOW-06 | **Q043** P3-FLOW-08 |
| 2026-05-17 | **Q043** P3-FLOW-08 | **Q044** P3-FLOW-09 |
| 2026-05-18 | — | Очередь **Q051–053**: порт edge, v2rayN, native app brief (фидбек бета) |
| 2026-05-18 | — | **Q054–061** + **`TSPU-OBSERVATIONS.md`**: 12 пунктов ТСПУ по матрице |
| 2026-05-18 | **Q044** P3-FLOW-09 | **Q051** P2-RED-EDGE-PORT-01 — продукт вперёд флоу; **8443** |
| 2026-05-18 | — | CodeRabbit audit → **Q063–Q078** pre-GTM security; **`AUDIT-2026-05-SECURITY.md`** |
| 2026-05-18 | **Q051** P2-RED-EDGE-PORT-01 | **Q063** P6-RED-PAY-03 — порядок: **security → продукт → флоу** |
| 2026-05-18 | **Q063** P6-RED-PAY-03 | **Q064** P3-RED-SUP-01 |
| 2026-05-17 | — | Синхронизация бэклога: **`BACKLOG-MAP.md`**, §5.1 ✅, FAQ, Q032 помечен «до GTM» |
