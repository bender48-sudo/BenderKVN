# Security + GTM audit — CodeRabbit раунд 2 (Q101)

**ID:** **P2-RED-CODERABBIT-02** (Q101).  
**Дата:** 2026-05-19  
**Связка:** [`AUDIT-2026-05-TSPU-REDTEAM-04.md`](AUDIT-2026-05-TSPU-REDTEAM-04.md) (ТСПУ раунд 3), Q063–097, Q086–097.  
**Валидация:** сверка exploration CodeRabbit с кодом в `main` (не слепое принятие).

---

## Executive summary

| Измерение | Сейчас | После Q102–116 | После Q102–122 (+ ТСПУ хвост) |
|-----------|--------|----------------|-------------------------------|
| **Security** | **5,5 / 10** | **7,5 / 10** | **8 / 10** |
| **Ops** | **6,5 / 10** | **8 / 10** | **8,5 / 10** |
| **Product** | **6,5 / 10** | **7,5 / 10** | **8 / 10** |
| **TSPU / edge** | **5 / 10** ([раунд 3](AUDIT-2026-05-TSPU-REDTEAM-04.md)) | **6 / 10** | **7,5 / 10** |

**GTM readiness:** **conditional** → **ready для ~10k** после **Q102–105 (P0)** + **Q106–109 (P1)**; **архитектура ~30k** — отдельный слой (**Q117+**, ноды/edge по §10 COMMERCIAL-BACKLOG, не только security).

**Блокеры GTM (P0):** публичные **3010/3011**, **replay bind token**, **секрет bind в `user_actions`**, **github SNI в live sub** (ТСПУ = security масштаба).

---

## Таблица находок (P0 → P3)

| ID | P | Проблема | Файл | Статус | Q |
|----|---|----------|------|--------|---|
| CR-01 | **P0** | Subscription-page **0.0.0.0:3010/3011** — обход Caddy/RL | `compose/ams/remnawave-sub/docker-compose.yml.tmpl:8,24` | **NEW** | **Q102** |
| CR-02 | **P0** | `bind_token` не сбрасывается после bind → replay `/start bind_*` | `web_trial_db.py:196-206` | **NEW** | **Q103** |
| CR-03 | **P0** | Сырой `bind_token` в `log_action` → SQLite | `handlers.py:364` | **NEW** | **Q104** |
| T24-01 | **P0** | Live sub: SNI **github/microsoft/bing** (Q058 repo-only) | panel template / sub | **NEW** | **Q105** |
| CR-04 | **P1** | **k9x2m1:8443** — `handle { reverse_proxy :3000 }` без `@blocked` | `Caddyfile-latvia-full.txt:425+` | **NEW** | **Q106** |
| CR-05 | **P1** | Amount verify **pass** если нет `amount` в metadata | `payment_amount_verify.py:35-36,56-58` | **NEW** | **Q107** |
| CR-06 | **P1** | `YOOKASSA_WEBHOOK_SKIP_API_VERIFY` обходит API verify | `auth.py:91-95` | **VERIFY** (Q071 alarm есть) | **Q108** |
| CR-07 | **P1** | `/portal-setup-resolve` отдаёт **`sub_url`** (shared secret) | `portal_browser_resolve.py:82-87` | **NEW** (≠ Q089 cabinet) | **Q109** |
| CR-08 | **P1** | **PromoCreate** FSM: message-handlers **без** `ADMIN_ID` | `handlers.py:1040+` | **REGRESSION** | **Q109b** → в **Q106** security batch или отдельно |
| CR-09 | **P2** | `SUPPORT_GROUP_ID=0` — тихий no-op support | `support_handler.py:102,159` | **NEW** | **Q110** |
| CR-10 | **P2** | Trial claim TOCTOU (check → provision) | `portal_web_trial.py:52-69` | **NEW** | **Q111** |
| CR-11 | **P2** | **lv.conntest.xyz:9443** / AMS Caddy — нет HSTS блока | Caddy templates | **NEW** | **Q112** |
| CR-12 | **P2** | `local_dt` naive в drift sync keys | `scheduler.py:72-73` | **NEW** | **Q113** |
| CR-13 | **P3** | Fallback hostnames в `config.py` | `config.py` | **NEW** | **Q114** |
| CR-14 | **P3** | Schema drift `database.py` vs `web_trial_db` | DB init | **NEW** | **Q115** |
| CR-15 | **P3** | `:2053` в compose env tmpl | `*.env.tmpl` | **NEW** | **Q116** |
| T24-03+ | **P1–P2** | MUX без XHTTP, selfsteal github, 1 relay, whitelist L3 | см. TSPU-04 | **NEW** | **Q117–121** |

