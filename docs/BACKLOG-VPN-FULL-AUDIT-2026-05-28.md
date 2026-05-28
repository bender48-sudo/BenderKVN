# Полный бэклог VPN — аудит Claude 2026-05-28 + синтез

**Назначение:** единый список **всех** задач (немедленно → долгосрок), включая задачи **владельца**.  
**Источники:** [`AUDIT-2026-05-28-VPN-FULL-CLAUDE.md`](AUDIT-2026-05-28-VPN-FULL-CLAUDE.md), [`AUDIT-2026-05-VPN-STABILITY-CLAUDE.md`](AUDIT-2026-05-VPN-STABILITY-CLAUDE.md), [`AUDIT-2026-05-27-INSTAGRAM-RELAY.md`](AUDIT-2026-05-27-INSTAGRAM-RELAY.md), [`VPN-STABILITY-BACKLOG.md`](VPN-STABILITY-BACKLOG.md), [`AUDIT-2026-05-28-CLAUDE-RECONCILIATION.md`](AUDIT-2026-05-28-CLAUDE-RECONCILIATION.md).

**Продуктовое ограничение:** пользователь **не** выбирает NL/LV/turbo вручную — только auto balance + routing.

**Линейная очередь агента (один Q → commit):** по-прежнему [`BACKLOG-QUEUE.md`](BACKLOG-QUEUE.md). Этот файл — **полная карта**; для «отработать всё» идти по **Phase 1 → 4** сверху вниз, не пропуская **Verify gate**.

---

## Verify gate (обязателен после КАЖДОЙ правки агента)

Без **exit 0** на gate — **не** считать задачу закрытой, **не** коммитить.

```bash
python ops/verify_vpn_balancer_profile.py    # VPN_BALANCER_PROFILE_OK
python ops/probe_subscription.py
python ops/diagnose_happ_import.py           # batch_risk=LOW, xhttp=0
python ops/transport_mux_audit.py
bash ops/smoke_sub_page_ha.sh
python ops/smoke_ams_safe_deploy.py --skip-sub-probe
python ops/drift-check.py                    # целевой: problems → 0 или documented waive
```

**Ручной smoke (владелец / РФ):** Happ → обновить подписку → Instagram + Telegram 5 мин без «то грузит / то нет».

---

## Адекватность аудита Claude 28.05 (что принять / что отбросить)

| Тезис аудита | Вердикт | Действие |
|--------------|---------|----------|
| Catch-all только proxy-5..7 (SPOF) | **Устарело** | Закрыто gen=26; не повторять |
| ru-monitor.env MISSING | **Ложно** | Закрыть drift tmpl hash; не переустанавливать вслепую |
| balancer/watchdog MISSING | **Ложно** | drift-check OK |
| AMS swap=0 | **Ложно** | Проверять периодически `free -h` |
| 194.221.250.50 = broken outbound | **Ложно** | Q-VPN-STAB-010 DONE — destination Meta/CDN |
| Удалить xhttp из template навсегда | **NO-GO** | Happ-only trim; TSPU запас — Q-VPN-STAB-020 |
| Включить burstObservatory с hicloud | **Риск** | closed-pipe; server-side health вместо |
| «33% на relay» при random | **Устарело** | ~9% при 11 paths |
| regexp.ru слишком широкий | **Верно** | VPN-AUD-210, осторожный патч |
| Второй relay IP | **Верно** | Q120 + VPN-AUD-301 |
| fragment per-ISP | **Верно** | VPN-AUD-320, долгосрок |
| DNS leak 1.1.1.1 | **Верно** | VPN-AUD-230 |
| bufferSize 64 | **Верно** | VPN-AUD-120, низкий риск |
| Happ 11 имён proxy-N | **Верно** | VPN-AUD-140 remarks |
| Один шаблон trial=paid | **Верно** | VPN-AUD-410 |
| drift 25 missing | **Устарело** | VPN-AUD-150 — актуальный drift-check |

---

## Phase 0 — Закрыто (не открывать повторно)

