# Runbook: per-host operator SSH keys (P1-RED-SSH-01)

## 1. Сгенерировать ключи (Windows)

```powershell
cd d:\Va\projects\VPN
pwsh -File ops/ssh_rollout_operator_keys.ps1 -GenerateOnly
```

Создаёт (если нет): `bvpn_lv_ed25519`, `bvpn_ams_ed25519`. **`bvpn_nl`** — как раньше, отдельно.

## 2. Добавить pubkey на сервер (не удаляя старый)

```powershell
pwsh -File ops/ssh_rollout_operator_keys.ps1 -InstallLv
pwsh -File ops/ssh_rollout_operator_keys.ps1 -InstallAms
```

Проверка входа **новым** ключом:

```powershell
ssh -i $env:USERPROFILE\.ssh\bvpn_lv_ed25519 -p 3333 root@176.126.162.158 "hostname"
ssh -i $env:USERPROFILE\.ssh\bvpn_ams_ed25519 -p 3344 root@168.100.11.140 "hostname"
```

Обновить **`%USERPROFILE%\.ssh\config`** по **`ssh/config.example`**.

## 3. Smoke + audit

```powershell
.\scripts\ssh-smoke-test.ps1
python ops/ssh_audit.py
```

Ожидается **`SSH_AUDIT_OK`**.

## 4. Убрать legacy shared key (после входа новыми ключами)

```powershell
# Проверка новых ключей (обновите ~/.ssh/config из ssh/config.example):
ssh -o IdentitiesOnly=yes -i $env:USERPROFILE\.ssh\bvpn_lv_ed25519 -p 3333 root@176.126.162.158 hostname
ssh -o IdentitiesOnly=yes -i $env:USERPROFILE\.ssh\bvpn_ams_ed25519 -p 3344 root@168.100.11.140 hostname

pwsh -File ops/ssh_remove_legacy_shared_key.ps1
python ops/ssh_audit.py
```

Если **LV/AMS не отвечают** по SSH — подождите 10–30 мин (fail2ban) или зайдите с панели хостера, затем повторите.

## 5. Restricted keys (опционально, уже на LV)

Для NL watchdog на LV — оставить отдельную строку с `command="/usr/local/sbin/bvpn-watchdog-probe"`. Не смешивать с операторским ключом.

## Откат

До удаления legacy-ключа вход по старому `id_ed25519` сохраняется. Backup `authorized_keys`:

```bash
cp -a /root/.ssh/authorized_keys /root/.ssh/authorized_keys.bak-$(date +%Y%m%d)
```
