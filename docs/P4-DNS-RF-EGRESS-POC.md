# PoC: RF egress для WL-tier (P4-DNS-07/08)

**Очередь:** **Q060** — **параллельный** поток P4; не блокирует **Q062** (tier-3 может быть «coming soon»).

## Цель

Нода/прокси в **РФ** (Yandex Cloud / др.) для профилей **wl-direct** (:80) и **wl-routed** (:443) — см. **`PRODUCT-TIER-PROFILES.md`**.

## PoC чеклист (владелец)

- [ ] VPS в RF, **158.160.x** класс, порты **80/443** открыты.
- [ ] Remnawave node + inbound Reality **sni=www.yandex.ru**.
- [ ] Тест с усечённым WL: только RU наружу — tier-2/3 коннектятся.
- [ ] **Whitelist IP** — источник не GitHub seed (**P4-DNS-08**): свой файл + `ops` update runbook.

## Go/no-go

| Исход | Действие |
|-------|----------|
| **Go** | Добавить node в панель; включить tier 2–3 в template |
| **No-go** | Оставить tier-3 «скоро» в FAQ; turbo + wl-direct заглушка |

## Smoke

**`P4_RF_EGRESS_POC_OK`** — этот файл + §12 go/no-go от владельца.
