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

**Порядок (репо закрыто → прод):**

1. ~~**Q063–078** security~~ **DONE** (код в репо)
2. ~~**Q051–062** продукт~~ **DONE** (репо + docs)
3. ~~**Q044–050** флоу~~ **DONE** (репо)
4. ~~**Q079–Q084**~~ **DONE** (накат LV/AMS)
5. ~~**Q085**~~ **DONE** (ТСПУ red-team отчёт)
6. **Фаза 6** — GTM hardening (**Q086–097**, см. **`AGENT-PHASE6-BACKLOG.md`**)
7. **Q032** — возвраты в оферте (**только владелец**, параллельно)

**NEXT:** **Q120** (2-й RU relay — **только владелец**, нужен 2-й VPS).

| Кому | Документ |
|------|----------|
| **Агент — сейчас** | — (очередь агента до **Q120**); **Q120** / **Q032** — владелец |
| Владелец (параллельно) | **`docs/MANUAL-OWNER-CHECKLIST.md`**, LTE § **`AUDIT-2026-05-TSPU-REDTEAM.md`** |
| Аудиты | **`POST-DEPLOY-REVIEW-2026-05.md`**, **`AUDIT-2026-05-TSPU-REDTEAM.md`** |
| Правило Cursor | **`sequential-backlog.mdc`** |

