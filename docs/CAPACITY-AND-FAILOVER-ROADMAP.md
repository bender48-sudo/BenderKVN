# Ёмкость и отказоустойчивость (300 → 10k users)

**Связано:** `docs/NODE-POLICY-LV-NL.md`, `docs/COMMERCIAL-BACKLOG.md` §10.1, `docs/RUNBOOK-LV-DOWN-NL-FAILOVER.md`.

> **Live baseline (2026-06-11, PROOF-001):** штатный Bender Auto = **Candidate D relay-only×6**; **NL не в injectHosts**; effective VPN exit = **LV** за relay. Разделы ниже с «NL direct в inject» / «Intl relay+NL» описывают **исторический или целевой** профиль (**VPN-AUD-220**), не текущий прод. **Q167–Q171** = failover/backup edge, не active capacity.

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

| Сейчас (PROOF-001, 2026-06-11) | Следующие шаги (**VPN-ARCH-001** owner A/B/C/D) |
|--------|----------------------------------|
| **NL не в injectHosts**; connected; failover-only + backup edge | **A:** re-include NL после acceptance gates; **B:** keep failover-only; **C:** decom; **D:** 3-я prod-нода (**VPN-NODE-RUNBOOK-001**) |
| Stealth: TG только relay (live) | **Не** NL в TG без A/B |
| Relay-only×6 → single LV exit | Relay→NL :443 PoC (**VPN-AUD-275**) только после owner decision |
| Historical: NL direct :443×4 (**VPN-AUD-220**) | **Не** считать historical DONE live proof |

Acceptance gates before prod PATCH: см. **`BENDERVPN-MASTER-BACKLOG.md`** §VPN-ARCH-001 (**MONITOR-FLAP-001** 24h soak, probes, owner approval, rollback).

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
