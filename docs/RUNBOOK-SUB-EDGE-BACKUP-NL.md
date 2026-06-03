# Runbook: backup subscription edge на NL (jurisdiction)

**Скрипт:** `ops/patch-caddy-sub-backup-nl.sh`  
**Probe:** `ops/smoke_sub_jurisdiction_backup.py`

## Зачем

При **мёртвом LV VPS** (p4n7q/k9x2m1 на `176.126.162.158`) HTTPS подписка недоступна, хотя AMS sub-page и NL VPN живы. Backup edge на **NL** (`91.90.192.17`, **`:4433`**) проксирует `/api/sub/*` → AMS `:3010`. На NL **`:8443`** занят **rw-core** (VPN alt inbound), не Caddy.

## DNS (владелец / Dynadot)

| FQDN | A record |
|------|----------|
| **n4l8q.conntest.xyz** | **91.90.192.17** (bvpn-nl) |

TTL 300–600 при инциденте.

## Firewall AMS

На AMS **3010/3011** закрыты для интернета (**P0-SEC-03**). Для backup edge разрешите **NL** (`91.90.192.17`) в **`ops/bvpn-docker-firewall.sh`** (`SUB_ALLOW_IPS`) и примените на AMS:

```bash
SUB_PORTS="3010 3011" bash /usr/local/sbin/bvpn-docker-firewall.sh
```

## Установка (один раз)

На NL backup edge — блок в **`caddy-selfsteal`** (`/opt/caddy/Caddyfile`, маркер `SUB_JURISDICTION_BACKUP_NL`), не отдельный контейнер на **:8443** (там **rw-core**).

```powershell
scp -o ConnectTimeout=20 ops/patch-caddy-sub-backup-nl.sh bvpn-nl:/tmp/
ssh -o ConnectTimeout=30 bvpn-nl "sed -i 's/\r$//' /tmp/patch-caddy-sub-backup-nl.sh; bash /tmp/patch-caddy-sub-backup-nl.sh"
```

При **нестабильном SSH** к LV/AMS: скрипты failover крутить с рабочей станции (`python ops/lv_node_down_nl_failover.py --status`), cron — на **AMS** (`deploy_ams_node_resilience.ps1`) когда `bvpn-ams` снова принимает `scp`.

## Env (репо / `ops/site.env`)

```bash
export SUB_JURISDICTION_BACKUP_ORIGIN=https://n4l8q.conntest.xyz:4433
```

`ops/site_urls.py` включает origin в `sub_all_probe_urls()` для drift probe.

## Smoke

```bash
python ops/smoke_sub_jurisdiction_backup.py
python ops/subscription_origin_drift_probe.py --split-host
```

Ожидаем **HTTP 200/304** на backup при живом AMS (тело может отличаться от k9x2m1 в split-host режиме).

## Пользователи

При падении LV edge: выдать backup URL в поддержке / статусе:

`https://n4l8q.conntest.xyz:4433/api/sub/<shortId>`

(тот же shortId, что в панели). После восстановления LV — снова основной origin из бота.

## Связанные документы

- `docs/RUNBOOK-JURISDICTION-FAILOVER.md` § A.2
- `docs/RUNBOOK-LV-DOWN-NL-FAILOVER.md` — трафик VPN (template), не HTTPS sub
