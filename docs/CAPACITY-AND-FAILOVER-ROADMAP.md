# Ёмкость и отказоустойчивость (300 → 10k users)

**Связано:** `docs/NODE-POLICY-LV-NL.md`, `docs/COMMERCIAL-BACKLOG.md` §10.1, `docs/RUNBOOK-LV-DOWN-NL-FAILOVER.md`.

> **Live baseline (2026-06-11, PROOF-001 + QUALITY-PROOF-001):** штатный Auto = **Candidate D relay-only×6**; **NL не active delivery**; RU relay→NL TCP PASS с LV; **A2/A4** (`patch_add_nl_intl_gated.py`) feasible after **MONITOR-FLAP** soak + controlled smoke. Historical **VPN-AUD-220** / **Q167–Q171** — не текущий prod.

---

## Три слоя «балансировки»

| Слой | Что делает |
|------|------------|
| **Happ** | `leastLoad` между outbound в подписке |
| **Шаблон Xray (live)** | Intl_Stealth + Intl_Direct → **relay-only×6** (`RELAY6_SELECTOR`) |
| **Шаблон Xray (historical / target)** | Intl_Stealth (TG/IG → relay only), Intl_Direct (catch-all relay+NL) — **VPN-AUD-220**, not live |
| **Операции** | `balancer.sh` (алерты 80/95/100%), AMS cron LV↔NL failover, backup edge `n4l8q:4433` |

Цель — не 50/50 в панели, а **N+1 ёмкость** и **пережить падение одного компонента**.

---

## Пороги по базе (users в панели)

| Users | Действие |
|-------|----------|
| **~80** на **≥2 delivery-path nodes** (80% soft-cap 50×N) | Планировать **(N+1)**-ю prod-ноду — **сейчас N=1** (LV exit) для штатного Auto |
| **2 000** | Апгрейд RAM **AMS** |
| **8 000** | Load test sub; отдельный edge для подписки |

Пик сессий при 10k учёток: ориентир **3–8k** одновременно (`COMMERCIAL-BACKLOG` §10.3).

---

## Матрица отказов

| Упало | VPN | Подписка (обновить) | Авто / runbook |
|-------|-----|---------------------|----------------|
| **LV** | relay-only×6 (exit LV) в штатном режиме; NL direct **после** failover PATCH | p4n7q/k9x2m1 мертвы | `lv_node_down_nl_failover` (AMS cron); **n4l8q:4433** |
| **NL** | relay-only×6 (exit LV); NL не в штатном sub | Edge LV жив | Обычно без PATCH |
| **LV + NL** | Даун до 3-й ноды в injectHosts | — | **3-я нода** (другой DC/AS) |
| **1 relay** | 2-й relay | — | ✅ 2 relay live; autotrim |
| **AMS** | Кэш sub в Happ | 502 на edge | Jurisdiction runbook |

После PATCH шаблона — **обновить подписку** в Happ (`subscription_config_notify`).

---

## NL как полноценная нода

| Сейчас (PROOF-001 + QUALITY-PROOF-001, 2026-06-11) | Следующие шаги (**VPN-ARCH-001**) |
|--------|----------------------------------|
| **NL не active delivery**; connected; failover + backup edge; **pre-qualified** for A2/A4 | **Preferred:** A2/A4 **controlled smoke** after soak — **`patch_add_nl_intl_gated.py`**; **not** blind PATCH |
| RU relay→NL ~55–61 ms TCP (LV probe) | **Interim B** OK short-term; **not C** (healthy); **not D** unless smoke fails |
| Stealth: TG только relay (live) | Intl_Stealth остаётся relay-only; NL только Intl_Direct |
| Relay-only×6 → single LV exit | NL в capacity math **только после** smoke + post-inclusion audit |

Controlled smoke gates: **`BENDERVPN-MASTER-BACKLOG.md`** §VPN-ARCH-001 (**MONITOR-FLAP-001** 24h soak, owner approval, mobile cohort, rollback).

---

## Рекомендуемый порядок (агент)

1. **VPN-AUD-271** — NL health baseline (`NL_NODE_HEALTH_OK`)
2. **VPN-AUD-272** — deploy LV scripts + full `vpn_verify_gate`
3. **VPN-AUD-273** — disable legacy relay-NL :9443 hosts в панели
4. **VPN-AUD-274** — BBR audit NL (SSH)
5. **VPN-AUD-275** — relay→NL :443 PoC (dry-run → apply после probe)
6. **VPN-AUD-276** — 3-я нода: `deploy-node.sh` + injectHosts (владелец: IP/SSH)
7. **VPN-AUD-310** — latency-aware selector (staging)

**Владелец:** Q032, VPN-AUD-103 smoke, IP/SSH 3-й ноды.
