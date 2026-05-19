# Фаза 6 — GTM hardening (после Q085)

**Старт:** 2026-05-19 после **Q085** (`AUDIT-2026-05-TSPU-REDTEAM.md`) и **`POST-DEPLOY-REVIEW-2026-05.md`**.

**Правило:** одна строка **NEXT** в **`BACKLOG-QUEUE.md`**; один Q → один коммит → стоп.

---

## Карта источников

| Источник | Что закрывает |
|----------|----------------|
| **Q085** TSPU red-team | Discovery **:2053**, sunset LV, alt apex, RU probe → **Q090–Q095** |
| **POST-DEPLOY review** | Admin FSM, **:2054**, debug print, cabinet → **Q086–Q089**, **Q096** |
| Незакоммиченный flow | ЛК Mini App, меню бота → деплой в **Q097** или отдельный hotfix |

**Нумерация:** в отчёте TSPU «Q086» = discovery **:2053** → в очереди это **Q090** (security **Q086–089** идут первыми как GTM blockers).

---

## Очередь (Q086–Q097)

| Q | ID | Приоритет | Done when | Verify |
|---|-----|-----------|-----------|--------|
| **086** | **P3-RED-ADMIN-FSM-01** | **P0** | Admin FSM: только `ADMIN_TELEGRAM_ID` | `smoke_admin_fsm_auth.py` |
| **087** | **P6-RED-PAY-08** | **P0** | Удалить DEBUG print crypto hash; нет api_key в логах | grep `handlers.py` |
| **088** | **P1-RED-NET-2054-01** | **P0** | Убрать/закрыть публичный `:2054` → panel в Caddy | external curl fail |
| **089** | **P3-RED-CABINET-02** | **P1** | Cabinet: не отдавать `bind_url` без auth | POST smoke |
| **090** | **P2-RED-DISCOVERY-PORT-01** | **P1** | User-facing URL только **:8443** (`site_urls`) | grep no `:2053` bot+FAQ |
| **091** | **P2-RED-EDGE-SUNSET-2053-01** | **P1** | LV: **2053** → 301 **:8443** или off | curl :2053 |
| **092** | **P3-FLOW-11-LIVE-01** | **P2** | Live alt apex + FAQ/бот (не только runbook) | curl alt :8443 |
| **093** | **P1-RED-TSPU-BLOCK-RU-01** | **P2** | Block probe cron с RU egress | **TSPU_BLOCK_PROBE_RU_OK** |
| **094** | **P5-COM-STATUS-TRIM-01** | **P2** | `/status` без лишних ops-деталей | review HTML |
| **095** | **P1-PRO-TIER-SWITCH-01** | **P3** | Tier hint в боте/portal | manual |
| **096** | **P2-RED-EDGE-HEADERS-01** | **P2** | HSTS + CSP на portal/setup | curl -I |
| **097** | **P3-FLOW-LK-DEPLOY-01** | **P2** | Закоммитить + LV/AMS: cabinet.html, меню, flow | Mini App smoke |

**Владелец (не Q):** **Q032** оферта; **`MANUAL-OWNER-CHECKLIST.md`** (BotFather, LTE 5 пунктов из TSPU audit).

---

## GTM gate

| Условие | Q |
|---------|---|
| **Блокеры** | **086–088** (+ **089** strongly recommended) |
| **ТСПУ discovery до GTM** | **090–091** |
| **После GTM** | **092–097**, P4-DNS, native app |

**Вердикт:** см. **`POST-DEPLOY-REVIEW-2026-05.md`** — условно не готов до **086–088**.

---

## Commit templates

| Q | Пример |
|---|--------|
| 086 | `security: P3-RED-ADMIN-FSM-01 — admin edit FSM authz` |
| 087 | `security: P6-RED-PAY-08 — remove crypto debug print` |
| 088 | `ops: P1-RED-NET-2054-01 — close public panel :2054` |
| 090 | `fix: P2-RED-DISCOVERY-PORT-01 — canonical :8443 in bot and FAQ` |
| 091 | `ops: P2-RED-EDGE-SUNSET-2053-01 — grace 2053 redirect LV` |
