# Runbook: несколько origin подписки (P2-RED-SUB-01)

**Задача бэклога:** **`P2-RED-SUB-01`** — ≥2 независимых публичных имени на один backend subscription-page; блокировка одного домена не обнуляет выдачу конфига.

## 1. Схема (прод)

| Роль | Host | Путь | Upstream |
|------|------|------|----------|
| **Primary** | **`p4n7q.conntest.xyz:8443`** | `/api/sub/*` | AMS **`168.100.11.140:3010`** (LV Caddy) |
| **Alternate** | **`k9x2m1.conntest.xyz:8443`** | `/api/sub/*` | тот же AMS **:3010** (отдельное DNS-имя) |
| Панель | **`k9x2m1.conntest.xyz:8443`** | остальное | AMS **:3000** |

Оба имени — edge **bvpn-lv**; разнесение **DNS/SNI**. С **P6-RED-SUBHA-01** alt origin (**k9x2m1**) идёт на второй инстанс sub-page (**AMS :3011**), primary (**p4n7q**) — **:3010**; см. **`docs/RUNBOOK-P6-SUBSCRIPTION-HA.md`**.

## 2. Накат alternate origin на LV

```bash
# с рабочей машины (репо):
scp -P 3344 ops/patch-caddy-sub-alt-origin-lv.sh root@176.126.162.158:/tmp/
ssh bvpn-lv 'bash /tmp/patch-caddy-sub-alt-origin-lv.sh'
```

Эталон Caddy: **`Caddyfile-latvia-full.txt`** (блок **`k9x2m1`** с `handle @sub_path_alt`).

## 3. Конфиг ops (репо)

**`ops/site.env`** (по образцу **`ops/site.env.example`**):

```bash
export SUB_PUBLIC_ORIGIN=https://p4n7q.conntest.xyz:8443
export SUB_ALT_PUBLIC_ORIGINS=https://k9x2m1.conntest.xyz:8443
```

## 4. Мониторинг расхождения

Проверка всех origin на **200/304** и **одинаковый SHA256** тела smoke-подписки:

```bash
python ops/subscription_origin_drift_probe.py
python ops/subscription_origin_drift_probe.py --json
```

Интеграция: **`monitor.sh`** (CHECK alt), **`daily-report.sh`**, **`capacity_snapshot.py`** — при необходимости.

**Алерт:** HTTP ≠ 200/304 на любом origin → Caddy LV, sub-page на AMS. После **P6-RED-SUBHA-01** (split-host) **`body_drift=true` нормален** — проверяйте `python ops/subscription_origin_drift_probe.py --split-host`.

## 5. Инцидент «один домен в реестре»

1. Проверить alternate: `curl -fsSI "https://k9x2m1.conntest.xyz:8443/api/sub/<shortId>"`.
2. Если primary мёртв, а alternate жив — обновить ссылки в боте/FAQ на alternate (временно).
3. Завести новое имя + DNS при долгой блокировке обоих **`*.conntest.xyz`**.

## 6. Связанные файлы

- **`docs/RUNBOOK-P6-SUBSCRIPTION-EDGE.md`** — rate limit, load probe
- **`ops/subscription_load_probe.py`** — нагрузка на один URL
- **`docs/COMMERCIAL-BACKLOG.md` §5.1** — **P6-RED-SUBHA-01** (горизонталь sub-page)
