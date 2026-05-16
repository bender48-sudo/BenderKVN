# Runbook — логирование края подписки без токена в URL

**Связь:** **`P1-RED-LOG-01`** в **`docs/COMMERCIAL-BACKLOG.md` §5.1**.

## Зачем

Публичный URL подписки содержит идентификатор конфига; при обычном access-log запись может сохранять **полный URI** в JSON или combined-форме. При централизованных логах и бэкапах журналов это увеличивает blast radius наблюдений («чёрная шляпа» из бэклога).

**Цель:** для сайта Caddy с **`/api/sub/*`** не писать access-line matcher-ом через **`log_skip`**.

## Где живёт прод

Основной edge для **`SUB_PUBLIC_ORIGIN`** (см. **`ops/site.env.example`**) сейчас на **LV** — блок типа **`p4n7q….:2053`** в **`/etc/caddy/Caddyfile`**. Эталон в репо: **`Caddyfile-latvia-full.txt`**.

При добавлении **второго** публичного имени того же профиля — для каждого server-блока повторить фрагмент перед **`log {`**:

```caddyfile
    @sub_path path /api/sub/*
    log_skip @sub_path

    log {
        output file /var/log/caddy/sub-access.log {
            roll_size 10mb
            roll_keep 3
        }
        format json
    }
```

## Как применить на живом LV

| Сценарий | Файл |
|----------|------|
| Патч + validate + restart | **`ops/patch-caddy-logskip-inplace.sh`** |
| Альтернатива через восстановление фиксированного `.bak`** | **`ops/fix-caddy-security.sh`** |

Smoke после: **`curl`** к probe-URL подписки → **200**; затем проверить, что новые записи **`sub-access.log`** не содержат свежего пути **`/api/sub/…`** (старые строки возможны до ротации).

## Retention и доступ

**`roll_size`/`roll_keep`** — минимум для расследований; доступ к файлу ограничить; согласовать с **`P3-TR-01`**.
