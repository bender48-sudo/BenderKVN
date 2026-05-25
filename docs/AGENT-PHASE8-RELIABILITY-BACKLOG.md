# Phase 8 — Reliability · TSPU · Speed (единый контекст)

**Источники:** CodeRabbit 5-phase plan (2026-05), **`docs/VPN-INCIDENT-LESSONS-2026-05-25.md`**, **`docs/VPN-DIAGNOSTIC-2026-05-25.md`**, **`AUDIT-2026-05-TSPU-REDTEAM-04.md`** (TSPU **5.0/10**).

**Кредо:** надёжность → безопасность/скрытность → скорость без регрессии → простота. **Без техдолга:** каждая задача закрывается с verify и записью в §12.

**Исполнение:** только **`docs/BACKLOG-QUEUE.md`** — одна строка **`NEXT`** → коммит → стоп. Детали задачи — в таблице ниже + колонки очереди.

---

## 0. Запреты (из инцидента 2026-05-25 — обязательны для всех Q)

| Запрет | Причина |
|--------|---------|
| Не включать `burstObservatory` без dry-run + Happ `error_log` без `closed pipe` | E1 |
| Не убирать Relay из injectHosts (14 хостов gen=20) | E2–E3 |
| Не использовать `patch_restore_happ_stable` / снимки с observatory | E4 |
| Не менять routing + injectHosts + balancer в одном PATCH | E8 |
| Не откатывать routing leak-fix ради скорости | E7 — IG/TG снова не откроются |
| Не накатывать AMS compose/env в хотфиксе VPN/бота | инцидент 502/P1000 |
| Не деплоить бот без `py_compile` + grep monitor после restart | E10 |

**Эталон подписки (не ломать):** gen=20 — **`ops/patch_restore_14_relay_no_obs.py`**, 10565 B, 14 proxy, RELAY×6, no observatory.

---

## 1. Gate: проверка после каждой задачи

### Перед изменением

- Прочитать **§0** и колонку **Regression guard** задачи.
- Template/VPN: `python ops/patch_restore_14_relay_no_obs.py` (dry-run → `already on 14-relay profile`).

### После кода в репо (обязательно)

```bash
python -m py_compile bot_src/*.py bot_src/webhook_server/*.py   # затронутые файлы
python -m unittest discover -s tests -q                          # если есть тесты
```

### После деплоя бота (AMS hot-patch)

```powershell
pwsh -File ops/deploy-bot-handlers-ams.ps1   # или узкий скрипт из задачи
python ops/_verify_sub_refresh_deploy.py
ssh … "docker logs remna-shop-bot --since 10m 2>&1 | grep -E 'Monitor loop critical|NameError' || echo OK"
```

### После деплоя template / edge (только если задача трогает)

```bash
python ops/smoke_ams_safe_deploy.py --skip-sub-probe
python ops/probe_subscription.py
python ops/diagnose_happ_import.py
# RELAY present, ~10565 B, no observatory, LIVE_SUB_SNI_OK если SNI
python ops/smoke_live_sub_sni.py          # при задачах TSPU/SNI
```

### Полный продукт (после любого прод-деплоя — обязательно)

```bash
python ops/smoke_ams_safe_deploy.py
python ops/probe_subscription.py
python ops/smoke_product_backlog_static.py
python ops/transport_mux_audit.py          # если template/MUX
```

Критерий «не ухудшили»: sub **200**, 14 proxy + RELAY, IG/TG **открываются** (routing), скорость — не хуже baseline access_log (см. Q132).

---

## 2. Приоритет: от критичного к мелкому

