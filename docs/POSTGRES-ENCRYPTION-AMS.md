# Postgres encryption at rest — AMS (P1-RED-DATA-01)

## Схема

| Слой | Реализация |
|------|------------|
| Данные | PostgreSQL в Docker → bind mount **`/mnt/remnawave-pgdata`** |
| Том | Файл **`/opt/remnawave/postgres.luks.img`** (LUKS2, 2 GiB) |
| Mapper | **`/dev/mapper/remnawave-pg`** |
| Ключ LUKS | **Не на диске AMS** — Bitwarden **`BenderVPN/ams/postgres-luks-key`** (+ офлайн копия) |
| После reboot | Ручной unlock: **`ops/ams_postgres_luks_unlock.sh`** (ключ с workstation) |

**Почему не named Docker volume:** LUKS-том монтируется на хосте до `docker compose up`.

## Проверка

```bash
ssh bvpn-ams 'python3 /opt/scripts/ams_postgres_crypt_probe.py'
# → POSTGRES_CRYPT_OK
```

## Ротация ключа LUKS

См. **`docs/RUNBOOK-POSTGRES-LUKS-AMS.md` §4** (`cryptsetup luksKeySlot`).

## Связанные файлы

- **`ops/ams_postgres_luks_enable.sh`** — первичная миграция (окно обслуживания)
- **`ops/ams_postgres_luks_unlock.sh`** — unlock после перезагрузки
- **`compose/ams/remnawave/docker-compose.yml.tmpl`** — bind mount
- Gate: **`docs/RUNBOOK-AMS-SAFE-DEPLOY.md`**
