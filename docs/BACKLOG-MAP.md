# Карта бэклога BenderVPN

**Назначение:** одна страница «куда смотреть». **Исполнять** только по **`BACKLOG-QUEUE.md`** (строка **`NEXT`**).

---

## Иерархия документов

| Уровень | Файл | Роль |
|---------|------|------|
| **1. Исполнение** | **`docs/BACKLOG-QUEUE.md`** | Линейная очередь **Q001…**; единственный **`NEXT`** |
| **2. Задачи и журнал** | **`docs/COMMERCIAL-BACKLOG.md`** | ID, Done when, §7.1 P3-FLOW, **§12** прогресс на проде |
| **2b. Canonical master** | **`docs/BENDERVPN-MASTER-BACKLOG.md`** | All product/VPN/billing IDs incl. CodeRabbit remediation (`c03f638`) |
| **2c. CodeRabbit triage** | **`docs/CODERABBIT-AUDIT-TRIAGE-2026-06-14.md`** | Accepted/rejected findings; remediation order |
| **3. Флоу (продукт)** | **`docs/USER-FLOW-BACKLOG.md`** | Принципы, MVP/Comfort, бабушка-тест |
| **4. Агент — VPN аудит** | **`docs/BACKLOG-VPN-FULL-AUDIT-2026-05-28.md`** | Полный бэклог Claude 28.05 + gate |
| **4. Агент — сейчас** | **`docs/AGENT-PHASE11-VPN-NODE-RESILIENCE-BACKLOG.md`** | Q167–170 node + sub edge resilience |
| **4 (закрыто)** | **`docs/AGENT-PHASE10-BOT-CODERABBIT-BACKLOG.md`** | Q161–166 bot CodeRabbit раунд 2 |
| **4 (закрыто)** | **`docs/AGENT-PHASE9-BOT-CODERABBIT-BACKLOG.md`** | Q142–160 bot CodeRabbit |
| **4 (закрыто)** | **`docs/AGENT-PHASE8-RELIABILITY-BACKLOG.md`** | Q122–141 reliability/TSPU/speed |
| **4c. GTM (закрыто)** | **`docs/AGENT-PHASE6-BACKLOG.md`** | Q086–097 |
| **4a. Прод (закрыто)** | **`docs/AGENT-PROD-DEPLOY-BACKLOG.md`** | Q079–084 |
| **4b. Владелец** | **`docs/MANUAL-OWNER-CHECKLIST.md`** | Q032, BotFather, DNSSEC, видео |
| Закрыто (репо) | AUDIT / PRODUCT / FLOW backlogs | Q063–050 |
| **5. Карта пути** | **`docs/USER-FLOW-JOURNEY.md`** | Персоны, сценарии (закрыт **P3-FLOW-00**) |
| **6. Владелец (ручное)** | **`docs/MANUAL-OWNER-CHECKLIST.md`** | Bitwarden, BotFather, DNSSEC — не в очереди Q |
| **7. Политики** | **`POLICY-SEQUENTIAL-WORK.md`**, **`POLICY-BACKLOG-ORDER.md`** | Один Q → коммит; продукт → UX |

**Параллельно (не NEXT):** **P4-DNS** — §8 бэклога, отдельный владелец.

---

## Фазы очереди (сводка)

| Фаза | Q | Статус | Тема |
|------|---|--------|------|
| **1** | 001–022 | **Закрыта** | Scale, monetize, P6-RED (sub/mux/pg), GTM wiki |
| **2** | 023–031 | **Закрыта** | Safe-deploy, P1-RED, публичный `/status` |
| **3** | 033–050, 063–078, 051–062 | **Репо закрыто** | Код/docs: security → продукт → флоу |
| **4** | 079–084 | **Закрыта** | Накат LV/AMS (агент + SSH) |
| **5** | 085 | **Закрыта** | ТСПУ red-team отчёт |
| **6** | 086–097 | **Закрыта** | GTM security + discovery + polish |
| **7** | 098–121 | **Закрыта** | TSPU раунд 2, SNI live, selfsteal, MUX docs |
| **8** | 122–141 | **Закрыта** | Bot reliability → VPN speed → observability |
| **9** | 142–160 | **Закрыта** | CodeRabbit bot: renew idempotency, DB, cache, UX |
| **10** | 161–166 | **Закрыта** | CodeRabbit bot раунд 2 |
| **11** | 167–171 | **Закрыта** | LV→NL failover, backup sub **n4l8q:4433**, flow smoke gate |
| **16** | 184–187 | **Закрыта** | inject parity gate, sub sample, autotrim runbook |
| **17** | 188–195 | **Закрыта** | help_connect, BBR, P4-DNS docs, observatory staging, DNS cron |
| **12** | 172–173 (VPN-AUD-210/220) | **210 REVERTED, 220 DONE (historical)** | geosite:ru NO-GO; NL :443×4 was live stealth split — **not current** (Candidate D relay-only×6 per PROOF-001) |