| Приор. | Q | ID | Фаза CR | Статус очереди | Суть |
|--------|---|-----|---------|----------------|------|
| **P0** | 122 | **P2-RED-BOT-TIMEOUT-01** | CR-1 | **DONE** | HTTP timeout на все Remna API (aiohttp) |
| **P0** | 123 | **P2-RED-BOT-RETRY-01** | CR-1 | **NEXT** | Retry + backoff (502/503/504, connection) |
| **P0** | 125 | **P2-OPS-BACKUP-GLOB-01** | CR-1 | TODO | Cleanup `backup_*.tar.gz` (не `shop_bot_*.db`) |
| **P0** | 126 | **P2-RED-BOT-POOL-01** | CR-1 | TODO | Shared `ClientSession` + shutdown hook |
| **P1** | 124 | **P2-RED-BOT-JITTER-01** | CR-1 | TODO | `SUB_REFRESH_JITTER_MAX_SEC` в `config.py` + grep констант |
| **P1** | 128 | **P2-OPS-SQLITE-WAL-01** | CR-2 | TODO | WAL + `busy_timeout` в `initialize_db` |
| **P1** | 127 | **P2-OPS-SCHED-CONCURRENT-01** | CR-2 | TODO | `gather` + semaphore для poll users |
| **P1** | 129 | **P2-RED-BOT-AUTORENEW-01** | CR-2 | TODO | `days_left <= 0` (+ опц. pre-renew day 1) |
| **P1** | 132 | **P1-PRO-VPN-SPEED-01** | VPN | TODO | Direct-first balancer для IG/TG/Google (**не** откат routing) |
| **P2** | 130 | **P2-RED-MUX-XHTTP-AUDIT-01** | CR-3 | TODO | xHTTP в `transport_mux_audit.py` |
| **P2** | 131 | **P2-OPS-TRANSPORT-HEALTH-01** | CR-3 | TODO | `transport_profile_health.py` + алерт |
| **P2** | 133 | **P2-RED-BOT-EXPIRY-HOUR-01** | CR-4 | TODO | Уведомление при `hours_left <= 6` |
| **P2** | 134 | **P2-OPS-BOT-HEALTH-01** | CR-5 | TODO | `/health` panel+DB+latency |
| **P2** | 135 | **P2-OPS-SCHED-METRICS-01** | CR-5 | TODO | Метрики цикла scheduler |
| **P2** | 136 | **P2-RED-TSPU-ALERT-01** | CR-5 | TODO | TG alert из `tspu_block_probe` + cooldown |
| **P2** | 137 | **P2-OPS-SUB-LATENCY-01** | CR-5 | TODO | p50/p95 `provision_key` |
| **P3** | 138 | **P2-DOC-SNI-MIGRATION-01** | CR-3 | TODO | Runbook SNI (дополнить Q105) |
| **P3** | 139 | **P2-DOC-RU-RELAY-02-01** | CR-4 | TODO | Runbook 2-го relay (дополняет Q120) |
| **P3** | 140 | **P2-DOC-BOOTSTRAP-FALLBACK-01** | CR-4 | TODO | Runbook backup bootstrap (Q047 live) |
| **P3** | 141 | **P2-DOC-MONITORING-01** | CR-5 | TODO | `docs/MONITORING.md` |
| **OWNER** | 120 | **P2-OPS-RU-RELAY-02-VPS-01** | CR-4 | TODO | 2-й RU VPS (владелец) |

**Уже сделано (не дублировать):**

| Q | Что |
|---|-----|
| 105 | Live SNI yandex |
| 118 | Selfsteal без github |
| 113 | Scheduler TZ |
| hotfix | `SUB_REFRESH_JITTER_MAX_SEC=300` на AMS (Q124 формализует в config) |
| gen=20 | `patch_restore_14_relay_no_obs` |

---

## 3. Done when / Verify / Regression guard (по задачам)

### Q122 — P2-RED-BOT-TIMEOUT-01 (DONE)

| | |
|--|--|
| **Done when** | `REMNA_API_TIMEOUT` в `config.py`; все `ClientSession` бота (remnawave_api, scheduler) с `aiohttp.ClientTimeout(connect=5, total=30)` |
| **Verify** | `py_compile`; unit/smoke без зависания при mock timeout |
| **Regression guard** | Не менять panel URL, не трогать template |
| **Deploy** | `deploy-bot-handlers-ams.ps1` или sub-набор |
| **Commit** | `fix: P2-RED-BOT-TIMEOUT-01 — Remna API client timeouts` |

### Q123 — P2-RED-BOT-RETRY-01

| | |
|--|--|
| **Done when** | `tenacity` в зависимостях образа бота; decorator на `_fetch_json`/`_post_json`; retry только transient (connect, 502/503/504) |
| **Verify** | `py_compile`; лог `retry attempt` при симуляции 503 |
| **Regression guard** | Не retry на 401/404 |
| **Commit** | `fix: P2-RED-BOT-RETRY-01 — exponential backoff Remna API` |

### Q125 — P2-OPS-BACKUP-GLOB-01

| | |
|--|--|
| **Done when** | `scheduler.py` glob `backup_*.tar.gz`; prune >20; log при удалении |
| **Verify** | `py_compile`; dry-run на тестовой dir |
| **Regression guard** | Имена как в `create_backup_and_send` (`backup_{ts}.tar.gz`) |
| **Commit** | `fix: P2-OPS-BACKUP-GLOB-01 — prune tar.gz backups` |

### Q126 — P2-RED-BOT-POOL-01

| | |
|--|--|
| **Done when** | Module-level session pool; `close_session()` на shutdown; лимит connections |
| **Verify** | `py_compile`; monitor 1 цикл без leak warning |
| **Regression guard** | Зависит от Q122 (timeout на том же session) |
| **Commit** | `fix: P2-RED-BOT-POOL-01 — shared aiohttp session` |

