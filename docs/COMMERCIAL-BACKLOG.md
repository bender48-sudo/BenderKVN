# BenderVPN — коммерческий бэклог

**Версия документа:** 2026-05-17 — фаза 3: portal + Mini App (**Q033–039** ✅), **NEXT=Q040**; карта **`docs/BACKLOG-MAP.md`**. Фазы 1–2 и **P4-DNS** (параллель) — без изменений статуса.
**Цель:** стабильный **8–9/10** (нишевый коммерческий VPN в РФ); измеримый рост к максимально достижимому качеству.  
**Определение «готово»:** по каждой задаче выполнен критерий в колонке **Done when** + при необходимости запись в трекере (статусы `TODO` / `DOING` / `DONE`).

---

## 1. Срез продакшена (зафиксировано по SSH, AMS + LV)

Используйте как **baseline** для порогов ниже; обновляйте строку даты после каждого замера.

| Объект | Факт (снимок **2026-05-15**; **переснять** `users`/RAM при SSH — `python ops/capacity_snapshot.py`) |
|--------|----------------|
| **Роль AMS** | Панель + подписка (`remnawave`, postgres, redis, subscription-page, бот, AdGuard, Caddy-selfsteal). **`remnanode` AMS** — **stopped (drain, P1-ARCH-AMS-DECOM 4a)**; не running в `docker ps`. |
| **Роль LV** | Production-нода (`remnanode` + AdGuard); `/opt/scripts/*`. |
| **Роль NL** | Production-нода (`remnanode`). |
| **Пользователи в БД** (`users`) | **≈58** (ориентир; см. журнал §12) |
| **Ноды в панели** | **3 записи**; prod **online: LV + NL**; Amsterdam-01 — **decom**, `connected=false`; шаг **4c** (удалить запись в UI) — **waive до scale** (не блокер, см. §12). |
| **Inject / AMS hosts** | Не входят в `injectHosts`; целевые `hosts`: `isHidden` + `isDisabled` (зафиксировано **2026-05-14**). |
| **Размер БД Postgres** | **~11 MB** (ориентир) |
| **RAM хоста AMS** | **~2 GiB** — панель + edge без prod VPN после drain |
| **Цели роста (продукт)** | **~10k** учёток к **концу лета 2026**; **~30k** в **2027**; GTM wiki — [**`docs/templates/GTM-WIKI-PAGE.md`**](https://github.com/VaDi-ai/BenderKVN/blob/main/docs/templates/GTM-WIKI-PAGE.md) (реестр **`docs/GTM-WIKI.md`**) |
| **Инфра-триггеры при росте** | **2k** users → апгрейд AMS; **8k** → load test sub + отдельный edge; soft-cap нод → 3-я prod (**§10.1**) |
| **Публичный portal** | **`/start`**, **`/portal/`** (Mini App), **`/setup/?t=`** на **k9x2m1** — репо **`web/portal/`**; см. **`BACKLOG-MAP.md`** |
| **Вывод** | Модель роста: **2 prod-ноды (LV+NL) + панель AMS**. Узкие места: RAM/API панели, подписка (**P6**). Монетизация go-live **2026-05-16**. Онбординг: portal + бот (**фаза 3**). |

---

## 2. Легенда приоритетов

| Метка | Что закрывает |
|-------|----------------|
| **P0** | Безопасность, целостность, компрометация = конец доверия |
| **P1** | Продукт, РФ‑выживаемость, конфигурация матрицы |
| **P2** | Надёжность, мониторинг, бэкапы, SSH‑дисциплина |
| **P3** | Юзерфлоу, поддержка, коммуникация инцидентов (**P3-FLOW-*** — см. **`docs/USER-FLOW-BACKLOG.md`**) |
| **P4** | DNS‑bootstrap / белые списки (**не** основной VPN) |
| **P5** | Полировка после «восьмёрки» |
| **P6** | Ёмкость: метрики, пороги, ноды, подписка, рост до **10k–30k+** |

### 2.1 Сначала продукт, потом UX

Закреплённый порядок: **качество продукта и эксплуатация** (стабильность, бэкапы, drift, метрики) — **раньше**, чем **удобство пользования** (**P3-UX-***). Детали и обоснование — **`docs/POLICY-BACKLOG-ORDER.md`**. В таблице §3 строка **10** не стартует, пока не закрыт разумный минимум эксплуатации (в т.ч. строка **9b**).

---

## 3. Очередь по спринтам (историческая карта)

Спринты **1–12** — архив закрытого и группировка по темам. **Исполнять новую работу** только по линейной очереди **`docs/BACKLOG-QUEUE.md`** (одна задача → коммит → новая сессия). Параллельно: только **P4-DNS** при отдельном человеке.

| # | Спринт‑кусок | ID |
|---|----------------|-----|
| 1 | TLS + секреты + argv | **P0-SEC-01** ✅, **P0-SEC-02** ✅, **P0-OPS-01** ✅ |
| 2 | Подписка `:3010` + UFW + compose | **P0-SEC-03** ✅ |
| 3 | Digest образов | **P0-OPS-02** ✅ |
| 4 | **Архитектура**: AMS = только панель | ~~**P1-ARCH-AMS-DECOM**~~ ✅ *(drain выполнен 2026-05-14; шаг **4c** опционально — удалить запись ноды в UI)* |
| 5 | **Прод ↔ репо**: синхронизация `/opt/scripts/` + compose/env templates | **P1-OPS-DRIFT-01** ✅, **P1-OPS-DRIFT-02** ✅ |
| 5b | **После P0‑SEC‑05 / миграции панели**: снять DRIFT и починить мониторинг вместимости (`balancer` → публичный `PANEL_URL`) | ~~**P2-OPS-DRIFT-POST-P0**~~ ✅, **P2-MON-BALANCER-PANEL-URL** ✅ (см. §12), ~~**P2-ENG-DRIFT-CHECK-01**~~ ✅ |
| 6 | Конфиг в одном месте + ru-monitor хосты + чистка артефактов | **P1-ENG-01** ✅ (`ops/site_urls.py` + `deploy-node.sh`), **P1-ENG-02** ✅, ~~**P1-ENG-03**~~ ✅ (`archive/tmp-remna-shop-bot-patches/` + `redact_bvpn_artifacts`) |
| 7 | Мониторинг «Xray реально жив» + state dirs | ~~**P2-MON-01**~~ ✅, ~~**P2-MON-02**~~ ✅ |
| 8 | Бэкапы (off-host + restore test) + patches | ~~**P2-BAK-01**~~ ✅, ~~**P2-BAK-02**~~ ✅ |
| 9 | Метрики ёмкости (**старт P6 до роста базы**) | ~~**P6-SCALE-01**~~ ✅, ~~**P6-SCALE-04**~~ ✅ (a)(b)(c) §12 **2026-05-16** — **`RUNBOOK-P6-SUBSCRIPTION-EDGE`**) |
| **9a** | **Коммерция (до массового привлечения)** | **P2-COM-MONETIZE-01…04** → **`RUNBOOK-COMMERCE-GO-LIVE`**; затем **P6-RED-PAY-01** при включении оплаты |
| 9b | **Эксплуатация (хвост P2):** drift post-P0, TG/SSH/утечки, gates | ~~**P2-OPS-DRIFT-POST-P0**~~ ✅, ~~**P2-MON-03**~~ ✅, ~~**P2-SSH-01**~~ ✅, ~~**P2-SEC-LOG-01**~~ ✅, ~~**P2-OPS-AMS-SAFE-DEPLOY-01**~~ ✅, ~~**P2-OPS-RESTORE-TEST-01**~~ ✅ |
| 10 | **(после §2.1 — UX не раньше продукта)** Онбординг и тексты | ~~**P1-PRO-01…04**~~ ✅ (см. **`docs/FAQ.md`**, **`docs/RUNBOOK-INCIDENT.md`**, **`docs/HAPP-MATRIX.md`**, **`docs/POLICY-SNI-MONITORING.md`**), ~~**P3-UX-01**~~ ✅ (**`docs/ONBOARDING.md`**), ~~**P3-UX-02**~~ ✅ (**`bot_src/user_messages.py`**, **`docs/support/USER-FACING-ERRORS.md`**), ~~**P3-UX-03**~~ ✅ (**`docs/templates/USER-INCIDENT-BROADCAST.md`**) |
| 11 | DNS PoC → FAQ (по ресурсу) | **P4-DNS-01** → ~~**P4-DNS-02**~~ ✅ (блок DNS bootstrap **`docs/FAQ.md`**) → **P4-DNS-03** |
| 12 | **Red team / ТПСУ** — порядок **§5.1** (фаза роста 10k): **P2-RED-SUB/MUX** → **P6-RED-PAY/SUBHA** → **P1-RED-DATA/Vault** после monetize или **2k** users | см. **§5.1** |
| **13** | **Пользовательский флоу (бабушка-тест, bootstrap без VPN)** | **P3-FLOW-00…13** → **`docs/USER-FLOW-BACKLOG.md`**, очередь **фаза 3** в **`BACKLOG-QUEUE.md`** |

---

## 4. P0 — Критично

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P0-SEC-01**~~ ✅ | Убрать **`curl -sk`** / **`CERT_NONE`** там, где **Bearer** или **изменение состояния** панели. | **DONE:** журнал §12 **2026-05-14**. |
| ~~**P0-SEC-02**~~ ✅ | Переписать **`ops/sync-sub-token-ams.sh`**: секрет **не** в `ssh "…${VAL}…"`. | **DONE:** защита heredoc/whitelist (**`selfsteal-monitor`** и др.), журнал §12. |
| ~~**P0-SEC-03**~~ ✅ | Решение по **`0.0.0.0:3010`**: зачем, кто достучится, UFW / reverse proxy. | **DONE:** **DOCKER-USER** / iptables, журнал §12. |
| ~~**P0-SEC-04**~~ ✅ | **`/opt/remnawave/` на LV**: legacy дерево с **копиями** JWT/Postgres/API-секретов активного AMS. | **DONE 2026‑05‑15** (журнал §12): архив **`/opt/_archive/remnawave-legacy-*`**, **`chattr +i`** по runbook; живого **`/opt/remnawave/`** на LV нет. |
| ~~**P0-SEC-05**~~ ✅ | После **P0-SEC-04**: ротация `JWT_AUTH_SECRET`, `JWT_API_TOKENS_SECRET`, `POSTGRES_PASSWORD` на AMS + перевыпуск и раскладка **`REMNA_API_TOKEN`** в 4 местах. | **DONE 2026‑05‑15** (журнал §12): фаза A **`rotate_ams_panel_core_secrets.py --apply`** + **`--force-recreate remnawave`**; фаза B новый API‑токен → AMS shop/sub + LV **`balancer.env`** / **`ru-monitor.env`**; smoke входа в панель / sub / мониторов. |
| ~~**P0-OPS-01**~~ ✅ | **`deploy-node.sh`**: токен панели **не** в argv. | **DONE:** **2026-05-14**, журнал §12. |
| ~~**P0-OPS-02**~~ ✅ | Образы Docker: **`:latest` → digest** для критичных сервисов. | **DONE:** пины критичных образов **2026-05-14**; см. журнал (**adguard**/postgres позже pinning). |

---

## 5. P1 — Продукт и инженерия

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P1-PRO-01**~~ ✅ | Линия продукта: основной VPN vs аварийный режим (в т.ч. DNS). | **2026-05-15**: пользовательский **`docs/FAQ.md`** (основной VPN vs DNS/bootstrap; ссылка на **`P4-DNS-02`** в бэклоге). Юридическая оферта — вне репо. |
| ~~**P1-PRO-02**~~ ✅ | Внутренний SLA + runbook инцидента (1 стр.). | **2026-05-15**: **`docs/RUNBOOK-INCIDENT.md`** (роли, рекомендация первого ответа ≤60 мин, проверки, эскалация; имена — в частной базе не в git). |
| ~~**P1-PRO-03**~~ ✅ | Матрица Happ: один источник `TEMPLATE_UUID`, URL панели, правила нод; **rollback** после PATCH. | **2026-05-15**: **`docs/HAPP-MATRIX.md`** + **`ops/site_urls.py`** / **`ops/site.env.example`**; процедуры **`ru_bypass_routing`** / **`freeze_ams_node`**, снапшоты **`.secrets/snapshots/`**. |
| ~~**P1-PRO-04**~~ ✅ | Политика probe‑SNI / снижение сигнатуры мониторинга. | **2026-05-15**: **`docs/POLICY-SNI-MONITORING.md`** (принципы + журнал согласований; код без обязательных правок). |
| ~~**P1-PRO-RU-BYPASS-01**~~ ✅ | **Split-tunneling** RU-приложений/сайтов: direct в Happ-template; список и процесс в **`docs/RU-BYPASS.md`**. | **2026-05-15 DONE**: журнал §12; **`ops/ru_bypass_routing.py`**, **`ops/probe_routing.py`**. |
| ~~**P1-OPS-SELFSTEAL-01**~~ ✅ | **Selfsteal fingerprint `EXPECTATIONS`** vs актуальные upstream'ы. | **2026-05-15 DONE**: шапка у `EXPECTATIONS` в **`selfsteal-monitor.py`**; **`ads.x5.ru` → HTTP 302** + tolerate (журнал §12). |
| ~~**P1-ENG-01**~~ ✅ | Один конфиг **без секретов** для публичных URL/UUID (панель, подписка, ru‑relay для ops). | **`ops/site_urls.py`**, **`ops/site.env.example`**, **`deploy-node.sh`** (опц. source), wiring в ключевые `ops/*.py`. |
| ~~**P1-ENG-02**~~ ✅ | **`ru-monitor.py`**: не «ровно N» таргетов; устойчивость к смене числа хостов. | Закрыто **Monitor-block D (2026-05-14)**: предупреждение если **<4** целей; нет жёсткого «expected 16». |
| ~~**P1-ENG-03**~~ ✅ | `tmp_*.py` → архив; **`bvpn-artifacts`** без сохранённых живых JWT. | **`archive/tmp-remna-shop-bot-patches/`** + README; **`ops/redact_bvpn_artifacts.py`**. |
| ~~**P1-OPS-DRIFT-01**~~ ✅ | Синхронизация прод ↔ репо для `/opt/scripts/{monitor.sh,daily-report.sh,ru-monitor.py,…}`. Закрыта 2026-05-14: репо ← прод для всех 10 управляющих файлов (LV/AMS/NL), `ops/drift-check.py` сравнивает md5 в один SSH-вызов на хост, `docs/DEPLOY.md` — процедура и карта SoT. |
| ~~**P1-OPS-DRIFT-02**~~ ✅ | Sanitized **`compose/**/*.tmpl`**, **`docs/SECRETS.md`**, **`ops/sanitize_compose_templates.py`** + **`ops/extract_vault.py`**, рендер **`ops/render_compose.py`** (`--only` / `--none` для compose), **`ops/drift-check.py`** с `tmpl_only_keys` и нормализацией CRLF. Закрыто 2026-05-15. |
| ~~**P1-ARCH-NODE-UNIFY**~~ ✅ | Единый стиль **`remnanode`**: **`env_file` + `node.env.tmpl`**, digest pin (**`sha256:9d57375a8168d…`**), образ **`ghcr.io/remnawave/node`**. | **`compose/lv|nl|ams/remnanode/`** нормализовано в репо; **`drift-check`** зелёный после деплоя **`.env`** на NL/(AMS legacy). |
| ~~**P1-ARCH-AMS-DECOM**~~ ✅ | **AMS VPN drained** (`remnanode` stopped): freeze inject + hosts hidden/disabled → drain → daily metric «sub still resolves AMS IPs». | **2026-05-14**: шаги **1**, **2**, **4a** (журнал). **2026-05-15**: метрика в **`daily-report.sh`** через **`ops/count_users_with_ams_sub.py`**. Опционально **4c** — удалить Amsterdam-01 в панели. Детальный план шагов 1–5 — записи журнала **2026-05-14**. |

