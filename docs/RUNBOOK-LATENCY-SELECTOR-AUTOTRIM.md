# Runbook: latency selector autotrim (VPN-AUD-310)

**Назначение:** server-side trim `Intl_Direct` / `Intl_Stealth` selectors на LV при деградации relay или NL — без observatory и без PATCH injectHosts.

**Хост:** `bvpn-lv` (`/etc/bvpn/ru-monitor.env`, cron каждые 15 мин).

---

## Компоненты

| Файл | Роль |
|------|------|
| `ops/relay_latency_probe.py` | TCP latency к RU relay IP |
| `ops/nl_reachability_probe_ru.py` | NL :443 reachability из RU |
| `ops/latency_selector_autotrim.py` | dry-run / `--apply` PATCH selector |
| `ops/run_latency_selector_autotrim.sh` | wrapper с token из env |
| `ops/install_latency_autotrim_cron.sh` | cron `/etc/cron.d/bvpn-latency-autotrim` |
| `ops/smoke_latency_selector_autotrim.py` | статический smoke + dry-run |

---

## Deploy

```powershell
powershell -File ops/deploy_lv_vpn_ops.ps1
```

На LV:

```bash
bash /opt/scripts/install_latency_autotrim_cron.sh   # idempotent
grep bvpn-latency /etc/cron.d/bvpn-latency-autotrim
```

---

## Verify (gate / smoke)

**Workstation (без RU probe):**

```bash
python ops/smoke_latency_selector_autotrim.py
```

**На LV (полный dry-run + RU probes):**

```bash
ssh bvpn-lv 'set -a; . /etc/bvpn/ru-monitor.env; set +a; python3 /opt/scripts/latency_selector_autotrim.py'
# ожидание: [autotrim] no selector change  или  Dry-run
```

**Cron log:**

```bash
ssh bvpn-lv 'tail -20 /var/log/bvpn-latency-autotrim.log'
```

**Gate (включает autotrim dry-run на LV):**

```bash
ssh bvpn-lv 'bash /opt/scripts/vpn_verify_gate.sh'
```

---

## Поведение

- **Hysteresis:** 2 плохих probe → trim; 3 OK → restore.
- **Relay:** trim целого медленного relay IP (min 3 path).
- **NL:** drop proxy-7..10 из selector если RU probe fail (injectHosts не трогаем).
- **Оба relay dead:** no PATCH.
- **`--apply`:** только при изменении selector; затем `subscription_config_notify`.

---

## NO-GO

1. PATCH injectHosts из autotrim (только selector).
2. `relay_failover_template.py` на gen≥47 (использовать autotrim).
3. Observatory на прод без staging A/B.

---

## Откат

Snapshot перед PATCH: `.secrets/snapshots/` на машине, где запускали `--apply`.

Восстановление: PATCH template из snapshot + `subscription_config_notify`.
