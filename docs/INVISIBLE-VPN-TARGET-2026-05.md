# Цель продукта: «невидимый VPN» (2026-05)

**North star:** пользователь **не ощущает**, что VPN включён — ни на `.ru`/банках/госуслугах, ни в Instagram/Telegram/YouTube. Нет ручного выбора сервера. Пинг в Happ **&lt;120 ms** типично из РФ. Speedtest стартует. Нет «то грузит / то нет».

**Ограничение UX:** один профиль «🚀 BenderVPN Auto», auto balance + routing (без «выберите NL/LV»).

---

## Два слоя трафика

| Слой | Куда | Как должно работать |
|------|------|---------------------|
| **RU-direct** | `.ru`, geosite:ru, банки, маркетплейсы | `outboundTag: direct` — **мимо туннеля**, как без VPN |
| **Intl** | IG, TG, Meta, YouTube, speedtest | Быстрый зашифрованный путь; DPI не видит конечный IP |

---

## Текущий прод (2026-05-29, template gen≥48)

| Компонент | Состояние |
|-----------|-----------|
| **injectHosts** | **10** — relay#1×3 + relay#2×3 + NL direct×4 |
| **Intl_Direct** | **relay×6 + NL×4** catch-all (speedtest/general) |
| **Intl_Stealth** | **relay×6 only** — TG/Meta IP + geosite rules (VPN-AUD-221) |
| **Catch-all** | **Intl_Direct** (не Super/LV — без footgun gen=132) |
| **Super / DNS_LV / observatory** | **нет** |
| **Autotrim (LV cron 15 min)** | relay slow IP + NL fail → selector trim; injectHosts NL остаётся |
| **Gate** | `ops/vpn_verify_gate.sh` на bvpn-lv → `VPN_VERIFY_GATE_OK` |
| **Sub broadcast** | выключен (gen bump без TG spam) |

**Probe baseline (RU, 2026-05-29):** relay TCP ~8–10 ms; NL `:443` ~52 ms.

---

## Закрыто в этом спринте

| ID | Что |
|----|-----|
| **Q120 / VPN-AUD-201** | relay#2 `46.173.28.252`, hysteria, injectHosts |
| **gen=47** | relay-only sub (Happ ping fix) |
| **VPN-AUD-310** | `latency_selector_autotrim.py` + cron |
| **VPN-AUD-220** | NL в Intl gated probe (`patch_add_nl_intl_gated.py`) |
| **VPN-AUD-221** | stealth split TG/Meta→relay only (`patch_intl_stealth_split.py`) |
| **VPN-AUD-101** | `vpn_verify_gate.py` / `.sh` |
| **VPN-AUD-BBR-01** | `audit_bbr_congestion.py` — relay+LV bbr+fq (2026-05-30 OK) |

### Задачи скорости (карта)

См. **`docs/VPN-SPEED-AUDIT-TASKS-2026-05-30.md`** — P1/P2/P3 после stealth split + Amnezia/GitHub аудита.

---

## Следующий шаг (P1)

| ID | Задача |
|----|--------|
| **VPN-AUD-103** | Владелец: smoke speedtest/TG 10 min после refresh sub |
| **VPN-AUD-230** | Split DNS (DoH intl) |
| **VPN-AUD-110** | bufferSize 64→128 (video/speedtest) |
| **VPN-AUD-430** | leastLoad + observatory — **только staging A/B** |

### NO-GO

- NL в **Super_Balancer** / catch-all LV direct из РФ
- RELAY_DNS / DNS `:53` direct
- observatory hicloud на прод без staging
- `relay_failover_template` → LV direct на gen≥47 (заблокировано)

---

## Verify (после любого template patch)

```bash
# на bvpn-lv
bash ops/vpn_verify_gate.sh

# локально (без RU probe)
python ops/verify_vpn_balancer_profile.py
python ops/probe_subscription.py
```

---

*Обновлено 2026-05-29 после VPN-AUD-220/310/101.*
