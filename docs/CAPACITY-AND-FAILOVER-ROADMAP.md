# Ёмкость и отказоустойчивость (300 → 10k users)

**Связано:** `docs/NODE-POLICY-LV-NL.md`, `docs/COMMERCIAL-BACKLOG.md` §10.1, `docs/RUNBOOK-LV-DOWN-NL-FAILOVER.md`.

---

## Три слоя «балансировки»

| Слой | Что делает |
|------|------------|
| **Happ** | `leastLoad` между outbound в подписке |
| **Шаблон Xray** | Intl_Stealth (TG/IG → relay only), Intl_Direct (catch-all relay+NL) |
| **Операции** | `balancer.sh` (алерты 80/95/100%), AMS cron LV↔NL failover, backup edge `n4l8q:4433` |

Цель — не 50/50 в панели, а **N+1 ёмкость** и **пережить падение одного компонента**.

---

## Пороги по базе (users в панели)

| Users | Действие |
|-------|----------|
| **~80** на 2 нодах (80% soft-cap 50×2) | Планировать **3-ю prod-ноду** |
| **2 000** | Апгрейд RAM **AMS** |
| **8 000** | Load test sub; отдельный edge для подписки |

Пик сессий при 10k учёток: ориентир **3–8k** одновременно (`COMMERCIAL-BACKLOG` §10.3).

---

## Матрица отказов

| Упало | VPN | Подписка (обновить) | Авто / runbook |
|-------|-----|---------------------|----------------|
| **LV** | relay+NL direct; NL основной после failover | p4n7q/k9x2m1 мертвы | `lv_node_down_nl_failover` (AMS cron); **n4l8q:4433** |
| **NL** | LV + relay | Edge LV жив | Обычно без PATCH |
| **LV + NL** | Даун до 3-й ноды в injectHosts | — | **3-я нода** (другой DC/AS) |
| **1 relay** | 2-й relay | — | ✅ 2 relay live; autotrim |
| **AMS** | Кэш sub в Happ | 502 на edge | Jurisdiction runbook |

После PATCH шаблона — **обновить подписку** в Happ (`subscription_config_notify`).

---

## NL как полноценная нода

| Сейчас | Следующие шаги (бэклог Q174–181) |
|--------|----------------------------------|
| NL direct :443×4 в injectHosts | **Relay→NL :443** inbound + probe |
| Stealth: TG только relay→LV | **Не** NL в TG без A/B |
| ~4% lifetime traffic vs LV | `nl_node_health_probe.py`, VPN-AUD-310 latency trim |
| 0 usersOnline при малой базе | Норма для RU+stealth; не признак слабого VPS |

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
