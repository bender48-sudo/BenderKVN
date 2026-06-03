# Runbook: LV недоступен → NL-only в подписке

**Скрипт:** `ops/lv_node_down_nl_failover.py`  
**Verify NL sub:** `ops/verify_nl_failover_sub.py`

## Что чинит / что нет

| Проблема | Этот runbook |
|----------|----------------|
| VPN клиент бьётся в мёртвый LV при живом NL | **Да** — `injectHosts` только NL, балансеры только `proxy…N` на NL |
| Подписка не открывается (HTTPS к p4n7q/k9x2m1) | **Нет** — edge Caddy на **LV**; нужен живой LV или отдельный edge (см. `RUNBOOK-JURISDICTION-FAILOVER.md`) |
| Панель / subscription-page на AMS | Не трогаем — обычно живы |

## Обязательный gate (без деградации)

### Перед NL failover (штатный прод, LV жив)

```bash
python ops/lv_node_down_nl_failover.py --gate
```

Ожидаем: `GATE_MULTIPATH_OK` (`probe_subscription` + `verify_vpn_balancer_profile`).

### Применить NL failover (LV down или `--force` для учений)

```bash
python ops/lv_node_down_nl_failover.py --gate --apply
# или автоматически по статусу ноды:
python ops/lv_node_down_nl_failover.py --auto --gate --apply
```

Ожидаем после PATCH: `GATE_NL_FAILOVER_OK` (`verify_nl_failover_sub` — только NL outbounds).

### Восстановление после оплаты LV

```bash
python ops/lv_node_down_nl_failover.py --restore --gate --apply
```

Ожидаем: снова `GATE_MULTIPATH_OK`.

Состояние для отката: `.secrets/snapshots/template-before-lv-nl-failover-*.json` и `.secrets/lv_nl_failover_state.json`.

## Статус

```bash
python ops/lv_node_down_nl_failover.py --status
```

## Пользователям

После `--apply` (failover или restore): **обновить подписку** в Happ/Streisand и переподключить VPN.  
При `push_ams=True` бот может разослать напоминание (generation bump).

## Деплой при мёртвом SSH на LV

| Где | Что |
|-----|-----|
| **AMS** | `pwsh -File ops/deploy_ams_node_resilience.ps1` — cron `run_lv_node_failover_auto_ams.sh` (токен из `/opt/remna-shop/.env`, `REMNA_BASE_URL`) |
| **LV** | `pwsh -File ops/deploy_lv_node_resilience.ps1` — когда SSH на **176.126.162.158** восстановлен |
| **Workstation** | `python ops/lv_node_down_nl_failover.py --status` / `--gate` (без `--apply` пока LV **connected**) |

**Hot prod:** не вызывать `--apply` / `--force`, если `--status` показывает **LV connected** — иначе деградация multipath.

## Связанные документы

- `docs/NODE-POLICY-LV-NL.md` — роли LV/NL
- `docs/VPN-INCIDENT-LESSONS-2026-05-25.md` — почему нет observatory auto-failover
- `docs/RUNBOOK-JURISDICTION-FAILOVER.md` — потеря LV edge
- `ops/restore_template_working.py` — полный multipath, если state-файл потерян
