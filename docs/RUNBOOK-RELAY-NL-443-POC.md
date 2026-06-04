# Runbook: Relay → Netherlands :443 (VPN-AUD-275)

**Цель:** симметрия с relay→LV — RU relay терминирует на **NL direct :443**, не на :9443 (legacy снят VPN-AUD-273).

**Статус:** **LIVE 2026-06-04 (VPN-AUD-279)** — injectHosts **16**, Intl_Direct **16** (relay×6+NL×4+relay-NL×6), Intl_Stealth **relay×6** only. **VPN-AUD-281:** хосты в inject обязаны **`isHidden=true`** (иначе sub остаётся на 10 proxy). Мониторинг: `usersOnline` NL, **O-VPN-002** smoke. Откат: snapshot `template-before-relay-nl-443-inject-*`.

---

## Скрипты (VPN-AUD-275)

| Скрипт | Назначение |
|--------|------------|
| `ops/patch_add_relay_nl_443_hosts.py` | Создать 6 hosts (relay1+relay2 ×3 SNI), `--apply` → hidden+disabled |
| `ops/probe_relay_nl_443_poc.py` | Gate: hosts + `NL_REACHABILITY` (LV SSH) + Happ geosite + RU bypass |
| `ops/patch_trim_injecthosts_relay_nl.py` | **Не** для :443 — только trim legacy :9443 из inject |
| `ops/patch_relay_nl_inject_hidden.py` | Fix `isHidden=true` на relay-NL :443 (VPN-AUD-281) |
| `ops/probe_injecthosts_sub_parity.py` | inject UUID count vs live `vless_proxy` |

---

## Предусловия

1. `python ops/nl_node_health_probe.py --require-ru-probe` на **LV** → **NL_NODE_HEALTH_OK**
2. `python3 /opt/scripts/vpn_verify_gate.py` на **LV** → **VPN_VERIFY_GATE_OK**
3. `python ops/patch_add_relay_nl_443_hosts.py --apply` → **RELAY_NL_443_HOSTS_OK** (6 hosts)
4. `python ops/probe_relay_nl_443_poc.py --require-hosts` → **RELAY_NL_443_POC_OK**
5. **NO-GO:** TG/IG в Intl_Stealth через NL без staging A/B; **не** `--apply` inject без snapshot

---

## Порядок (когда включаем в injectHosts)

1. Snapshot template + hosts
2. Добавить UUID relay→NL :443 в `injectHosts` (симметрия: +3 к relay→LV)
3. Расширить `Intl_Direct` selector (не Stealth) — `balancer_selectors.INTL_RELAY_NL_SELECTOR` pattern
4. `python ops/verify_vpn_balancer_profile.py`
5. `--apply` + `subscription_config_notify`
6. 7 дней: `usersOnline` NL > 0, нет регрессии VPN-AUD-103

---

## Откат

Snapshot в `.secrets/snapshots/` + `restore_template_working.py` или `lv_node_down_nl_failover.py --restore`.
