# VPN Diagnostic Report — 2026-05-25

Systematic top-down check (CodeRabbit plan). Live probes from workstation + SSH `bvpn-lv` / `bvpn-ams` / `bvpn-nl`.

---

## Executive summary

| Layer | Verdict | Primary signal |
|-------|---------|----------------|
| **Infrastructure** | **OK** | LV/NL nodes up, Xray 26.3.27, Caddy active, AMS PG/Redis healthy |
| **Network** | **OK** | :443/:8443/:9443 listening on LV; panel API 200 |
| **Subscription** | **OK** (post gen=20) | 10565 B, 14 proxy, RELAY+LV+NL, no xhttp, no observatory |
| **Application / bot** | **OK** (post deploy) | `SUB_REFRESH_JITTER_MAX_SEC=300` на AMS; monitor без NameError |
| **TSPU / external** | **Stale data** | `ru-monitor` state.json last check **2026-05-19**; `bvpn-monitor.log` fresh **2026-05-25** |

**Root cause of «весь день не работает / не дошли пуши» (cascade):**

1. **Template regressions** (observatory `closed pipe`, injectHosts без Relay) — **исправлено** gen=18–20.
2. **Bot scheduler bug** — цикл мониторинга падает **до** рассылки `MSG_SUB_CONFIG_REFRESH`; очередь 63+ пользователей не обрабатывалась автоматически.
3. **Happ `UnknownContentType`** — ожидаемо для Virtual Host (1 JSON-профиль); не блокирует туннель при Append custom.

---

## Phase 1 — Infrastructure

### Latvia (176.126.162.158)

| Check | Result |
|-------|--------|
| `remnanode` | Up 6 days |
| `adguardhome` | Up 5 weeks |
| `systemctl caddy` | **active** |
| `xray version` | **26.3.27** |
| OOM kills | None in recent dmesg |
| Ports | :443 (rw-core), :8443/:9443 (caddy) |

### Amsterdam (168.100.11.140)

| Check | Result |
|-------|--------|
| `remnawave`, `remnawave-db`, `remnawave-redis` | Up, healthy |
| `remnawave-subscription-page` (+b) | Up |
| `remna-shop-bot` | Up 18h |
| `remnanode` on AMS | **Not running** (ожидаемо: AMS decom, панель только) |
| `pg_isready` | **accepting connections** |
| `valkey-cli ping` | **PONG** |

### Netherlands

| Check | Result |
|-------|--------|
| `remnanode` | Up 9 days, Xray 26.3.27 |

### Russia Relay (72.56.0.145)

| Check | Result |
|-------|--------|
| SSH :3344 | Timeout from probe host (не подтверждено в этом прогоне) |
| Sub config | **RELAY→LV ×3, RELAY→NL ×3** в live sub (gen=20) |

---

## Phase 2 — Network / panel

| Check | Result |
|-------|--------|
| LV :443/:8443/:9443 | Listening |
| Panel nodes API | Latvia **connected**, 14 users; NL **connected**, 2 users; Amsterdam-01 **not connected** (0 users) |
| Panel spam | `ECONNREFUSED 168.100.11.140:2222` — попытки поднять AMS node (шум, не P0) |

---

## Phase 3 — Subscription flow

Probe user `HrHLoNuL_7x8JD3n-YBovJso4` / client `trwQJNNKr65fsfPpJShCcXpXU`:

| Check | Result |
|-------|--------|
| `p4n7q:8443` / `:2053` | HTTP **200** |
| Size | **10565 bytes** |
| Outbounds | **16** (14 vless/tcp proxy) |
| xhttp | **0** |
| burstObservatory | **absent** |
| Balancer | **random** |
| Paths | LV×4, NL×4, RELAY×6 |
| `diagnose_happ_import` | **batch_risk=LOW** |

---

## Phase 4 — Known bugs

### P0 — Bot scheduler (`SUB_REFRESH_JITTER_MAX_SEC`)

```
Monitor loop critical error: name 'SUB_REFRESH_JITTER_MAX_SEC' is not defined
```

- Повторяется **каждые 5 минут** в `docker logs remna-shop-bot` на AMS.
- Ломает **весь** цикл `start_subscription_monitor` (не только sub refresh): auto-renew, expiry notify, **очередь обновления подписки**.
- **Fix in repo:** `bot_src/subscription_refresh.py` — `SUB_REFRESH_JITTER_MAX_SEC = 300`.
- **Deployed:** `deploy-bot-sub-refresh-ams.ps1` (2026-05-25), `sub_config_generation=20` без смены шаблона.

### Other

| Check | Result |
|-------|--------|
| `REMNA_PUBLIC_KEY` / `REMNA_API_TOKEN` on bot | Set |
| `ValueError: too many values` (provision_key) | Not seen in recent logs |

---

## Phase 5 — External / monitoring

| Source | Result |
|--------|--------|
| `/var/lib/bvpn-ru-monitor/state.json` (LV) | Last checks **2026-05-19** — устарело для «сейчас» |
| `/var/log/bvpn-monitor.log` | **2026-05-25 17:30** — monitor.sh жив |
| RU relay live probe | Не завершён (SSH timeout) |

---

## Remediation matrix

| Failure mode | Action |
|--------------|--------|
| Sub без Relay / observatory | **Done** — `patch_restore_14_relay_no_obs`, gen=20 |
| Пуши не доходят | **Done** — bot deploy; очередь догоняется батчами; ручной notify при необходимости |
| Медленно IG/TG/Google при рабочем VPN | **Open** — random balancer на RELAY; см. **`VPN-INCIDENT-LESSONS-2026-05-25.md` §4** |
| Happ «0 servers» | Объяснить: Virtual Host = 1 профиль; обновить подписку 🔄 |
| AMS node 2222 errors | Отключить/скрыть Amsterdam-01 в панели или принять как decom-noise |
| ru-monitor stale | Запустить `ru-monitor.py` на LV / проверить cron |
| Relay SSH | Проверить с LV: `ssh -p 3344 root@72.56.0.145` |

---

## Verify loop (after bot deploy)

```bash
python ops/probe_subscription.py
python ops/diagnose_happ_import.py
ssh bvpn-ams "docker logs remna-shop-bot --since 10m 2>&1 | grep -i SUB_REFRESH_JITTER || echo OK_no_jitter_error"
```

---

*Updated: 2026-05-25. Template gen=20; bot jitter fix deployed. Speed tuning — follow lessons doc §4.*

См. также **`docs/VPN-INCIDENT-LESSONS-2026-05-25.md`** — полный реестр ошибок и запретов.
