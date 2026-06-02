# Q120 / O-VPN-001: что купить — 2-й RU relay VPS

**Зачем:** сейчас **все** relay-пути (`proxy-5..7`) = один IP `72.56.0.145`. Блокировка или деградация → relay мёртв для всех. Второй relay = **+3 inbound** relay→LV, другой AS, меньше «VPN тупит».

**Не путать с:** NL VPS (`91.90.192.17`) — это EU exit. Relay — **мост RU→LV**, пользователь не выбирает его вручную.

---

## Минимальные требования

| Параметр | Требование |
|----------|------------|
| **Страна** | Россия (для низкой задержки RU→relay) |
| **AS / DC** | **Другой** провайдер и автономная система, не тот же что у `72.56.0.145` |
| **CPU/RAM** | 1 vCPU, 1 GB RAM достаточно (только relay, не exit) |
| **Диск** | 10–20 GB |
| **ОС** | Ubuntu 22.04 LTS |
| **Сеть** | **Inbound TCP 443** (VLESS Reality). **Исходящий** TCP 443 к LV `176.126.162.158` |
| **SSH** | root, ключ ed25519; порт **не 22** (например 3344/3345) — как relay#1 |
| **IPv4** | 1 статический публичный IPv4 |

---

## Желательно

- Другой **город/DC** (Москва vs SPb vs регион)
- Без «VPN/hosting» в reverse DNS (мелочь, не блокер)
- Возможность **доп. IP** позже (не обязательно с Day 1)

---

## Не нужно на relay

- Большой трафик / «безлимит 10 ТБ» — relay пропускает, основной объём на LV/NL
- Открытый DNS :53 на relay для клиентов — **не** использовать (relay блокирует исходящий 53)
- Панель Remna / бот — только на AMS

---

## После покупки — передать агенту

1. **IPv4** нового relay — ✅ **`46.173.28.252`**
2. **SSH:** `root@46.173.28.252:22`, ключ **`timeweb_relay`**
3. **Провайдер:** Timeweb Cloud RU (Ubuntu 24.04)
4. Probe path: ✅ **`TSPU_BLOCK_PROBE_RU_OK`** relay1 + relay2 (**2026-05-29**)

Агент: [`RUNBOOK-RU-RELAY-EXPANSION.md`](RUNBOOK-RU-RELAY-EXPANSION.md). **VPN-AUD-201** ✅ gen=44 — **обновить подписку в Happ**.

---

## Verify после онбординга

```bash
python ops/smoke_tspu_block_probe_ru.py   # 2 relay targets OK
python ops/verify_vpn_balancer_profile.py
# smoke с телефона РФ: IG/TG 5 min
```

---

## NL и «максимальная скорость»

2-й **RU relay** ≠ NL. Для EU exit:

- **Сейчас:** NL direct временно out of random (gen=38)  
- **Следующий шаг после probe RU:** relay→NL на **:443** (VPN-AUD-220) или вернуть NL в **Intl_Direct** only  

Покупка 2-го RU relay **не заменяет** решение по NL, но **сразу** улучшает стабильность intl через relay→LV.
