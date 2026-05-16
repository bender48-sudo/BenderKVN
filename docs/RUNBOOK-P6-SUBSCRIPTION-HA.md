# Runbook: горизонталь subscription-page (P6-RED-SUBHA-01)

**Цель:** пик «утреннего stampede» обновлений подписок не упирается в **один** процесс `remnawave-subscription-page`.

## Схема (split-host на проде)

| Публичный origin | Caddy (bvpn-lv) | AMS backend |
|------------------|-----------------|-------------|
| **p4n7q.conntest.xyz:2053** `/api/sub/*` | rate limit **120/min/IP** | **:3010** `remnawave-subscription-page` |
| **k9x2m1.conntest.xyz:2053** `/api/sub/*` | rate limit **120/min/IP** | **:3011** `remnawave-subscription-page-b` |

Оба инстанса читают одну панель (`http://remnawave:3000`). Happ/клиенты с двумя URL в подписке распределяют refresh между origin’ами.

## Накат

1. **AMS** — второй сервис в compose + firewall:
   - `compose/ams/remnawave-sub/docker-compose.yml.tmpl` (сервис **`remnawave-subscription-page-b`**)
   - `pwsh -File ops/deploy-sub-page-ha-ams.ps1` **или** вручную: `docker compose up -d` в `/opt/remnawave/sub`, затем  
     `SUB_PORTS="3010 3011" bash ops/bvpn-docker-firewall.sh`
2. **LV** — Caddy split-host:
   - `bash ops/patch-caddy-sub-split-host-lv.sh` (на **bvpn-lv**)
3. **Verify:**
   - `bash ops/smoke_sub_page_ha.sh` (на LV) → **`SUB_PAGE_HA_SPLIT_HOST_OK`**
   - `python ops/subscription_ha_load_probe.py --total 60 --concurrency 15` → **`SUB_HA_LOAD_PROBE_OK`**

## Критерий закрытия бэклога

Нагрузочный тест **N** параллельных GET на **оба** origin без роста **p95** и без массовых **502** (см. baseline **P6-SCALE-04c**: p95≈**1.83s** при **120** req, **c=30** на primary).

## Откат

1. LV: восстановить Caddy из `Caddyfile.bak-pre-subha-split-*` (k9x2m1 снова на **:3010**).
2. AMS: `docker compose stop remnawave-subscription-page-b`; firewall `SUB_PORTS=3010`.

## Связанные файлы

- **`docs/RUNBOOK-P6-SUBSCRIPTION-MULTI-ORIGIN.md`** — два DNS-имени (P2-RED-SUB-01)
- **`docs/RUNBOOK-P6-SUBSCRIPTION-EDGE.md`** — rate limit / load probe (P6-SCALE-04)
- **`ops/subscription_load_probe.py`**, **`ops/subscription_ha_load_probe.py`**