### 5.1 Red team / ТПСУ — конкретные доработки (приоритет: критичные → мелкие)

Источник: аудит «чёрного оппонента» + дорожная карта смягчения (sing-box/USENIX DPI‑литература, Vault/SPIFFE, Snowflake‑подобный bootstrap).

**Порядок по умолчанию (таблица ниже):** P1‑RED → P2‑RED → P6‑RED → P3‑RED → P5‑RED.

**Фаза 1 (Q001–Q022, закрыта 2026-05-17):** **P2-RED-SUB/MUX**, **P6-RED-PAY-01** (idempotency), **P6-RED-SUBHA/PG**, коммерция **§5.3**, **P6-SCALE-***.

**Фаза 2 (Q023+, линейная очередь):** **P2-OPS-AMS-SAFE-DEPLOY-01** → **P6-RED-PAY-02** (auth webhook) → **P1-RED-SSH-01** → **P1-RED-DNS-01** → **P1-RED-DATA-01** → **P1-RED-SEC-01** → **P3-RED-MIN/JURIS** → **P5-COM-01**. Старт после go-live монетизации (**P2-COM-MONETIZE-02** ✅); при **users > 2k** — ускорить **P1-RED-DATA/SEC**. **P5-RED-RD-01** — вне критического пути.

**Параллельно (не NEXT):** **P4-DNS-01…06** — mobile bootstrap / whitelist SKU.

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P1-RED-DATA-01**~~ ✅ | **AMS Postgres**: шифрование тома LUKS; ключ вне VPS. | **2026-05-17** Q027 — **`POSTGRES-ENCRYPTION-AMS`**, **`POSTGRES_CRYPT_OK`**. |
| ~~**P1-RED-SEC-01**~~ ✅ | **Machine credentials**: короткоживущие секреты (пилот broker → панель). | **2026-05-17** Q028 — **`RUNBOOK-SHORT-LIVED-CREDS`**, **`SHORT_LIVED_TOKEN_OK`**. |
| ~~**P1-RED-SSH-01**~~ ✅ | **Blast radius SSH**: per-host ключи; без одного root-ключа на все VPS. | **2026-05-17** Q025 — **`SSH-KEY-INVENTORY`**, **`SSH_AUDIT_OK`**. |
| ~~**P1-RED-DNS-01**~~ ✅ | **DNS**: ≥2 регистратора; probe делегирования; DNSSEC — runbook (включить у владельца). | **2026-05-17** Q026 — **`DNS_DELEGATION_OK`**, **`RUNBOOK-DNS-RED-TEAM`**. |
| **P1-RED-LOG-01** | **Логи edge подписки / Caddy**: **`log_skip`** для **`/api/sub/*`** на сайтах публичной подписки; **retention** + доступ к access-log. Репозиторий: **`Caddyfile-latvia-full.txt`**, **`docs/RUNBOOK-CADDY-SUBSCRIPTION-LOGS.md`**, **`ops/patch-caddy-logskip-inplace.sh`** / **`ops/fix-caddy-security.sh`**. | **DONE (репо):** эталон **p4n7q** + runbook. Хвост **k9x2m1** → **P1-RED-LOG-02** (**Q066**). |
| **P1-RED-LOG-02** | **`log_skip`** на **k9x2m1** для **`/api/sub/*`** (второй origin **P2-RED-SUB-01**). | **`SUB_LOG_SKIP_K9_OK`**; grep access-log после refresh. **Q066**. |
| ~~**P6-RED-PAY-03**~~ ✅ | **Auto-renew:** списание баланса перед `provision_key`; при недостатке — skip + уведомление. | **2026-05-18:** **`AUTO_RENEW_BILLING_OK`**; `try_deduct_balance`. **Q063**. |
| **P3-RED-SUP-01** | **Support:** ответы из группы только **SUPPORT_STAFF_IDS** / admin. | **`SUPPORT_REPLY_AUTHZ_OK`**. **Q064**. |
| **P2-OPS-SCHED-01** | **Expiry notify:** UTC-aware сравнение `expireAt`. | **`EXPIRY_TZ_OK`**. **Q065**. |
| **P6-RED-PAY-04** | **CryptoBot:** webhook **POST**; `compare_digest` для secret. | **`CRYPTOBOT_WEBHOOK_POST_OK`**. **Q067**. |
| **P6-RED-PAY-05** | **Webhook XFF:** `WEBHOOK_TRUST_PROXY_HEADERS` default **false**; smoke spoof. | **`WEBHOOK_XFF_HARDEN_OK`**. **Q068**. |
| **P1-RED-NET-01** | **Panel bind:** `127.0.0.1:3000` в compose (не `0.0.0.0`). | external :3000 fail. **Q069**. |
| **P6-RED-PAY-06** | **Сумма платежа:** cross-check metadata vs invoice. | **`PAYMENT_AMOUNT_VERIFY_OK`**. **Q070**. |
| **P6-RED-PAY-07** | **YooKassa:** CRITICAL log / smoke если `SKIP_API_VERIFY` на проде. | smoke unset. **Q071**. |
| **P3-RED-SETUP-01** | **Setup API:** Caddy rate_limit на `/setup/api/*`. | burst → 429. **Q072**. |
| **P3-RED-SUP-02** | **Support flood:** rate limit user→support. | ручной test. **Q073**. |
| ~~**P2-RED-BOOT-01**~~ ✅ | **Не только Telegram**: резервный канал (**HTTPS JSON mirror** на **k9x2m1**). | **`RUNBOOK-P2-STATUS-BOOT-CHANNEL`**, **`build_status_mirror.py`**, cron LV; smoke **`STATUS_CHANNELS_OK`** §12 |
| ~~**P2-RED-SUB-01**~~ ✅ | **Подписка — несколько origin**: ≥2 независимых имени/CDN‑края на синхронизированную версию конфига; сценарий «один домен в реестре блокировок» не режет всю базу. | **2026-05-16:** **p4n7q** + **k9x2m1** `/api/sub/*` → AMS **:3010**; **`RUNBOOK-P6-SUBSCRIPTION-MULTI-ORIGIN`**, **`subscription_origin_drift_probe.py`**, smoke **`SUB_MULTI_ORIGIN_OK`** на LV. |
| ~~**P2-RED-MUX-01**~~ ✅ | **Не один транспорт для всех**: продуктовая матрица **≥2 независимых транспортных профиля** (разные инбаунды/порты/узлы), чтобы DPI не кластеризовал всю аудиторию по одному JA3/Reality‑шаблону. | **2026-05-16:** **`TRANSPORT-MUX-MATRIX`**, **`transport_mux_audit.py`** — sample 25: **100%** users both primary+alt, **alt_ob_share≈56%**. |
| ~~**P2-RED-TLS-01**~~ ✅ | **Клиентский стек**: квартальный обзор **sing-box / uTLS / ECH**. | **`TLS-CLIENT-STACK-REVIEW`**, **`tls_client_stack_audit.py`**, **`reviews/TLS-QUARTERLY-2026-Q2`** §12 |
| ~~**P6-RED-SUBHA-01**~~ ✅ | **Горизонталь subscription-page**: несколько инстансов за LB + кэш на edge для «утреннего stampede» обновления подписок (дополняет **P6-SCALE-04**). | **2026-05-16:** split-host **p4n7q→:3010**, **k9x2m1→:3011**; **`RUNBOOK-P6-SUBSCRIPTION-HA`**; HA load **60×200** p95≈**1.48s** / **1.51s**. |
| ~~**P6-RED-PG-01**~~ ✅ | **Postgres**: read‑реплики (или managed Postgres при переносе), явный **pool limit** приложений, нагрузочный тест «массовое обновление клиентов за 1 ч». | **`RUNBOOK-P6-POSTGRES-RED`**, Prisma **`connection_limit=15`**, stampede probe §12 |
| ~~**P6-RED-PAY-01**~~ ✅ | **Очередь платежей бота**: webhook **idempotency**, DLQ, чтобы TG‑бот не был узким горлышком при всплеске продаж. | **2026-05-16:** **`PaymentWebhookQueue`**, таблица **`webhook_deliveries`**, деплой **`deploy-bot-payment-webhook-ams.ps1`**, smoke **`WEBHOOK_PAY_IDEMPOTENCY_OK`**. |
| ~~**P6-RED-PAY-02**~~ ✅ | **Auth webhook**: YooKassa verify, loopback Flask **:1488**, crypto secret. | **2026-05-17** Q024 — **`WEBHOOK_AUTH_OK`**, **`RUNBOOK-COMMERCE-GO-LIVE` §2**. |
| ~~**P3-RED-MIN-01**~~ ✅ | **Минимизация данных**: политика + инвентарь; redact webhook. | **2026-05-17** Q029 — **`DATA-MINIMIZATION-POLICY`**, **`DATA_MINIMIZATION_OK`**. |
| ~~**P3-RED-JURIS-01**~~ ✅ | **Гео‑ и провайнер‑диверсификация**: runbook «нас отключил один VPS/агентство платежей за день» — перенос DNS/IP без зависимости от одной юрисдикции. | **2026-05-17:** **`JURISDICTION-FAILOVER-WIKI`**, **`RUNBOOK-JURISDICTION-FAILOVER`**, **`TABLETOP-JURISDICTION-EXERCISE`**; smoke **`JURIS_FAILOVER_OK`**. Tabletop на проде — **1×/год** (календарь владельца). |
| **P5-RED-RD-01** | **R&D**: PoC канала bootstrap по модели **эфемерных посредников** (идеология [**Snowflake**](https://github.com/cohosh/snowflake)) — только для получения статуса/нового endpoint’а, не замена нодам. | Внутренний doc go/no-go + оценка стоимости поддержки. |
| **P2-RED-EDGE-PORT-01** | **Порт публичного edge ≠ 2053:** **`:2053`** = дефолт **3X-UI** (сканы, ТСПУ). Перенести HTTPS край на **`8443`** (основной), запас **`4433`** / **`10443`** — обоснование **`docs/EDGE-PORT-RECOMMENDATION.md`**. Grace **2053→8443** 7–14 дней. **Не путать** с VPN inbound (**Q056**). | **`RUNBOOK-P6-EDGE-PORT-MIGRATION`**; **`EDGE-PORT-RECOMMENDATION.md`**; smoke **`SUB_EDGE_PORT_OK`**. |
| **P1-PRO-CLIENT-V2RAYN-01** | **Windows v2rayN:** бета — **не коннектится** ни LTE, ни Wi‑Fi (Happ на iOS в том же тесте — отдельная история). Матрица совместимости, разбор выдачи подписки под **v2rayN** (UA/format/routing), правки шаблона при необходимости; ветка **Windows** в portal/боте — **второй** клиент рядом с Happ. | **`docs/CLIENT-V2RAYN.md`** (или § в **`HAPP-MATRIX`**); ручной или **`ops/smoke_v2rayn_sub.py`** smoke на Win; **`V2RAYN_CLIENT_OK`** §12; FAQ/onboarding — явный шаг для ПК без Happ. |
| **P2-RED-TSPU-VLESS-01** | **Палево VLESS / ~15 дней на ТСПУ:** полевое наблюдение — слабый fingerprint → бан на **конкретной** ТСПУ. Runbook: симптомы, смена транспорта/шаблона, связь с **MUX** и **TLS‑review**; **не** крутить всю базу на один outbound. | **`docs/RUNBOOK-TSPU-VLESS-INCIDENT.md`**; tabletop; **`TSPU_VLESS_PLAYBOOK_OK`** §12. Матрица: **`docs/TSPU-OBSERVATIONS.md`** п.1. |
| **P1-RED-TSPU-BLOCK-01** | **Блокировка «в ЧС»:** порты **>990** (telnet), обрыв **SSL handshake** с RU‑сети. Probe + алерт (отдельно от `ru-monitor` SNI). | **`ops/tspu_block_probe.py`** (или расширение monitor); cron LV; smoke **`TSPU_BLOCK_PROBE_OK`**. п.3. |
| **P2-RED-VPN-INBOUND-PORT-01** | **Inbound VPN ≠ дефолт 443** при бане у хостера: политика смены порта **remnanode** (LV/NL), обновление injectHosts/подписки, grace. Связь с **P2-RED-EDGE-PORT-01** (edge sub/panel). | Runbook **`RUNBOOK-VPN-INBOUND-PORT`**; smoke sub после смены; **`VPN_INBOUND_PORT_OK`**. п.4. |
| **P2-RED-SELFSTEAL-REVIEW-01** | **Selfsteal / decoy:** наблюдение — «заглушка при прямом заходе» **не даёт** выигрыша. Аудит **`selfsteal-monitor`**, Caddy **:9443**, 13 SNI — **выключить**, упростить или оставить только ops‑нужное. | Решение go/no-go в **`docs/TSPU-OBSERVATIONS.md`** п.5; **`SELFSTEAL_REVIEW_OK`** §12. |
| **P2-RED-SNI-ROTATE-01** | **Ротация Reality dest/SNI:** уйти с **`api.github.com`** / bing / microsoft; приоритет **`www.yandex.ru`** (референс WL + [Xray #2283](https://github.com/XTLS/Xray-core/issues/2283)). | Snapshot + patch; **`SNI_ROTATE_OK`**. **`PRODUCT-TIER-PROFILES.md`**. |
| **P1-PRO-SUB-TIER-01** | **Три уровня в подписке:** turbo (NL) / **wl-direct** (RF, :80, без routing) / **wl-routed** (RF, :443, vision) — см. референс-разбор. | **`PRODUCT-TIER-PROFILES.md`**; 3 named outbounds; FAQ «не на роутер» для tier-3; **`SUB_TIER_PROFILES_OK`**. |
| **P1-RED-TSPU-THREAT-MODEL-01** | **Модель угроз ТСПУ (wiki):** п.7–9 — ТСПУ независимы, IP‑бан временный, массовый ручной, малый сервер реже; связка с **NODE-POLICY**, GTM, **не** масштабировать один паттерн. | **`docs/TSPU-THREAT-MODEL.md`** (из **`TSPU-OBSERVATIONS`**); саппорт‑шпаргалка 1 стр. |
| **P1-RED-NODE-DNS-01** | **Резолвер на нодах:** свой DNS (AdGuard/unbound), upstream **не** провайдерский; ТСПУ/провайдер **удаляет** записи заблокированных. | Док: кто резолвит что; AdGuard upstream для Xray; probe «ломается ли A/AAAA»; **`NODE_DNS_RESOLVER_OK`**. п.11. |

**Контекст бета (2026‑05‑18):** полная матрица 12 пунктов — **`docs/TSPU-OBSERVATIONS.md`**. Высокий ping в Happ; «баннер 1984» → **GeoIP на устройстве** + **P5-PROD-NATIVE-APP-01**; **RU-BYPASS** ✅ на сервере. Happ (РФ‑клиент) — компромисс App Store.

### 5.2 Смена `REMNA_API_TOKEN` без регресса (после остального бэклога)

**Порядок:** выполнять **после** приоритетных P2 / P6 / §5.1 — на проде уже есть guardrails (**`ops/check-ams-subscription-token-layout.sh`**, **`ops/fix-ams-subscription-api-token.sh`**, **`docs/SECRETS.md`** §3). Накат AMS — **`docs/RUNBOOK-AMS-SAFE-DEPLOY.md`**. Задача ниже — **формализовать одноразовую процедуру** на случай **намеренной** смены токена, чтобы не повторять сбои **2026‑05‑16**.

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P1-OPS-REMNA-TOKEN-01**~~ ✅ | **Единый runbook + автоматизация смены `REMNA_API_TOKEN`** по всем потребителям (**`docs/SECRETS.md` §3**: shop; **`/opt/remnawave/sub/.env`**; в compose подписки только **`REMNAWAVE_API_TOKEN=${REMNA_API_TOKEN}`**, без `eyJ…` в YAML; LV **`balancer.env`/`ru-monitor.env`**; **`.secrets/vault.env`** + **`python ops/render_compose.py`** где применимо; перезапуск контейнеров/сервисов). Инцидент **2026‑05‑16**: инлайн JWT в **`sub/docker-compose.yml`** → **502** клиентам; синхрон LV **`/opt/remnawave`** давал рассинхрон. **Документ:** **`docs/RUNBOOK-REMNA-API-TOKEN.md`**; **скрипт:** **`bash ops/remna_api_token_rollout.sh`** (**`dry-run`** / **`verify-ams`** / **`sync-ams-sub`**). **Запрет:** коммит и публичные каналы. | **DONE 2026‑05‑15 (репо):** формализация процедуры. **При первой реальной ротации только скриптом** — добавить строку §12 со smoke (**подписка 200**, бот/`panel_api`, **`drift-check`** или waive). |

### 5.3 Коммерция и монетизация (до 10k users)

Выполнять **после** спринта **9** (метрики) и **параллельно** с закрытием **P6-SCALE-04**, **до** массового GTM (**`docs/GTM-GROWTH-OUTLINE.md`**). Процедура: **`docs/RUNBOOK-COMMERCE-GO-LIVE.md`**.

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P2-COM-MONETIZE-01**~~ ✅ | **Финальные цены** в боте: модель **баланса** (**6.67 ₽/день**), пополнение без привязки к периоду. | **2026-05-16:** **`DAILY_RATE=6.67`**, **`TOPUP_PRESETS`**, UI «Пополнить баланс», **`deploy-bot-balance-model-ams.ps1`**; smoke `balance_to_days(200)=29`. |
| ~~**P2-COM-MONETIZE-02**~~ ✅ | **`BOT_PAYMENTS_LIVE=1`**: креды платёжек в **`/opt/remna-shop/.env`**, smoke E2E (Stars / YooKassa / crypto — что включено). | **2026-05-16:** Stars live, **`ops/smoke_payments_live_ams.py`**, idempotency topup. |
| ~~**P2-COM-MONETIZE-03**~~ ✅ | **Legal URLs** в боте: **`TERMS_URL`**, **`PRIVACY_URL`**, **`SUPPORT_USER`** (админка/env), без заглушек в прод-сообщениях. | **2026-05-16:** telegra.ph + **@Bender_KVN_bot**, **`ops/check_legal_urls_ams.py`**. |
| ~~**P2-COM-MONETIZE-04**~~ ✅ | **Go-live чеклист** перед рекламой: **§5.3** + **`RUNBOOK-COMMERCE-GO-LIVE` §4** (safe deploy, sub edge, restore test, GTM outline). | **2026-05-16:** §12 **COM-MONETIZE go-live OK**; **`ops/smoke_commerce_golive_ams.py`**; **P6-RED-PAY-01** при пике продаж. |

---

## 6. P2 — Надёжность

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P2-MON-01**~~ ✅ | **`monitor.sh`** (LV): **`remnanode` + `docker exec … xray version` + порты**, не только `ss :443` (AMS xray после drain выключен). | **Репо 2026-05-15**: «контейнер up, Xray мёртв» → **`xray_lv_core`**; нет контейнера → **`xray_lv_remnanode`**. |
| ~~**P2-MON-02**~~ ✅ | Разные каталоги state: `ru-monitor` vs `monitor.sh`. | **2026-05-15**: комментарии в `monitor.sh` / `ru-monitor.py` + строка в примере crontab **`DEPLOY.md`** (§6 таблица уже была). |
| ~~**P2-MON-03**~~ ✅ | Политика: что уходит в Telegram (минимум метаданных). | **`docs/POLICY-TELEGRAM-ALERTS.md`** (2026-05-16). |
| ~~**P2-SSH-01**~~ ✅ | Таблица: где `accept-new`, где pin `known_hosts`; меньше `StrictHostKeyChecking=no` в проде. | **`docs/SSH-HOST-KEY-PRACTICE.md`** (2026-05-16). |
| ~~**P2-BAK-01**~~ ✅ | Расписание: `ops/pg_dump_remnawave.sh` (AMS) + `ops/pull-latest-dump-ams-to-lv.sh` (LV); квартальный **restore test**. | **Репо 2026-05-16**: runbook + cron example. Restore test **2026-05-16** — **`ops/remnawave_restore_test.sh`**, §4 runbook + §12 (**`P2-OPS-RESTORE-TEST-01`**). |
| ~~**P2-BAK-02**~~ ✅ | **Патчи** схемы БД / миграции — не смешивать с «просто дампом»; бэкап до ручных SQL. | Зафиксировано в **`RUNBOOK-BACKUP-REMNAWAVE.md`** §2 (P2-BAK-02). |
| ~~**P2-CHORE-SUB-ENV**~~ ✅ | **`monitor.sh`** — smoke подписки как **`daily-report.sh`**: **`SUB_PUBLIC_ORIGIN`**, **`SUB_MONITOR_PROBE_URL`**, **`PANEL_URL`** после **`source /etc/bvpn/balancer.env`** (fallback = дефолты как у daily-report/tmpl). | См. репозиторий **2026‑05‑15**; деплой на LV **`/opt/scripts/monitor.sh`**. |
| ~~**P2-OPS-DRIFT-POST-P0**~~ ✅ | После ротации секретов и смены URL панели: снять **DRIFT** прод ↔ репо (**`deploy-node.sh`**, **`selfsteal-monitor.py`**, AMS **`/opt/remnawave/docker-compose.yml`** и **`.env`**, **`/opt/remna-shop/.env`** и т.д.). | **2026-05-16**: деплой скриптов LV/AMS из репо; **`/etc/bvpn/balancer.env`**, **`ru-monitor.env`** — рендер из **`.secrets/vault.env`**; AMS **`remnawave` / `sub` / `remna-shop`** — файлы из рендера + **`docker compose up -d`**. **`python ops/drift-check.py`**: **28/28 OK**, exit **0** (журнал §12). |
| ~~**P2-SEC-LOG-01**~~ ✅ | Гигиена секретов: если **`BOT_TOKEN`** / JWT попали в **транскрипты Cursor**, скриншоты, общие логи — считать компрометацией до проверки. | **`docs/POLICY-SECRET-LEAK-RESPONSE.md`** (2026-05-16). |
| ~~**P2-ENG-DRIFT-CHECK-01**~~ ✅ | **`ops/drift-check.py`**: нестабильные **TIMEOUT** на LV. | Retry + растущий deadline на chunk (**4×** попытки для **`bvpn-lv`**, **2×** прочие) + backoff; см. **`docs/DEPLOY.md`** (§ drift-check примечание). Репо **2026‑05‑15**. |
| ~~**P2-MON-BALANCER-PANEL-URL**~~ ✅ | **`balancer.sh`** на LV после переноса панели на AMS всё ещё бил в **`http://localhost:3000`** → **`USERS=0 NODES=0`** в логе, алерты вместимости бессмысленны. | **DONE 2026‑05‑15**: **`PANEL_URL`** в **`/etc/bvpn/balancer.env`** + правка **`balancer.sh`** (репо **`compose/_shared/etc-bvpn-lv/balancer.env.tmpl`**); smoke **`HTTP 200`** на **`/api/users`** (журнал §12). |
| ~~**P2-OPS-AMS-SAFE-DEPLOY-01**~~ ✅ | **Gate наката AMS** compose/env: бэкап → **`extract_vault.py`** → dry-run токена → render в `/tmp` → smoke sub/panel → **`drift-check`**. | **`RUNBOOK-AMS-SAFE-DEPLOY`** §3–4, **`ops/smoke_ams_safe_deploy.py`** → **AMS_SAFE_DEPLOY_OK** §12 |
| ~~**P2-OPS-RESTORE-TEST-01**~~ ✅ | **Квартальный restore test** дампа Remnawave (изолированный Postgres). | **2026-05-16** на **bvpn-lv**: **`ops/remnawave_restore_test.sh`**, дамп с LV после pull AMS, **36** tables, **97** migrations — §4 runbook + §12. |
| ~~**P2-OPS-IMAGE-PIN-01**~~ ✅ | **Digest pin** хвоста образов: **adguard**, **postgres**, **caddy**, **valkey** (см. журнал **P0-OPS-02**). | **`docs/IMAGE-PINS.md`**, **`check_compose_image_pins.py`**; digests с прода AMS/LV **2026-05-16**. |

---

## 7. P3 — Юзерфлоу и доверие

**Порядок:** блок **P3-UX** не является приоритетом, пока не закрыт контур качества продукта — **`docs/POLICY-BACKLOG-ORDER.md`**, §2.1, §3 строка **10**.

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P3-UX-01**~~ ✅ | Онбординг: подписка → клиент → первый коннект + FAQ при ошибке. | **`docs/ONBOARDING.md`** (2026‑05‑15): одна точка входа + ссылки на **`docs/FAQ.md`**, технические доки только для команды. |
| ~~**P3-UX-02**~~ ✅ | Тексты ошибок для людей (не «TLS timeout»). | **`bot_src/user_messages.py`** + поддержка **`docs/support/USER-FACING-ERRORS.md`**. |
| ~~**P3-UX-03**~~ ✅ | Шаблон сообщения пользователям при инциденте. | **`docs/templates/USER-INCIDENT-BROADCAST.md`**. |
| ~~**P3-OPS-SUPPORT-REMNA-LOGIN**~~ ✅ | Саппорт / операторы: панель Remnawave показывает **Forbidden + E000** не только из‑за прокси, но и при **неверном пароле** и др. политиках (**403**, не **401**). | Абзац **`docs/RUNBOOK-INCIDENT.md`** § «Логин в панель Remnawave» + отсылка к Rescue CLI. **2026‑05‑15** |
| ~~**P3-TR-01**~~ ✅ (репо) | Политика логов (что, сколько, кто читает). | **`docs/POLICY-LOGS-DATA.md`** — внутренний черновик; публичная политика/оферта — вне репо при согласовании. |

### 7.1 Пользовательский флоу (P3-FLOW) — «бабушка-тест» и bootstrap без VPN

**Проблема:** без работающего VPN клиент часто **не доходит до Telegram-бота** → не получает подписку.  
**Детали, карта пути, приоритеты:** **`docs/USER-FLOW-BACKLOG.md`**.

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P3-FLOW-00**~~ ✅ | Карта флоу + критерии приёмки (3 персоны). | **2026-05-17:** **`USER-FLOW-JOURNEY.md`**; smoke **`USER_FLOW_JOURNEY_OK`**. Бумажное ревью 3× — владелец. |
| ~~**P3-FLOW-14**~~ ✅ | **Единый портал** `web/portal/` + **`content/ru.json`** — один UI для сайта и Mini App (iPhone/Android/**Windows**/**Mac**, Happ на телефон и ПК). | **2026-05-17:** **`portal_bundle_audit.py`** → **`PORTAL_BUNDLE_OK`**; **`site_urls.public_*_url()`**. |
| ~~**P3-FLOW-01**~~ ✅ | **Bootstrap-сайт** (clearnet): `/start`, `/portal` на LV; journey **as-is бот** (App Store/Google Play без шага устройства). | **2026-05-17:** **`PUBLIC_BOOTSTRAP_OK`**; **`RUNBOOK-USER-BOOTSTRAP-SITE`**. |
| ~~**P3-FLOW-02**~~ ✅ | **Веб-выдача конфига**: `/setup/?t=`, QR, copy; HMAC + verify API на LV. | **2026-05-17:** **`PORTAL_SETUP_PAGE_OK`**; бот → ссылка в **Q038**. |
| ~~**P3-FLOW-12**~~ ✅ | **Telegram Mini App** — тот же `web/portal/`; Menu Button + inline WebApp. | **2026-05-17:** **`TELEGRAM_MINIAPP_PORTAL_OK`**; **`RUNBOOK-TELEGRAM-MINIAPP`**. |
| ~~**P3-FLOW-03**~~ ✅ | Бот: Mini App + браузер + `/setup/?t=`; портал UI в стиле HITVPN. | **2026-05-17:** **`BOT_PORTAL_LINKS_OK`**; **`portal_links.py`**. |
| ~~**P3-FLOW-04**~~ ✅ | Мастер **«Подключить VPN»**; главный CTA → Mini App. | **2026-05-17:** FSM + 4 устройства; **`VPN_SETUP_WIZARD_OK`**; portal `#device=`. |
| ~~**P3-FLOW-05**~~ ✅ | QR подписки (бот + web). | **2026-05-17:** **`BOT_SUBSCRIPTION_QR_OK`** / **`PORTAL_SUBSCRIPTION_QR_OK`**; кнопка «QR для Happ» → `subscriptionUrl`. |
| ~~**P3-FLOW-06**~~ ✅ | Видео/GIF первого коннекта на сайте (не только TG). | **2026-05-17:** **`/portal/guide.html`**, GIF iOS/Android; **`PORTAL_SETUP_VIDEO_OK`**. |
| ~~**P3-FLOW-07**~~ ✅ | Синхронизация FAQ / онбординг / бот / сайт (в т.ч. **live-оплата**). | **2026-05-17:** **`PAYMENT_COPY_SYNC_OK`**; Stars + 6,67 ₽/день. |
| ~~**P3-FLOW-08**~~ ✅ | Ошибки на сайте (как **`USER-FACING-ERRORS.md`**). | **2026-05-17:** **`/start/help/errors/`**, 5 кейсов; **`PORTAL_HELP_ERRORS_OK`**. |
| **P3-FLOW-09** | Ветки по типу устройства (бот + сайт). | ≤ 5 шагов на ветку. |
| **P3-FLOW-10** | Метрики воронки (сайт → бот → ключ → sub). | Wiki + еженедельный срез; без PII в git. |
| **P3-FLOW-11** | Запасной домен bootstrap (блокировки). | Второе имя + probe; связь **P2-RED-SUB-01**. |
| **P3-FLOW-13** | A11y portal (контраст, шрифт 18px+, `lang=ru`). | Lighthouse a11y ≥ 95. |
| **P3-FLOW-15** | **Баланс в веб-ЛК:** read-only API `GET /portal/api/cabinet` (JWT/HMAC по `BVPN-ID` + email recover); UI в `#cabinet`. **Оплата в браузере** — после подключения эквайринга (сейчас Stars/карта только в боте). | Smoke **`PORTAL_CABINET_BALANCE_OK`**; без live acquiring в scope. |
| **P3-FLOW-16** | **Привязка Telegram ↔ web-клиент:** deep link `/start bind_<BVPN-ID>` или код в ЛК; перенос `telegram_id` с отрицательного surrogate на реальный chat id; один баланс/ключи. | Smoke **`WEB_TG_BIND_OK`**; web-only не теряются в scheduler. |
| **P3-FLOW-17** | **Канал уведомлений без TG:** карточка «Обновления VPN» (есть) + опционально Web Push / transactional email при смене `sub_config_generation` и низком балансе. | Smoke **`WEB_NOTIFY_CHANNEL_OK`**; не дублировать TG после bind. |

**Продуктовые хвосты (не FLOW):** ~~**P3-UX-01…03**~~ ✅; открыто **P5-COM-02** (возвраты).

---

## 8. P4 — DNS / белые списки (отдельный SKU)

**Исполнение:** **не** в линейной очереди **Q023+** — параллельный поток (**`docs/BACKLOG-QUEUE.md`**). Связь с **P1-RED-DNS-01** (критичные имена) и **P4-DNS-04** (мониторинг зоны).

| ID | Задача | Done when |
|----|--------|-----------|
| **P4-DNS-01** | PoC: **dnstt** или **slipstream** + свой домен; замер через НСДИ и провайдера. | Внутренний doc с цифрами. |
| ~~**P4-DNS-02**~~ ✅ | Позиционирование: bootstrap **≠** полноценный VPN. | Блок **`docs/FAQ.md`** («DNS bootstrap ≠ VPN»); PoC (**P4-DNS-01**) отдельно. |
| **P4-DNS-03** | Гайд пользователя (iOS/Android, DNS, ключ). | Прохождение без root. |
| **P4-DNS-04** | Мониторинг зоны/authoritative отдельно от RU SNI‑проб. | **`ops/dns_delegation_probe.py`** на LV → **`DNS_DELEGATION_OK`** (P1-RED-DNS-01); TG-алерт — по необходимости. |
| **P4-DNS-05** | План Б: второй домен/ключ; ToS хостинга; внутренняя юр. оценка. | Wiki + owner. |
| **P4-DNS-06** | (Опц.) Только статический bootstrap через DNS. | Спека «что разрешено». |
| **P4-DNS-07** | **RF egress** при **усечённом whitelist** (провод): весь **не‑РФ** режется → **прокси/нода в РФ** для выхода в «разрешённый» интернет. Не путать с основным VPN NL/LV. | PoC + go/no-go; связь **P4-DNS-01**. **`TSPU-OBSERVATIONS`** п.10. |
| **P4-DNS-08** | **Whitelist IP:** списки **не** с устаревших GitHub seed; свой источник + периодическое обновление; мониторинг «пропали» IP. | Wiki источника; probe или ручной регламент 1×/нед. п.12. |

---

## 9. P5 — После «восьмёрки»

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P5-COM-01**~~ ✅ | Публичный статус инцидентов. | **2026-05-17:** HTML **`/status`** на **k9x2m1**, **`incidents.json`**, smoke **`PUBLIC_STATUS_PAGE_OK`**. |
| **P5-COM-02** | Правила возвратов при массовом дауне. | Текст в оферте. |
| **P5-PROD-NATIVE-APP-01** | **Своё iOS/Android‑приложение** (замена зависимости от Happ): Network Extension (**лимит ~15 MB** на iOS), GeoIP split на устройстве, доверие/модерация App Store. Happ остаётся **временным** рекомендованным клиентом до релиза. | Product brief **`docs/NATIVE-APP-BACKLOG.md`** (архитектура, MVP scope, go/no-go store); не блокирует **P2-RED-EDGE-PORT-01** / **P1-PRO-CLIENT-V2RAYN-01**. |
| **P5-ENG-01** | Общий HTTP‑клиент для Python **ops** (TLS, таймауты). | Новые скрипты без `CERT_NONE`. |
| ~~**P5-ENG-02**~~ ✅ | Общий `load_env` для мониторов. | **`ops/load_env_file.py`** + **`ops/site_urls.py`**; тест **`tests/test_load_env_file.py`** (`python -m unittest discover -s tests`). |
| **P5-ENG-03** | **Бот:** lazy `REMNA_API_TOKEN` + TTL inbound cache. | ротация без restart. **Q076**. |
| **P1-ENG-04** | Hardcoded IP/domains в **bot** → env / `site_urls`. | grep clean. **Q077**. |
| **P2-OPS-BACKUP-01** | Backup DB: timestamp в имени файла. | `backup_YYYYMMDD_*`. **Q074**. |
| **P2-CHORE-SUP-01** | `support_handler` → `DB_FILE` из `database.py`. | один SoT path. **Q075**. |
| **P2-OPS-REMNA-KEY-01** | VLESS: fail если нет `REMNA_PUBLIC_KEY`. | smoke URI. **Q078**. |

---

## 10. P6 — Ёмкость и пороги (рост базы)

### 10.1 Правило «AMS = панель, prod-нагрузка на LV+NL»

**Целевая архитектура**: AMS — **панель, подписка и edge**; прод-VPN там **не выполняется** (`remnanode` **stopped / drain**, **P1-ARCH-AMS-DECOM**). Полезная нагрузка — **LV + NL**.

Рост **пользователей в БД** и **пикового API / подписки** увеличивают риск **OOM и latency на AMS** без привязки к VPN-трафику ноды. Действия по порогам:

| Условие (любое из) | Действие |
|---------------------|----------|
| **Available RAM** на AMS **< 300 MiB** устойчиво 15+ мин | Вертикальный апгрейд RAM VPS или перенос тяжёлых сервисов (**P6**); `remnanode` на AMS уже не ключевой фактор. |
| **Контейнер `remnawave`** стабильно **> 700 MiB** RSS | Профилирование API; проверить утечки / кэш |
| **`users` в БД > 2 000** | Вертикальный апгрейд AMS-панели; рассмотреть split `panel ↔ db ↔ redis` по доке Remnawave |
| **`users` > 8 000** | Обязательный **нагрузочный тест** подписки + панели; **отдельный** хост для subscription edge |
| **Сессий на LV или NL > soft-cap** (`P6-SCALE-02`) | Добавление третьей prod-ноды; пересмотр распределения в `injectHosts` |
| **Ошибки / таймауты** на `p4n7q…/api/sub/*` при пике | **P6-SCALE-04**: CDN / rate limit / кэш (не откладывать) |
| **RU-monitor** > **4 мин** на цикл | **P6-SCALE-06**: батчи / меньше целей / параллель |
| **Postgres** `active_connections` **> 85%** `max_connections` устойчиво 10+ мин | Снизить `connection_limit` / убрать лишние клиенты; апгрейд AMS; read-replica (**P6-RED-PG-01**) |
| **Stampede load test** `pg_stampede_load_probe`: `bad_http_rate` **> 2%** или `p95` refresh **> 3 s** | **P6-SCALE-04** edge + **P6-SCALE-05** panel; повторить после фикса |
| **`users` > 8 000** без read-replica / managed Postgres | Обязательный stampede test + решение по §2 **`RUNBOOK-P6-POSTGRES-RED`** |

### 10.2 Задачи P6

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P6-SCALE-01**~~ ✅ | Метрики: сессии по нодам, RPS `/api/*`, Postgres latency/size, Redis, RPS подписки, RAM по контейнерам. | **В репо:** `python ops/capacity_snapshot.py` — users/nodes, пороги §10.1, **HTTPS probe подписки** (latency + код). Docker/Postgres/RPS — расширения. |
| ~~**P6-SCALE-02**~~ ✅ | Soft cap пользователей на ноду + правило добавления ноды в матрицу. | **`docs/NODE-POLICY-LV-NL.md`** (50/user/node, 80/95/100%); **`capacity_snapshot.py`** soft-cap NOTICE. |
| ~~**P6-SCALE-03**~~ ✅ | Postgres: индексы, `pg_stat_statements`, окно бэкапа не в пик. | **`RUNBOOK-P6-POSTGRES-MAINTENANCE`**, **`pg_remnawave_audit.py`**; cron **35 1,7,13,19** AMS / **50** LV. |
| ~~**P6-SCALE-04**~~ ✅ | Публичная подписка: edge/CDN, **rate limit** по IP, защита от абьюза. | **(a)(b)(c)** закрыты §12 **2026-05-16**: Caddy RL **120/min/IP** на LV; post-RL probe **120** req **c=30** → **120×200**, **p95≈1.83s**, **5xx=0**. Репо: **`RUNBOOK-P6-SUBSCRIPTION-EDGE`**, **`subscription_load_probe`**, **`capacity_snapshot`**. |
| ~~**P6-SCALE-05**~~ ✅ | Рост API панели: вертикаль/горизонталь по доке; Redis eviction. | **`RUNBOOK-P6-PANEL-API-SCALE`**; Valkey **256mb/allkeys-lru**; **`panel_refresh_load_probe`** **100×200** p95≈**1.4s** §12 |
| ~~**P6-SCALE-06**~~ ✅ | RU-monitor укладывается в cron **< 5 мин** при текущем числе хостов. | **2026-05-16:** **`duration_sec`**, **`RU_MONITOR_CYCLE_OK`** §12; **`RUNBOOK-P6-RU-MONITOR-SCALE`** (Q017). |
| ~~**P6-SCALE-07**~~ ✅ | Нагрузка на поддержку: шаблоны (P3) + при росте очереди — вторая линия / SLA ответа. | **`RUNBOOK-P6-SUPPORT-SCALE`**, **`support_queue_snapshot.py`**; **21** topics, **SUPPORT_QUEUE_OK** §12 |
| ~~**P6-SCALE-NL-VERIFY**~~ ✅ (репо) | Продукт / ёмкость: все активные пользователи на **LV** при живой **NL** — осознанная политика (**leastLoad**, squads, запасная нода) или ошибка конфигурации? | **`docs/NODE-POLICY-LV-NL.md`** — критерии проверки; фактический аудит squads/UI — по окну эксплуатации. |

Задачи **P6‑RED‑SUBHA‑01**, **P6‑RED‑PG‑01**, **P6‑RED‑PAY‑01** дублируются в сводной таблице **§5.1** (единый порядок «критичные → мелкие» для ТПСУ).

### 10.3 Про «30k подписчиков»

- **30k платящих** при **пике 3–8k** сессий, **2 prod-ноды (LV + NL) + панель AMS**, **edge** у подписки и **апгрейде** панели — **реалистично** при закрытии P0–P2 и P6.
- **Базовая модель**: 2 prod-ноды + 1 панель. Третья prod-нода добавляется при превышении soft-cap (P6-SCALE-02).
- **30k одновременных** на **одной** ноде или **вся** нагрузка на **одном 2 GiB** без изменений — **нет**.
- **P4 (DNS)** не масштабируется как основной канал на десятки тысяч пользователей.

---

## 11. Связь с аудитом репозитория

**Карта:** **`docs/BACKLOG-MAP.md`** — иерархия документов и фазы.

**Закрыто:** **P0–P2**, **P6** (фаза 1), **P1/P3-RED** + **P5-COM-01** (фаза 2), **P3-FLOW-00, 14, 01, 02, 12, 03** (Q033–038).

**Сейчас (агент):** **`NEXT=Q064`** (**P3-RED-SUP-01**). Порядок: **Q063–078** (security) → **Q051–062** (продукт) → **Q044–050** (флоу).

**До GTM:** **Q032** **P5-COM-02** (только владелец, не NEXT агента).

**Security:** **`docs/AUDIT-2026-05-SECURITY.md`**. **Продукт:** **`AGENT-PRODUCT-BACKLOG.md`**, **`TSPU-OBSERVATIONS.md`**. **Флоу:** **`AGENT-FLOW-BACKLOG.md`** после **Q062**.

**Вне срочной очереди Q:** **P5-PROD-NATIVE-APP-01** (своё приложение; brief **`docs/NATIVE-APP-BACKLOG.md`**).

**Параллельно:** **P4-DNS**; **P5-ENG-01** (ops HTTP); **`MANUAL-OWNER-CHECKLIST.md`** (DNSSEC, BotFather, LUKS, **`PORTAL_SETUP_HMAC_SECRET`** на AMS).

**Операционная память:** **`KNOWLEDGE-BASE.md`**, **`POLICY-REPO-WORKFLOW.md`**, **`NODE-POLICY-LV-NL.md`**.

---

## 12. Журнал прогресса (заполнять вручную)

| Дата | Что сделано |
|------|-------------|
| 2026-05-18 | **P6-RED-PAY-03 — DONE (Q063):** auto-renew списывает баланс до `provision_key`; skip + уведомление при нехватке; **`AUTO_RENEW_BILLING_OK`**. **NEXT=Q064**. |
| 2026-05-18 | **Очередь:** линейный порядок **Q063–078 → Q051–062 → Q044–050**; **NEXT=Q063**. |
| 2026-05-18 | **CodeRabbit audit:** **`docs/AUDIT-2026-05-SECURITY.md`**; **Q063–Q078** в очереди. |
| 2026-05-18 | **Handoff агенту:** **`AGENT-PRODUCT-BACKLOG.md`** (Q051–062: что/зачем/почему), **`.cursor/rules/product-backlog.mdc`**. Продукт **впереди** флоу. **NEXT=Q051**. |
| 2026-05-18 | **Порт edge:** **`EDGE-PORT-RECOMMENDATION.md`** — **8443**. **Тиры:** **`PRODUCT-TIER-PROFILES.md`**, **Q062**. |
| 2026-05-18 | **ТСПУ 12 пунктов:** **`docs/TSPU-OBSERVATIONS.md`** — матрица «наблюдение → продукт → бэклог». Новые ID **§5.1**: **P2-RED-TSPU-VLESS-01**, **P1-RED-TSPU-BLOCK-01**, **P2-RED-VPN-INBOUND-PORT-01**, **P2-RED-SELFSTEAL-REVIEW-01**, **P2-RED-SNI-ROTATE-01**, **P1-RED-TSPU-THREAT-MODEL-01**, **P1-RED-NODE-DNS-01**; **P4-DNS-07/08**. Очередь **Q051–061**. |
| 2026-05-18 | **Бэклог по фидбеку бета:** **P2-RED-EDGE-PORT-01**, **P1-PRO-CLIENT-V2RAYN-01**, **P5-PROD-NATIVE-APP-01**; **Q051–053**. Happ — компромисс App Store до native app. |
| 2026-05-17 | **P3-FLOW-08 — DONE (Q043):** `/start/help/errors/` — 5 человекочитаемых кейсов; ссылки с setup/portal/бота; **`PORTAL_HELP_ERRORS_OK`**. **NEXT=Q044** P3-FLOW-09. |
| 2026-05-17 | **P3-FLOW-06 — DONE (Q042):** `/portal/guide.html` + GIF iOS/Android; кнопка в боте и на portal; **`PORTAL_SETUP_VIDEO_OK`**. **NEXT=Q043** P3-FLOW-08. |
| 2026-05-17 | **P3-FLOW-05 — DONE (Q041):** QR подписки в боте (`show_sub_qr`) и portal (`#device=` + localStorage); **`BOT_SUBSCRIPTION_QR_OK`**, **`PORTAL_SUBSCRIPTION_QR_OK`**. **NEXT=Q042** P3-FLOW-06. |
| 2026-05-17 | **P3-FLOW-07 — DONE (Q040):** FAQ/ONBOARDING/portal — оплата live (Stars, 6,67 ₽/день); **`PAYMENT_COPY_SYNC_OK`**. **NEXT=Q041** P3-FLOW-05. |
| 2026-05-17 | **P3-FLOW-04 — DONE (Q039):** мастер «Подключить VPN» (FSM, 4 устройства, Mini App CTA, chat fallback); portal `#devices`/`#device=`; **`VPN_SETUP_WIZARD_OK`**. **NEXT=Q040** P3-FLOW-07. |
| 2026-05-17 | **Синхронизация бэклога:** **`BACKLOG-MAP.md`**; §5.1 Red team ✅; §11/§1; FAQ оплата; **`MANUAL-OWNER-CHECKLIST`** фаза 3. |
| 2026-05-17 | **P3-FLOW-03 — DONE (Q038):** кнопки Mini App / браузер / «Моя настройка»; HIT-style portal CSS; **`BOT_PORTAL_LINKS_OK`**. **NEXT=Q039** P3-FLOW-04. |
| 2026-05-17 | **P3-FLOW-12 — DONE (Q037):** Mini App = **`/portal/`**; **`portal.js`** + WebApp в боте; **`TELEGRAM_MINIAPP_PORTAL_OK`**. **NEXT=Q038** P3-FLOW-03. |
| 2026-05-17 | **P3-FLOW-02 — DONE (Q036):** **`portal_setup_token.py`**, **`/setup/?t=`** + QR, **`bvpn-setup-verify`**, **`PORTAL_SETUP_PAGE_OK`**. **NEXT=Q037** P3-FLOW-12. |
| 2026-05-17 | **P3-FLOW-01 — DONE (Q035):** **`/start/`**, **`/portal/`** на LV; journey as-is бот; trial → **App Store/Google Play** в репо; **`PUBLIC_BOOTSTRAP_OK`**. **NEXT=Q036** P3-FLOW-02. |
| 2026-05-17 | **P3-FLOW-14 — DONE (Q034):** **`web/portal/`** (ru.json, 4 устройства, Happ phone+PC); journey/FAQ обновлены; **`PORTAL_BUNDLE_OK`**. **NEXT=Q035** P3-FLOW-01. |
| 2026-05-17 | **P3-FLOW-00 — DONE (Q033):** **`USER-FLOW-JOURNEY.md`** (персоны + Win/Mac); **`USER_FLOW_JOURNEY_OK`**. **NEXT=Q034** P3-FLOW-14. |
| 2026-05-17 | **Агент-бэклог флоу:** **`docs/AGENT-FLOW-BACKLOG.md`** — Q032–Q047, portal=сайт+Mini App; **NEXT=Q033**. |
| 2026-05-17 | **Бэклог P3-FLOW:** **`docs/USER-FLOW-BACKLOG.md`**, §7.1 + спринт §3 п.13; фаза 3 в **`BACKLOG-QUEUE.md`** (bootstrap без VPN, веб-выдача конфига, мастер в боте). |
| 2026-05-17 | **P5-COM-01 — DONE (Q031):** публичная страница **`/status`**, **`public_status_page.py`**, **`incidents.json`**; deploy **`deploy-public-status-page-lv.ps1`**; smoke **`PUBLIC_STATUS_PAGE_OK`**. **Фаза 2 очереди закрыта.** |
| 2026-05-17 | **P3-RED-JURIS-01 — DONE (Q030):** wiki + runbook VPS/PSP failover, tabletop template; **`jurisdiction_failover_audit.py`** → **`JURIS_FAILOVER_OK`**. **NEXT=Q031** P5-COM-01. |
| 2026-05-17 | **P3-RED-MIN-01 — DONE (Q029):** **`DATA-MINIMIZATION-POLICY`**, **`DATA-INVENTORY-INTERNAL`**, **`payload_redact`**; smoke **`DATA_MINIMIZATION_OK`**. **NEXT=Q030** P3-RED-JURIS-01. |
| 2026-05-17 | **P1-RED-SEC-01 — DONE (Q028):** **`remna_credential_broker.py`** на LV (TTL **3600s**, audit log); **ru-monitor** + **balancer**; smoke **`SHORT_LIVED_TOKEN_OK`**. **NEXT=Q029** P3-RED-MIN-01. |
| 2026-05-17 | **P1-RED-DATA-01 — DONE (Q027):** LUKS2 **`postgres.luks.img`** → **`/mnt/remnawave-pgdata`**; compose bind mount; **`POSTGRES_CRYPT_OK`** + **`AMS_SAFE_DEPLOY_OK`**; ключ только Bitwarden. **NEXT=Q028** P1-RED-SEC-01. |
| 2026-05-17 | **P1-RED-DNS-01 — DONE (Q026):** wiki **`DNS-CRITICAL-NAMES`** + **`RUNBOOK-DNS-RED-TEAM`**; Dynadot **`conntest.xyz`** + reserve registrar; **`dns_delegation_probe.py`** на LV → **`DNS_DELEGATION_OK`**; DNSSEC — runbook (включить в Dynadot). **NEXT=Q027** P1-RED-DATA-01. |
| 2026-05-17 | **P1-RED-SSH-01 — DONE (Q025):** per-host **`bvpn_lv_ed25519`** / **`bvpn_ams_ed25519`**; legacy shared key снят с LV+AMS; **`ops/ssh_audit.py`** + **`ssh_audit_from_ams.sh`** → **`SSH_AUDIT_OK`** (AMS+NL с панели, все три с workstation). **NEXT=Q026** P1-RED-DNS-01. |
| 2026-05-17 | **P6-RED-PAY-02 — DONE (Q024):** **`webhook_server/auth.py`** — loopback allowlist, YooKassa **`Payment.find_one`**, **`CRYPTO_WEBHOOK_SECRET`**; Flask **`WEBHOOK_BIND_HOST=127.0.0.1`**; smoke **`WEBHOOK_AUTH_OK`**. **NEXT=Q025** P1-RED-SSH-01. |
| 2026-05-17 | **P2-OPS-AMS-SAFE-DEPLOY-01 — DONE (Q023):** **`ops/smoke_ams_safe_deploy.py`** + **`ops/ams_safe_deploy_bundle.sh`**; runbook §3 smoke + §4 урок **502/P1000**; прод **`AMS_SAFE_DEPLOY_OK`**. **NEXT=Q024** P6-RED-PAY-02. |
| 2026-05-17 | **Фаза 2 очереди:** в **`BACKLOG-QUEUE.md`** добавлены **Q023–Q031**; **NEXT=Q023** (**P2-OPS-AMS-SAFE-DEPLOY-01**). В бэклог — **P6-RED-PAY-02** (webhook auth); **§5.1** / **§11** / **§8 P4** синхронизированы; **P6-SCALE-06** → ✅ в §10.2. |
| 2026-05-17 | **P6-RED-PG-01 — DONE (Q022):** Prisma **`connection_limit=15`** на AMS (patch + tmpl); Postgres **`max_connections=100`**; **`pg_stampede_load_probe`** **120×25** (60+60 на **p4n7q**/**k9x2m1**) → **120×200**, **p95≈1.15–1.20s**, **peak_conn=15/100** (15%), **PG_STAMPEDE_LOAD_OK**; read-replica — при **users≥8k** (**`RUNBOOK-P6-POSTGRES-RED`**). Очередь фазы закрыта. |
| 2026-05-16 | **P2-RED-TLS-01 — DONE (Q2 2026):** Xray **26.3.27** LV+NL; sing-box **v1.13.12**; sub **vless+reality+vision**; mux OK; шаблон без изменений. След. ревью **2026-08-16**. **NEXT=Q022** P6-RED-PG-01. |
| 2026-05-16 | **P2-RED-BOOT-01 — DONE:** HTTPS mirror **`/api/ops/status.json`** на **k9x2m1** (Caddy file_server + cron ***/2**); **`smoke_status_channels.py`** → **STATUS_CHANNELS_OK**; § в **`RUNBOOK-INCIDENT`**. |
| 2026-05-16 | **P6-SCALE-07 — DONE:** метрика очереди (**`support_queue_snapshot.py`**: pending/SLA/tickets_24h); бот — timestamps **`support_last_*_at`**; шаблоны **`SUPPORT-REPLY-TEMPLATES`**; пороги 2-й линии **15/25**. Smoke: **active_topics=21**, **SUPPORT_QUEUE_OK**. |
| 2026-05-16 | **P6-SCALE-05 — DONE:** Valkey **`allkeys-lru`** + **256mb** (runtime AMS + compose tmpl); **`panel_refresh_load_probe`** **100** req **c=25**, **40** shortUuid, **100×200**, **p95≈1.4s**, **0** bad HTTP; **`valkey_memory_audit.py`**. |
| 2026-05-16 | **ru-monitor 401 (LV) — FIXED:** протухший **`REMNA_API_TOKEN_LV`**; выровнен с рабочим AMS shop JWT (**`sync-lv-remna-token-from-ams.ps1`**). Smoke: **`total=16 ok=16`**, **`duration_sec≈8s`**, **`RU_MONITOR_CYCLE_OK`**. |
| 2026-05-16 | **P6-SCALE-06 — DONE:** **`ru-monitor.py`** — **`duration_sec`** (в т.ч. abort), **`JITTER_MAX=60`**; **`ru_monitor_cycle_probe.py`**, **`RUNBOOK-P6-RU-MONITOR-SCALE`**. |
| 2026-05-16 | **GTM-WIKI-01 — owner gate CLOSED:** канон URL + §1; еженедельная синхронизация — **`RUNBOOK-GTM-WIKI`**. |
| 2026-05-16 | **P2-OPS-IMAGE-PIN-01 — DONE:** digest pin **postgres/valkey/adguard** в compose tmpl (prod sha256); **Caddy v2.11.2** — host pin в **`IMAGE-PINS.md`**; **`check_compose_image_pins.py`**. Накат compose на прод — при следующем safe-deploy. |
| 2026-05-16 | **P6-SCALE-03 — DONE:** **`RUNBOOK-P6-POSTGRES-MAINTENANCE`**; **`pg_remnawave_audit.py`** (AMS: PG **17.6**, 62 idx, largest **432 kB**); backup cron вне **06 UTC** (**`35 1,7,13,19`** / **`50`**); compose tmpl + **`pg_enable_stat_statements_ams.sh`** (накат extension — по safe-deploy). **NEXT=Q015** GTM-WIKI-01. |
| 2026-05-16 | **P6-SCALE-02 — DONE:** **`NODE-POLICY-LV-NL.md`** — soft cap **50** user/node, пороги **80/95/100%**, playbook 3-й ноды; **`capacity_snapshot.py`** — те же NOTICE. **NEXT=Q014** P6-SCALE-03. |
| 2026-05-16 | **P6-RED-SUBHA-01 — DONE:** второй **`remnawave-subscription-page-b`** AMS **:3011**; LV Caddy split-host (**`patch-caddy-sub-split-host-lv.sh`**); **`subscription_ha_load_probe.py`** 60 req c=15 → primary p95≈**1.48s**, alt **1.51s**, **0×502**. **NEXT=Q013** P6-SCALE-02. |
| 2026-05-16 | **P2-RED-MUX-01 — DONE:** профили **primary** (LV/443) + **alt** (NL:9443, LV:8443); аудит **`TRANSPORT_MUX_OK`** (25 users, alt ~56% outbounds). **NEXT=Q012** sub-page HA. |
| 2026-05-16 | **P2-RED-SUB-01 — DONE:** alternate origin **k9x2m1.conntest.xyz:2053/api/sub/** (Caddy **`patch-caddy-sub-alt-origin-lv.sh`**); мониторинг **`monitor.sh`** CHECK 5b + **`ops/subscription_origin_drift_probe.py`** / **`smoke_sub_multi_origin_lv.sh`** (SHA256 совпадает). **NEXT=Q011** mux profiles. |
| 2026-05-16 | **P6-RED-PAY-01 — DONE:** in-process очередь webhook (**`payment_queue.py`**), SQLite idempotency/DLQ (**`webhook_deliveries`**), быстрый **200** на duplicate; smoke на AMS. **NEXT=Q010** P2-RED-SUB-01. |
| 2026-05-16 | **COM-MONETIZE go-live OK** (**P2-COM-MONETIZE-04**): чеклист **`RUNBOOK-COMMERCE-GO-LIVE` §4** — safe-deploy runbook, **P6-SCALE-04**, restore test, **§10.1**, GTM outline (wiki живой — **Q015**). Smoke **`ops/smoke_commerce_golive_ams.py`** на AMS. Эпик **§5.3** закрыт; при пике продаж — **P6-RED-PAY-01** (**NEXT=Q009**). |
| 2026-05-16 | **P2-COM-MONETIZE-03 — DONE:** legal URLs уже в SQLite бота (не заглушки `config.py`): **terms** / **privacy** → telegra.ph, **support** → **@Bender_KVN_bot**; smoke **`ops/check_legal_urls_ams.py`** → **LEGAL_OK=true**. **NEXT=Q008** go-live чеклист. |
| 2026-05-16 | **P2-COM-MONETIZE-02 — DONE:** AMS **`BOT_PAYMENTS_LIVE=1`** (`ops/patch-remna-shop-payments-live-ams.sh`, **`docker restart`**); канал **Telegram Stars**; **`process_topup_payment`** + idempotency **`topup_charge:*`**; smoke **`ops/smoke_payments_live_ams.py`** — invoice link OK, admin **`expireAt`** bump, повтор без дубля баланса. **NEXT=Q007** legal URLs. |
| 2026-05-16 | **Бэкап cron (хвост Q004):** на **AMS** `5 */6` → **`pg_dump_remnawave.sh`**, на **LV** `15 */6` → **`pull-latest-dump-ams-to-lv.sh`** (`ops/install-remnawave-backup-cron.sh`); свежий дамп **`remnawave-20260516-170159.sql.gz`** (168K) на AMS+LV, SHA256 OK. |
| 2026-05-16 | **P2-COM-MONETIZE-01 (уточнение владельца):** тарификация **баланс + 6.67 ₽/день**, не «месячные» планы. **`deploy-bot-balance-model-ams.ps1`**, колонка **`users.balance`**, меню «Пополнить баланс», пресеты **200/500/1000/2000 ₽** с оценкой дней. **NEXT=Q006** live payments. |
| 2026-05-16 | **P2-OPS-RESTORE-TEST-01 — DONE:** **`ops/remnawave_restore_test.sh`** на **bvpn-lv** (ephemeral **`postgres:17`**, порт **55432**); предварительно **`pull-latest-dump-ams-to-lv.sh`** → **`remnawave-20260514-203204.sql.gz`** (163K, SHA256 OK). Restore ~**5 s**, **36** public tables, **`_prisma_migrations`=97**, без **ERROR** в логе. Дата в **`RUNBOOK-BACKUP-REMNAWAVE` §4**. **NEXT=Q005** monetize prices. |
| 2026-05-16 | **P6-SCALE-04 (c) — DONE:** после edge RL (**(b)**) — **`subscription_load_probe`** **total=120**, **concurrency=30** на probe URL (рабочая станция): **120×200**, **p95≈1.83s**, **p50≈1.12s**, **hard_errors=0**, **bad_http_rate=0**; **429/5xx=0**. Эпик **P6-SCALE-04** закрыт (a)(b)(c). |
| 2026-05-16 | **P6-SCALE-04 (b):** на **bvpn-lv** — Caddy **v2.11.2** + **`mholt/caddy-ratelimit`** (`ops/lv-install-caddy-ratelimit.sh`), зона **`sub_api_per_ip`** **120/min/IP** на **`/api/sub/*`** (`ops/patch-caddy-sub-ratelimit.sh`, эталон **`Caddyfile-latvia-full.txt`**). Smoke probe URL → **200**; **`subscription_load_probe`** 5×**200** p95≈**1.3s**. |
| 2026-05-16 | **Последовательная очередь:** **`docs/BACKLOG-QUEUE.md`** (Q001…Q005 **DONE**, **NEXT=Q006** P2-COM-MONETIZE-02), **`docs/POLICY-SEQUENTIAL-WORK.md`**, **`.cursor/rules/sequential-backlog.mdc`**. |
| 2026-05-16 | **План «бэклог vs рост 10k/30k» в репо:** §1 цели роста; спринт **§3 п.9a** (**P2-COM-MONETIZE**); **§5.3**, переупорядочен **§11**; **`RUNBOOK-AMS-SAFE-DEPLOY`**, **`RUNBOOK-COMMERCE-GO-LIVE`**, **`GTM-GROWTH-OUTLINE`**; **P2-OPS-AMS-SAFE-DEPLOY-01**, **P2-OPS-RESTORE-TEST-01**, **P2-OPS-IMAGE-PIN-01**; **P6-SCALE-04** критерии (a)(b)(c). **P6-SCALE-04 (a):** probe **20** req, c=10 → **19×200**, p95≈**11.5s**, 1 hard_error (с рабочей станции). **(b)(c)** CDN/RL на проде — открыто. Amsterdam **4c** — waive до scale. |
| 2026‑05‑15 | **`docs/POLICY-REPO-WORKFLOW.md`** — операционная дисциплина репозитория (SoT, секреты, AMS/LV JWT, sanitize убивает `compose/` как по MAP); **`.cursor/rules/bendervpn-repo-workflow.mdc`** для Cursor. **`docs/ONBOARDING.md`** + закрыта **`P3-UX-01`**. Обновлён **`ops/remna_api_token_rollout.sh` dry-run** под двухтокенную схему. |
| 2026-05-17 | **Инцидент 502 после наката rendered `tmpl` на AMS (закрыт):** **`remnawave`** — цикл перезапусков, Prisma **P1000** (пароль в **`DATABASE_URL`** из vault не совпадал с фактическим Postgres); **`remnawave-subscription-page`** — **401** к панели (неверный **`REMNA_API_TOKEN`** в смонтированном **`sub/docker-compose.yml`**). **Починка на AMS:** откат **`/opt/remnawave/.env`**, **`/opt/remnawave/sub/docker-compose.yml`**, **`/opt/remna-shop/.env`** из **`*.before-drift-20260516-120658`** + **`docker compose up -d`**; публичный sub-smoke → **200**, прогон **`subscription_load_probe`**: **20/20 × 200**, p95 ≈ **1.5 s**. **Урок:** перед накатом **`panel.env.tmpl`** обновить vault (**`extract-vault`** с прода) и не перезаписывать sub/shop без сверки токена (**`RUNBOOK-REMNA-API-TOKEN`**). |
| 2026-05-17 | **P6-SCALE-04 (нагрузочный смок):** добавлен **`ops/subscription_load_probe.py`**; прогон **120** запросов, **concurrency 30** на `site_urls.sub_monitor_probe_url()` — **p95 ≈ 4.2s**, **502** на все ответы (**status_histogram 502=120**), **hard_errors=0**; одновременно **GET /api/users** с рабочей машины дал **502** — трактовать как **проверку устойчивости канала при деградации upstream**, повторить смок когда панель/sub стабильно **200/304**, при необходимости смотреть AMS **`remnawave` / subscription-page** / Caddy. |
| 2026-05-16 | **~~P2-OPS-DRIFT-POST-P0~~ ✅:** SSH с рабочей машины — выкладка **`balancer.sh`**, **`backup-remnawave.sh`**, **`ru-monitor.py`**, **`deploy-node.sh`** (LV+AMS) из репо; **`/etc/bvpn/balancer.env`** и **`ru-monitor.env`** (LV) — байтовый рендер из **`compose/_shared/...` + `.secrets/vault.env`**; AMS — **`/opt/remnawave/docker-compose.yml`**, **`.env`**, **`/opt/remnawave/sub/docker-compose.yml`**, **`/opt/remna-shop/.env`** из рендера + **`docker compose up -d`** (пересозданы **`remnawave-db`**, **`remnawave`**, **`remnawave-subscription-page`**, **`remna-shop-bot`**). **`python ops/drift-check.py`**: **28/28 OK**, exit **0** (~10 мин). Локальные копии рендера удалены. |
| 2026-05-16 | Тот же день (**до наката):** drift-check **17 OK / 11 DRIFT** — снимок зафиксирован; процедура **`DRIFT-POST-P0.md`**; затем закрыто (строка выше). |
| 2026-05-16 | **§2.1 «продукт → UX»** + доки: **`docs/POLICY-BACKLOG-ORDER.md`**, **`docs/POLICY-TELEGRAM-ALERTS.md`**, **`docs/SSH-HOST-KEY-PRACTICE.md`**, **`docs/POLICY-SECRET-LEAK-RESPONSE.md`**, **`docs/DRIFT-POST-P0.md`** (waive/post-P0 drift). В **`docs/KNOWLEDGE-BASE.md`** — ссылки на политики + сохранён **`DEPLOY.md`** в §1. **§7 P3** — явное напоминание не ставить UX раньше эксплуатации. |
| 2026-05-16 | **P6 (продолжение):** **`docs/RUNBOOK-P6-SUBSCRIPTION-EDGE.md`** — edge подписки, rate limit/WAF, критерий load test. **`ops/capacity_snapshot.py`** — HTTPS probe публичной подписки (HEAD→GET, latency, алерт если не 200/304). Сплинт §3 п.9: **P6-SCALE-01** закрыт минимумом; **P6-SCALE-04** — runbook + probe; полный load test — когда будет окно. |
| 2026-05-16 | **Cursor User Rules:** дубликат инструкции — `%USERPROFILE%\.cursor\RULE-PASTE-INTO-USER-RULES.md` (вставить в Settings → Rules → User Rules); в репо — **`docs/CURSOR-USER-RULES-SNIPPET.md`**. **Прод:** `pg_dump_remnawave.sh` → AMS `/opt/scripts/`, `pull-latest-dump-ams-to-lv.sh` → LV `/opt/scripts/` (`bash -n` OK). **P6-SCALE-01 (минимум):** **`ops/capacity_snapshot.py`**, строки в **`DEPLOY.md`** / **`KNOWLEDGE-BASE.md`**. |
| 2026-05-16 | **~~P2-BAK-01~~ / ~~P2-BAK-02~~**: **`docs/RUNBOOK-BACKUP-REMNAWAVE.md`** — AMS→LV дамп, пример **`ops/crontab-remnawave-backup.example`**, обновлены **`DEPLOY.md`** (таблица скриптов, §5 crontab AMS/LV), шапка **`backup-remnawave.sh`** (legacy vs канонический путь), строка в **`KNOWLEDGE-BASE.md`**. Restore test — чеклист в runbook; дату успешного прогона зафиксировать в §4 runbook + §12. |
| 2026-05-16 | **~~P2-MON-01~~ / ~~P2-MON-02~~**: `monitor.sh` на LV — перед `ss :443/:8443` проверяются **`remnanode` running** и **`docker exec remnanode xray version`**; новые ключи **`xray_lv_remnanode`**, **`xray_lv_core`**. Комментарии «где state» в `monitor.sh`, `ru-monitor.py`, пример crontab в **`DEPLOY.md`**. Деплой: `pwsh -File ops/deploy-monitor-lv.ps1`. |
| 2026-05-16 | **Red team / ТПСУ → бэклог**: добавлен **§5.1** с ID **P1‑RED‑*** … **P5‑RED‑RD‑01** (шифрование БД, Vault/SPIFFE, SSH blast radius, DNS‑диверсификация, log_skip подписки, резерв без TG, multi‑origin подписки, multi‑transport, квартальный TLS‑ревью sing-box; **P6‑RED‑*** масштаб; **P3‑RED‑*** минимизация данных и юрис‑runbook; **P5‑RED‑RD‑01** Snowflake‑PoC). Спринт **§3 п.12**. |
| 2026-05-16 | **Разворот пробного тарифа (прод AMS):** `grandfather_panel_users_expire.py --apply` — **54/59** профилям Remnawave **`expireAt` → 2099** (до cut-off **16.05.2026 00:00 МСК**); **1** уже новее порога без изменения; **`/opt/remna-shop/.env`**: TRIAL/`REMNA_DEFAULT_DAYS`/ **`BOT_PAYMENTS_LIVE`**; **`bot_src`**: кнопка «Бесплатно 3 месяца», текст выдачи + HTML, scheduler без оплаты. Сценарий: **`ops/remote_ams_rollout_trials.sh`** + `scp` в **`/tmp/bvpn-rollout/`**. |
| 2026-05-15 | **`docs/KNOWLEDGE-BASE.md`** — точка входа (правила, типовые ошибки); **`README.md`** для GitHub. **~~`P1-OPS-REMNA-TOKEN-01`~~** оформлен как **`docs/RUNBOOK-REMNA-API-TOKEN.md`** + **`ops/remna_api_token_rollout.sh`**. **~~`P3-OPS-SUPPORT-REMNA-LOGIN`~~ ✅**: секция в **`RUNBOOK-INCIDENT`**. Зрелость: ~~**`P2-CHORE-SUB-ENV`**~~ (**`monitor.sh`** `SUB_*` + **`PANEL_URL`**), ~~**`P2-ENG-DRIFT-CHECK-01`**~~ (**`drift-check`** retries LV), ~~**`P1-RED-LOG-01`**~~ (**`RUNBOOK-CADDY-SUBSCRIPTION-LOGS`**, эталон **`Caddyfile-latvia-full.txt`** с **`log_skip /api/sub/*`**). |
| 2026-05-14 | **P0-pre**: pg_dump remnawave (`/var/backups/remnawave/`) + git snapshot (`.snapshots/pre-P0-…`), SHA256 зафиксированы |
| 2026-05-14 | **P0-SEC-03 DONE**: `0.0.0.0:3010` закрыт через iptables `DOCKER-USER` (только LV `176.126.162.158`); systemd-юнит `ams-docker-firewall.service`; `ENABLE_DEBUG_LOGS=false`; LV→AMS `200 OK`, прямой доступ снаружи отвергнут |
| 2026-05-14 | **P0-SEC-01 DONE**: убран `ssl.CERT_NONE` из 15 `ops/*.py`, добавлен общий `ops/panel_client.py` (strict TLS + retry); `monitor.sh` / `daily-report.sh` — `-sk → -s` для LE-эндпоинтов (selfsteal `127.0.0.1` остался `-sk` намеренно); `.secrets/*.sh` — то же; `check.py` оставлен `CERT_NONE` с явным комментарием (это relay-проба чужих SNI). Smoke: `panel_api.py nodes/inject-count` отвечают, `curl -fsS` к панели/подписке без `-k` → 200 |
| 2026-05-14 | **Новая находка → P1-OPS-DRIFT-01**: репо `monitor.sh` / `daily-report.sh` дрейфуют с продом (`/opt/scripts/`): на проде hardcode `ADMIN_CHAT_ID` / `TEST_SUB_KEY` / `id.x5.ru`, в репо — env-based + `ads.x5.ru` + UFW hints. P0-SEC-01 применён точечно к прод-baseline; нужен отдельный спринт «raise prod to repo». |
| 2026-05-14 | **P0-SEC-02 DONE**: `sync-sub-token-ams.sh` устарел/удалён после миграции панели на AMS (на серверах нет). Расширил задачу: убил shell-injection вектор в `selfsteal-monitor.py:ssh_batch_check` — был `f"for sni in {sni_str}; do"` (если SNI прилетит из API с метасимволами — RCE на AMS). Сделал defense-in-depth: (1) strict DNS-label whitelist на python-стороне, (2) here-doc payload вместо интерполяции, (3) `case` re-check внутри bash. Smoke: `total=24 ok=24 critical=0 warning=0`, ноды отвечают как ожидается. Hash прод совпадает с репо после деплоя. |
| 2026-05-14 | **P0-OPS-01 DONE**: `deploy-node.sh` — порядок резолва токена `env → /etc/bvpn/balancer.env → .secrets/panel-token.txt → interactive read -rs → legacy argv с loud WARN`; 5-й позиционный аргумент остаётся как deprecated с громким предупреждением. Дополнительно убран остаточный leak: все `curl -H "Authorization: Bearer …"` переписаны на `_curl_auth_config | curl --config -` (header читается из stdin, secret не виден в `ps -ef` / `/proc/$pid/cmdline`). Smoke на LV: `--config -` даёт байт-в-байт тот же ответ, что `-H Authorization`; `ps auxww` не содержит Bearer. Задеплоено на LV (`c130744…`) и AMS (`c130744…`) — hash идентичен репо. |
| 2026-05-14 | **P0-OPS-02 DONE**: 4 критичных образа закреплены через `image: tag@sha256:DIGEST` (supply-chain immutability). Бэкапы compose-файлов рядом с оригиналом (`.bak-YYYYMMDD-HHMMSS`). Pinning: LV `remnanode → ghcr.io/remnawave/node@sha256:9d5737…`, AMS `remnanode → remnawave/node@sha256:9d5737…`, AMS `remnawave-subscription-page → remnawave/subscription-page@sha256:37dd48…`, AMS `remnawave → remnawave/backend@sha256:a0e9a3…`. Контейнеры пересозданы; smoke: panel `nodes` → все 3 (LV/AMS/NL) `connected=True`, sub endpoint `HTTP 200`. **Перенесено в P1**: `adguard:latest`, `caddy:2.9`, `postgres:17.6`, `valkey/valkey:8.1-alpine` — также pinning через digest. |
| 2026-05-14 | **P0-audit DONE**: единый скрипт `ops/p0-audit.sh` (запускается на LV и AMS, выводит `OK / WARN / FAIL`). Финальный прогон по обоим хостам: контейнеры up, критичные образы pinned, sub endpoint 200, TLS panel/sub валидируется системным CA, `iptables DOCKER-USER` корректно фильтрует 3010 (LV ACCEPT + DROP остальных), нет Bearer-токенов в `ps auxww`, бэкапы скриптов и compose-файлов на местах, cron на LV (monitor/daily/ru-monitor/selfsteal) живой. **Все P0 закрыты — переход к P1.** |
| 2026-05-14 | **Архитектурное уточнение → P1-ARCH-AMS-DECOM**: AMS — **только панель/подписка**, нода `remnanode` на AMS оставлена временно для users, чей клиент ещё не пересохранил подписку. Сейчас к AMS-ноде привязано **5 «прямых» injectHosts** — естественного оттока нет, новые подписки садятся на AMS. Зафиксирован план декомиссии (freeze growth → метрика → коммуникация → drain → cleanup → удалить пины и AMS-xray алерты из `monitor.sh`). §1 «Срез продакшена» и §10 «P6 Capacity» пересчитаны на **2 prod-ноды (LV+NL) + 1 панель**. |
| 2026-05-14 | **Переоценка после P0**: ~7.2 → ~**7.8/10**. Существенный прогресс по безопасности и operational hygiene; до устойчивых 8.5+ нужны P1 (DRIFT, ARCH-AMS-DECOM, PRO, ENG-01..03) и P2 (мониторинг «Xray реально жив», off-host бэкапы, SSH-дисциплина). 30k-цель остаётся реалистичной при закрытии P0–P2 и P6. |
| 2026-05-14 | **P1-ARCH-AMS-DECOM шаги 1-2 — оказались уже фактически выполнены**. Pre-flight (pg_dump AMS `7bdf1350…` + panel snapshot) сделан, написан безопасный `ops/freeze_ams_node.py` (dry-run по умолчанию, на `panel_client.PanelClient`). Dry-run показал: на Amsterdam-01 8 хостов (5 «прямых AMS» + 3 «Relay AMS»), **все имеют `isHidden=True`**, и **ни одного нет в `injectHosts.values`** (16 UUIDs там — это LV+NL). `probe_users_subs.py` по 10 рандомным активным юзерам: **AMS=0 outbound** у каждого. На AMS xray прямо сейчас: `ss` 0 ESTABLISHED на :443 и :8443, `docker stats remnanode` 0 B NET I/O за 3+ часа, 0 уникальных source IP в xray-логах. → Шаг 1 (freeze growth) и шаг 2 (метрика «AMS=0») закрыты эмпирически. **Готовы к шагу 4 (drain & cleanup)** без шага 3 (коммуникация) — поскольку коммуницировать некому. |
| 2026-05-14 | **P1-ARCH-AMS-DECOM шаг 4a (drain) — DONE, soft-stop без удаления.** На LV `monitor.sh` пропатчен: CHECK 3-4 (XRay Amsterdam :443/:8443) закомментированы с пометкой «DISABLED — P1-ARCH-AMS-DECOM drain phase», бэкап `/opt/scripts/monitor.sh.before-ams-drain-20260514-204413`, `bash -n` OK. На AMS выполнен `docker compose stop remnanode` (Exited(0)), порты `:443/:8443/:2222` на 127.0.0.1 — closed. Все остальные сервисы AMS живы (panel healthy, sub-page, db healthy, redis healthy, бот, AdGuard, caddy-selfsteal). Панель: `Amsterdam-01 connected=False` (ожидаемо), LV+NL `connected=True`. Re-probe 10 user'ов: LV=8/NL=8/AMS=0 — подписки не сломались. `monitor.sh` отработал на LV: тишина (нет alert/нет recovery). **Rollback в 1 команду**: `ssh -p 3344 root@168.100.11.140 'cd /opt/remnanode && docker compose start remnanode'`. Compose-файл, ноду в БД панели и SSH-ключ — не трогали. Через 24-48h тишины в саппорте → шаг 4b (`docker compose down` + rm из compose), затем 4c (`DELETE /api/nodes/{uuid}` + чистка mon-secrets). |
| 2026-05-14 | **P1-ARCH-AMS-DECOM hotfix: ru-monitor.py поднял шум, потому что `monitor.sh` я заглушил, а второй мониторящий сервис — нет.** 23:46 MSK прилетели 8 алертов «SNI failure» (5 на AMS-направлениях, 3 на Relay-через-AMS). Причина: `ru-monitor.py` (LV, cron `*/5`) берёт таргеты из `/api/hosts` и фильтрует только `isDisabled` — но мы выключили AMS только через `isHidden`. Решение архитектурно чище: расширил `ops/freeze_ams_node.py` флагом `--disable` (PATCH с `isDisabled=true` + GET-back verify), применил к 8 целевым хостам. Антиспам `ru-monitor.py` подавил повторы внутри суток (1 alert на target — больше не повторится). Следующий cron-tick (`[2026-05-14T20:56:19Z] total=16 ok=16 fail=0 transitions=0`) подтвердил: 8 хостов выпали из проверки, остальные 16 зелёные. Бонус: тех-долг — WARNING `expected 16 targets, got 24` исчез сам (был зарождающийся, теперь снова 16). Дополнительный probe 10 user'ов: LV/NL/AMS = 8/8/0 — двойная защита (`isHidden + isDisabled`) ничего не сломала. |
| 2026-05-14 | **Усвоенный урок** добавлен в P1-OPS-DRIFT-01: «при изменениях платформы (drain/decom/freeze) обязателен чек-лист всех мониторов в edits» — у нас 2 параллельных monitor: `/opt/scripts/monitor.sh` (LV bash) и `/opt/scripts/ru-monitor.py` (LV python, через RU-relay). Оба должны быть синхронизированы при любых архитектурных правках. |
| 2026-05-14 | **Monitor-block (A+B+C+D) — DONE.** Закрыта тема «непонятно, тихо потому что ок vs монитор сдох». Изменения: **D**) `monitor.sh.STATE_DIR /tmp/bvpn_states → /var/lib/bvpn-monitor` + миграция маркеров; то же для `ru-monitor.py.ANTISPAM_DIR` (фиксит баг «recover не приходит после reboot» — `/tmp` чистится). Заодно ослабил `expected = 16` → `len(targets) < 4`. **B**) `daily-report.sh` теперь рисует AMS как `🟡 (decom)` вместо 🔴; в `ALERT_COUNT` читает оба пути (legacy/new) для миграционного периода. **C**) Watchdog на NL: `*/15 * * * *`, SSH NL→LV через выделенный ключ `/root/.ssh/lv_watchdog`, restricted `command="/usr/local/sbin/bvpn-watchdog-probe"` + `from="91.90.192.17"` + no-pty/no-forward, локальный antispam `/var/lib/bvpn-watchdog`. Алертит **только при stale >30 мин** (monitor.sh / ru-monitor.py) или потере SSH к LV; шлёт recovery когда оживает. **Молчит когда всё ок** — никаких пустых отбивок. **A**) `/status` admin-only команда в `remna-shop-bot`: показывает nodes (с decom-меткой), hosts (active/hidden/disabled), subscription HTTP code. Async через aiohttp+TLS, использует существующий `REMNA_API_TOKEN` из `/app/.env`. Деплой: host-edit + `docker cp` + restart; backup `admin_handlers.py.before-status-20260514-212813`. Полный rollback в одну команду. |
| 2026-05-14 | **Post-block findings**: (1) первый `/status` в боте показал `active=-7` из-за моей наивной формулы `total - hidden - disabled` (на 8 AMS-хостах оба флага одновременно). Поправлено: `visible = !hidden && !disabled`, остальные счётчики показываются как есть. Деплой через `docker cp` + restart, backup `admin_handlers.py.before-status-v2-…`. (2) `selfsteal-monitor.py` тоже зашумел из-за drain'а AMS — Caddy на AMS:9443 возвращает 500 на bing/etc, потому что reverse_proxy ходит через мёртвый remnanode. Решено симметрично остальным: закомментирована строка `("amsterdam", AMSTERDAM_HOST)` в `NODES`, ANTISPAM_DIR переехал в `/var/lib/bvpn-monitor`, маркеры мигрированы; backup `selfsteal-monitor.py.before-decom-20260514-213408`. (3) Поймал ортогональный сигнал: `latvia:ads.x5.ru` теперь отвечает 302 вместо ожидаемых 503/502/504 — это **не наш регресс**, а реальное изменение upstream'а x5.ru. Заведён `P1-OPS-SELFSTEAL-01` на пересмотр `EXPECTATIONS`. |
| 2026-05-14 | **Новая продуктовая задача от пользователя**: `P1-PRO-RU-BYPASS-01` — split-tunneling для российских приложений (Я.Маркет, Авито, WB, Ozon, Госуслуги, Сбер, T-Bank, MAX, ВК/ОК, Яндекс.*, банки, мобильные ЛК, доставка/еда) — трафик в RU-ресурсы идёт **напрямую**, в обход VPN, даже при включённом VPN. Реализация: `routing.rules[].outboundTag="direct"` в `templateJson.remnawave.routing` через PATCH `/api/subscription-templates` (атомарно, со снапшотом — как `freeze_ams_node.py`). Готовая инфра: `panel_client.PanelClient` уже умеет, нужен только список доменов + matcher (`domain:` + `geosite:category-ru` + `geoip:ru`). |
| 2026-05-15 | **P1-PRO-RU-BYPASS-01 DONE.** Split-tunneling для RU-приложений. Inspection текущего `templateJson.routing.rules` показал что **частично уже есть**: `geosite:category-ru` + regexp на `.ru/.рф/.рус/.орг.рус` + `geoip:ru` уже направляют RU-трафик в `direct`. Найдены 2 проблемы: (1) **`max.ru` и `oneme.ru` сидят в block-rule** — MAX-мессенджер VK блокируется xray-клиентом даже без VPN, противоречит запросу пользователя; (2) **`.com / .net / .online / .eu` российские домены НЕ покрыты** regexp'ом (VK на vk.com, Яндекс на yandex.com, Сбер на sber.com, Tinkoff/T-Bank на .com, маркетплейсы на .com/.eu — все шли через VPN). Решение: написан атомарный `ops/ru_bypass_routing.py` (dry-run по умолчанию, snapshot + verify, как `freeze_ams_node.py`) и `ops/probe_routing.py` для проверки рендера. Изменения: (a) из block-rule убраны `max.ru`/`oneme.ru` (rule стал `domain=[]`, legacy-entry); (b) в direct-rule добавлены 35 доменов: MAX (`max.ru`, `oneme.ru`, `mybridge.ru`), VK (`vk.com`/`vk.me`/`vk.link`/`vkuservideo.com`/`vkuservideo.net`/`vkuser.net`/`userapi.com`/`vkontakte.com`), Яндекс (`yandex.com`/`yandex.net`/`yandexcloud.net`/`yastatic.net`/`ya.com`), мобильные (`mts.com`/`megafon.com`/`beeline.com`/`tele2.com`), банки (`sber.com`/`sberbank.com`/`sberbank.online`/`sbermegamarket.com`/`tinkoff.com`/`tbank.com`/`vtb.com`/`alfabank.com`/`raiffeisen.com`), маркетплейсы (`avito.com`/`ozon.com`/`wildberries.eu`/`aliexpressru.com`), госуслуги (`gosuslugi.com`/`pochta.com`). Backup: `.secrets/snapshots/template-before-ru-bypass-20260515_112742.json`. PATCH + verify прошли. Probe 3 случайных активных user'ов через UA Happ/1.9.4 показал: `R0 block.domain=[]`, `R3 direct.domain=41 entries (6 starting + 35 new)`, `outbounds=18 (proxy*=16)` — рендеринг ОК. **Изменение касается всех 25 активных юзеров** при следующем refresh подписки (1-24 ч; Hiddify/Happ обычно обновляют каждый запуск, v2rayN/NekoBox — по требованию). Rollback в 1 PATCH через snapshot. Что **не покрыто** этим изменением — `geosite:category-ru` (общий список v2fly, обновляется upstream'ом) и `geoip:ru` (если RU-сервис на иностранном CDN). |
| 2026-05-15 | **P1-OPS-SELFSTEAL-01 DONE** (15 мин). Probe `ads.x5.ru` ×10 c LV: устойчиво **HTTP 302 → `Location: https://x5media.ru/`** (60-170ms), upstream X5 вынес ad-platform на отдельный домен. `id.x5.ru` (200) и `5post-gate.x5.ru` (404) — стабильны. Патч: `EXPECTATIONS["ads.x5.ru"] = {"expected": 302, "tolerate": [302, 301, 503, 502, 504]}` (старые 5xx оставлены в tolerate — если X5 вернёт сервис, не алертим). Деплой LV: backup `selfsteal-monitor.py.before-x5fix-20260515-081711`, install, syntax OK, md5 `72ed0c7f`. Cron-tick подтвердил: `state.json` показал `latvia:ads.x5.ru { status: ok, code: 302 }`, в логе `ALERT RECOVERED: latvia:ads.x5.ru` (после 130 retry'ев в `critical`). Sync репо ← прод выполнен (`selfsteal-monitor.py` уже был обновлён локально перед scp), `drift-check.py`: 11/11 OK. |
| 2026-05-15 | **P1-OPS-DRIFT-02 DONE**: `compose/**/*.tmpl`, `docs/SECRETS.md`, `sanitize-compose` / `extract-vault`, рендер **`ops/render_compose.py`** с `--only`/`--none`, оболочка **`ops/render-compose.sh`**, расширение **`ops/drift-check.py`** (`tmpl_only_keys`, CRLF-norm), **`docs/DEPLOY.md` §7** переписан. В бэклог занесены **P0-SEC-04/05**, **P1-ARCH-NODE-UNIFY**. **P1-ENG**: `ops/site.env.example`, ENG-02 отмечено закрытым Monitor-block D; ENG-03 — `ops/redact_bvpn_artifacts.py` + очистка типовых JWT в `bvpn-artifacts`. SSH **drift-check** с этой машины не прогонялся до конца (таймаут) — повторить с рабочего хоста с `bvpn-*` в `ssh_config`. |
| 2026-05-15 | **P1-ENG-01 (конфиг URL)**: добавлен **`ops/site_urls.py`** (опциональный **`ops/site.env`** по **`site.env.example`**), ключевые maintenance-скрипты переведены на него + **`deploy-node.sh`** может source'ить **`ops/site.env`** из репо; **`panel_client`/`panel_api`/`freeze_ams_node`/`ru_bypass_routing`**; **`ops/bot-admin-handlers`** — сборка `SUB_PROBE_URL` из **`SUB_PUBLIC_ORIGIN`** / **`SUB_MONITOR_PROBE_SUFFIX`**. Новые доки: **`docs/P1-POST-AUDIT.md`** (плотный аудит после полного закрытия P1), **`docs/RU-BYPASS.md`**. **`docs/DEPLOY.md`** §2 п.7 — указание на `site.env`. |
| 2026-05-15 | **P1-PRO-01…04 (продуктовая линия)**: **`docs/FAQ.md`** — позиционирование основного VPN vs DNS/bootstrap; **`docs/RUNBOOK-INCIDENT.md`** — внутренний инцидент-runbook + SLA ответа; **`docs/HAPP-MATRIX.md`** — матрица шаблона/URL/rollback; **`docs/POLICY-SNI-MONITORING.md`** — политика SNI-проб. Спринт-строка 10: блок PRO закрыт; остаются **P3-UX-01/02**. |
| 2026-05-15 | **P1 полностью закрыт + `docs/P1-POST-AUDIT.md` PASS (go P2 с оговорками).** Сделано в репозитории: **P1-ARCH-NODE-UNIFY** — `compose/{nl,ams}/remnanode/{docker-compose.yml,node.env}.tmpl`, digest pin **`ghcr.io/remnawave/node@sha256:9d5737…`**, **`ops/drift-check.py`** дополнен парами **`.env`**; **P1-ENG-03** — **`archive/tmp-remna-shop-bot-patches/`** (40× `tmp_*.py` из корня); **P1 AMS-decom метрика** — **`ops/count_users_with_ams_sub.py`** + интеграция в **`daily-report.sh`**, smoke sub через **`SUB_MONITOR_PROBE_URL`**; **selfsteal** — шапка-док к **`EXPECTATIONS`**; **P2-CHORE-SUB-ENV** добавлен (хардкод smoke в **`monitor.sh`**). **Критичное, не P1:** **`P0-SEC-04`/`P0-SEC-05`** остаются открытыми. **Деплой обязателен:** `daily-report.sh`, `count_users_with_ams_sub.py`, при необходимости split **`/opt/remnanode/.env`** на NL/(AMS) под новые шаблоны — иначе **`drift-check`** покажет расхождение до наката. |
| 2026-05-15 | **`python ops/drift-check.py`** повторён (`PYTHONUNBUFFERED=1`): **28** пар, **OK=13**, **problems=15**, exit **1**. Много **TIMEOUT** на батчах LV/AMS (латентность SSH/нагрузка), плюс **DRIFT**: `selfsteal-monitor.py`, `deploy-node.sh` (LV), `balancer.env`, AMS **`/opt/remnawave/docker-compose.yml`** и **`.env`**. **Репо под P0-SEC-04:** **`ops/fix-caddy-security.sh`** — chmod только для существующих путей (`remnanode`, опц. legacy/архив). **На LV:** завершить архив **`/opt/remnawave/`** → **`/opt/_archive/…`** (если **`chmod -R`** на огромном дереве «висит» — уменьшить бэкапы внутри или дождаться окончания), затем **`chattr +i`**. |
| 2026-05-15 | **P0-SEC-04 / P0-SEC-05 — процедура в репозитории:** **`docs/RUNBOOK-P0-SEC04-SEC05.md`**, скрипты **`ops/archive_lv_remnawave_legacy.sh`**, **`ops/rotate_ams_panel_core_secrets.py`**. Исполнение на LV/AMS — вручную; после успеха добавить строку **«P0-SEC-04/05 DONE»** с датой ниже. |
| 2026-05-15 | **P0-SEC-04 / P0-SEC-05 DONE (прод).** **LV:** **`/opt/remnawave/`** заархивирован в **`/opt/_archive/remnawave-legacy-*`**, **`chattr +i`** (наследие закрыто). **AMS:** фаза A — ротация JWT + Postgres **`rotate_ams_panel_core_secrets.py --apply`**, контейнер **`remnawave`** пересоздан (**`--force-recreate`**); фаза B — новый **`REMNA_API_TOKEN`** из UI → **`/opt/remna-shop/.env`**, **`/opt/remnawave/sub/.env`**, LV **`/etc/bvpn/balancer.env`** (**`PANEL_TOKEN`/`REMNA_API_TOKEN`**) и **`/etc/bvpn/ru-monitor.env`**; **`docker compose up -d`** / **`--force-recreate`** для shop и subscription-page. Супер‑админ восстановлен через **Rescue CLI** после потери входа. Добавлены вспомогательные патчи URL панели: **`FRONT_END_DOMAIN`** / **`PANEL_DOMAIN`**, Caddy **`header_up`** (журнал ops/thread). |
| 2026-05-15 | **Инцидент эксплуатации → задачи P2/P3.** **`ru-monitor.py`**: серия **`HTTP 401`** до обновления **`REMNA_API_TOKEN`** на LV; после фазы B тик **`total=16 ok=16`**. **`balancer.sh`**: до правки бил в **`localhost:3000`** → **`USERS=0 NODES=0`**; исправлено **`PANEL_URL=https://k9x2m1.conntest.xyz:2053`** + синхронизация **`balancer.sh`** с репо; проверка **`/api/users` → HTTP 200**. **`python ops/drift-check.py`**: exit **1**, **DRIFT** по нескольким файлам + **TIMEOUT** на чтении **`/etc/bvpn/*.env`** → занесено как **`P2-OPS-DRIFT-POST-P0`**, **`P2-ENG-DRIFT-CHECK-01`**. UX: **Forbidden/E000** при логине часто означает неверный пароль (**403**) → **`P3-OPS-SUPPORT-REMNA-LOGIN`**. Продукт: все ~58 пользователей на LV при живой NL — на усмотрение политики → **`P6-SCALE-NL-VERIFY`**. |
| 2026-05-15 | **Черновики P3/P4/P6 (репо):** синхрон **§4** с **§11** (**P0-SEC‑01…03**, **P0‑OPS‑01/02** — ✅ в таблице). ~~**P3‑UX‑02/03**~~: **`bot_src/user_messages.py`**, поддержка **`docs/support/USER-FACING-ERRORS.md`**, шаблон **`docs/templates/USER-INCIDENT-BROADCAST.md`**. ~~**P3‑TR‑01**~~ (внутренний черновик): **`docs/POLICY-LOGS-DATA.md`**. ~~**P4‑DNS‑02**~~: блок в **`docs/FAQ.md`**. ~~**P6‑SCALE‑NL‑VERIFY**~~ (репо): **`docs/NODE-POLICY-LV-NL.md`**. **P5‑ENG‑02** старт: **`ops/load_env_file.py`**. **Деплой бота:** скопировать обновлённый **`handlers.py`** + **`user_messages.py`** в образ **`shop_bot/bot/`** на AMS. |
| 2026-05-15 | **Хвост перед большим P6 edge / P5:** ~~**`P5-ENG-02`**~~ (репо): **`load_env_file`** читает **`export`**, подключён в **`site_urls`**, **`tests/test_load_env_file.py`**; **`user_messages`** расширен (профиль, трафик, копия sub, админ, пакеты); исправлен баг **`show_referrals`**: **`ref_text` → `text`**. **`KNOWLEDGE-BASE`** — ссылки на новые доки. |
| 2026-05-15 | **AMS бот деплой + baseline подписки (перед P6‑SCALE‑04 RL/CDN):** **`ops/deploy-bot-handlers-ams.ps1`**/`§4.3.1` — выкладка **`handlers.py`** + впервые **`user_messages.py`** (**md5 хост**: **`b18f17e9…`**, **`b505115dc…`**), **`docker restart remna-shop-bot`**. Probe **`subscription_load_probe`**: **total 60**, **concurrency 15**, **p95 ≈ 863 ms**, **59× HTTP 200** + **1× hard_error** (TLS/таймаут), **`http_200_304_rate=1.0`** по учтённым ответам. Следующий шаг оператора: включение RL/CDN по **`RUNBOOK-P6-SUBSCRIPTION-EDGE`** §§0–2. |