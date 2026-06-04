# Онбординг 3-й prod-ноды

**Для владельца:** зарегистрировать VPS → передать агенту **root SSH**, **публичный IP**, **регион/провайдер**.

**Для агента:** после IP — `deploy-node.sh` + injectHosts + verify (см. Q179 / O-VPN-009).

---

## Требования к VPS

| Параметр | Рекомендация |
|----------|----------------|
| **Регион** | Не тот же DC/AS что LV **и** NL (диверсификация) |
| **RAM** | ≥ 2 GiB (как LV/NL) |
| **Порты** | :443, :8443 (xhttp reserve), SSH |
| **ОС** | Ubuntu 22.04 |

---

## Шаги агента (когда есть SSH)

1. `bash ops/deploy-node.sh` — по runbook в `docs/DEPLOY.md`
2. Панель: нода **connected**, 4× Direct :443 hosts
3. `injectHosts` — добавить UUID (скрипт в deploy-node)
4. Балансеры: включить в `Intl_Direct` pool (не TG stealth без A/B)
5. `python ops/vpn_verify_gate.py`
6. `subscription_config_notify` — напоминание обновить sub

---

## Проверка отказоустойчивости

При **LV+NL down** (учение): в injectHosts остаются только хосты 3-й ноды → клиенты с обновлённой sub на EU-exit #3.

См. `docs/RUNBOOK-LV-DOWN-NL-FAILOVER.md` (обратный restore после восстановления).
