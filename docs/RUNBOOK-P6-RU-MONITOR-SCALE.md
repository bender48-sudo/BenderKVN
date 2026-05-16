# Runbook: RU-monitor cycle time (P6-SCALE-06)

**Цель:** cron **`*/5 * * * *`** на **bvpn-lv** — полный прогон **`ru-monitor.py`** укладывается в **< 5 мин** (300 s).

## Что изменено

- **`ru-monitor.py`**: лог **`duration_sec=`** в каждой сводке; **`JITTER_MAX=60`** (было 120).
- **`ops/ru_monitor_cycle_probe.py`**: читает последнюю строку **`/var/log/bvpn-ru-monitor.log`**.

## Verify на LV

```bash
python3 /opt/scripts/ru_monitor_cycle_probe.py
# ожидать: RU_MONITOR_CYCLE_OK и duration_sec < 300
tail -5 /var/log/bvpn-ru-monitor.log
```

После деплоя дождаться одного cron-тика (≤5 мин) или запустить вручную:

```bash
/opt/scripts/ru-monitor.py
```

## Пороги

| duration_sec | Действие |
|--------------|----------|
| **< 240** | OK |
| **240–300** | WARNING в логе; планировать батчи/параллель |
| **> 300** | FAIL probe; риск наложения cron — срочно оптимизировать |

## Связанные файлы

- **`docs/DEPLOY.md`** §6 — cron и state dirs
- **`docs/COMMERCIAL-BACKLOG.md` §10.2** — **P6-SCALE-06**