| Блок | Q | Смысл |
|------|---|--------|
| Legal (владелец) | 032 | Возвраты — **TODO** |
| Репо + прод Q001–085 | … | **DONE** |
| **GTM security** | **086–089** | Admin, print, :2054, cabinet |
| **ТСПУ / discovery** | **090–095** | :8443 UX, sunset 2053, alt apex, RU probe |
| **Polish** | **096–097** | HSTS/CSP, flow/LK deploy |

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
| 064 | **P3-RED-SUP-01** | **DONE** | Ответы из support group только **SUPPORT_STAFF_IDS** / admin | **`SUPPORT_REPLY_AUTHZ_OK`** §12 | `support_handler.py` |
| 065 | **P2-OPS-SCHED-01** | **DONE** | Expiry notify: сравнение в **UTC** (aware datetime) | **`EXPIRY_TZ_OK`** §12 | `scheduler.py` |
| 066 | **P1-RED-LOG-02** | **DONE** | **`log_skip`** `/api/sub/*` на **k9x2m1** | **`SUB_LOG_SKIP_K9_OK`** §12 | **`RUNBOOK-CADDY-SUBSCRIPTION-LOGS`** |
| 067 | **P6-RED-PAY-04** | **DONE** | **CryptoBot POST** + `hmac.compare_digest` | **`CRYPTOBOT_WEBHOOK_POST_OK`** §12 | `app.py` |
| 068 | **P6-RED-PAY-05** | **DONE** | **`WEBHOOK_TRUST_PROXY_HEADERS` default false** | **`WEBHOOK_XFF_HARDEN_OK`** §12 | `auth.py` |
| 069 | **P1-RED-NET-01** | **DONE** | Panel **127.0.0.1:3000** в compose tmpl | compose tmpl §12 | `docker-compose.yml.tmpl` |
| 070 | **P6-RED-PAY-06** | **DONE** | Cross-check суммы платежа vs invoice | **`PAYMENT_AMOUNT_VERIFY_OK`** §12 | `payment_queue.py` |
| 071 | **P6-RED-PAY-07** | **DONE** | CRITICAL log если `SKIP_API_VERIFY` на проде | **`YOOKASSA_SKIP_VERIFY_OK`** §12 | `auth.py` |
| 072 | **P3-RED-SETUP-01** | **DONE** | Caddy **rate_limit** `/setup/api/*` | Caddy tmpl §12 | Caddy k9x2m1 |
| 073 | **P3-RED-SUP-02** | **DONE** | Rate limit user→support | `support_handler.py` §12 | `support_handler.py` |
| 074 | **P2-OPS-BACKUP-01** | **DONE** | Backup filename с **timestamp** | **`BACKUP_FILENAME_OK`** §12 | `handlers.py` |
| 075 | **P2-CHORE-SUP-01** | **DONE** | `support_handler` → `DB_FILE` из `database.py` | **`SUPPORT_DB_UNIFY_OK`** §12 | `support_handler.py` |
| 076 | **P5-ENG-03** | **DONE** | Lazy `REMNA_API_TOKEN` + inbound cache TTL | `remnawave_api.py` §12 | `remnawave_api.py` |
| 077 | **P1-ENG-04** | **DONE** | Hardcoded IP в bot → env / `site_urls` | **`HANDLERS_IP_OK`** §12 | `handlers.py` |
| 078 | **P2-OPS-REMNA-KEY-01** | **DONE** | Fail fast без `REMNA_PUBLIC_KEY` | **`REMNA_PUBLIC_KEY_OK`** §12 | `remnawave_api.py` |
| 051 | **P2-RED-EDGE-PORT-01** | **DONE** | **P0** Edge **2053→8443** | **`SUB_EDGE_PORT_OK`** §12 | **`RUNBOOK-P6-EDGE-PORT-MIGRATION.md`** |
| 052 | **P1-PRO-CLIENT-V2RAYN-01** | **DONE** | **P1** v2rayN Win | **`V2RAYN_CLIENT_OK`** §12 | **`CLIENT-V2RAYN.md`** |
| 053 | **P5-PROD-NATIVE-APP-01** | **DONE** | **P2** Brief iOS/Android | **`NATIVE-APP-BACKLOG.md`** §12 | **§Q053** |
| 054 | **P2-RED-TSPU-VLESS-01** | **DONE** | **P1** Runbook VLESS / ТСПУ | **`TSPU_VLESS_PLAYBOOK_OK`** §12 | **`RUNBOOK-TSPU-VLESS-INCIDENT.md`** |
| 055 | **P1-RED-TSPU-BLOCK-01** | **DONE** | **P1** Probe RU block | **`TSPU_BLOCK_PROBE_OK`** §12 | **`tspu_block_probe.py`** |
| 056 | **P2-RED-VPN-INBOUND-PORT-01** | **DONE** | **P1** Inbound VPN ≠443 | **`VPN_INBOUND_PORT_OK`** §12 | **`RUNBOOK-VPN-INBOUND-PORT.md`** |
| 057 | **P2-RED-SELFSTEAL-REVIEW-01** | **DONE** | **P1** Selfsteal go/no-go | **`SELFSTEAL_REVIEW_OK`** §12 | **`TSPU-OBSERVATIONS.md`** Q057 |
| 058 | **P2-RED-SNI-ROTATE-01** | **DONE** | **P0** SNI **yandex.ru** | **`SNI_ROTATE_OK`** §12 | `REMNA_SERVER_SNI` |
| 059 | **P1-RED-TSPU-THREAT-MODEL-01** | **DONE** | **P1** Wiki ТСПУ | **`TSPU-THREAT-MODEL.md`** §12 | **§Q059** |
| 060 | **P4-DNS-07/08** | **DONE** | **P4** RF egress PoC wiki | **`P4_RF_EGRESS_POC_OK`** §12 | **`P4-DNS-RF-EGRESS-POC.md`** |
| 061 | **P1-RED-NODE-DNS-01** | **DONE** | **P1** DNS на нодах | **`NODE_DNS_RESOLVER_OK`** §12 | **`RUNBOOK-NODE-DNS-RESOLVER.md`** |
| 062 | **P1-PRO-SUB-TIER-01** | **DONE** | **P0** 3 tier sub (portal + docs) | **`SUB_TIER_PROFILES_OK`** §12 | **`PRODUCT-TIER-PROFILES.md`** |
| 044 | **P3-FLOW-09** | **DONE** | **ФЛОУ** Ветки iPhone/Android/Win | **`PORTAL_DEVICE_BRANCHES_OK`** §12 | **`AGENT-FLOW-BACKLOG` §Q044** |
| 045 | **P3-FLOW-13** | **DONE** | a11y portal | **`PORTAL_A11Y_OK`** §12 | §7.1 |
| 046 | **P3-FLOW-10** | **DONE** | Метрики воронки | **`FUNNEL_METRICS_OK`** §12 | **`FUNNEL-METRICS.md`** |
| 047 | **P3-FLOW-11** | **DONE** | Запасной домен bootstrap | **`BACKUP_BOOTSTRAP_DOMAIN_OK`** §12 | **`RUNBOOK-BACKUP-BOOTSTRAP-DOMAIN.md`** |
| 048 | **P3-FLOW-15** | **DONE** | Баланс в веб-ЛК (read API) | **`PORTAL_CABINET_BALANCE_OK`** §12 | `portal_cabinet.py` |
| 049 | **P3-FLOW-16** | **DONE** | Привязка TG ↔ web (`BVPN-ID` / email) | **`WEB_TG_BIND_OK`** §12 | `web_tg_bind.py` |
| 050 | **P3-FLOW-17** | **DONE** | Уведомления web-only (portal) | **`WEB_NOTIFY_CHANNEL_OK`** §12 | events card + cabinet |

