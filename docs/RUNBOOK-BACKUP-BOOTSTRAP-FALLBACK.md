# Runbook: fallback bootstrap при недоступности основного домена (P2-DOC-BOOTSTRAP-FALLBACK-01)

Дополняет **`docs/RUNBOOK-BACKUP-BOOTSTRAP-DOMAIN.md`** (Q047 live на **p4n7q**).

## Быстрый путь

1. Подтвердить инцидент: `curl -fsSI https://k9x2m1.conntest.xyz:8443/portal/` с RU и EU.
2. Если RU fail / EU OK — включить **alt apex** (Caddy на LV, DNS второго registrar).
3. Обновить FAQ / бот / portal copy — ссылка на зеркало (не подменять канон в `site_urls` без согласования).
4. Probe: `python ops/smoke_public_bootstrap.py`, `python ops/smoke_telegram_miniapp.py`.

## Откат

Снять alt server block; вернуть пользователям основной URL.

## Verify

**`BACKUP_BOOTSTRAP_DOMAIN_OK`** + строка в §12.
