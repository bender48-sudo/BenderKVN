# Runbook: публичный статус инцидентов (P5-COM-01)

**URL (прод):** **`https://k9x2m1.conntest.xyz:2053/status`** — HTML для пользователей, **без** доступа к админ-Telegram.

**Технический JSON (ops):** **`/api/ops/status.json`** — **`RUNBOOK-P2-STATUS-BOOT-CHANNEL`**.

## Как обновляется

| Что | Где |
|-----|-----|
| Автоматика (ноды, подписка) | Cron LV ***/2** → **`build_status_mirror.py`** → `/var/www/bvpn-status/status.json` + **`index.html`** |
| Ручные инциденты | **`/var/www/bvpn-status/incidents.json`** на LV (редактировать по SSH) |

Пример формата инцидентов: **`ops/incidents.public.example.json`**.

```bash
# на LV после правки incidents.json:
PYTHONPATH=/opt/scripts python3 /opt/scripts/build_status_mirror.py \
  -o /var/www/bvpn-status/status.json
```

## Публикация сообщения при дауне

1. Создать/обновить **`incidents.json`** (статус `investigating` → `resolved`).
2. Пересобрать HTML (команда выше или дождаться cron ≤2 мин).
3. Пользователям — ссылка на **`/status`** + шаблон **`docs/templates/USER-INCIDENT-BROADCAST.md`**.
4. Строка в **`COMMERCIAL-BACKLOG.md` §12**.

## Деплой / Caddy

```powershell
pwsh -File ops/deploy-public-status-page-lv.ps1
```

Патч Caddy идемпотентный (**`PUBLIC_STATUS_PAGE_01`**). Эталон: **`Caddyfile-latvia-full.txt`**.

## Проверка

```powershell
python ops/smoke_public_status_page.py
# ожидать: PUBLIC_STATUS_PAGE_OK
```

## Что не класть на страницу

- Токены, IP внутренних сервисов, stack trace, имена хостов провайдера.
- Полный список нод с внутренними именами (на HTML — только агрегат «Серверы VPN»).