### Q124 — P2-RED-BOT-JITTER-01

| | |
|--|--|
| **Done when** | Константа в `config.py`; import в `subscription_refresh.py`; grep `bot_src` на undefined config refs |
| **Verify** | `_verify_sub_refresh_deploy.py` → 300 |
| **Regression guard** | Не менять jitter semantics (300s max) |
| **Commit** | `chore: P2-RED-BOT-JITTER-01 — centralize sub refresh jitter` |

### Q128 — P2-OPS-SQLITE-WAL-01

| | |
|--|--|
| **Done when** | `PRAGMA journal_mode=WAL`; `busy_timeout=5000` в `initialize_db` |
| **Verify** | `py_compile`; backup smoke (checkpoint note в runbook если нужно) |
| **Regression guard** | Не ломать `create_backup_and_send` |
| **Commit** | `fix: P2-OPS-SQLITE-WAL-01 — WAL mode shop DB` |

### Q127 — P2-OPS-SCHED-CONCURRENT-01

| | |
|--|--|
| **Done when** | Poll users via `asyncio.gather` + `SCHEDULER_CONCURRENT_API_CALLS` (default 10); partial failure isolated |
| **Verify** | `py_compile`; log batch duration |
| **Regression guard** | После Q122–Q126; не увеличивать нагрузку на panel без timeout |
| **Commit** | `fix: P2-OPS-SCHED-CONCURRENT-01 — parallel user poll` |

### Q129 — P2-RED-BOT-AUTORENEW-01

| | |
|--|--|
| **Done when** | `days_left <= 0`; log trigger; опционально renew при `days_left == 1` + balance |
| **Verify** | `py_compile`; code review condition |
| **Commit** | `fix: P2-RED-BOT-AUTORENEW-01 — renew on expired access` |

### Q132 — P1-PRO-VPN-SPEED-01 ⚠️ продукт / template

| | |
|--|--|
| **Done when** | Новый patch (напр. `patch_balancer_direct_first_intl.py`): правила geosite IG/TG/… → balancer только на **8 Direct** outbounds; RELAY — отдельное fallback-правило **ниже**; gen+1 |
| **Verify** | `probe_subscription.py` (14 proxy, RELAY still in sub); Happ access_log: IG/TG чаще `LV:443 Direct`; **нет** `closed pipe`; пользовательский smoke «открывается + быстрее» |
| **Regression guard** | **§0 полностью**; dry-run → apply → notify; откат: `patch_restore_14_relay_no_obs.py` |
| **Commit** | `product: P1-PRO-VPN-SPEED-01 — direct-first balancer intl apps` |

### Q130 — P2-RED-MUX-XHTTP-AUDIT-01

| | |
|--|--|
| **Done when** | `transport_mux_audit.py` считает xhttp; метрики в JSON |
| **Verify** | `python ops/transport_mux_audit.py` exit 0 |
| **Regression guard** | Read-only audit |
| **Commit** | `ops: P2-RED-MUX-XHTTP-AUDIT-01 — xhttp in mux audit` |

### Q131 — P2-OPS-TRANSPORT-HEALTH-01

| | |
|--|--|
| **Done when** | `ops/transport_profile_health.py`; alert if profile 0% or >80% dominance |
| **Verify** | script exit 0 на live sub |
| **Commit** | `ops: P2-OPS-TRANSPORT-HEALTH-01 — profile distribution probe` |

### Q133–Q141

См. CodeRabbit phase 4–5; docs-only задачи без prod PATCH template.

### Q120 — OWNER

2-й RU relay VPS — **`MANUAL-OWNER-CHECKLIST.md`**; агент не блокирует Q122+.

---

## 4. Связь с CodeRabbit phases

| CodeRabbit | Q |
|------------|---|
| Phase 1 Critical Bot | Q122–Q126, Q124 |
| Phase 2 Speed/Scale | Q127–Q129, Q128 |
| Phase 3 TSPU | Q105✓ Q118✓ Q130–Q132 Q138 |
| Phase 4 Availability | Q120 OWNER Q139–Q140 Q133 |
| Phase 5 Observability | Q134–Q137 Q141 |

---

## 5. TSPU maturity path (5.0 → 7+)

1. **Q122–Q126** — бот не падает молча (reliability).
2. **Q132** — скорость intl без потери доступа.
3. **Q130–Q131** — видимость transport mix.
4. **Q120** (owner) — второй relay.
5. Не поднимать TSPU score в docs без **`smoke_live_sub_sni.py`** green.

---

*Обновлять при закрытии Q. Очередь: **`BACKLOG-QUEUE.md`** фаза 8.*
