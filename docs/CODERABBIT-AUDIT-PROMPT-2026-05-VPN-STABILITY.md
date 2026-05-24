# CodeRabbit + Claude — аудит стабильности VPN / Happ / балансировка (2026-05)

**Когда:** после жалоб владельца: «VPN включён, но не работает», Instagram/медиа отваливается, страница подписки сначала ошибка → потом ок.  
**Цель:** не UX бота, а **продуктовая стабильность VPN**: подписка → Happ → Xray → LV/NL, **без ручного выбора ноды пользователем**.

**Критическое продуктовое ограничение (не обсуждается):**

> Пользователь **не должен** вручную выбирать NL/LV/turbo в Happ.  
> Переключение между нодами — **наша** ответственность: шаблон подписки, `injectHosts`, `burstObservatory`, `leastLoad`, health/failover в конфиге клиента.  
> Советы вида «выберите NL вручную» — **не приемлемы** как финальное решение.

---

## Контекст (уже найдено агентом — проверить, расширить, опровергнуть)

### Логи пользователя (Windows/Happ, 2026-05-24)

**`access_log.txt`** (~41 мин, локальный SOCKS 127.0.0.1 → Xray):

| Метрика | Значение |
|---------|----------|
| Строк | 1256 |
| Маршруты | `proxy-6` 435, `proxy-8` 327, `proxy-7` 244, **`direct` 250 (~20%)** |
| Явных reject/fail/timeout | **0** |
| Повторы к `194.221.250.50:443` | **524** (похоже на retry-loop) |
| Переключение outbounds | `proxy-7` появляется с ~20:26:13 (flap между proxy-6/7/8) |

**`subscription_log.txt`** (Happ, импорт подписки):

| Паттерн | Частота | Интерпретация |
|---------|---------|---------------|
| `Server response: 200` ~11560 bytes | стабильно | Edge отдаёт тело |
| `ImportResult(count=0, lastParseError=UnknownContentType)` | **1054×** | Happ не парсит batch |
| `*** Subscription BenderVPN with 0 servers: ***` | **537×** | UI «0 серверов» → «ошибка» |
| `Append custom … count=1` | после сбоев | Остаётся **1** профиль |
| `502` / `429` | 1 / 1 | Редкие сбои sub-page |

**Регрессия по датам в том же логе:**

- **Apr 05:** batch 2 → `ImportResult(count=4)` — 4 сервера в Happ.
- **May 24:** оба batch → `count=0`; только **Append custom count=1**.

### Live probe с прода (2026-05-24, `python ops/probe_subscription.py`)

```
Happ GET HTTP 200, 11562 bytes
remarks: '🚀 BenderVPN Auto'
outbounds: 18
  LV:443 ×4, LV:8443 ×1, RELAY→LV ×3  → summary LV=8
  NL:443 ×4, NL:8443 ×1, RELAY→NL ×3  → summary NL=8
transport: vless/tcp (14) + vless/xhttp (2)
routing: 5 rules, 3× outboundTag=direct (RU bypass)
burstObservatory: present in JSON
```

**Вывод агента:** сервер отдаёт полный конфиг (18 outbounds, LV/NL паритет), но Happ в логах **часто применяет только 1 custom-профиль** после `UnknownContentType` → клиентский auto-balance **ломается**.

### AMS host (SSH snapshot)

- RAM 1.9 GiB, **~95 MiB free**, **swap 0**, load низкий.
- LV node SSH с рабочей машины владельца — **timeout** (метрики LV/NL не подтверждены).

### Архитектура (документация репо)

- Один Virtual Host «BenderVPN Auto» + **`injectHosts`** (16 UUID) → many outbounds под одним профилем.
- **`burstObservatory`** ping ~15s + **`Super_Balancer` / `leastLoad`** — выбор лучшего outbound **на клиенте**.
- **`balancer.sh`** — только **мониторинг** capacity/CPU + TG-алерты, **не** переключает пользователей.
- Политика нод: **`docs/NODE-POLICY-LV-NL.md`**, матрица: **`docs/HAPP-MATRIX.md`**, mux: **`docs/TRANSPORT-MUX-MATRIX.md`**.

