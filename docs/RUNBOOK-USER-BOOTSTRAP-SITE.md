# Runbook: bootstrap-сайт /start (P3-FLOW-01)

**URL (прод):**

| Путь | Назначение |
|------|------------|
| `https://k9x2m1.conntest.xyz:8443/start/` | Bootstrap без VPN (главная) |
| `https://k9x2m1.conntest.xyz:8443/portal/` | То же для Telegram Mini App |
| `https://k9x2m1.conntest.xyz:8443/setup?t=…` | Персональная выдача: QR + копирование ссылки (P3-FLOW-02) |

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

## Setup token (P3-FLOW-02)

Секрет на LV: **`/etc/bvpn/portal-setup.env`** (`PORTAL_SETUP_HMAC_SECRET`). Не в git.

```bash
# на LV:
set -a; . /etc/bvpn/portal-setup.env
PYTHONPATH=/opt/scripts python3 /opt/scripts/portal_setup_token.py sign --short-id SHORTID
# → URL: https://k9x2m1.conntest.xyz:8443/setup?t=TOKEN
```

Сервис verify: **`bvpn-setup-verify.service`** (`127.0.0.1:8871`), Caddy **`/setup/api/*`**.

Деплой setup:

```powershell
pwsh -File ops/deploy-portal-setup-lv.ps1
```

## Проверка

```powershell
python ops/smoke_public_bootstrap.py
python ops/smoke_portal_setup_page.py
# PUBLIC_BOOTSTRAP_OK / PORTAL_SETUP_PAGE_OK
```

## Rollback

1. Восстановить Caddy из бэкапа `Caddyfile.bak-pre-user-portal-*`.
2. `systemctl restart caddy`.
3. Каталог `/var/www/bvpn-portal/` можно оставить.