| ID | Задача | Доказательство |
|----|--------|----------------|
| VPN-AUD-000 | Intl + Super multipath 11 paths | gen=26, `82a9808`, `VPN_BALANCER_PROFILE_OK` |
| VPN-AUD-001 | ru-monitor anti-flap TG | `d38a77e`, deploy LV |
| VPN-AUD-002 | xhttp trim Happ path | Q-VPN-STAB-005 DONE |
| VPN-AUD-003 | policy 30/30 live | verify + template |
| VPN-AUD-004 | AMS 2G swap | `swapon` на AMS |
| VPN-AUD-005 | split Intl_Direct / Super rules | routing R1/R2 + catch-all |
| VPN-AUD-006 | 194.221.250.50 investigation | Q-VPN-STAB-010 |
| VPN-AUD-007 | AMS=0 в sub | probe_subscription |
| VPN-AUD-008 | NL node reachable :9443 | Q-VPN-STAB-012 |
| VPN-AUD-009 | balancer.sh + watchdog на проде | drift-check OK |
| VPN-AUD-010 | PANEL_URL / REMNA 8443 LV | SSH env |
| VPN-AUD-011 | Instagram relay-only Intl | gen=25 → 26 |

---

## Phase 1 — Немедленно (агент, 1–3 дня)

| ID | P | Исполнитель | Задача | Done when | Verify |
|----|---|-------------|--------|-----------|--------|
| **VPN-AUD-101** | P0 | Агент | **`ops/vpn_verify_gate.sh`** — один скрипт = весь gate | exit 0 печатает `VPN_VERIFY_GATE_OK` | все подкоманды в gate |
| **VPN-AUD-102** | P0 | Агент | **Broadcast / notify gen≥26** всем ACTIVE (обновить sub) | `broadcast_refresh_sub.py --apply` или bump+notify; sample 5 users gen | бот лог; sub bytes изменились |
| **VPN-AUD-103** | P0 | Владелец | **Ручной smoke РФ:** IG/TG/общий веб 10 мин после refresh | Нет «то грузит то нет» | отчёт в §12 или Telegram владельцу |
| **VPN-AUD-110** | P1 | Агент | **bufferSize** 64→128 в template policy | PATCH template + gen+1 | gate; нет роста disconnect на video |
| **VPN-AUD-111** | P1 | Агент | **connIdle/handshake** audit — не ухудшать latency | dry-run diff policy | gate |
| **VPN-AUD-120** | P1 | Агент | **Meta/TG IP CIDR refresh** (R1 rule) | скрипт + patch template | iOS background TG probe |
| **VPN-AUD-121** | P1 | Агент | **OpenAI + Google IP-CIDR** в R1 (iOS) | domains + cidr в template | gate |
| **VPN-AUD-130** | P1 | Агент | **Happ remarks** в injectHosts (человекочитаемые) | `patch_subscription_custom_remarks.py` | diagnose import OK |
| **VPN-AUD-140** | P1 | Агент | **docker events → TG** (die/oom remnanode/panel) | cron LV или AMS | тест `docker kill` staging |
| **VPN-AUD-150** | P1 | Агент | **Drift 8→0** или waive doc: compose adguard, panel.env, shop, ru-monitor tmpl | drift-check + RUNBOOK | 28/28 OK или список waive |
| **VPN-AUD-151** | P1 | Агент | **Синхрон ru-monitor.env** с tmpl (без смены токена) | render + diff; только REMNA_API_URL/comments | ru-monitor цикл OK |
| **VPN-AUD-160** | P2 | Агент | **Disable isHidden** relay-NL hosts в панели (proxy-12..14) если 0% 30d | panel API / freeze | probe: меньше мёртвых UUID в sub |

---

## Phase 2 — Краткосрочно (неделя 1–2)

