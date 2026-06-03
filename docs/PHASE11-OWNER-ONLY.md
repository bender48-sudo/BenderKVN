# Фаза 11 — что остаётся только владельцу

Агент закрыл **Q167, Q168, Q170** на проде (AMS cron, smoke OK, шаблон не трогали).

## Одна обязательная ручная операция (Q169)

**Dynadot** → зона `conntest.xyz` → добавить запись:

| Тип | Host | Value |
|-----|------|-------|
| **A** | `n4l8q` | `91.90.192.17` |

TTL 300–600. Без этого TLS и `patch-caddy-sub-backup-nl.sh` на NL не пройдут smoke.

После сохранения DNS (подождать 5–15 мин):

```powershell
cd d:\Va\projects\VPN
pwsh -File ops/finish_phase11_prod.ps1
```

Или только NL:

```powershell
scp -o ConnectTimeout=25 ops/patch-caddy-sub-backup-nl.sh bvpn-nl:/tmp/patch-nl.sh
ssh -o ConnectTimeout=60 bvpn-nl "bash /tmp/patch-nl.sh"
python ops/smoke_sub_jurisdiction_backup.py
```

## Не входит в фазу 11 (как и раньше)

| Задача | Почему не агент |
|--------|------------------|
| **Q032** возвраты в оферте | юридический текст |
| **BotFather** :8443 /portal | ваш Telegram |
| Оплата/включение **LV VPS**, если SSH мёртв | биллинг хостера |
| Recovery-коды Dynadot, DNSSEC | Bitwarden / офлайн |

## Повторный прогон без ручных шагов

`ops/finish_phase11_prod.ps1` — ретраи scp/ssh; безопасен на живом LV (только dry-run / skip).
