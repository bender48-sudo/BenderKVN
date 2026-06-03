# Phase 11 — VPN node & edge resilience

**Цель:** VPN и обновление подписки остаются рабочими, если отвалилась **нода** (LV/NL) или **LV edge** (p4n7q/k9x2m1), без ручного geo и без регрессии gen=20+ (§0 phase 8).

**Источники:** [`VPN-INCIDENT-LESSONS-2026-05-25.md`](VPN-INCIDENT-LESSONS-2026-05-25.md), [`RUNBOOK-LV-DOWN-NL-FAILOVER.md`](RUNBOOK-LV-DOWN-NL-FAILOVER.md), [`RUNBOOK-JURISDICTION-FAILOVER.md`](RUNBOOK-JURISDICTION-FAILOVER.md), [`BACKLOG-VPN-FULL-AUDIT-2026-05-28.md`](BACKLOG-VPN-FULL-AUDIT-2026-05-28.md) (**VPN-AUD-310**, **VPN-AUD-420**), инцидент «LV не оплачен → весь VPN».

**Исполнение:** только [`BACKLOG-QUEUE.md`](BACKLOG-QUEUE.md) — одна строка **`NEXT`** → verify → коммит → стоп.

**Уже в репо (не дублировать в Q167):** `ops/routing_geo_common.py` + `patch_routing_client_refresh.py` (CIDR вместо `geoip:private`, Streisand → XRAY_JSON) — на проде **2026-06**.

---

## 0. Запреты (наследие phase 8 §0 + этот эпик)

| Запрет | Причина |
|--------|---------|
| Не включать `burstObservatory` без staging | E1 closed pipe |
| Не смешивать в одном PATCH: routing + injectHosts + balancer | E8 |
| NL failover **не** заменяет живой LV edge для HTTPS `/api/sub/` | SPOF Caddy на LV |
| `--apply` NL failover только после `GATE_MULTIPATH_OK` | не ухудшить штатный прод |
| `--restore` только когда LV node `isConnected` снова true | иначе клиенты снова бьют в мёртвый LV |

---

## 1. Gate (до и после каждой Q)

### Штатный прод (LV+NL multipath)

```bash
python ops/lv_node_down_nl_failover.py --gate
# ожидаем: GATE_MULTIPATH_OK (verify_vpn_balancer_profile + probe_subscription)
```

### Режим NL-only (после Q167 apply на учениях / реальный LV down)

```bash
python ops/lv_node_down_nl_failover.py --gate --apply   # только при LV down или --force drill
python ops/verify_nl_failover_sub.py
# ожидаем: GATE_NL_FAILOVER_OK
```

### После любого prod PATCH template

```bash
python ops/smoke_ams_safe_deploy.py --skip-sub-probe
python ops/probe_subscription.py
python ops/vpn_verify_gate.py
```

Полный продукт после деплоя edge/бота — template из **phase 8 §1** (`smoke_product_backlog_static.py`, IG/TG routing).

---

## 2. Очередь фазы 11

| Q | ID | Слой | Суть |
|---|-----|------|------|
| **167** | **P2-OPS-LV-NL-FAILOVER-REPO-01** | Template | Закрепить в `main`: `lv_node_down_nl_failover.py`, runbook, `verify_nl_failover_sub`; gate в доке |
| **168** | **P2-OPS-NODE-FAILOVER-AUTO-01** | Автоматизация | Cron/ru-monitor hook: LV down → `--auto --gate --apply`; restore; TG alert; cooldown |
| **169** | **P2-RED-SUB-EDGE-JURISDICTION-01** | Edge | Второй origin подписки не на LV (NL Caddy или AMS backup URL в `site_urls`/бот) |
| **170** | **P1-PRO-SUB-DEAD-OUTBOUND-01** | Sub-page | VPN-AUD-420: не отдавать dead outbounds в sub (опционально после 169) |

