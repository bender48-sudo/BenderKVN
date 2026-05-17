# Runbook: LUKS для Postgres AMS (P1-RED-DATA-01)

## 0. Preconditions

- Gate: **`docs/RUNBOOK-AMS-SAFE-DEPLOY.md`**
- Свежий **`pg_dump`** / **`backup-remnawave`** (LV)
- Ключ LUKS в Bitwarden **`BenderVPN/ams/postgres-luks-key`** (ещё не на VPS)

## 1. Первичное включение (окно ~10–15 мин)

```powershell
cd d:\Va\projects\VPN
pwsh -File ops/deploy-postgres-luks-ams.ps1 -Enable
```

Скрипт запросит LUKS passphrase (или сгенерирует и покажет **один раз** — сразу в Bitwarden).

**Downtime:** `remnawave` + `remnawave-db` остановлены на время `rsync`.

## 2. После reboot VPS

```powershell
# Ключ из Bitwarden — в stdin, не в командной строке:
$sec = Read-Host -AsSecureString "LUKS passphrase"
# или: bw get password "BenderVPN/ams/postgres-luks-key" | ssh ...
ssh bvpn-ams 'bash /opt/scripts/ams_postgres_luks_unlock.sh'
```

Проверка:

```bash
ssh bvpn-ams 'mountpoint /mnt/remnawave-pgdata && docker exec remnawave-db pg_isready -U postgres'
python ops/ams_postgres_crypt_probe.py  # через ssh remote
```

## 3. Smoke

```bash
ssh bvpn-ams 'python3 /opt/scripts/ams_postgres_crypt_probe.py'
# POSTGRES_CRYPT_OK
```

И **`ops/smoke_ams_safe_deploy.py`** — панель/sub.

## 4. Ротация LUKS key (без простоя VPN-пользователей)

Окно: только restart **remnawave-db** (~1–2 мин), пользователи на нодах не отваливаются.

```bash
# На AMS, mapper уже открыт:
NEW_KEY_FILE=/root/luks-new.key   # сгенерировать на workstation, не коммитить
cryptsetup luksAddKey /opt/remnawave/postgres.luks.img /root/luks-old.key $NEW_KEY_FILE
cryptsetup luksRemoveKey /opt/remnawave/postgres.luks.img /root/luks-old.key
rm -f /root/luks-old.key /root/luks-new.key
```

Обновить Bitwarden. Старый ключ — revoke после проверки unlock.

## 5. Откат

Если миграция не завершена: не удалять **`remnawave_remnawave-db-data`** volume до успешного smoke.

Полный откат: restore compose на named volume + `docker compose up` (см. **`ops/PANEL-MIGRATION-ROLLBACK.md`**).
