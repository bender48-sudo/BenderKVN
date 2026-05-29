# Runbook: второй RU relay VPS (P2-DOC-RU-RELAY-02-01 / Q120)

**Владелец:** **Q120** `P2-OPS-RU-RELAY-02-VPS-01` — агент не блокирует очередь.

## Цель

Два независимых RU egress для `tspu_block_probe` и template Relay — снижение единой точки отказа **72.56.0.145**.

## Инвентарь (2026-05-29)

| | relay#1 | relay#2 |
|---|---------|---------|
| IP | `72.56.0.145` | **`46.173.28.252`** |
| Провайдер | Selectel | **Timeweb Cloud RU** |
| SSH admin | `selectel_relay`, port **3344** | `timeweb_relay`, port **22** |
| LV probe | `id_ed25519` → `bvpncheck@:3344` | `id_ed25519_relay2` → `bvpncheck@:22` |
| Hysteria / panel inbounds | live | **live** VPN-AUD-201 **2026-05-29** (gen=44, 14 injectHosts) |

**Timeweb:** открыть **3345/tcp** в cloud firewall (sshd слушает; с LV пока **22**).

## Шаги (владелец)

1. Поднять 2-й VPS в RU (другой ASN/DC по возможности). ✅ **2026-05-29**
2. SSH: LV → relay#1 **3344**, relay#2 — отдельный ключ в `docs/SSH-KEY-INVENTORY.md`. ✅
3. На relay#2: `ops/install_ru_relay2_probe.sh` + `check.py` (bvpncheck forced command). ✅
4. Probe с LV: `python ops/tspu_block_probe_ru.py` — **2× OK** (relay1 + relay2).
5. После стабильных probe — добавить 3-й Relay host в panel (отдельный Q, не смешивать с routing patch).

## Verify

**2× `TSPU_BLOCK_PROBE_RU_OK`** (оба relay в одном прогоне); журнал §12; **Q120** → DONE в `docs/BACKLOG-QUEUE.md`.

```bash
# на LV
/opt/scripts/run_tspu_block_probe_ru.sh
python ops/smoke_tspu_block_probe_ru.py   # repo
```
