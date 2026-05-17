# Runbook: retention и purge (P3-RED-MIN-01)

## Webhook deliveries (bot)

```sql
-- На AMS внутри remna-shop-bot или sqlite3 data/shop_bot.db
DELETE FROM webhook_deliveries
 WHERE status = 'done'
   AND updated_at < datetime('now', '-90 days');
VACUUM;
```

Рекомендация: monthly cron на AMS (окно с низкой нагрузкой).

## user_actions

Удалять строки старше **365 дней** (если политика подтверждена юристом):

```sql
DELETE FROM user_actions WHERE created_at < datetime('now', '-365 days');
```

## Запрос пользователя «удалить данные»

1. Деактивировать ключи в панели (admin).  
2. Удалить строки `users` / `vpn_keys` по `telegram_id` в bot DB.  
3. Панель: удалить user по процедуре Remnawave (если требуется полное удаление).  
4. Зафиксировать тикет в support log (без копии лишних PII).

## Проверка

```bash
python ops/data_minimization_audit.py
```