---

## Промпт (скопировать в CodeRabbit PR / Claude)

```
Repo: BenderVPN — commercial VPN (~60 users). Stack: Remnawave panel (AMS), remnanode LV+NL,
subscription-page (AMS :3010/:3011), Caddy edge (LV), Happ client (full Xray JSON in sub).

LANGUAGE: Review in Russian. Quote RU user-facing strings where relevant.

MUST READ FIRST (validate / extend / disagree):
- docs/CODERABBIT-AUDIT-PROMPT-2026-05-VPN-STABILITY.md (this file — evidence tables)
- docs/HAPP-MATRIX.md, docs/NODE-POLICY-LV-NL.md, docs/TRANSPORT-MUX-MATRIX.md
- docs/RU-BYPASS.md, docs/RUNBOOK-P6-SUBSCRIPTION-HA.md
- BenderVPN_Documentation_v2_5.md § injectHosts, burstObservatory, leastLoad
- balancer.sh (monitor-only, NOT client failover control)

PRODUCT CONSTRAINT (hard):
Users MUST NOT manually pick NL/LV/turbo in Happ. Node selection and failover MUST be
achieved via subscription template + client-side balancers we ship in the sub JSON.
Reject recommendations that end with "user should select NL manually".

EVIDENCE SUMMARY (from owner logs + live probe — verify against code):
1) Happ subscription import: UnknownContentType → count=0 → UI "0 servers" → Append custom count=1
2) Live sub JSON has 18 outbounds (LV=8, NL=8) but Happ may only load 1 profile
3) access_log: ~20% traffic direct (RU bypass); proxy-6/7/8 flapping; 524 retries to 194.221.250.50:443
4) Apr→May regression: batch import count=4 → count=0 in Happ logs
5) AMS RAM tight (95MB free, no swap); LV metrics unverified

PRIMARY FILES (subscription / balance / ops):
- ops/probe_subscription.py, ops/probe_users_subs.py, ops/transport_mux_audit.py
- ops/capacity_snapshot.py, ops/subscription_ha_load_probe.py, ops/subscription_load_probe.py
- ops/add_injecthosts.py, ops/freeze_ams_node.py, ops/ru_bypass_routing.py
- ops/panel_api.py, ops/check_balancer.py, ops/inject_by_node.py
- balancer.sh, ops/deploy-sub-page-ha-ams.ps1, ops/patch-caddy-sub-split-host-lv.sh
- bot_src/subscription_refresh.py, bot_src/subscription_resolve.py (if sub notify/bump)
- docs/PRODUCT-TIER-PROFILES.md (turbo / wl-* tiers)
- web/portal/content/ru.json tier_profiles (user sees turbo/wl — but must NOT pick manually)

SCOPE — VPN STABILITY / HAPP / AUTO-BALANCE:

1) SUBSCRIPTION → HAPP PIPELINE
   - Why UnknownContentType on every batch import while HTTP 200 and JSON valid?
   - Is vless/xhttp (proxy-5) breaking Happ batch parser?
   - Is multi-part / mixed Content-Type subscription response expected by Happ?
   - Why Append custom count=1 vs 18 outbounds in probe_subscription?
   - Map: subscription-page code path → response headers/body → Happ import stages
   - Fix options that preserve auto-balance (no manual node pick)

2) CLIENT AUTO-BALANCE (we "manage Happ" only via sub JSON)
   - burstObservatory + leastLoad: correct config for LV/NL parity?
   - Can observatory trap all traffic on LV when NL healthier? (P6-SCALE-NL-VERIFY)
   - Does flap proxy-6/7/8 explain "VPN on but dead"? Tuning: interval, subjectSelector, strategy
   - Should we reduce injectHosts count for stability vs 16-outbound matrix?
   - Trial users: P3-FLOW-21 "single outbound" vs full matrix — impact on stability

3) ROUTING / SPLIT TUNNEL
   - RU bypass direct rules: can Instagram/Meta/CDN accidentally match direct or block?
   - ~20% direct in access_log: expected vs bug for international apps?
   - geoip:ru + geosite:category-ru side effects on non-RU apps

4) INFRA / OVERLOAD (LV "перегружена"?)
   - Is balancer.sh sufficient or do we need active template-side deprioritization of LV?
   - AMS RAM no swap + dual sub-page — stampede risk vs 502/429 in logs
   - Subscription HA split-host (p4n7q/k9x2m1) — client refresh behavior
   - What server-side actions exist today to shift load LV→NL WITHOUT user action?

5) "PAGE ERROR THEN OK"
   - Separate: web /setup/ / portal vs Happ sub refresh
   - Correlate subscription_log "0 servers" flash with user-visible errors
   - sub_config_generation notify flow — does refresh help or hurt?

6) RETRY STORM 194.221.250.50:443
   - Hypothesis: broken outbound / app retry — what should logs show on node?
   - Recommend observability (which IP is LV/NL/relay)

DELIVERABLES:

| Section | Content |
|---------|---------|
| Root cause hypotheses | Ranked P0/P1 with evidence from logs + code |
| Happ compatibility | Table: feature (xhttp, burstObservatory, injectHosts count, JSON size) → Happ support → risk |
| Auto-balance verdict | Does current template ACTUALLY auto-shift LV↔NL? Yes/No/Partial + why |
| Gap vs product constraint | List anything forcing manual node pick today |
| Fix plan | Max 15 items Q-VPN-STAB-001… each: change (template/ops/code) + verify command + rollback |
| False positives | What is working (probe 18 outbounds, HA split-host, RU bypass intent) |
| NO-GO | Recommendations that violate "no manual NL pick" |

VERIFY COMMANDS (agent already has):
  python ops/probe_subscription.py
  python ops/transport_mux_audit.py
  python ops/capacity_snapshot.py
  python ops/subscription_ha_load_probe.py
  bash ops/smoke_sub_page_ha.sh

Constraints:
- No vault/secrets in output
- No "user picks NL" as final fix
- Prefer template/ops changes over Happ UI instructions
- Be harsh on UnknownContentType + count=0 flash + single-profile fallback
```