### Фаза 4 — накат на прод (агент + SSH)

**Старт:** после **Q050** (репо). Инструкции: **`docs/AGENT-PROD-DEPLOY-BACKLOG.md`**.

| Q | ID | Статус | Done when (кратко) | Verify | Runbook / § |
|---|-----|--------|-------------------|--------|-------------|
| 079 | **P2-OPS-DEPLOY-BOT-SEC-01** | **DONE** | Бот AMS: security-код + env; webhook/support smokes | **`WEBHOOK_AUTH_OK`** + **`AUTO_RENEW_BILLING_OK`** | **`AGENT-PROD-DEPLOY-BACKLOG` §Q079** |
| 080 | **P2-OPS-DEPLOY-EDGE-01** | **DONE** | Caddy LV **:8443** + portal; live sub/bootstrap smoke | **`SUB_EDGE_PORT_OK`** live | **`RUNBOOK-P6-EDGE-PORT-MIGRATION`** |
| 081 | **P2-OPS-DEPLOY-PANEL-01** | **DONE** | Panel :3000 снаружи закрыт (UFW); API **:8443** OK | external :3000 fail | **`RUNBOOK-AMS-SAFE-DEPLOY`** |
| 082 | **P2-OPS-SSH-HYGIENE-01** | **DONE** | `authorized_keys` dedup (2 строки) | dedup OK | **`SSH-KEY-INVENTORY`** |
| 083 | **P2-OPS-PROD-SMOKE-01** | **DONE** | Батарея prod smokes + LUKS/DNS probes | **`PROD_SMOKE_BATTERY_OK`** §12 | §Q083 в prod-deploy doc |
| 084 | **P2-OPS-DRIFT-SYNC-01** | **DONE** | waive **`DRIFT-POST-P0.md`** (panel bind, SSH timeout) | §12 | **`DRIFT-POST-P0.md`** |

### Фаза 5 — ТСПУ red-team (после Q084)

| Q | ID | Статус | Done when (кратко) | Verify | Runbook / § |
|---|-----|--------|-------------------|--------|-------------|
| 085 | **P2-RED-TSPU-AUDIT-02** | **DONE** | Отчёт red-team «как ТСПУ»; таблица P0–P3; Q086+ | **`TSPU_REDTEAM_OK`** + **`docs/AUDIT-2026-05-TSPU-REDTEAM.md`** | ТСПУ-бриф; **`TSPU-OBSERVATIONS.md`** |

### Фаза 6 — GTM hardening (после Q085)

Детали: **`docs/AGENT-PHASE6-BACKLOG.md`**. Источники: **`POST-DEPLOY-REVIEW-2026-05.md`**, **`AUDIT-2026-05-TSPU-REDTEAM.md`**.

