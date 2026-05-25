# Мониторинг BenderVPN (P2-DOC-MONITORING-01)

## Каналы

| Канал | Где | Что ловит |
|-------|-----|-----------|
| `monitor.sh` (LV) | cron | ноды, sub-page, docker |
| `ru-monitor.py` (LV) | cron | RU path, injectHosts |
| `daily-report.sh` | cron | сводка + AMS decom |
| Telegram `/status` | бот admin | ручной снимок |
| `https://k9x2m1.conntest.xyz/status` | публичный JSON | инциденты (без ops-секретов) |

## Бот / AMS (после phase 8)

| Проверка | Команда |
|----------|---------|
| Health | `curl -fsS http://127.0.0.1:1488/health` на AMS |
| Monitor loop | `docker logs remna-shop-bot --since 15m \| grep -E 'Monitor loop critical\|SCHEDULER_CYCLE'` |
| Remna retry | `grep 'retry attempt' …` при 503 panel |
| Sub refresh jitter | `python ops/_verify_sub_refresh_deploy.py` |
| Transport mix | `python ops/transport_mux_audit.py --json` |
| Profile health | `python ops/transport_profile_health.py` |
| TSPU block | `python ops/tspu_block_probe.py`; alert: `python ops/tspu_block_probe_alert.py` |

## Пороги (ориентир)

- Sub probe: **200**, p95 &lt; baseline §12.
- Transport: primary+alt в sub ≥ **95%** (`TRANSPORT_MUX_OK`).
- Бот: нет `NameError` / `Monitor loop critical` после деплоя.

## После деплоя бота

`pwsh -File ops/deploy-bot-handlers-ams.ps1` → health + monitor grep (**`VPN-INCIDENT-LESSONS`** §0).