| ID | P | Исполнитель | Задача | Done when | Verify |
|----|---|-------------|--------|-----------|--------|
| **VPN-AUD-201** | P0 | Владелец+агент | **Q120 — второй RU relay VPS** | Новый IP; inbound в панели; injectHosts | ru-monitor 2 targets; multipath 12+ paths |
| **VPN-AUD-202** | P1 | Агент | **Relay failover v1:** при ru-monitor N fail — **временно** убрать proxy-5..7 из selector (скрипт, не ручной) | `ops/relay_failover_template.py` dry-run | staging only → then prod |
| **VPN-AUD-210** | P1 | Агент | **regexp.ru → geosite:ru** без поломки TG/IG | A/B на копии template; leak-fix regression | access_log RU apps via proxy |
| **VPN-AUD-220** | P1 | Агент | **NL relay :443** inbound (не только :9443) | panel host + node | NL sessions >0% 7d |
| **VPN-AUD-230** | P1 | Агент | **DNS:** DoH/ split для intl domains в template | dns object PATCH | dns leak probe script |
| **VPN-AUD-240** | P1 | Агент | **subscription_load_probe** baseline p95 после gen=26 | журнал §12 | p95 < 2s @ 120 rps |
| **VPN-AUD-250** | P2 | Агент | **transport_mux_audit:** xhttp в отчёте (Q103) | code | audit script |
| **VPN-AUD-260** | P2 | Агент | **singbox.generator mount** test при следующем image bump | checklist в RUNBOOK-AMS | sub 200 post-upgrade |

---

## Phase 3 — Среднесрок (2–4 недели)

| ID | P | Исполнитель | Задача | Done when | Verify |
|----|---|-------------|--------|-----------|--------|
| **VPN-AUD-301** | P0 | Владелец | **Второй LV IP** (или второй DC) для 4 Direct | 2 IP в injectHosts | ТСПУ block одного IP не убивает все Direct |
| **VPN-AUD-310** | P1 | Агент | **Server-side health:** ru-monitor → PATCH selector (LV+NL only) при relay down | автоматизация + cooldown | MTTR < 15 min без ручного patch |
| **VPN-AUD-320** | P1 | Агент | **Fragment per-ISP** шаблоны (МТС/Билайн on, default off) | 2 template profiles или Response Rule | probe с РФ SIM |
| **VPN-AUD-330** | P1 | Агент | **gRPC inbound** (v2rayN / advanced; не Happ batch) | 1 inbound LV | v2rayN connect |
| **VPN-AUD-340** | P1 | Агент | **Redis use-case audit** — AOF если payment rate-limit | doc + optional AOF | restart redis no bypass |
| **VPN-AUD-350** | P2 | Агент | **PG на отдельный хост** / RAM AMS +2G | architecture doc + migrate plan | OOM test sub stampede |
| **VPN-AUD-360** | P2 | Агент | **shortId rotation** policy | panel inbounds | doc |
| **VPN-AUD-370** | P2 | Агент | **Q-VPN-STAB-020** recovery xhttp URL для TSPU (бот выдаёт alt sub) | bot command + template | TSPU probe OK |

---

## Phase 4 — Долгосрок (1–2 месяца)

