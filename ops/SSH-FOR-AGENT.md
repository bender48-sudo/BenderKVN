# SSH для работы агента Cursor

Агент **не получает отдельный логин**. Он выполняет команды в **вашем** терминале Cursor на Windows. Если у вас работает `ssh bvpn-lv`, сможет и агент (когда вы просите «зайди на сервер и …»).

## 1. Один раз: ключ и config

1. Per-host ключи (**P1-RED-SSH-01**): `pwsh -File ops/ssh_rollout_operator_keys.ps1 -GenerateOnly`, затем `-InstallLv` / `-InstallAms`. Инвентарь: **`docs/SSH-KEY-INVENTORY.md`**.
2. Скопируйте блоки из `ssh/config.example` в **`%USERPROFILE%\.ssh\config`** (`bvpn_lv_ed25519`, `bvpn_ams_ed25519`, `bvpn_nl`, relay).
3. Аудит: `python ops/ssh_audit.py` → **`SSH_AUDIT_OK`**.

Права на Windows для OpenSSH: ключ и `config` должны быть доступны только вам (при необходимости см. [документацию OpenSSH для Windows](https://learn.microsoft.com/windows-server/administration/openssh/openssh_keymanagement)).

**EU-хосты:** `bvpn-lv` / `bvpn-ams` / `bvpn-nl` — **разные** `IdentityFile` (см. `ssh/config.example`).

## 2. Проверка

```powershell
cd d:\Va\projects\VPN
.\scripts\ssh-smoke-test.ps1
```

Если какой-то хост падает — смотрите сообщение ssh (порт, ключ, `authorized_keys`).

## 3. Бэкап перед правкой

Делайте снимок **до** изменения (пример для Latvia; пути подставьте под свою задачу):

Удалённая команда в **одинарных** кавычках, чтобы PowerShell не трогал `$(...)`.

```powershell
ssh bvpn-lv 'ts=$(date +%s); tar czf /root/bvpn-backup-$ts.tgz -C /etc bvpn 2>/dev/null; ls -la /root/bvpn-backup-*.tgz | tail -3'
```

Для каталога со стеком (подставьте реальный путь):

```powershell
ssh bvpn-lv 'ts=$(date +%s); mkdir -p /root/stacks-bak && cp -a /path/to/compose/dir /root/stacks-bak/$ts'
```

Храните бэкапы на сервере и периодически выгружайте критичное off-box.

## 4. Как просить агента

Формулировки вроде: «Подключись по `ssh bvpn-lv`, сделай X, перед этим бэкап каталога Y» — после шага 1–2 это выполнимо из Cursor.

## 5. Безопасность

- Не вставляйте приватные ключи и пароли в чат.
- Не коммитьте `config` с секретами, если репозиторий когда-либо станет публичным; держите личный `~/.ssh/config` локально.
- Для прод-правок со временем лучше отдельный пользователь с `sudo` и минимальными правами вместо постоянного `root`.
