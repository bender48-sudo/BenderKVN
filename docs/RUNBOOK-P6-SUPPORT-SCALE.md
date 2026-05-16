# Runbook: поддержка при росте (P6-SCALE-07)

**Цель:** измеримая очередь тикетов, SLA первого ответа, шаблоны и эскалация во вторую линию.

## SLA

| Уровень | Цель |
|---------|------|
| Первый ответ пользователю | **≤ 60 мин** в рабочее окно (**`RUNBOOK-INCIDENT`**) |
| Эскалация инфраструктуре | При массовом дауне или breach SLA |

## Метрика очереди

```bash
python ops/support_queue_snapshot.py
# с AMS (по умолчанию scp БД):
python ops/support_queue_snapshot.py --ssh-host bvpn-ams
```

| Поле | Смысл |
|------|--------|
| `pending_reply` | Топики, где последнее сообщение от пользователя без ответа |
| `pending_sla_breach` | Ожидают ответ **> 60 мин** |
| `tickets_24h` | Обращения за сутки |
| `escalate_second_line` | **true** если `pending_reply≥15` **или** `tickets_24h≥25` |

Exit **0** → `SUPPORT_QUEUE_OK`. Exit **1** при `pending_sla_breach>0`.

## Бот (AMS)

Топики форума в **`SUPPORT_GROUP_ID`**; метки времени в SQLite:

- `support_last_user_at` — входящее от пользователя
- `support_last_staff_at` — ответ из группы поддержки

Деплой: **`pwsh -File ops/deploy-bot-support-queue-ams.ps1`** (перезапуск `remna-shop-bot`).

## Шаблоны

- **`docs/templates/SUPPORT-REPLY-TEMPLATES.md`**
- **`docs/support/USER-FACING-ERRORS.md`**
- Инцидент пользователям: **`docs/templates/USER-INCIDENT-BROADCAST.md`**

## Еженедельно (GTM)

Вместе с **`capacity_snapshot.py`** — один прогон **`support_queue_snapshot.py`**; при `escalate_second_line` — не наращивать рекламу до разгрузки очереди.