**Сейчас:** **NEXT=—** (фазы 16–17 закрыты **2026-06-04**). **Product/capacity track:** [`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md) + implementation backlog in [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md). Владелец: **Q032**, **O-VPN-002**, **O-VPN-009**, **P4-DNS-05**, live **P4-DNS-01** VPS.

**Gate после каждой VPN-правки:** `python ops/vpn_verify_gate.py`

---

## Фазы 3–4 (логика)

```
[DONE репо] Q033–050, Q063–078, Q051–062
[DONE]      Q079–084  prod deploy (агент+SSH)
[DONE]      Q085      TSPU red-team audit
[OWNER]     Q032 + MANUAL-OWNER-CHECKLIST
[DONE]      Q086–097  GTM hardening
[ACTIVE]    Q122–141  Phase 8 reliability (CodeRabbit + VPN incident)
[OWNER]     Q120      2-й RU relay VPS
```

**Gate:** накат AMS — **`RUNBOOK-AMS-SAFE-DEPLOY`** (не Q).

---

## Публичные URL продукта (после Q035–037)

| URL | Назначение |
|-----|------------|
| `https://k9x2m1.conntest.xyz:8443/start/` | Bootstrap (целевой порт после **Q080**) |
| `https://k9x2m1.conntest.xyz:8443/portal/` | Portal + **Mini App** (BotFather после Q080) |
| `https://k9x2m1.conntest.xyz:8443/setup/?t=…` | Персональная выдача |
| `https://k9x2m1.conntest.xyz:8443/status` | Публичный статус |
| `:2053` | Grace period (снять после миграции пользователей) |

Код: **`web/portal/`**, **`ops/site_urls.py`**.

---

## Продукт / коммерция (вне Q001+)

**SoT:** [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) — TRACK 0–6, ACQ-*, QA-*, DEVICE-*.

| ID | Статус | Комментарий |
|----|--------|-------------|
| **QA-OWNER-PREVIEW-FIX-002** | **DONE** repo `8a107ba` | Bot visual preview + cabinet CTA dedup |
| **MONITOR-FLAP-001** | **DEPLOYED LV + soak PARTIAL** | **MONITOR-FLAP-TUNE-001 repo DONE** — deploy + short re-soak |
| **MONITOR-FLAP-TUNE-001** | **DEPLOYED LV + short soak** | Soak from 2026-06-13 16:46 UTC; 30m/6h review |
| **OPS-ALERT-HYGIENE-001** | **DEPLOYED LV + soak PASS** | Cert digest batched; per-target cert spam stopped |
| **ACQ-*** / **REF-*** | OPEN | См. MASTER; не дублировать OPS-CAPACITY-300 / NODE-RELAY-ADD |
| **VPN-ARCH-001** | AWAITING APPROVAL | **QUALITY-PROOF-001 DONE**: NL pre-qualified; A2/A4 smoke after soak; not active capacity |
| **VPN-ARCH-30K-CAPACITY-PACK-001** | **DOCS DONE** | [`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md) + runbook + routing strategy + registry example — impl OPEN |
| **VPN-NODE-RUNBOOK-001** | **DOCS DONE / IMPL OPEN** | [`VPN-NODE-RUNBOOK.md`](VPN-NODE-RUNBOOK.md) + acceptance checklist |
| **VPN-NODE-REGISTRY-001** | **DONE** | [`ops/config/vpn_node_registry.yaml`](../ops/config/vpn_node_registry.yaml) + validator |
| **SUB-GEN-SELECTOR-STRATEGY-001** | **DONE** | [`ops/vpn_node_selector.py`](../ops/vpn_node_selector.py) dry-run |
| **SUB-GEN-SELECTOR-INTEGRATION-001** | **OPEN** | Live subscription generator wiring (after owner review) |
| **NODE-SMOKE-MATRIX-RUNNER-001** | **DONE** | [`ops/vpn_node_smoke_matrix.py`](../ops/vpn_node_smoke_matrix.py) — readiness matrix (dry-run) |
| **SUB-GEN-SELECTOR-APPLY-GATE-001** | **DONE** | [`ops/vpn_selector_apply_gate.py`](../ops/vpn_selector_apply_gate.py) — APPLY_ALLOWED gate; current state false |
| **VPN-ARCH-CONSOLIDATION-001** | **DONE (partial)** | Patch-on-patch → guardrails; [`docs/VPN_PRODUCTION_GUARDRAILS.md`](VPN_PRODUCTION_GUARDRAILS.md) + [`docs/VPN_PATCH_SCRIPT_MIGRATION_MAP.md`](VPN_PATCH_SCRIPT_MIGRATION_MAP.md) |
| **VPN-PRODUCTION-GUARDRAILS-001** | **DONE** | [`ops/vpn_production_guardrails.py`](../ops/vpn_production_guardrails.py) — central capacity validator; 21 tests |
| **VPN-AUTO-CUTTING-GUARD-001** | **PARTIAL (3/4 cron done)** | Manual patchers gated; autotrim + injecthosts sync + relay_failover migrated; LV→NL failover pair remains |
| **VPN-CONFIG-STABILITY-SCALABILITY-STEALTH-SPRINT-001** | **DONE (repo-side)** | [`docs/VPN-CONFIG-STABILITY-SCALABILITY-STEALTH-SPRINT-2026-06-17.md`](VPN-CONFIG-STABILITY-SCALABILITY-STEALTH-SPRINT-2026-06-17.md) — registry model + generator + integrity verifier + stealth guard; no prod apply |
| **SCRIPT-MIGRATE-INJECTHOSTS-SYNC-001** | **DONE** | [`ops/sync_injecthosts_connected.py`](../ops/sync_injecthosts_connected.py) — guardrail-wired apply; 20 tests |
| **VPN-CAPACITY-GATE-001** | **DONE** | Apply gate consumes guardrail; guardrail blockers surfaced |
| **VPN-NODE-INVENTORY-SOT-001** | **DONE (examples)** / live schema OPEN | Lifecycle/capacity SoT vocabulary in registry example + template |
| **SCRIPT-MIGRATE-LATENCY-AUTOTRIM-001** | **DONE** | [`ops/latency_selector_autotrim.py`](../ops/latency_selector_autotrim.py) — guardrail-wired apply; 18 tests |
| **SCRIPT-MIGRATE-RELAY-FAILOVER-001** | **PARTIAL** | `relay_failover_template` migrated (8 tests); LV→NL failover pair OPEN |
| **SCRIPT-MIGRATE-NL-RELAY-PATCHERS-001** | **OPEN** | P1 remaining cron auto-cutter / add-node patcher migration |
| **NODE-RU-NL-BALANCER-CANARY-001** | **PARTIAL** | [`docs/NODE-RU-NL-BALANCER-CANARY-2026-06-17.md`](NODE-RU-NL-BALANCER-CANARY-2026-06-17.md) — SSH PASS; NL→staging; owner canary; live apply gated |
| **NL-NODE-CANARY-ENABLE-001 / RU-NODE-CANARY-ENABLE-001** | **PARTIAL / OPEN** | NL SSH PASS + synthetic preview; traffic smoke + APPROVE PROD APPLY still gated — [`NL-A2-A4-CONTROLLED-CANARY-SMOKE-2026-06-17.md`](NL-A2-A4-CONTROLLED-CANARY-SMOKE-2026-06-17.md) |
| **CLIENT-STABILITY-OWNER-CANARY-PROFILE-001** | **DONE** | [`ops/generate_owner_canary_profile.py`](../ops/generate_owner_canary_profile.py) — owner-only `.local` plan |
| **RELAY1-DRAIN-OR-RETEST-001** | **DECISION READY** | [`RELAY1-DRAIN-OR-RETEST-DECISION.md`](RELAY1-DRAIN-OR-RETEST-DECISION.md) — owner go/no-go |
| **NODE-ONBOARD-NEW-PROD-PATH-001** | **READY FOR OWNER ACTION** | [`VPN-NODE-PURCHASE-REQUEST.md`](VPN-NODE-PURCHASE-REQUEST.md) + onboarding execution |
| **VPN-SELECTOR-SPEED-STABILITY-POLICY-001** | **DONE** | Selector excludes suspect/lab/disabled/backup (tested) |
| **VPN-NODE-PROCUREMENT-POLICY-001** | **DOCS DONE** | Owner-safe VPS purchase — [`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md) §13 |
| **UX-AUTO-CONNECT-PRINCIPLE-001** | **DOCS DONE** | One-button BenderVPN Auto — no server picker — §14 + routing strategy §10 |
| **ROUTING-PROFILE-RU-DIRECT-001** | **DOCS DONE / IMPL OPEN** | [`VPN-ROUTING-PROFILE-STRATEGY.md`](VPN-ROUTING-PROFILE-STRATEGY.md) |
| **NODE-SMOKE-MATRIX-001** | **DOCS DONE / IMPL OPEN** | [`VPN-NODE-ACCEPTANCE-CHECKLIST.md`](VPN-NODE-ACCEPTANCE-CHECKLIST.md) |
| **ROLLOUT-CANARY-DRAIN-001** | **DOCS DONE / IMPL OPEN** | Process in runbook + capacity plan |
| **MONITOR-CAPACITY-001** | OPEN | Capacity metrics/dashboard — not started |
| **CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-001** | **DIAGNOSED** | [`CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-2026-06-17.md`](CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-2026-06-17.md) — report(10): single relay endpoint dominates resets (80%); TUN/routing healthy |
| **CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-001** | **DONE (owner-gated)** | [`CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-2026-06-17.md`](CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-2026-06-17.md) — bad relay = ru-relay-1; registry incident + owner desktop canary excludes bad path; desktop PASS pending owner canary import |
| **DESKTOP-RELAY1-SERVICE-REPAIR-DEPLOY-001** | **PARTIAL (owner-gated)** | [`DESKTOP-RELAY1-SERVICE-REPAIR-2026-06-17.md`](DESKTOP-RELAY1-SERVICE-REPAIR-2026-06-17.md) — relay1 is hysteria TCP-forwarder (no xray); scoped hysteria-client restart did NOT clear resets; kept degraded; relay2-only canary is workaround |
| **RU-RELAY-ARCH-UNIFICATION-001** | **DONE (PATH C)** | [`RU-RELAY-ARCH-UNIFICATION-2026-06-17.md`](RU-RELAY-ARCH-UNIFICATION-2026-06-17.md) — relay1≡relay2 (identical hysteria forwarders, shared upstream); formalized STANDARD_RU_RELAY_PATH_V1; registry path_role/architecture_compliance/shared_upstream_group + fail-closed generator gate (+tests). Real gap = independent exit/upstream |
| **NEW-INDEPENDENT-EXIT-PATH-001** | **DONE — PATH A** | [`NEW-INDEPENDENT-EXIT-PATH-2026-06-17.md`](NEW-INDEPENDENT-EXIT-PATH-2026-06-17.md) |
| **NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-AND-PROMOTION-001** | **WAITING_CLEAN_DIRECT_BASIC_SMOKE** | [`NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-2026-06-18.md`](NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-2026-06-18.md) |
| **NL-DIRECT-BASIC-SMOKE-GUARD-001** | **DONE (repo)** | `analyze_nl_canary_smoke.py` — report(12) → NOT_TESTED_INVALID_SMOKE |
| **NL-DIRECT-PATH-SERVER-PROFILE-FIX-001** | **PATH B — DONE (repo) / WAITING_CLEAN_DIRECT_BASIC_SMOKE** | [`NL-DIRECT-PATH-SERVER-PROFILE-FIX-2026-06-18.md`](NL-DIRECT-PATH-SERVER-PROFILE-FIX-2026-06-18.md) — strip REALITY `sockopt.fragment` (report 13 NL direct reset) |
| **NL-INDEPENDENT-EXIT-FIX-001** | **DONE (repo) / WAITING_CLEAN_DIRECT_BASIC_SMOKE** | [`NL-INDEPENDENT-EXIT-FIX-2026-06-18.md`](NL-INDEPENDENT-EXIT-FIX-2026-06-18.md) — split DIRECT_BASIC + SPLIT_STEALTH profiles; validator guards |
| **CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-001** | **OPEN (proposed)** | Relay-path de-weight/replace; owner-gated; no broad prod apply |

---

## Открыто вне очереди

| ID | Где | Комментарий |
|----|-----|-------------|
| **P4-DNS-01…06** | §8 | Mobile bootstrap SKU |
| **P5-ENG-01** | §9 | Общий HTTP-клиент **ops** |
| **Q063–Q078** | **`AUDIT-2026-05-SECURITY.md`** | Pre-GTM security (CodeRabbit) |
| **P5-PROD-NATIVE-APP-01** | §9, **Q053** | Своё iOS/Android (замена Happ) |
| **TSPU (12 пунктов)** | **`TSPU-OBSERVATIONS.md`**, §5.1 | Матрица наблюдений → **Q051–061** |
| **P2-RED-EDGE-PORT-01** | §5.1, **Q051** | Уход с **:2053** (ТСПУ) |
| **P1-PRO-CLIENT-V2RAYN-01** | §5.1, **Q052** | v2rayN на Windows |
| **P4-DNS-07/08** | §8, **Q060** | RF egress, whitelist IP |
| **P5-RED-RD-01** | §5.1 | R&D Snowflake PoC |
| **§1 срез продакшена** | §1 | Переснять users/RAM при SSH |

---

## Smoke для агента (фаза 3)

```powershell
python ops/portal_bundle_audit.py      # PORTAL_BUNDLE_OK
python ops/smoke_public_bootstrap.py   # PUBLIC_BOOTSTRAP_OK
python ops/smoke_portal_setup_page.py  # PORTAL_SETUP_PAGE_OK  # если есть
python ops/smoke_telegram_miniapp.py   # TELEGRAM_MINIAPP_PORTAL_OK
```

---

*Обновлять эту карту при смене фазы или добавлении Q078+.*