| Q | ID | Статус | Done when (кратко) | Verify | Commit (пример) |
|---|-----|--------|-------------------|--------|-----------------|
| 086 | **P3-RED-ADMIN-FSM-01** | **DONE** | Admin FSM только для `ADMIN_TELEGRAM_ID` | **`ADMIN_FSM_AUTHZ_OK`** | `security: P3-RED-ADMIN-FSM-01 — admin FSM authz` |
| 087 | **P6-RED-PAY-08** | **DONE** | Убрать DEBUG print с api_key в crypto hash | **CRYPTO_DEBUG_PRINT_OK** | `security: P6-RED-PAY-08 — remove crypto debug print` |
| 088 | **P1-RED-NET-2054-01** | **DONE** | Закрыть публичный `:2054` → panel (Caddy LV) | Caddy tmpl | `ops: P1-RED-NET-2054-01 — close panel :2054` |
| 089 | **P3-RED-CABINET-02** | **DONE** | Cabinet: не отдавать `bind_url` без auth | **CABINET_BIND_AUTH_OK** | `security: P3-RED-CABINET-02 — cabinet bind auth` |
| 090 | **P2-RED-DISCOVERY-PORT-01** | **DONE** | User-facing только **:8443** (`site_urls`) | **DISCOVERY_PORT_OK** | `fix: P2-RED-DISCOVERY-PORT-01 — canonical :8443` |
| 091 | **P2-RED-EDGE-SUNSET-2053-01** | **DONE** | LV **2053** → 301 **8443** | Caddy tmpl | `ops: P2-RED-EDGE-SUNSET-2053-01 — grace 2053` |
| 092 | **P3-FLOW-11-LIVE-01** | **DONE** | Live alt apex + FAQ/бот | Caddy p4n7q :8443 portal | `ops: P3-FLOW-11-LIVE-01 — backup domain live` |
| 093 | **P1-RED-TSPU-BLOCK-RU-01** | **DONE** | Скрипты + cron в репо; live RU → **Q099** | smoke static OK | `ops: P1-RED-TSPU-BLOCK-RU-01 — RU probe scripts` |
| 094 | **P5-COM-STATUS-TRIM-01** | **DONE** | `/status` без лишних ops-деталей | `to_public_status` | `product: P5-COM-STATUS-TRIM-01` |
| 095 | **P1-PRO-TIER-SWITCH-01** | **DONE** | Tier hint бот/portal | wizard + guide | `product: P1-PRO-TIER-SWITCH-01` |
| 096 | **P2-RED-EDGE-HEADERS-01** | **DONE** | HSTS + CSP Caddy | Caddy tmpl | `ops: P2-RED-EDGE-HEADERS-01 — HSTS CSP` |
| 097 | **P3-FLOW-LK-DEPLOY-01** | **DONE** | Commit ЛК/меню (cabinet.html, flow) | deploy LV/AMS | `product: P3-FLOW-LK-DEPLOY-01` |

### Фаза 7 — аудиты раунд 2 (после Q097)

