# Runbook: отключили VPS или платёжку за день (P3-RED-JURIS-01)

**Wiki:** **`docs/JURISDICTION-FAILOVER-WIKI.md`**. Общий порядок инцидента — **`docs/RUNBOOK-INCIDENT.md`**.

Без секретов: только хосты, имена, пути. Токены — Bitwarden / vault на AMS.

---

## Общие правила

1. **Сначала классификация** (5 мин): VPN массово down vs только оплаты vs только одно DNS-имя.
2. **Не менять DNS и compose параллельно** — одно изменение → smoke → следующий шаг.
3. **AMS compose/env** — только **`docs/RUNBOOK-AMS-SAFE-DEPLOY.md`**.
4. После mitigation — **`docs/templates/USER-INCIDENT-BROADCAST.md`** + строка **§12** бэклога.

### Smoke после шагов

```powershell
cd d:\Va\projects\VPN
python ops/jurisdiction_failover_audit.py
python ops/smoke_status_channels.py
python ops/subscription_origin_drift_probe.py
```

---

## § A — отключили один VPS

### A.1 Матрица «кто упал»

| Хост | IP | SSH | Если недоступен |
|------|-----|-----|-----------------|
| **bvpn-lv** | 176.126.162.158 | `:3333`, ключ `bvpn_lv_ed25519` | Нет публичного HTTPS; подписка/панель снаружи мертвы |
| **bvpn-ams** | 168.100.11.140 | `:3344`, ключ `bvpn_ams_ed25519` | Нет панели, бота, Postgres; LV Caddy → 502 на upstream |
| **bvpn-nl** | (см. ssh config) | alias `bvpn-nl` | Часть нод offline; edge может быть жив |
| **RU relay** | 72.56.0.145 | `:3344` | RU SNI-probe / relay; VPN через NL/LV может жить |

**Проверка с админской машины:**

```powershell
ssh -o IdentitiesOnly=yes -i $env:USERPROFILE\.ssh\bvpn_lv_ed25519 -p 3333 root@176.126.162.158 "hostname; uptime"
ssh -o IdentitiesOnly=yes -i $env:USERPROFILE\.ssh\bvpn_ams_ed25519 -p 3344 root@168.100.11.140 "hostname; uptime"
```

Статус без SSH: **`python ops/smoke_status_channels.py`** и mirror **`/api/ops/status.json`**.

### A.2 LV недоступен (edge)

**Цель за 24 ч:** новый edge IP + те же FQDN или backup apex.

| Фаза | Действие |
|------|----------|
| **T+0** | Подтвердить: `curl -fsS -o NUL -w "%{http_code}" https://k9x2m1.conntest.xyz:2053/` с внешней сети → не 200. NL-ноды: **`python ops/panel_api.py nodes`**. |
| **T+1 ч** | Заказать **новый VPS** в **другой** стране/ASN (не тот же дата-центр, что старый LV). Минимум: Ubuntu, 2 vCPU, Caddy, открыты **2053/tcp**. |
| **T+2–4 ч** | Восстановить Caddy из **`Caddyfile-latvia-full.txt`** / последний бэкап с LV (если доступен snapshot). Секреты TLS — из Bitwarden, не из git. |
| **T+4–6 ч** | **DNS:** в Dynadot обновить A **`k9x2m1`** и **`p4n7q`** → новый IP (TTL учесть до 1 ч). Альтернатива: переключение на **backup apex** — **`RUNBOOK-DNS-RED-TEAM` §3**, **`dns_critical_inventory.json`**. |
| **T+6–12 ч** | Smoke: **`subscription_origin_drift_probe`**, **`monitor.sh`** на новом хосте, **`p0-audit.sh`**. Alternate origin — **`RUNBOOK-P6-SUBSCRIPTION-MULTI-ORIGIN`**. Пользователям — «обновите подписку» (**`FAQ.md`**). |
| **T+24 ч** | Постмортем: нужен ли постоянный второй edge (active/passive). |

**AMS жив, LV мёртв:** пользователи с **уже выданным** конфигом на NL могут работать; **новые** подписки и панель — нет, пока не восстановлен edge.

### A.3 AMS недоступен (control plane)

**Цель за 24 ч:** восстановить панель+shop+PG **на том же IP** (провайдер) или **restore на новый AMS** из бэкапа.

