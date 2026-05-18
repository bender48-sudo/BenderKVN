# Аудит безопасности (CodeRabbit, 2026-05-18)

**Источник:** внешний repo review (6 фаз). **Валидация:** сверка с кодом и `docs/COMMERCIAL-BACKLOG.md` / `BACKLOG-QUEUE.md`.

**Очередь исполнения:** **`docs/BACKLOG-QUEUE.md`** — **Q063–Q078** (сейчас), затем **Q051–062** (продукт), затем **Q044–050** (флоу). **`NEXT=Q063`**.

---

## Сводка адекватности

| Находка CodeRabbit | Вердикт | Комментарий |
|--------------------|---------|-------------|
| Auto-renew без списания баланса | **Подтверждено Critical** | `bot_src/scheduler.py:130-145` — `provision_key` без `add_balance` |
| Любой в support group → ответ пользователю | **Подтверждено Critical** | `support_handler.py:135-150` — нет allowlist |
| Timezone expiry notify | **Подтверждено High** | `scheduler.py:83-85` — `replace(tzinfo=None)` |
| k9x2m1 без `log_skip` | **Подтверждено High** | `Caddyfile-latvia-full.txt:280+` vs `p4n7q` строки 6-7; **P1-RED-LOG-01** закрыт только для p4n7q |
| CryptoBot GET | **Подтверждено High** | `app.py:119` `methods=["GET"]` |
| XFF trust default True | **Подтверждено High** | `auth.py:43`; loopback peer OK, риск при расширении CIDR |
| Panel `0.0.0.0:3000` | **Подтверждено Medium** | `compose/ams/remnawave/docker-compose.yml.tmpl:65` |
| Amount без cross-check | **Подтверждено Medium** | `payment_queue.py:128-129` |
| SKIP_API_VERIFY без alarm | **Подтверждено Medium** | `auth.py:89` |
| Hardcoded IP | **Подтверждено Medium/Low** | `handlers.py:204`; частично покрыто **P1-ENG-01** (`site_urls.py`) |
| Setup API без RL на Caddy | **Частично** | RL есть на `setup_verify_service.py` (5/h/IP); **нет** Caddy RL на `/setup/api/*` |
| Оценка зрелости **6.5/10** | **Занижена** | Для ~60 users и закрытых P0–P2/P6 реалистичнее **~8/10**; критические баги в scheduler/support — отдельно |
| DNSSEC «закрыт в Q026» | **Уточнение** | Q026 = runbook + probe; **включение DNSSEC** — `MANUAL-OWNER-CHECKLIST` |
| Lazy token / P5-ENG-01 | **Не дублировать** | **P5-ENG-01** = HTTP-клиент **ops**; бот → **P5-ENG-03** (Q076) |

---

## Матрица → бэклог

| Severity | ID | Q | Файлы |
|----------|-----|---|--------|
| Critical | **P6-RED-PAY-03** | 063 | `scheduler.py` |
| Critical | **P3-RED-SUP-01** | 064 | `support_handler.py` |
| High | **P2-OPS-SCHED-01** | 065 | `scheduler.py` |
| High | **P1-RED-LOG-02** | 066 | `Caddyfile-latvia-full.txt`, `patch-caddy-logskip-inplace.sh` |
| High | **P6-RED-PAY-04** | 067 | `app.py`, `auth.py` (POST + `compare_digest`) |
| High | **P6-RED-PAY-05** | 068 | `auth.py`, `smoke_webhook_auth_ams.py` |
| Medium | **P1-RED-NET-01** | 069 | `docker-compose.yml.tmpl` |
| Medium | **P6-RED-PAY-06** | 070 | `payment_queue.py` |
| Medium | **P6-RED-PAY-07** | 071 | `app.py`, smoke |
| Medium | **P3-RED-SETUP-01** | 072 | Caddy k9x2m1 `/setup/api/*` |
| Medium | **P3-RED-SUP-02** | 073 | `support_handler.py` |
| Low | **P2-OPS-BACKUP-01** | 074 | `handlers.py:186` |
| Low | **P2-CHORE-SUP-01** | 075 | `support_handler.py:15` |
| Medium | **P5-ENG-03** | 076 | `remnawave_api.py` |
| Low | **P1-ENG-04** | 077 | `handlers.py`, `site_urls.py` |
| Medium | **P2-OPS-REMNA-KEY-01** | 078 | `remnawave_api.py:210` |

---

## Проверка (smoke)

| Q | Verify |
|---|--------|
| 063 | `ops/smoke_autorenew_billing.py` (новый) или ручной: auto_renew + balance=0 → нет extend |
| 064 | `ops/smoke_support_authz.py` или ручной в test group |
| 065 | unit/ручной: `days_left` при UTC expireAt |
| 066 | grep `/api/sub/` в access-log k9x2m1 после refresh |
| 067–068 | `ops/smoke_webhook_auth_ams.py` |
| 069 | `curl` AMS public IP:3000 — fail |
| 070–071 | smoke + лог mismatch |
| 072 | burst POST `/setup/api/web-trial` → 429 |

---

## Не в очереди (уже закрыто / вне scope)

- Webhook idempotency — **P6-RED-PAY-01** ✅  
- Webhook auth baseline — **P6-RED-PAY-02** ✅  
- `log_skip` p4n7q — **P1-RED-LOG-01** ✅ (хвост k9x2m1 → **P1-RED-LOG-02**)  
- Edge :8443 — **Q051** (продукт, не дублировать)  
- Возвраты — **Q032** / **P5-COM-02**