| Q | ID | Статус | Done when (кратко) | Verify | Commit (пример) |
|---|-----|--------|-------------------|--------|-----------------|
| 098 | **P2-RED-TSPU-AUDIT-03** | **DONE** | Red-team ТСПУ после фазы 6 | **TSPU_REDTEAM_OK** live | `docs: P2-RED-TSPU-AUDIT-03 — TSPU round 2` |
| 099 | **P2-OPS-RU-RELAY-01** | **DONE** | SSH LV→`72.56.0.145:3344`; `tspu_block_probe_ru.py` через forced `check.py` | **TSPU_BLOCK_PROBE_RU_OK** live LV | `ops: P2-OPS-RU-RELAY-01 — RU relay SSH` |
| 100 | **P2-DOC-PORT-8443-01** | **DONE** | KB/ONBOARDING/JOURNEY/runbooks → **:8443** | grep journey/runbooks | `docs: P2-DOC-PORT-8443-01` |
| 101 | **P2-RED-CODERABBIT-02** | **DONE** | CodeRabbit + валидация; merged backlog | **`AUDIT-2026-05-SECURITY-02.md`** | `docs: P2-RED-CODERABBIT-02 — security audit 2` |
| 102 | **P1-RED-SUB-VERIFY-3010-01** | **DONE** | **P0-SEC-03** жив: DOCKER-USER **3010+3011** LV-only; smoke внешний fail | `p0-audit.sh` / curl AMS:3010 | `ops: verify sub ports firewall SUBHA` |
| 103 | **P3-RED-BIND-TOKEN-INVALIDATE-01** | **DONE** | `bind_token=NULL` после bind | replay bind fail | `security: bind token invalidate` |
| 104 | **P3-RED-BIND-TOKEN-LOG-01** | **DONE** | Не логировать сырой bind token | grep bot.db | `security: redact bind token logs` |
| 105 | **P2-RED-SNI-LIVE-01** | **DONE** | Panel SNI yandex; нет github в live sub | **`LIVE_SUB_SNI_OK`** | `ops: P2-RED-SNI-LIVE-01` |
| 106 | **P1-RED-CADDY-K9-BLOCKED-01** | **DONE** | `@blocked` на k9x2m1:8443 | panel paths 404 | `ops: P1-RED-CADDY-K9-BLOCKED-01` |
| 107 | **P6-RED-PAY-06b** | **DONE** | Webhook reject без amount metadata | smoke | `security: payment amount required` |
| 108 | **P6-RED-PAY-07b** | **DONE** | Prod gate `SKIP_API_VERIFY` | smoke flag | `security: yookassa skip verify gate` |
| 109 | **P3-RED-PORTAL-RESOLVE-01** | **DONE** | setup-resolve без `sub_url` + PromoCreate ADMIN guard | API JSON | `security: portal resolve leak` |
| 110 | **P3-RED-SUP-GROUP-01** | **DONE** | `SUPPORT_GROUP_ID` fail-fast prod | startup log | `ops: support group id check` |
| 111 | **P3-RED-TRIAL-ATOMIC-01** | **DONE** | Атомарный web trial claim | concurrent test | `security: trial claim atomic` |
| 112 | **P2-RED-EDGE-HEADERS-02** | **DONE** | HSTS **lv:9443** на **bvpn-lv**; AMS shop без Caddy (шаблон AMS для decoy) | `patch-caddy-hsts-9443-lv.sh` OK | `ops: edge headers 9443 lv` |
| 113 | **P2-OPS-SCHED-01b** | **DONE** | naive local_dt → UTC | scheduler smoke | `fix: scheduler key expiry TZ` |
| 114 | **P1-ENG-CONFIG-01** | **DONE** | `public_urls.py`; без k9 fallback при `BOT_PAYMENTS_LIVE=1` | py_compile | `chore: config explicit hosts` |
| 115 | **P2-CHORE-DB-SCHEMA-01** | **DONE** | bind columns + index в `initialize_db` | py_compile | `chore: unify web trial schema` |
| 116 | **P2-OPS-ENV-8443-01** | **DONE** | env tmpl без :2053 | grep compose | `ops: env templates 8443` |
| 117 | **P2-RED-MUX-XHTTP-01** | **DONE** | MUX + XHTTP-first incident/FAQ | transport audit | `product: P2-RED-MUX-XHTTP-01` |
| 118 | **P2-RED-SELFSTEAL-SNI-01** | **DONE** | Убрать github :9443 selfsteal | Caddy | `ops: selfsteal SNI` |
| 119 | **P2-RED-WHITELIST-L3-01** | **DONE** | Runbook whitelist (черновик есть) | doc | `docs: whitelist L3` |
| 120 | **P2-OPS-RU-RELAY-02-VPS-01** | **TODO** | 2-й RU relay VPS (владелец) | 2× `tspu_block_probe` | OWNER — **`RUNBOOK-RU-RELAY-EXPANSION`** (Q139) |
| 121 | **P2-RED-TLS-JA3-01** | **DONE** | TLS client stack audit | **TLS_CLIENT_STACK_AUDIT_OK** | `ops: JA3 audit` |

**Аудиты:** [`AUDIT-2026-05-SECURITY-02.md`](AUDIT-2026-05-SECURITY-02.md) (Q101), [`AUDIT-2026-05-TSPU-REDTEAM-04.md`](AUDIT-2026-05-TSPU-REDTEAM-04.md) (ТСПУ **5/10**).  
**Параллельно (владелец, не NEXT):** **Q120**, **Q032** (оферта).

### Фаза 8 — Reliability · скорость · TSPU (CodeRabbit + инцидент 2026-05-25)

