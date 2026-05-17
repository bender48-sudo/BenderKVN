# Внутренний инвентарь данных (P3-RED-MIN-01)

Только для ops/разработки. Не публиковать сырые пути прод-хостов.

## Bot SQLite (`shop_bot.db` на AMS)

| Таблица | Поле | Класс | Retention |
|---------|------|-------|-----------|
| users | telegram_id | identifier | life of account |
| users | username | optional PII | life of account |
| users | balance, total_spent | billing | life of account |
| vpn_keys | vless_uuid, key_email | technical | key lifetime |
| webhook_deliveries | payload_json | **redacted** billing ref | **90d** |
| user_actions | action, meta | ops / idempotency | 365d |

Полный машиночитаемый список: **`ops/data_field_inventory.json`**.

## Remnawave Postgres (AMS)

- Пользователи панели, ноды, hosts, шаблоны подписки  
- **Не** дублируем PAN/карту; JWT API — machine tokens (**`docs/SECRETS.md`**)  
- Том: LUKS **`docs/POSTGRES-ENCRYPTION-AMS.md`**

## Запрещённые поля (не добавлять без review)

`card_number`, `cvv`, `passport`, `phone`, `home_address`, `gps_*`, полный raw webhook body.

## Код

| Требование | Файл |
|------------|------|
| Redact webhook before SQLite | `bot_src/webhook_server/payload_redact.py` |
| Legal URLs | `bot_settings.terms_url`, `privacy_url` |

## Smoke

```bash
python ops/data_minimization_audit.py
# docker exec remna-shop-bot python /opt/scripts/data_minimization_audit.py
```
