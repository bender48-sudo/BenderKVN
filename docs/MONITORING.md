# Мониторинг BenderVPN (P2-DOC-MONITORING-01)

## Каналы

| Канал | Где | Что ловит |
|-------|-----|-----------|
| `monitor.sh` (LV) | cron | ноды, sub-page, docker |
| `ru-monitor.py` (LV) | cron | RU path, injectHosts |
| `selfsteal-monitor.py` (LV) | cron | Caddy selfsteal fingerprint (13 SNI) |
| `daily-report.sh` | cron | сводка + AMS decom |
| Telegram `/status` | бот admin | ручной снимок |
| `https://k9x2m1.conntest.xyz/status` | публичный JSON | инциденты (без ops-секретов) |

## Уровни алертов (MONITOR-FLAP-001 / MONITOR-FLAP-TUNE-001 / OPS-ALERT-HYGIENE-001)

| Уровень | Куда | Примеры |
|---------|------|---------|
| **silent / log** | `/var/log/bvpn-*.log`, state.json | CDN quorum blip (log-only); cert change при cooldown digest; retried counter без hourly repeat |
| **warning / digest** | log + опционально один TG digest | RU MONITOR cert rotation (батч ≤1/ч); CDN SNI degraded fail_streak 1/3; retried WARNING ≤1/ч на SNI |
| **paging** | Telegram 🚨 | sustained fail (fail_streak ≥3 @ */5 cron); **non-CDN** quorum ≥2 SNI; baseline RU sustained; RU TLS down batch |

**Deploy на LV:** `50a6ac4` (2026-06-11) + **MONITOR-FLAP-TUNE-001** `21f5a97` (2026-06-13 16:41 UTC). Short soak **in progress** from first tuned cron **16:46:40 UTC** — review ~17:16 UTC (30m), ~22:46 UTC (6h). `ru-monitor.py` unchanged. See [`CHECKPOINT-2026-06-12-CLIENT-NODES-MONITORING.md`](CHECKPOINT-2026-06-12-CLIENT-NODES-MONITORING.md) §9.

### selfsteal-monitor.py — anti-flap

Пороги (override в `/etc/bvpn/balancer.env`):

| Переменная | Default | Смысл |
|------------|---------|--------|
| `SELFSTEAL_FAIL_STREAK_THRESHOLD` | 3 | ~15 мин sustained fail (@ */5) перед DOWN |
| `SELFSTEAL_OK_STREAK_THRESHOLD` | 2 | ~10 мин OK перед RECOVERED |
| `SELFSTEAL_RE_ALERT_COOLDOWN_SEC` | 900 | cooldown после RECOVERED |
| `SELFSTEAL_RECOVER_NOTIFY_MIN_SEC` | 3600 | не чаще 1 RECOVERED TG/час на SNI |
| `SELFSTEAL_RETRIED_WARN_LOG_SEC` | 3600 | retried WARNING не чаще 1/ч на SNI (MONITOR-FLAP-TUNE-001) |

CDN SNI (`microsoft`, `apple`, `bing`): **quorum blip → log-only**; TG paging только после **sustained fail** (fail_streak ≥3). Baseline RU SNIs (X5/VK/Ozon): paging после sustained fail **или** non-CDN quorum. `api.github.com` retried warnings: log ≤1/ч, **не TG**.

State: `/var/lib/bvpn-selfsteal-monitor/state.json` — поля `fail_streak`, `ok_streak`, `alerting`, `cooldown_until`, `last_retried_warn_log` (legacy entries мигрируют автоматически).

### ru-monitor.py — cert digest

Per-target `certificate changed` заменён на **один informational digest** за прогон (cooldown `RU_CERT_DIGEST_COOLDOWN_SEC`, default 3600). CDN SNI помечаются `[CDN]`; это diagnostic, не paging. DOWN/RECOVERED anti-flap (fail_streak 3 / ok_streak 2) **без изменений**.

Verify (repo):

```bash
python ops/test_selfsteal_monitor_antiflap.py
python ops/test_ru_monitor_cert_digest.py
```

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