**Контекст:** [`docs/AGENT-PHASE8-RELIABILITY-BACKLOG.md`](AGENT-PHASE8-RELIABILITY-BACKLOG.md), [`docs/VPN-INCIDENT-LESSONS-2026-05-25.md`](VPN-INCIDENT-LESSONS-2026-05-25.md).  
**Правило:** один Q → verify gate §1 phase8 doc → полный smoke продукта после деплоя → коммит → стоп. **Не ломать gen=20** (14 relay, no observatory panic).

| Q | ID | Статус | Done when (кратко) | Verify | Commit (пример) |
|---|-----|--------|-------------------|--------|-----------------|
| 122 | **P2-RED-BOT-TIMEOUT-01** | **DONE** | `ClientTimeout` на все Remna HTTP в боте | **`REMNA_API_TIMEOUT_OK`** §12 | `fix: P2-RED-BOT-TIMEOUT-01` |
| 123 | **P2-RED-BOT-RETRY-01** | **DONE** | tenacity: transient 502/503/504 + connect | **`REMNA_API_RETRY_OK`** §12 | `fix: P2-RED-BOT-RETRY-01` |
| 124 | **P2-RED-BOT-JITTER-01** | **DONE** | Jitter в `config.py`; grep undefined | config **300** | `chore: P2-RED-BOT-JITTER-01` |
| 125 | **P2-OPS-BACKUP-GLOB-01** | **DONE** | Prune `backup_*.tar.gz` not `shop_bot_*.db` | `py_compile` | `fix: P2-OPS-BACKUP-GLOB-01` |
| 126 | **P2-RED-BOT-POOL-01** | **DONE** | Shared aiohttp session + shutdown | `py_compile` + deploy | `fix: P2-RED-BOT-POOL-01` |
| 127 | **P2-OPS-SCHED-CONCURRENT-01** | **DONE** | `gather` + semaphore poll users | batch duration log | `fix: P2-OPS-SCHED-CONCURRENT-01` |
| 128 | **P2-OPS-SQLITE-WAL-01** | **DONE** | WAL + busy_timeout | `py_compile` | `fix: P2-OPS-SQLITE-WAL-01` |
| 129 | **P2-RED-BOT-AUTORENEW-01** | **DONE** | `days_left <= 0` | `py_compile` | `fix: P2-RED-BOT-AUTORENEW-01` |
| 130 | **P2-RED-MUX-XHTTP-AUDIT-01** | **DONE** | xHTTP в transport_mux_audit | **TRANSPORT_MUX_OK** (has_xhttp in JSON) | `ops: P2-RED-MUX-XHTTP-AUDIT-01` |
| 131 | **P2-OPS-TRANSPORT-HEALTH-01** | **DONE** | `transport_profile_health.py` | script in repo | `ops: P2-OPS-TRANSPORT-HEALTH-01` |
| 132 | **P1-PRO-VPN-SPEED-01** | **DONE** | `patch_balancer_direct_first_intl.py` (apply отдельно) | dry-run + apply gate §0 | `product: P1-PRO-VPN-SPEED-01` |
| 133 | **P2-RED-BOT-EXPIRY-HOUR-01** | **DONE** | Notify `hours_left <= 6` | `py_compile` + deploy | `fix: P2-RED-BOT-EXPIRY-HOUR-01` |
| 134 | **P2-OPS-BOT-HEALTH-01** | **DONE** | `/health` panel+DB | `curl :1488/health` AMS | `ops: P2-OPS-BOT-HEALTH-01` |
| 135 | **P2-OPS-SCHED-METRICS-01** | **DONE** | Cycle metrics в scheduler | **SCHEDULER_CYCLE** log | `ops: P2-OPS-SCHED-METRICS-01` |
| 136 | **P2-RED-TSPU-ALERT-01** | **DONE** | TG alert tspu_block_probe | `tspu_block_probe_alert.py` | `ops: P2-RED-TSPU-ALERT-01` |
| 137 | **P2-OPS-SUB-LATENCY-01** | **DONE** | p95 provision_key | slow >5s log | `ops: P2-OPS-SUB-LATENCY-01` |
| 138 | **P2-DOC-SNI-MIGRATION-01** | **DONE** | Runbook SNI migration | **`RUNBOOK-SNI-MIGRATION.md`** | `docs: P2-DOC-SNI-MIGRATION-01` |
| 139 | **P2-DOC-RU-RELAY-02-01** | **DONE** | Runbook 2-го relay | **`RUNBOOK-RU-RELAY-EXPANSION.md`** | `docs: P2-DOC-RU-RELAY-02-01` |
| 140 | **P2-DOC-BOOTSTRAP-FALLBACK-01** | **DONE** | Backup bootstrap runbook | **`RUNBOOK-BACKUP-BOOTSTRAP-FALLBACK.md`** | `docs: P2-DOC-BOOTSTRAP-FALLBACK-01` |
| 141 | **P2-DOC-MONITORING-01** | **DONE** | `MONITORING.md` | doc review | `docs: P2-DOC-MONITORING-01` |

