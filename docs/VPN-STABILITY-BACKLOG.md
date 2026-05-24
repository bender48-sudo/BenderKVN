# VPN Stability Backlog (Q-VPN-STAB-*)

**Синтез трёх аудитов (2026-05-25):**

| Источник | Файл / канал |
|----------|----------------|
| Агент + логи владельца | [`CODERABBIT-AUDIT-PROMPT-2026-05-VPN-STABILITY.md`](CODERABBIT-AUDIT-PROMPT-2026-05-VPN-STABILITY.md) |
| Claude | [`AUDIT-2026-05-VPN-STABILITY-CLAUDE.md`](AUDIT-2026-05-VPN-STABILITY-CLAUDE.md) |
| CodeRabbit | PR review (Phase 1–3 plan) |

**Продуктовое ограничение (все аудиты):** пользователь **не** выбирает NL/LV/turbo вручную. Failover — через sub JSON + `burstObservatory` / `leastLoad`.

**Консенсус аудиторов**

| Тема | Вердикт |
|------|---------|
| «0 серверов» в Happ | UX-инцидент; `Append custom count=1` → xray жив, auto-balance внутри JSON работает |
| xhttp + Happ batch-import | **Высокая** вероятность; нужен A/B до prod PATCH |
| Удалить xhttp из шаблона навсегда | **NO-GO** — теряем TSPU-запас (Q103, `TRANSPORT-MUX-MATRIX`) |
| Предпочтительный fix | **Happ-only** выдача без xhttp; полный конфиг — v2rayN и др. |
| `194.221.250.50:443` | **Назначение** в access_log, не outbound; Claude/CodeRabbit P0 здесь **ошиблись** |
| Регрессия batch-import | Последний успех batch2 **8 апр** (count=16); **не** совпадает 1:1 с деплоем XHTTP на ноду (**18 мая**) |
| Auto-balance | **PARTIAL** — механика в xray есть; NL может быть 0% (DPI); server-side LV→NL нет |
| Infra | AMS swap=0, drift balancer/watchdog — делать параллельно |

**Порядок исполнения:** Phase 1 (диагностика, только repo) → Phase 2 (prod fix подписки) → Phase 3 (verify + infra + UX).

---

## Phase 1 — Диагностика (repo, без prod PATCH)

### Q-VPN-STAB-001 · Content-Type в probe подписки

**Источник:** CodeRabbit Phase 1.  
**Проблема:** неизвестно, отдаёт ли `/api/sub/*` корректный `Content-Type: application/json`; ошибка может маскироваться под Happ `UnknownContentType`.  
**Изменение:** в `ops/probe_subscription.py` — логировать `Content-Type`, warn если не `application/json*`.  
**Verify:**
```bash
python ops/probe_subscription.py
# вывод: Content-Type=application/json (или явный WARN)
curl -sI "$SUB_PUBLIC_ORIGIN/api/sub/<short>" -A "Happ/1.9.4 (iOS)"
```
**Результат (2026-05-25):** `application/json; charset=utf-8` — **OK**. Content-Type **не** root cause.  
**Статус:** **DONE**

---

### Q-VPN-STAB-002 · diagnose_happ_import.py

**Источник:** CodeRabbit Phase 1; Claude P0-A.  
**Проблема:** нет автоматической симуляции Happ batch-parser — спор xhttp vs Content-Type vs размер JSON не закрыт.  
**Изменение:** `ops/diagnose_happ_import.py` + `ops/subscription_fetch.py`.  
**Verify:**
```bash
python ops/diagnose_happ_import.py
python -m py_compile ops/diagnose_happ_import.py
```
**Результат:** live `batch_risk=HIGH` (2× xhttp); variant B `LOW`.  
**Статус:** **DONE**

---

### Q-VPN-STAB-003 · A/B xhttp в staging Happ

