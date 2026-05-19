# Runbook: резервный канал статуса (P2-RED-BOOT-01)

**Зачем:** при блокировке **Telegram API** из РФ операторы всё ещё видят состояние сервиса по **HTTPS JSON** на отдельном домене.

## Два канала

| Канал | Как | Когда использовать |
|-------|-----|----------------------|
| **Telegram** | `/status` в админ-боте, алерты `monitor.sh` / `ru-monitor` | Основной, если API TG доступен |
| **HTTPS mirror** | `GET` **`https://k9x2m1.conntest.xyz:8443/api/ops/status.json`** | Резерв: браузер/curl с любой сети без TG |

URL настраивается через **`ops/site_urls.py`** (`STATUS_MIRROR_ORIGIN`, `STATUS_MIRROR_PATH`).

## Обновление JSON

На **bvpn-lv** cron ***/2** запускает **`build_status_mirror.py`** → `/var/www/bvpn-status/status.json`.

Ручной прогон:

```bash
source /etc/bvpn/balancer.env
python3 /opt/scripts/build_status_mirror.py
```

## Verify

```bash
python ops/smoke_status_channels.py
# ожидать: STATUS_CHANNELS_OK
```

## Quarterly drill «TG недоступен»

Раз в квартал (календарь в private wiki):

1. С рабочей станции в сети **без** VPN или с симуляцией блока TG — `curl -I https://api.telegram.org/` (может fail).
2. **`python ops/smoke_status_channels.py`** — mirror **200**, JSON свежий (`updated_at` < 10 мин).
3. Открыть mirror URL в браузере — `overall`, `nodes`, `subscription`.
4. Записать дату в **`COMMERCIAL-BACKLOG.md` §12**.

## Деплой

```powershell
pwsh -File ops/deploy-status-mirror-lv.ps1
```

См. также **`docs/RUNBOOK-INCIDENT.md`** § «Каналы связи».
