# Connection Health — P1/P2 REALITY probe design

**ID:** `CONNECTION-HEALTH-P1P2-001`  
**Связано:** `IP-ROTATE-NPLUS1-001` · `IP-ROTATE-DETECT-001` (stage 0) · `MONITOR-CONNECTION-HEALTH-001`  
**Дата:** 2026-06-25  
**Режим:** design only · **suspect-only** · **без auto-PATCH** · **без prod deploy**

---

## 1. Зачем (двойная польза)

| Дыра сейчас | Что даёт P1/P2 |
|-------------|----------------|
| `ru-monitor` + `check.py` видят TCP + **generic TLS** к selfsteal SNI | Не видят **REALITY/VLESS handshake fail** при живом TCP (тип B — DPI burn) |
| Нет «handshake fail до жалоб» | `reality_ok` trend + `error_class` — ранний сигнал connection health |
| IP rotation stage 0 без пробы | RU vs EU differential → `BURN_LIKELY` для **ручного** swap |

**Принцип no-log:** пробы не логируют destination пользователей, только synthetic one-shot к exit IP с vault creds; в алертах — `ep_<hash>`, не user UUID.

---

## 2. Порядок внедрения (gated)

```
G1-H1-SMOKE-001 (owner)  →  PASS
        ↓
CONNECTION-HEALTH-P1P2-001  →  repo script + LV cron (read-only)
        ↓
MONITOR-CONNECTION-HEALTH-001  →  dashboard L1–L2 panels
        ↓
IP-ROTATE stage 1 (hot-spare swap runbook)  →  отдельный owner OK
```

**Не делать до G1+H1:**

- Xray Stats / Prometheus на remnanode template
- Агрегатор docker-ошибок remnanode
- Любой PATCH panel/injectHosts из detect pipeline

---

## 3. P1 — REALITY handshake (RU vantage)

| Параметр | Значение |
|----------|----------|
| **Orchestrator** | `bvpn-lv` (как `ru-monitor.py`) |
| **Executor** | RU relay SSH — тот же хост, что `check.py` |
| **Частота** | `*/5` cron (в одном цикле с `check.py` или сразу после) |
| **Targets** | Exit IP из panel `GET /api/hosts` — `address`, `port`, inbound tag |
| **Port** | 443 (primary REALITY); опционально 8443 xhttp — отдельная метрика, не блокер v1 |
| **Input creds** | Vault-only: **synthetic probe user** (panel health inbound) **или** owner-canary shortUuid из vault — **не в git** |
| **Output** | JSON line per target: `ts`, `vantage=ru`, `ep_hash`, `tcp_ok`, `reality_ok`, `error_class`, `rtt_ms` |

### error_class (таксономия)

| Class | Интерпретация |
|-------|---------------|
| `ok` | REALITY handshake completed |
| `timeout` | TCP ok, handshake deadline |
| `reset` | RST после TCP |
| `tls_alert` | TLS/Reality alert до session |
| `refused` | TCP refused (тип A, не B) |
| `probe_error` | SSH/script failure — не считать burn |

### Реализация (будущий скрипт)

Предлагаемое имя: `ops/reality_probe.py` (runner на relay) + `ops/reality_probe_orchestrator.py` (LV).

Варианты probe engine (выбрать на impl gate):

1. **xray run -test** one-shot outbound с минимальным JSON (предпочтительно — ближе к prod path)
2. **sing-box** probe binary на relay (если уже есть)
3. Fallback: расширить `check.py` **недостаточно** — generic TLS ≠ REALITY

**Verify (staging first):**

- Симуляция: firewall drop REALITY на staging exit → `reality_ok=false`, `tcp_ok=true`, `error_class=reset|timeout`
- Prod dry-run 24h: log-only, **без TG**, сверка с `usersOnline` trends

---

## 4. P2 — Control vantage (EU)

| Параметр | Значение |
|----------|----------|
| **Vantage** | `bvpn-nl` SSH **или** LV localhost к exit IP |
| **Targets** | Те же exit IP, что P1 |
| **Частота** | `*/15` (дешевле; confirm-only) |
| **Output** | Тот же schema, `vantage=eu` |

