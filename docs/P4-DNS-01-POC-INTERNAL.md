# P4-DNS-01: PoC dnstt / slipstream (internal)

**Исполнитель:** агент + владелец (VPS, домен). **Не** в линейной Q-очереди.

---

## Цель

Замерить: проходит ли **DNS tunnel** через типичного RU ISP (НСДИ / mobile) для **bootstrap-only** доступа к `start/` URL.

---

## Кандидаты

| Технология | Плюсы | Минусы |
|------------|-------|--------|
| **dnstt** | UDP 53, простой relay | Нужен свой NS / делегирование |
| **slipstream** | QUIC-like over DNS | Сложнее ops |

---

## Чеклист PoC

1. [ ] Поддомен `dns-bootstrap.conntest.xyz` (или отдельный apex **P4-DNS-05**).
2. [ ] VPS relay (не AMS/LV prod) + firewall 53/tcp,udp.
3. [ ] Клиент iOS/Android test — импорт ключа.
4. [ ] Замеры: latency, success rate, блокировка через 24h.
5. [ ] Документ с цифрами → go/no-go для **P4-DNS-03** public guide.

---

## Verify

**`P4_DNS_01_POC_OK`** — таблица метрик в §12 + ссылка на этот файл (дата).

**NO-GO:** включать DNS bootstrap в основную оферту без отдельного SKU.