**NEXT=—** (фаза 8 Q122–141 закрыта агентом). **Q120** / **Q032** — владелец.

### Фаза 9 — Bot CodeRabbit (2026-05-25)

**Контекст:** [`docs/AUDIT-2026-05-BOT-CODERABBIT.md`](AUDIT-2026-05-BOT-CODERABBIT.md), [`docs/AGENT-PHASE9-BOT-CODERABBIT-BACKLOG.md`](AGENT-PHASE9-BOT-CODERABBIT-BACKLOG.md).  
**Правило:** один Q → verify gate phase9 doc → deploy бота при изменении `bot_src` → коммит → стоп.

| Q | ID | Статус | Done when (кратко) | Verify | Commit (пример) |
|---|-----|--------|-------------------|--------|-----------------|
| 142 | **P2-RED-BOT-RENEW-IDEM-01** | **NEXT** | `renewal_attempts` + recovery stale pending | `py_compile` + renew audit | `fix: P2-RED-BOT-RENEW-IDEM-01` |
| 143 | **P2-RED-BOT-MULTIKEY-01** | **TODO** | автопродление всех `vpn_keys` | `py_compile` | `fix: P2-RED-BOT-MULTIKEY-01` |
| 144 | **P2-RED-BOT-BACKOFF-01** | **TODO** | global Remna circuit breaker 30s | `py_compile` | `fix: P2-RED-BOT-BACKOFF-01` |
| 145 | **P2-RED-BOT-INBOUND-LOCK-01** | **TODO** | lock на inbound cache refresh | `py_compile` | `fix: P2-RED-BOT-INBOUND-LOCK-01` |
| 146 | **P2-RED-WEBHOOK-ASYNC-01** | **TODO** | Flask → background asyncio loop | `py_compile` + webhook smoke | `fix: P2-RED-WEBHOOK-ASYNC-01` |
| 147 | **P2-OPS-DB-INDEX-01** | **TODO** | indexes vpn_keys/referrals/actions + web_trial seq | EXPLAIN hot queries | `chore: P2-OPS-DB-INDEX-01` |
| 148 | **P2-OPS-DB-MIGRATE-01** | **TODO** | `schema_migrations` vN chain | fresh DB upgrade | `chore: P2-OPS-DB-MIGRATE-01` |
| 149 | **P2-OPS-WEBTRIAL-POOL-01** | **TODO** | sqlite pool web_trial | `py_compile` | `ops: P2-OPS-WEBTRIAL-POOL-01` |
| 150 | **P2-RED-BOT-ADMIN-FIX-01** | **TODO** | get_setting import, HTML, mac URL, @support | admin flow step 1 | `fix: P2-RED-BOT-ADMIN-FIX-01` |
| 151 | **P2-CHORE-KEYBOARD-STUBS-01** | **TODO** | cleanup keyboard stubs | menu grep | `chore: P2-CHORE-KEYBOARD-STUBS-01` |
| 152 | **P2-RED-SETUP-URL-DEDUP-01** | **TODO** | `setup_url_service.py` | wizard=portal URL | `refactor: P2-RED-SETUP-URL-DEDUP-01` |
| 153 | **P3-UX-MESSAGES-01** | **TODO** | user_messages consistency | grep | `product: P3-UX-MESSAGES-01` |
| 154 | **P2-RED-SUB-URL-CACHE-01** | **TODO** | sub URL cache 60s TTL | cache hit log | `perf: P2-RED-SUB-URL-CACHE-01` |
| 155 | **P2-OPS-SUB-REFRESH-BATCH-01** | **TODO** | batch 50 + TG 429 backoff | batch log | `ops: P2-OPS-SUB-REFRESH-BATCH-01` |
| 156 | **P2-OPS-SCHED-JITTER-02** | **TODO** | scheduler jitter + backup task | SCHEDULER_CYCLE | `ops: P2-OPS-SCHED-JITTER-02` |
| 157 | **P3-UX-LEGAL-FALLBACK-01** | **TODO** | terms/privacy fallback onboarding | `py_compile` | `product: P3-UX-LEGAL-FALLBACK-01` |
| 158 | **P3-UX-WIZARD-FALLBACK-01** | **TODO** | wizard Mini App unavailable text | wizard smoke | `product: P3-UX-WIZARD-FALLBACK-01` |
| 159 | **P3-RED-SUPPORT-RATELIMIT-PERSIST-01** | **TODO** | DB-backed support rate limit | `py_compile` | `security: P3-RED-SUPPORT-RATELIMIT-PERSIST-01` |
| 160 | **P3-RED-SUPPORT-SILENT-01** | **TODO** | support unavailable user msg | startup warn | `ops: P3-RED-SUPPORT-SILENT-01` |