**Связь с VPN audit:** Q168 ≈ **VPN-AUD-310** (server-side health → PATCH); Q170 = **VPN-AUD-420**. Relay trim уже через `latency_selector_autotrim` — не дублировать `relay_failover_template` (NO-GO gen≥47).

---

## 3. Done when / Verify (по задачам)

### Q167 — P2-OPS-LV-NL-FAILOVER-REPO-01

| | |
|--|--|
| **Done when** | Файлы `ops/lv_nl_failover_common.py`, `ops/lv_node_down_nl_failover.py`, `ops/verify_nl_failover_sub.py`, `docs/RUNBOOK-LV-DOWN-NL-FAILOVER.md`; ссылка в `docs/NODE-POLICY-LV-NL.md`; `py_compile` всех трёх скриптов |
| **Verify** | `python ops/lv_node_down_nl_failover.py --status` (LV connected); `--gate` → **GATE_MULTIPATH_OK** на проде; dry-run без `--apply` печатает план NL injectHosts |
| **Regression guard** | Не вызывать `--apply` на живом LV без `--force` (drill только по runbook) |
| **Commit** | `ops: P2-OPS-LV-NL-FAILOVER-REPO-01 — NL failover scripts + runbook` |

### Q168 — P2-OPS-NODE-FAILOVER-AUTO-01

| | |
|--|--|
| **Done when** | Скрипт/cron на AMS (или расширение ru-monitor): опрос `isConnected` LV prod; при down + NL up → `lv_node_down_nl_failover.py --auto --gate --apply`; при recovery → `--restore --gate --apply`; state file + cooldown ≥15 min; TG уведомление админу |
| **Verify** | Лог «skipped: LV up» на штатном проде; tabletop: mock LV down → один apply + `verify_nl_failover_sub` OK |
| **Regression guard** | Не apply при `GATE_MULTIPATH_OK` fail; не restore пока LV node down |
| **Commit** | `ops: P2-OPS-NODE-FAILOVER-AUTO-01 — auto LV→NL template failover` |

### Q169 — P2-RED-SUB-EDGE-JURISDICTION-01

| | |
|--|--|
| **Done when** | Публичный backup URL `/api/sub/` доступен при недоступности p4n7q (NL :8443 или AMS через VPN/DNS по `RUNBOOK-JURISDICTION-FAILOVER`); бот/portal отдают backup в FAQ или второй origin в sub URL list; drift probe оба origin |
| **Verify** | `subscription_origin_drift_probe` / curl backup → **200** + тот же payload SHA что primary (при живом AMS); drill: LV edge stop → backup sub **200** |
| **Regression guard** | Не снимать split-host :3010/:3011 на AMS |
| **Commit** | `ops: P2-RED-SUB-EDGE-JURISDICTION-01 — backup subscription edge` |

### Q170 — P1-PRO-SUB-DEAD-OUTBOUND-01

| | |
|--|--|
| **Done when** | Sub-page или pre-render фильтрует outbounds с `node.isConnected=false` (или panel hook); Happ не получает UUID мёртвой ноды |
| **Verify** | Симуляция одной ноды down → sub без её proxy; gate multipath после restore |
| **Regression guard** | Не ломать 14-relay / gen эталон без dry-run |
| **Commit** | `product: P1-PRO-SUB-DEAD-OUTBOUND-01 — filter dead node outbounds in sub` |

---

## 4. Пользовательский эффект (критерий эпика)

| Сценарий | После фазы 11 |
|----------|----------------|
| LV VPS выключен, NL жив | **Q167–168:** трафик через NL после refresh sub; **Q169:** HTTPS sub всё ещё качается |
| LV node down, edge жив | **Q167–168:** auto NL template ≤15 min MTTR |
| Relay RU down | Уже **autotrim**; не Q167 |
| Streisand routing error | Уже **CIDR private** patch |

---

*Версия: 2026-06-03. Синхронизировать с `BACKLOG-QUEUE.md` при смене NEXT.*