**Источник:** ревью агента (расхождение с Claude/CodeRabbit timeline).  
**Проблема:** нельзя резать xhttp в prod без доказательства.  
**Изменение:** scripted A/B в `diagnose_happ_import.py` + отчёт.  
**Verify:** [`AUDIT-2026-05-VPN-STABILITY-RESOLUTION.md`](AUDIT-2026-05-VPN-STABILITY-RESOLUTION.md)  
**Результат:** A=18 ob (2 fail xhttp), B=16 ob (0 fail) → **Q-VPN-STAB-005** justified.  
**Статус:** **DONE**

---

### Q-VPN-STAB-004 · transport_mux_audit: xhttp structures + NL breakdown

**Источник:** CodeRabbit Phase 1/3.  
**Проблема:** `parse_outbounds()` пропускает outbounds без `vnext`; нет per-node NL=0 warning.  
**Изменение:** `_outbound_endpoint()` + `servers`; node totals + xhttp INFO + NL warn.  
**Verify:**
```bash
python ops/transport_mux_audit.py
```
**Результат:** sample 5/5 NL present; xhttp=10 ob; `TRANSPORT_MUX_OK`.  
**Статус:** **DONE**

---

## Phase 2 — Fix pipeline подписки (prod)

### Q-VPN-STAB-005 · Happ-only: скрыть xhttp из выдачи

**Источник:** CodeRabbit Phase 2 (главный fix); заменяет Claude Q-VPN-STAB-001 «убрать из шаблона».  
**Проблема:** Happ batch-import падает на xhttp; полное удаление из template ломает TSPU.  
**Изменение (выбрать один путь после Q-VPN-STAB-003):**

| Вариант | Где | Плюсы / минусы |
|---------|-----|----------------|
| **A** | Panel: второй template / trim `injectHosts` для Response Rule `Happ → XRAY_JSON` | Нативно Remnawave; без форка sub-page |
| **B** | `remnawave-subscription-page` (AMS :3010/:3011): UA-filter `Happ/*` → strip xhttp outbounds | CodeRabbit plan; нужен форк/patch образа |
| **C** | Caddy на LV: `header` + sub_filter (last resort) | Хрупко на JSON |

**Целевое состояние для Happ UA:** 16 tcp outbounds (18 − 2 xhttp), `burstObservatory` + `leastLoad` на месте.  
**Verify:**
```bash
python ops/probe_subscription.py          # с Happ UA → xhttp count = 0
python ops/diagnose_happ_import.py        # batch-risk LOW
# реальный Happ: ImportResult batch2 count > 0
```
**Rollback:** restore template snapshot или отключить UA-filter.  
**Статус:** **DONE** (2026-05-25: `trim_injecthosts_no_xhttp.py --apply`, injectHosts 16→14, batch_risk LOW) · Content-Type на `/api/sub/*`

**Источник:** CodeRabbit Phase 2.  
**Проблема:** если edge отдаёт `text/plain` / без header — downstream и Happ могут падать иначе, чем на xhttp.  
**Изменение:** проверить `curl -I`; при необходимости — Caddy `header Content-Type application/json` на `/api/sub/*` или fix в sub-page.  
**Verify:**
```bash
curl -sI "https://p4n7q.conntest.xyz:8443/api/sub/<short>" -A "Happ/1.9.4 (iOS)" | grep -i content-type
python ops/probe_subscription.py
bash ops/smoke_sub_page_ha.sh
```
**Статус:** **DONE** (waived — Content-Type OK on prod)

---

### Q-VPN-STAB-007 · remnawave_api.py: content_type=None

**Источник:** CodeRabbit Phase 2.  
**Проблема:** `_fetch_json()` при нестандартном Content-Type может вернуть `None` → «panel_unreachable» в боте.  
**Изменение:** `bot_src/remnawave_api.py` — `resp.json(content_type=None)`, явный log warn/error.  
**Verify:**
```bash
python -m py_compile bot_src/remnawave_api.py
pytest tests/ -k remnawave -q
```
**Статус:** **DONE** (code)

---

### Q-VPN-STAB-008 · Push-notify после fix подписки

