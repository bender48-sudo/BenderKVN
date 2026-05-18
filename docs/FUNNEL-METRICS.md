# Метрики воронки (P3-FLOW-10)

**События без PII** — только имена шагов и хэш IP на LV.

## Portal (браузер / Mini App)

| Событие | Когда |
|---------|--------|
| `portal_view_home` | Главная `/start` или `/portal` |
| `portal_view_devices` | Экран выбора устройства |
| `portal_device_*` | Ветка iphone / android / windows / mac |
| `portal_view_cabinet` | Личный кабинет |
| `portal_cabinet_load` | Запрос баланса |

Лог на LV: **`/var/log/bvpn-funnel.jsonl`** (`POST /setup/api/funnel-event` → `setup_verify_service.py`).

## Бот

| `user_actions.action` | Когда |
|-----------------------|--------|
| `funnel_bot_start` | `/start` |
| `wizard_start` / `wizard_device` | Мастер подключения |

## Еженедельный срез (§12)

```bash
# LV
wc -l /var/log/bvpn-funnel.jsonl
rg -o '"event":"[^"]+"' /var/log/bvpn-funnel.jsonl | sort | uniq -c | sort -rn | head

# AMS (бот)
sqlite3 shop_bot.db "SELECT action, COUNT(*) FROM user_actions WHERE action LIKE 'funnel%' OR action LIKE 'wizard%' GROUP BY 1;"
```

Цели GTM — **`docs/GTM-GROWTH-OUTLINE.md`**.