---

## False positive / already fixed (не в очередь)

| Находка exploration | Почему не NEW |
|---------------------|---------------|
| Admin FSM «нет authz» (callbacks) | **Q086** — callbacks с `ADMIN_ID` на входе в promo flow |
| Cabinet `bind_url` leak | **Q089** — `portal_cabinet.py` без `sub_url` ✅ |
| HSTS/CSP на **:8443** p4n7q/k9x2m1 | **Q096** — в `Caddyfile-latvia-full.txt` ✅ |
| Public **:2054** | **Q088** — только комментарий в Caddy ✅ |
| `:2053` redirect | **Q091** — grace намеренный; sunset = ops, не security P0 |
| Webhook HMAC / idempotency | **Q067–068, Q024** ✅ |
| Panel **127.0.0.1:3000** в compose tmpl | **Q069** ✅ (но **k9x2m1 Caddy** всё ещё проксирует :3000 публично — **CR-04**) |
| Crypto POST + compare_digest | **Q067** ✅ |
| `DISCOVERY_PORT_OK` bot/FAQ | **Q090** ✅ |
| RU relay probe | **Q099** ✅ |

**VERIFY (smoke, не закрывать):** `python ops/smoke_admin_fsm_authz.py` (если есть), `YOOKASSA_WEBHOOK_SKIP_API_VERIFY` unset на AMS.

**Отдельно от Q089:** `portal_web_trial.py` отдаёт **`bind_url`** (deep link) — **by design**; риск — **CR-02/03/04**, не cabinet.

---

## Maturity scores (обоснование)

| Dimension | Score | Сильные стороны | Пробелы |
|-----------|-------|-----------------|---------|
| **Security** | **5,5** | Платежи: idempotency, HMAC; loopback panel tmpl; cabinet без sub_url | P0: 3010 public, bind replay+log; P1: sub_url resolve, amount skip |
| **Ops** | **6,5** | Digest pins, vault workflow, AMS safe-deploy, firewall script для 3010 | Compose всё ещё `0.0.0.0:3010`; AMS headers |
| **Product** | **6,5** | Trial/bind/pay flow, portal, support authz staff | Silent support; PromoCreate FSM gap; trial race |
| **TSPU** | **5** | :8443 edge, RU probe, MUX smokes | **Live github SNI**; XHTTP не в MUX; whitelist L3 |

---

## GTM readiness (один абзац)

**Conditional.** Для **~200 users** и старта GTM нельзя считать прод **ready**, пока не закрыты **Q102–105**: прямой доступ к subscription-page с интернета, повторное использование bind-токена и его хранение в логах, а также **продуктовый fingerprint** (github SNI) при целевой базе **10k**. После **Q102–109** (P0+P1 security) и деплоя — **ready для поэтапного роста до ~10k** при соблюдении **NODE-POLICY**, rate limit edge и мониторинга; **~30k** требует **инфра-слоя** (больше нод, отдельный edge/sub-shard, multi-region TSPU — **Q117–121** + §10 бэклога), не только закрытия CodeRabbit.

---

## Backlog Q102–116 (15 задач, критичное → мелкое)