### Differential logic

```
BURN_SUSPECT :=
  P1.tcp_ok = true
  AND P1.reality_ok = false
  AND P1.error_class IN (reset, timeout, tls_alert)
  AND fail_streak ≥ 2   # */5 → ~10 min

BURN_LIKELY :=
  BURN_SUSPECT
  AND P2.reality_ok = true   # EU control OK
  AND P2.fail_streak = 0 on same ep_hash (recent)
```

| RU | EU | Класс |
|----|-----|-------|
| FAIL | OK | **B** — DPI burn suspect |
| FAIL | FAIL | **A** — host/path down |
| OK | OK | healthy |
| OK | FAIL | probe misconfig / asymmetric route — investigate, не burn |

---

## 5. Correlator (suspect-only)

Переиспользовать anti-flap из `ru-monitor.py` / `selfsteal-monitor.py`:

| State field | Default |
|-------------|---------|
| `fail_streak` | 3 для PAGE (BURN_LIKELY) |
| `ok_streak` | 2 для RECOVERED |
| `re_alert_cooldown_sec` | 900 |

**Запрещено в pipeline:**

- `injectHosts` sync
- `latency_selector_autotrim` trigger
- Любой panel PATCH / node swap automation

**Разрешено:**

- TG **suspect** / **likely** digest
- Запись в `/var/log/bvpn-reality-probe.log`
- Публичный status JSON: `reality_probe_degraded: true` без IP plaintext

---

## 6. Алертинг

| Severity | Условие | Канал |
|----------|---------|-------|
| LOG | single P1 fail | file only |
| WARN | `BURN_SUSPECT` streak=2 | TG ops digest |
| PAGE | `BURN_LIKELY` | TG owner — «**ручной** swap по runbook» |
| RECOVERED | `ok_streak=2` | TG digest |

Шаблон (без user data):

> BURN_LIKELY · exit `ep_a1b2` · RU REALITY fail (`reset`) · EU OK · TCP ok · **auto-PATCH запрещён**

---

## 7. SLO

| Класс | Time-to-detect | Примечание |
|-------|----------------|------------|
| A — TCP down | ≤15 min | уже есть (`ru-monitor`) |
| B — DPI burn | ≤20 min | P1 @ */5, streak 2–3 |
| B — high confidence | ≤30 min | + P2 EU confirm |
| False positive budget | <1 BURN_LIKELY / month | ok_streak + cooldown |

---

## 8. Acceptance (impl gate)

| # | Done when |
|---|-----------|
| CH-P1-1 | `reality_probe.py` dry-run на staging: ok + simulated fail |
| CH-P1-2 | 24h log-only на prod LV, 0 probe_error storms |
| CH-P1-3 | Correlator классифицирует учебный B (staging firewall) |
| CH-P1-4 | Документирован vault path для probe creds (`docs/SECRETS.md` ref) |
| CH-P1-5 | Owner OK на TG PAGE template |
| CH-P2-1 | EU vantage подтверждает differential на staging |

---

## 9. Explicitly deferred (post P1/P2)

| Item | Why later |
|------|-----------|
| P3 relay path differential | После P1/P2 baseline |
| P4 app smoke через туннель | Тяжелее; owner device |
| P5 passive (`usersOnline` only) | Частично уже в `load_monitor.py` |
| Xray Stats exporter on node | remnanode template change — отдельный gate |
| Docker error aggregator | Шум + no-log review |

---

## 10. Ссылки

- Таксономия инцидентов A–F: session design `IP-ROTATE-DETECT-001` (owner `.local` copy 2026-06-24)
- Существующие пробы: `check.py`, `ru-monitor.py`, `selfsteal-monitor.py`, `tspu_block_probe_ru.py`
- Dashboard: [`CONNECTION-HEALTH-DASHBOARD-DESIGN.md`](CONNECTION-HEALTH-DASHBOARD-DESIGN.md)

**СТОП.** Код и cron — после `G1-H1-SMOKE-001` PASS + owner OK на impl gate §8.
