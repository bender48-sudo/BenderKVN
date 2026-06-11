# Карта бэклога BenderVPN

**Назначение:** одна страница «куда смотреть». **Исполнять** только по **`BACKLOG-QUEUE.md`** (строка **`NEXT`**).

---

## Иерархия документов

| Уровень | Файл | Роль |
|---------|------|------|
| **1. Исполнение** | **`docs/BACKLOG-QUEUE.md`** | Линейная очередь **Q001…**; единственный **`NEXT`** |
| **2. Задачи и журнал** | **`docs/COMMERCIAL-BACKLOG.md`** | ID, Done when, §7.1 P3-FLOW, **§12** прогресс на проде |
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

**Сейчас:** **NEXT=—** (фазы 16–17 закрыты **2026-06-04**). Владелец: **Q032**, **O-VPN-002**, **O-VPN-009**, **P4-DNS-05**, live **P4-DNS-01** VPS.

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
| **MONITOR-FLAP-001** | **DONE (repo)** | Selfsteal anti-flap — deploy LV pending |
| **OPS-ALERT-HYGIENE-001** | **DONE (repo)** | Cert digest + alert tiers — deploy LV pending |
| **ACQ-*** / **REF-*** | OPEN | См. MASTER; не дублировать OPS-CAPACITY-300 / NODE-RELAY-ADD |
| **VPN-ARCH-001** | AWAITING APPROVAL | **QUALITY-PROOF-001 DONE**: NL pre-qualified; A2/A4 smoke after soak; not active capacity |
| **VPN-NODE-RUNBOOK-001** | OPEN | Fast node+relay bring-up template (BACKLOG-CAPACITY-NODES-001) |

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