| Q | ID | P | Done when | Verify |
|---|-----|---|-----------|--------|
| **102** | **P1-RED-SUB-BIND-LOOPBACK-01** | P0 | `127.0.0.1:3010/3011` в compose tmpl + redeploy AMS + `bvpn-docker-firewall.sh` | с внешки `curl http://AMS:3010` → fail |
| **103** | **P3-RED-BIND-TOKEN-INVALIDATE-01** | P0 | `mark_web_claim_bound`: `bind_token = NULL` | повтор `bind_*` → ошибка |
| **104** | **P3-RED-BIND-TOKEN-LOG-01** | P0 | `log_action`: не писать сырой token | `grep bind_ bot.db` без новых токенов |
| **105** | **P2-RED-SNI-LIVE-01** | P0 | Panel Reality → yandex; нет github в sub | `python ops/smoke_live_sub_sni.py` → **OK** |
| **106** | **P1-RED-CADDY-K9-BLOCKED-01** | P1 | `@blocked` + `respond 404` на k9x2m1:8443 как p4n7q | `curl .../api/auth` → 404 |
| **107** | **P6-RED-PAY-06b** | P1 | Нет metadata amount → **reject** webhook | smoke empty metadata → fail |
| **108** | **P6-RED-PAY-07b** | P1 | Prod: `SKIP_API_VERIFY` unset; startup fail if set | `smoke_yookassa_skip_verify_flag.py` |
| **109** | **P3-RED-PORTAL-RESOLVE-01** | P1 | `/portal-setup-resolve` без `sub_url` (или HMAC one-time) | JSON без поля / 403 |
| **110** | **P3-RED-SUP-GROUP-01** | P2 | Fail-fast если `SUPPORT_GROUP_ID=0` на проде | startup warning/critical |
| **111** | **P3-RED-TRIAL-ATOMIC-01** | P2 | Claim trial атомарно (UNIQUE / txn) | concurrent POST → один success |
| **112** | **P2-RED-EDGE-HEADERS-02** | P2 | HSTS/CSP на lv:9443 + AMS Caddy | `curl -I` |
| **113** | **P2-OPS-SCHED-01b** | P2 | naive `local_dt` → UTC aware | нет ложного drift |
| **114** | **P1-ENG-CONFIG-01** | P3 | Убрать hardcoded fallback hosts | unset env → явная ошибка |
| **115** | **P2-CHORE-DB-SCHEMA-01** | P3 | bind columns в `initialize_db()` | fresh init OK |
| **116** | **P2-OPS-ENV-8443-01** | P3 | `:2053` → `:8443` в `*.env.tmpl` | `grep :2053 compose/` только grace Caddy |

**Доп. P1 (включить в Q109 или отдельный коммит):** PromoCreate message handlers — guard `ADMIN_ID` на каждом шаге (**CR-08**).

---

## ТСПУ-хвост (Q117–121, после security P0)

| Q | ID | P |
|---|-----|---|
| 117 | **P2-RED-MUX-XHTTP-01** | P1 |
| 118 | **P2-RED-SELFSTEAL-SNI-01** | P2 |
| 119 | **P2-RED-WHITELIST-L3-01** | P2 |
| 120 | **P2-RED-TSPU-PROBE-MULTI-01** | P2 |
| 121 | **P2-RED-TLS-JA3-01** | P2 |

---

## Критерий «ready» для 10k / 30k

| Цель | Критерий |
|------|----------|
| **10k users** | Q102–109 **DONE** + live **LIVE_SUB_SNI_OK** + **TSPU_BLOCK_PROBE_RU_OK** + NODE-POLICY soft cap |
| **30k users** | выше + **Q117–121** + §10 (отдельный edge, PG/redis scale, 3+ prod nodes) — **архитектура**, не один sprint |

---

## Verify (батарея)

```bash
python ops/smoke_live_sub_sni.py          # после Q105
python ops/smoke_yookassa_skip_verify_flag.py
python ops/smoke_tspu_redteam.py
python ops/smoke_discovery_port.py
python ops/smoke_product_backlog_static.py
```