| Фаза | Действие |
|------|----------|
| **T+0** | LV: `curl -fsS -o NUL -w "%{http_code}" http://168.100.11.140:3000/api/health` (с LV) или с админки. Проверить **LUKS**: после reboot Postgres не поднимется без **`ams_postgres_luks_unlock.sh`** — **`POSTGRES-ENCRYPTION-AMS`**. |
| **T+1 ч** | Если хостинг заблокировал — **новый VPS**, не в той же юрисдикции, что заблокированный. |
| **T+2–8 ч** | Restore: **`RUNBOOK-BACKUP-REMNAWAVE`** (последний `pg_dump` на LV **`/var/backups/remnawave/`**). Compose из репо + vault: **`RUNBOOK-AMS-SAFE-DEPLOY`**. |
| **T+8–12 ч** | **`REMNA_API_TOKEN`** shop/sub и LV balancer — **`RUNBOOK-REMNA-API-TOKEN`**. Sub-page **без** inline JWT. |
| **T+12–24 ч** | **`drift-check.py`**, **`smoke_webhook_auth_ams.py`** (если трогали shop), **`pg_remnawave_audit.py`**. |

**LV жив, AMS мёртв:** VPN на нодах может работать; **продления, бот, панель** — down.

### A.4 NL недоступен

Меньший blast radius: **`balancer.sh`** / панель — скрыть или снять NL target; уведомить пользователей на NL-only маршрутах. Подробнее **`NODE-POLICY-LV-NL`**. Edge и AMS не трогать, если они живы.

---

## § B — отключили платёжку / платёжное агентство

**Симптом:** VPN и подписка **200**, пополнение в боте падает, webhook 4xx/5xx или тишина в ЛК PSP.

### B.1 Немедленно (T+0 — 1 ч)

| Шаг | Действие |
|-----|----------|
| 1 | Подтвердить: **`python ops/smoke_payments_live_ams.py`** (осторожно: может создавать тестовые сущности — только по runbook commerce). |
| 2 | Логи бота на AMS: `docker logs remna-shop --tail 200` (имя контейнера уточнить на хосте). |
| 3 | Webhook path только через reverse proxy: **`WEBHOOK_BIND_HOST=127.0.0.1`** — **`smoke_webhook_auth_ams.py`**. |
| 4 | Шаблон пользователю: «оплата временно недоступна, VPN работает, продление вручную по поддержке». |

### B.2 YooKassa недоступна / аккаунт заморожен

| Шаг | Действие |
|-----|----------|
| 1 | В боте **отключить** кнопку YooKassa (feature flag / `.env` — по **`RUNBOOK-COMMERCE-GO-LIVE`**), оставить **Stars** и/или **crypto**, если договор позволяет. |
| 2 | Ручное продление: админ-команды бота / панель **`expireAt`** (см. smoke monetize). |
| 3 | Новый мерчант / новый `YOOKASSA_*` в **`/opt/remna-shop/.env`** → restart; webhook URL в ЛК YooKassa обновить. |
| 4 | Проверить **idempotency**: повтор webhook не дублирует баланс — **`WEBHOOK_PAY_IDEMPOTENCY_OK`**. |

### B.3 Telegram Stars / crypto

| Канал | Действие при блокировке |
|-------|-------------------------|
| **Stars** | Зависит от Bot API; при региональной блокировке TG — опора на **YooKassa/crypto** + зеркало статуса |
| **Crypto** | Проверить **`CRYPTO_WEBHOOK_SECRET`** в `.env`; см. **`SECRETS.md`** |

### B.4 Коммуникация и compliance

- Юридические URL в боте — **`P2-COM-MONETIZE-03`** (не менять в панике).
- Не логировать полные webhook-тела — **`DATA-MINIMIZATION-POLICY`**.

---

## § C — комбинированный сценарий (DNS + VPS)

1. Считать **DNS компрометированным**, если регистратор скомпрометирован — смена пароля + 2FA + recovery из **офлайн** (**`RUNBOOK-DNS-RED-TEAM` §4**).
2. Параллельно поднять edge на **новом IP** (§ A.2).
3. Не возвращать старый IP без проверки делегирования: **`python ops/dns_delegation_probe.py`** на LV.

---

## Критерии «день закрыт»

- [ ] VPN: большинство активных пользователей **connected** на нодах (выборка **`probe_routing.py`**).
- [ ] Подписка: **≥1 origin** → 200/304, drift probe OK.
- [ ] Панель или согласованный режим «только поддержка вручную».
- [ ] Платежи: явное сообщение в боте + хотя бы один **альтернативный** канал или ручное продление.
- [ ] **`jurisdiction_failover_audit.py`** → **`JURIS_FAILOVER_OK`**
- [ ] Запись в **§12** + назначена дата следующего tabletop.