**Источник:** Claude Q-VPN-STAB-003.  
**Проблема:** Happ обновляет sub раз в ~24 ч; старый конфиг остаётся.  
**Изменение:** после Q-VPN-STAB-005/006 — `ops/broadcast_refresh_sub.py` или `subscription_config_notify.py` + jitter (см. Q-VPN-STAB-015).  
**Verify:** sample 5 users → Happ `count > 0` после refresh.  
**Зависит от:** Q-VPN-STAB-005  
**Статус:** **PARTIAL** — gen=2 локально; push AMS с owner PC failed (SSH). Run from AMS.

---

## Phase 3 — Verify, UX, infra

### Q-VPN-STAB-009 · UX: «0 серверов» ≠ VPN сломан

**Источник:** Claude state machine; агент.  
**Проблема:** пользователь удаляет профиль при flash «0 servers».  
**Изменение:** copy в `web/portal/content/ru.json` (help.stuck) + бот FAQ: если VPN подключён — игнорировать сообщение; не удалять «BenderVPN Auto»; дождаться 🔄 refresh.  
**Verify:** ручной проход help.stuck; нет совета «выберите NL».  
**Статус:** TODO

---

### Q-VPN-STAB-010 · Идентифицировать 194.221.250.50 (назначение)

**Источник:** логи владельца; **исправление** Claude Q-VPN-STAB-002.  
**Проблема:** 524 строки access_log к одному **destination** IP (217× proxy-6, 154× proxy-8, 143× proxy-7) — приложение retry-loop, не мёртвый outbound.  
**Изменение:**
```bash
whois 194.221.250.50
# сопоставить с приложением (Instagram/Meta/CDN?)
# проверить routing: direct vs proxy для этого IP
```
**Verify:** отчёт в audit resolution; если RU bypass — правка `ru_bypass_routing.py`; если DPI — alt/XHTTP path (Q-VPN-STAB-005).  
**Статус:** TODO

---

### Q-VPN-STAB-011 · burstObservatory tuning

**Источник:** Claude Q-VPN-STAB-004.  
**Проблема:** interval=15s, флап proxy-6/7/8; observatory может пинговать лишние outbounds.  
**Изменение:** template PATCH: `interval=30s`, `subjectSelector=["proxy"]`, `destination=https://www.gstatic.com/generate_204`. Snapshot → `.secrets/snapshots/`.  
**Verify:** access_log 30 мин — меньше flap при стабильной сессии.  
**Статус:** TODO

---

### Q-VPN-STAB-012 · P6-SCALE-NL-VERIFY

**Источник:** Claude P1-D; CodeRabbit NL checks.  
**Проблема:** access_log только proxy-6/7/8 (LV?); NL sessions 0% — баг или DPI.  
**Изменение:** панель → sessions NL; `nc -zv 91.90.192.17 9443` с RU; при блоке — Q-VPN-STAB-013.  
**Verify:** non-zero NL sessions или документированный DPI trim.  
**Статус:** TODO (SSH NL)

---

### Q-VPN-STAB-013 · Trim мёртвые RELAY→NL outbounds

**Источник:** Claude Q-VPN-STAB-005.  
**Проблема:** leastLoad крутит недоступные NL → периодические зависания.  
**Изменение:** после Q-VPN-STAB-012 — убрать UUID из injectHosts если NL:9443 недоступен.  
**Verify:** `python ops/transport_mux_audit.py` → working alt only.  
**Зависит от:** Q-VPN-STAB-012  
**Статус:** TODO

---

### Q-VPN-STAB-014 · AMS swap 2 GB

**Источник:** Claude Q-VPN-STAB-006.  
**Проблема:** RAM ~95 MiB free, swap=0 → OOM при sub stampede.  
**Verify:** `ssh bvpn-ams free -h` → swap 2G.  
**Статус:** TODO

---

### Q-VPN-STAB-015 · Jitter при mass push-notify

**Источник:** Claude Q-VPN-STAB-011.  
**Изменение:** random delay 0–300 s в `subscription_config_notify.py` / broadcast.  
**Verify:** `python ops/subscription_ha_load_probe.py` — нет 429.  
**Статус:** TODO

