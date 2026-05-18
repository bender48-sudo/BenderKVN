# Агент: накат на прод (Q079–Q084)

**Когда:** репо-очередь **Q063–050** = **DONE** (код и docs). Этот блок — **применить на LV/AMS** через SSH и smokes.

**Не в scope агента:** см. **`docs/MANUAL-OWNER-CHECKLIST.md`** (только владелец).

**Правило:** один **Q** → один коммит (если менялись только docs — коммит docs; деплой — §12 без лишнего кода). После каждого Q — **стоп**.

**Gate AMS:** **`docs/RUNBOOK-AMS-SAFE-DEPLOY.md`**.  
**Gate LV Caddy:** `caddy validate` → `systemctl restart caddy`.

---

## Q079 — P2-OPS-DEPLOY-BOT-SEC-01

**Что:** накатить бота AMS (security-патчи Q063–078) + env.

**Шаги**

1. Убедиться, что в **`.secrets/`** / vault есть для merge в `/opt/remna-shop/.env`:
   - `SUPPORT_STAFF_IDS` (= `ADMIN_TELEGRAM_ID` или список через запятую)
   - `PORTAL_SETUP_HMAC_SECRET`
   - `CRYPTO_WEBHOOK_SECRET` (если crypto включён)
   - **нет** `YOOKASSA_WEBHOOK_SKIP_API_VERIFY=1`
2. `pwsh -File ops/deploy-bot-handlers-ams.ps1` (и при необходимости `deploy-bot-payment-webhook-ams.ps1`, `deploy-bot-balance-model-ams.ps1` — по drift).
3. Safe-deploy restart shop-bot.
4. Smokes (с машины с SSH или на AMS):
   - `python ops/smoke_webhook_auth_ams.py`
   - `python ops/smoke_support_authz.py`
   - `python ops/smoke_autorenew_billing.py`
   - `python ops/smoke_payment_amount_verify.py`
   - `python ops/smoke_yookassa_skip_verify_flag.py`

**Verify:** маркеры **`WEBHOOK_AUTH_OK`**, **`SUPPORT_REPLY_AUTHZ_OK`**, **`AUTO_RENEW_BILLING_OK`** в выводе.

**Владелец (1 строка, не блокирует Q079):** в кабинете CryptoBot переключить webhook на **POST** — агент напомнит в §12.

---

## Q080 — P2-OPS-DEPLOY-EDGE-01

**Что:** Caddy LV — **:8443** + portal/status (репо уже с блоками).

**Шаги**

1. Синхронизировать `Caddyfile-latvia-full.txt` на LV (`/etc/caddy/Caddyfile` или runbook sync).
2. На LV: `bash ops/patch-caddy-edge-port-8443-lv.sh` (если блоков ещё нет) **или** полная замена из репо по **`RUNBOOK-P6-EDGE-PORT-MIGRATION.md`**.
3. `caddy validate --config /etc/caddy/Caddyfile` → `systemctl restart caddy`.
4. `pwsh -File ops/deploy-user-portal-lv.ps1` (portal static).
5. `python ops/smoke_sub_edge_port.py` — **без** `SUB_EDGE_PORT_SKIP_LIVE`.
6. `python ops/smoke_public_bootstrap.py`, `python ops/smoke_telegram_miniapp.py` (URL из `site_urls` / env **:8443**).

**Verify:** **`SUB_EDGE_PORT_OK`**, **`PUBLIC_BOOTSTRAP_OK`**, live **200** на `:8443/portal/`.

**Владелец:** BotFather Web App URL → **:8443** (см. чеклист) — после Q080.

---

## Q081 — P2-OPS-DEPLOY-PANEL-01

**Что:** panel **127.0.0.1:3000** на AMS (Q069 tmpl → прод).

**Шаги**

1. Safe-deploy: render `compose/ams/remnawave/docker-compose.yml.tmpl` → прод.
2. `docker compose up -d` в `/opt/remnawave`.
3. С внешней сети: `curl` к `http://168.100.11.140:3000` → **connection refused** или timeout.
4. Через Caddy **:8443** панель/прокси — **200**.

**Verify:** external :3000 fail; панель через edge OK.

---

## Q082 — P2-OPS-SSH-HYGIENE-01

**Что:** AMS `authorized_keys` — убрать дубликат `root@vinni204329`.

**Шаги**

1. `ssh bvpn-ams` → backup `authorized_keys` → удалить дубликат, оставить `bender-bvpn_ams_ed25519`.
2. `.\scripts\ssh-smoke-test.ps1` (или `ops/ssh_audit.py`).

**Verify:** **`SSH_AUDIT_OK`** / один ключ root.

---

## Q083 — P2-OPS-PROD-SMOKE-01

**Что:** батарея prod/static smokes после Q079–Q081.

**Шаги** (локально + SSH где нужно):

```powershell
python ops/smoke_product_backlog_static.py
python ops/smoke_flow_backlog_static.py
python ops/smoke_ams_safe_deploy.py
python ops/portal_bundle_audit.py
python ops/smoke_portal_setup_page.py
ssh bvpn-lv 'python3 /opt/scripts/dns_delegation_probe.py'
ssh bvpn-ams 'python3 /opt/scripts/ams_postgres_crypt_probe.py'
```

**Verify:** **`PROD_SMOKE_BATTERY_OK`** (все exit 0); §12 одна строка со списком маркеров.

---

## Q084 — P2-OPS-DRIFT-SYNC-01

**Что:** `drift-check.py` exit 0 или задокументированный waive; обновить §1 срез (users/RAM) в §12 если SSH OK.

**Шаги**

1. `python ops/drift-check.py`
2. При DRIFT — только осознанный фикс или waive в **`DRIFT-POST-P0.md`**, не «закрыть глаза».

**Verify:** drift **0** или waive в docs.

---

## После Q084

- **Повторный аудит** (CodeRabbit / ручной) — уместен.
- **GTM** — после **Q032** (владелец) + **OWNER** чеклист (BotFather, DNSSEC, видео).