**NEXT=Q142** (фаза 9). **Параллельно (владелец):** **Q120**, **Q032**.

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
| 079 | `ops: P2-OPS-DEPLOY-BOT-SEC-01 — deploy AMS bot security + smokes` |
| 080 | `ops: P2-OPS-DEPLOY-EDGE-01 — Caddy LV :8443 + portal live smoke` |
| 081 | `ops: P2-OPS-DEPLOY-PANEL-01 — panel loopback AMS safe-deploy` |
| 082 | `ops: P2-OPS-SSH-HYGIENE-01 — AMS authorized_keys dedup` |
| 083 | `ops: P2-OPS-PROD-SMOKE-01 — prod smoke battery` |
| 084 | `ops: P2-OPS-DRIFT-SYNC-01 — drift-check green post-deploy` |

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
| 2026-05-19 | **Q085** P2-RED-TSPU-AUDIT-02 | — (отчёт **`AUDIT-2026-05-TSPU-REDTEAM.md`**, NEXT пусто) |
| 2026-05-19 | — | Фаза 6 **Q086–097** в очереди; **NEXT=Q086** |
| 2026-05-19 | **Q086** P3-RED-ADMIN-FSM-01 | **NEXT=Q087** |
| 2026-05-19 | **Q087–097** (непрерывный режим) | **NEXT** пусто, фаза 6 закрыта |
| 2026-05-20 | **Q102–121** (агент) | **NEXT=Q120** (владелец: 2-й RU VPS) |
| 2026-05-25 | **Q120** owner | **Фаза 8** Q122–141; **NEXT=Q122** (`AGENT-PHASE8-RELIABILITY-BACKLOG`) |
| 2026-05-25 | **Q122** P2-RED-BOT-TIMEOUT-01 | **Q123** P2-RED-BOT-RETRY-01 |
| 2026-05-25 | **Q123–129, Q133** phase8 bot reliability | **Q134** P2-OPS-BOT-HEALTH-01 |
| 2026-05-25 | **Q134–141** phase8 health/ops/docs + Q132 patch | — (фаза 8 агент закрыт) |
| 2026-05-18 | **Q080–Q084** фаза 4 prod deploy | — (фаза 4 закрыта) |
| 2026-05-18 | **Q079** P2-OPS-DEPLOY-BOT-SEC-01 | **Q080** P2-OPS-DEPLOY-EDGE-01 |
| 2026-05-18 | — | Репо Q063–050 **DONE**; фаза 4 **Q079–084** prod deploy |
| 2026-05-17 | — | Синхронизация бэклога: **`BACKLOG-MAP.md`**, §5.1 ✅, FAQ, Q032 помечен «до GTM» |