---

### Q-VPN-STAB-016 · Drift: balancer.sh (LV) + watchdog.sh (NL)

**Источник:** Claude Q-VPN-STAB-007/008; drift-q084.  
**Verify:** `python ops/drift-check.py` → OK.  
**Статус:** TODO

---

### Q-VPN-STAB-017 · Docs: Happ xhttp + verify loop

**Источник:** CodeRabbit Phase 3.  
**Изменение:**
- `docs/TRANSPORT-MUX-MATRIX.md` — § Happ: xhttp не в batch-import; UA-filter;
- закрыть Q103 с resolution;
- runbook verify после template PATCH:
```bash
python ops/probe_subscription.py
python ops/diagnose_happ_import.py
python ops/transport_mux_audit.py
bash ops/smoke_sub_page_ha.sh
```
**Статус:** TODO

---

### Q-VPN-STAB-018 · smoke_sub_page_ha в чеклист PATCH

**Источник:** Claude Q-VPN-STAB-014.  
**Изменение:** обязательный шаг после любого template/sub-page change в `HAPP-MATRIX.md`.  
**Статус:** TODO

---

## P2 / later (не блокируют Phase 1–2)

### Q-VPN-STAB-019 · Trial sub-template (P3-FLOW-21 prep)

**Источник:** Claude Q-VPN-STAB-009.  
Trial: LV primary ×3, без NL, без xhttp; observatory interval=60s.  
**Статус:** TODO (BLOCKED on Q062 для полного tier split)

---

### Q-VPN-STAB-020 · Recovery sub URL для TSPU (xhttp tier)

**Источник:** синтез; TSPU redteam T24-02.  
Отдельная выдача xhttp-only / xhttp-first для «не коннектит на LTE» — **бот выдаёт URL**, не ручной pick NL.  
**Статус:** TODO (после Q-VPN-STAB-005)

---

### Q-VPN-STAB-021 · AMS remnanode drain verify

**Источник:** Claude Q-VPN-STAB-016.  
**Verify:** `probe_subscription.py` → `AMS=0`.  
**Статус:** TODO

---

### Q-VPN-STAB-022 · Mass drift remediation

**Источник:** Claude Q-VPN-STAB-015.  
**Статус:** TODO

---

## Отменено / пересмотрено

| Было | Решение |
|------|---------|
| Claude **Q-VPN-STAB-001** «убрать xhttp из шаблона» | → **Q-VPN-STAB-005** Happ-only filter |
| Claude **Q-VPN-STAB-002** «194.221.250.50 = outbound» | → **Q-VPN-STAB-010** destination investigation |
| Claude **Q-VPN-STAB-013** label IP в probe | Отменено — IP не наш infra |
| CodeRabbit «Apr→May = XHTTP add» | Снято как доказанное; **Q-VPN-STAB-003** A/B |

---

## Done when (release gate)

- [ ] Happ UA: `probe_subscription` → xhttp=0, tcp outbounds ≥16
- [ ] `diagnose_happ_import.py` → batch-risk LOW
- [ ] Реальный Happ: `ImportResult(batch2 count > 0)` после auto-update
- [ ] `Content-Type: application/json` на обоих sub origins
- [ ] `transport_mux_audit.py` → `TRANSPORT_MUX_OK` + NL warning если 0
- [ ] `smoke_sub_page_ha.sh` → OK
- [ ] UX copy deployed (Q-VPN-STAB-009)
- [ ] AMS swap enabled
- [ ] 194.221.250.50 идентифицирован (Q-VPN-STAB-010)

---

## Рекомендуемый NEXT для агента

**Phase 1 — DONE** (см. [`AUDIT-2026-05-VPN-STABILITY-RESOLUTION.md`](AUDIT-2026-05-VPN-STABILITY-RESOLUTION.md)).

**Phase 2 NEXT:** **Q-VPN-STAB-008** (push-notify с AMS) → **Q-VPN-STAB-009** (UX copy).