---

## Отдельный блок для Claude (extended thinking)

Claude: используй тот же промпт выше, плюс:

1. **Смоделируй state machine** Happ import: HTTP 200 → batch1 UnknownContentType → 0 servers UI → Append custom → 1 server → leastLoad flaps between proxy-6/7/8. Где единая точка фикса?
2. **Предложи целевой sub-template** для trial vs paid (outbound count, observatory on/off, xhttp yes/no) с обоснованием.
3. **Если нельзя управлять Happ напрямую** — перечисли **все** рычаги, которые у нас есть (PATCH template, bump generation + push notify, disable host in panel, injectHosts trim, routing rules), и чего **нет**.
4. Сверь с **`docs/AUDIT-CLIENT-UX-2026-05.md` § P3-FLOW-21** (скрыть turbo/wl для trial).

---

## Как запустить

### CodeRabbit

1. PR (ветка `audit/vpn-stability-2026-05` или текущая) → описание PR = промпт + ссылка на этот файл.
2. Review type: **product / infra** (не security-only).
3. Приложить **без секретов**: выдержки из `access_log.txt` / `subscription_log.txt` (первые 50 строк + статистика из § выше).

### Claude

1. Project / chat → вставить промпт + приложить два log-файла.
2. Попросить deliverables-таблицу и draft `Q-VPN-STAB-*` backlog.

---

## После ответа ревьюеров

1. Сохранить сырой вывод:
   - CodeRabbit → `docs/AUDIT-2026-05-VPN-STABILITY-CODERABBIT.md`
   - Claude → `docs/AUDIT-2026-05-VPN-STABILITY-CLAUDE.md`
2. Свести в один backlog: `docs/VPN-STABILITY-BACKLOG.md` (Q-VPN-STAB-001…).
3. Приоритет P0: Anything where Happ loads **1 profile** instead of full auto-balance matrix.
4. Verify loop: `probe_subscription` → staging Happ import → `transport_mux_audit` → optional load probe.

**Не закрывать** задачу словами «выберите NL» — только автоматические механизмы в sub/ops.
