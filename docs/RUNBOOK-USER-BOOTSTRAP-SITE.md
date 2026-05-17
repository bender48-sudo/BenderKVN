# Runbook: bootstrap-сайт /start (P3-FLOW-01)

**URL (прод):**

| Путь | Назначение |
|------|------------|
| `https://k9x2m1.conntest.xyz:2053/start/` | Bootstrap без VPN (главная) |
| `https://k9x2m1.conntest.xyz:2053/portal/` | То же для Telegram Mini App |
| `https://k9x2m1.conntest.xyz:2053/setup/` | Выдача конфига (заглушка до Q036) |

Контент: **`web/portal/`** → **`/var/www/bvpn-portal/`** на **bvpn-lv**.

## Отличие от бота

| | Бот | Сайт |
|---|-----|------|
| Выбор устройства | Нет шага; сразу **App Store** / **Google Play** | Сначала **4 платформы** (iPhone, Android, Windows, Mac) |
| Windows/Mac | Пока только на сайте | Инструкции в `ru.json` |

## Деплой

```powershell
pwsh -File ops/deploy-user-portal-lv.ps1
```

Идемпотентный маркер Caddy: **`USER_PORTAL_BOOT_01`**. Эталон: **`Caddyfile-latvia-full.txt`**.

## Проверка

```powershell
python ops/smoke_public_bootstrap.py
# PUBLIC_BOOTSTRAP_OK
```

## Rollback

1. Восстановить Caddy из бэкапа `Caddyfile.bak-pre-user-portal-*`.
2. `systemctl restart caddy`.
3. Каталог `/var/www/bvpn-portal/` можно оставить.
