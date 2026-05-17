# SSH key inventory (P1-RED-SSH-01)

Цель: **разный blast radius** per host/role — компрометация одного ключа не даёт root на всех VPS.

## Оператор (рабочая станция / Cursor)

| Роль | SSH config `Host` | Локальный ключ (не в git) | На сервере |
|------|-------------------|---------------------------|------------|
| Latvia ops | `bvpn-lv` | `~/.ssh/bvpn_lv_ed25519` | `/root/.ssh/authorized_keys` |
| Amsterdam ops | `bvpn-ams` | `~/.ssh/bvpn_ams_ed25519` | `/root/.ssh/authorized_keys` |
| Netherlands node | `bvpn-nl` | `~/.ssh/bvpn_nl` | `/root/.ssh/authorized_keys` |
| Selectel relay | `bvpn-relay` | `~/.ssh/selectel_relay` | relay `authorized_keys` |

**Запрещено:** один `id_ed25519` в `authorized_keys` на **LV и AMS** одновременно (legacy).

Генерация: **`ops/ssh_rollout_operator_keys.ps1`**. Проверка: **`python ops/ssh_audit.py`** → **`SSH_AUDIT_OK`**.

## Серверные / machine keys (не операторские)

| Ключ на хосте | Назначение | Куда | Ограничение |
|---------------|------------|------|-------------|
| `/root/.ssh/id_ed25519` (LV) | ru-monitor, daily-report → relay/AMS | relay, AMS | Только с LV; не дублировать на NL |
| `/root/.ssh/lv_watchdog` (NL) | NL→LV probe | LV | `command=` в authorized_keys |
| `bvpncheck` (relay) | RU bypass probe | relay | `from=`, `command=` |

Эти ключи **не** заменяют операторские; ротация — отдельные runbook'и (`ru-monitor`, watchdog).

## Bitwarden / учёт

Для каждого операторского ключа: item **`BenderVPN/ssh/<host>`**, поле **public**, приватный только в `~/.ssh` (backup encrypted).

## Аудит

```powershell
cd d:\Va\projects\VPN
python ops/ssh_audit.py
```

Критерий **PASS**: нет **одинакового unrestricted** pubkey на двух из `bvpn-lv` / `bvpn-ams` / `bvpn-nl`; локально `bvpn_lv_ed25519` ≠ `bvpn_ams_ed25519`.

См. также: **`docs/RUNBOOK-SSH-KEY-ROLLOUT.md`**, **`ssh/config.example`**, **`docs/SSH-HOST-KEY-PRACTICE.md`**.
