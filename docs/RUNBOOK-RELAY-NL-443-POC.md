# Runbook: Relay → Netherlands :443 (VPN-AUD-275)

**Цель:** симметрия с relay→LV — RU relay терминирует на **NL direct :443**, не на :9443 (legacy снят VPN-AUD-273).

**Статус:** **dry-run / design** — не `--apply` без `NL_REACHABILITY_PROBE_RU_OK` с **bvpn-lv**.

---

## Предусловия

1. `python ops/nl_node_health_probe.py --require-ru-probe` на **LV** → **NL_NODE_HEALTH_OK**
2. `python ops/vpn_verify_gate.py` → **VPN_VERIFY_GATE_OK**
3. Inbound в панели: 3× «Relay2→NL» или аналог на **91.90.192.17:443** (создать в UI / API)
4. **NO-GO:** TG/IG в Intl_Stealth через NL без staging A/B

---

## Порядок (когда inbound готовы)

1. Snapshot template + hosts
2. Добавить UUID relay→NL :443 в `injectHosts` (симметрия: +3 к relay→LV)
3. Расширить `Intl_Direct` selector (не Stealth) — `balancer_selectors.INTL_RELAY_NL_SELECTOR` pattern
4. `python ops/verify_vpn_balancer_profile.py`
5. `--apply` + `subscription_config_notify`
6. 7 дней: `usersOnline` NL > 0, нет регрессии VPN-AUD-103

---

## Откат

Snapshot в `.secrets/snapshots/` + `restore_template_working.py` или `lv_node_down_nl_failover.py --restore`.