| ID | P | Исполнитель | Задача | Done when | Verify |
|----|---|-------------|--------|-----------|--------|
| **VPN-AUD-401** | P2 | Агент | **CDN-fronted fallback** при блокировке IP | design + PoC | — |
| **VPN-AUD-410** | P2 | Агент | **Trial sub-template** (Q-VPN-STAB-019; blocked on Q062 partial) | отдельный template UUID | trial user count=3 import |
| **VPN-AUD-420** | P2 | Агент | **Server-side sub filter** — не отдавать dead outbounds | sub-page patch | Happ never sees dead UUID |
| **VPN-AUD-430** | P2 | Агент | **leastLoad + observatory** только с gstatic probe + A/B на Happ | staging | no closed-pipe |
| **VPN-AUD-440** | P3 | Продукт | **Native app** (P5-PROD-NATIVE-APP-01) | — | — |
| **VPN-AUD-450** | P2 | Агент | **.secrets/** hygiene — example only in git | policy + gitignore | no tokens in git |
| **VPN-AUD-460** | P2 | Агент | **Credential broker** везде (не plaintext panel-token) | all ops scripts | rotation runbook |

---

## Задачи владельца (не блокируют агента, но критичны)

| ID | P | Задача | Done when |
|----|---|--------|-----------|
| **O-VPN-001** | P0 | **Q120:** аренда 2-го RU VPS (другой DC/AS) | IP + root SSH для агента |
| **O-VPN-002** | P0 | **VPN-AUD-103:** smoke с телефона РФ (IG/TG/YouTube) | «OK» или конкретный симптом |
| **O-VPN-003** | P0 | Сообщить пользователям: **обновить подписку** в Happ (gen≥26) | broadcast согласован с VPN-AUD-102 |
| **O-VPN-004** | P1 | **Q032** legal / оферта | URLs в боте |
| **O-VPN-005** | P1 | **Бюджет второго LV IP** / хостинг | invoice / IP |
| **O-VPN-006** | P1 | **Bitwarden** — не хранить panel-token в репо локально | — |
| **O-VPN-007** | P2 | **Happ на устройстве:** подтвердить `ImportResult count > 0` | скрин/log |
| **O-VPN-008** | P2 | Решение: **массовый waifu** regexp.ru vs geosite:ru (риск регрессии) | go/no-go |

---

## Связь с существующими ID

| Старый ID | Новый |
|-----------|-------|
| Q-VPN-STAB-001…018 | Phase 0 VPN-STABILITY |
| Q-VPN-STAB-019 | VPN-AUD-410 |
| Q-VPN-STAB-020 | VPN-AUD-370 |
| Q-VPN-STAB-022 | VPN-AUD-150 |
| Q120 | VPN-AUD-201 / O-VPN-001 |
| Q032 | O-VPN-004 |
| P1-PRO-VPN-SPEED-01 | VPN-AUD-000 |
| P6-SCALE-NL-VERIFY | VPN-AUD-008, VPN-AUD-220 |

---

## NO-GO (не делать)

1. Вернуть catch-all **только** relay (proxy-5..7).  
2. `Super_Balancer` selector `["proxy"]` на все 14 hosts (Q132 footgun).  
3. Включить observatory с hicloud без A/B.  
4. Удалить xhttp из infra/template без Happ-only path.  
5. «Выберите NL вручную» в UX.  
6. Массовый патч regexp.ru без rollback snapshot.

---

## Рекомендуемый порядок исполнения агентом

```
VPN-AUD-101 (gate script)
  → VPN-AUD-102 (notify gen26)
  → VPN-AUD-110,120,121,130 (template tuning, по одному commit)
  → VPN-AUD-150,151 (drift/env)
  → VPN-AUD-140 (docker events)
  → Phase 2 по приоритету + O-VPN-001 когда готов IP
```

**Параллельно владелец:** O-VPN-002, O-VPN-003.

---

## Журнал прогресса (§12)

| Дата | ID | Статус | Примечание |
|------|-----|--------|------------|
| 2026-05-28 | VPN-AUD-000…011 | DONE | gen=26, commits d38a77e, 82a9808, a7b2a69 |
| 2026-05-28 | VPN-AUD-101 | DONE | `ops/vpn_verify_gate.py` → VPN_VERIFY_GATE_OK |
| 2026-05-28 | VPN-AUD-102 | DONE | broadcast 56/57 OK; test-admin; gen≥27 |
| 2026-05-28 | VPN-AUD-110 | DONE | bufferSize 128; gen=27 |
| 2026-05-28 | VPN-AUD-120,121 | DONE | Intl IP 15 CIDR (TG/Meta/OpenAI); gen=28 |
| 2026-05-28 | VPN-AUD-130 | DONE | customRemarks: auto server, без «выберите LV/NL» |
| 2026-05-28 | VPN-AUD-111 | DONE | `audit_policy_latency.py` + gate; handshake=4, connIdle=300 |
| 2026-05-28 | VPN-AUD-140 | DONE | `docker_events_tg.py` on LV + cron */5; dry-run OK |
| 2026-05-28 | VPN-AUD-151 | DONE | ru-monitor.env prod = tmpl (8443, relay vars) |
| | VPN-AUD-103,150+ | TODO | owner smoke; drift waive |

---

*Обновлять таблицу §12 при закрытии каждого VPN-AUD-*. Карта: [`BACKLOG-MAP.md`](BACKLOG-MAP.md).*
