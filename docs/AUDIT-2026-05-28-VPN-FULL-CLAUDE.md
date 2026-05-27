# Полный аудит VPN-продукта BenderVPN — Claude (2026-05-28)

**Скоуп:** все слои стека — протокол, роутинг, relay, инфра, мониторинг, UX, безопасность.  
**Источники сессии:** live sub JSON, routing rules, `probe_subscription.py`, `drift-q084.txt` (исторический), panel template API, SSH снимки.  
**Сверка с продом после аудита:** [`AUDIT-2026-05-28-CLAUDE-RECONCILIATION.md`](AUDIT-2026-05-28-CLAUDE-RECONCILIATION.md), template **gen=26**.

> Этот документ — **архив формулировок аудита** на дату сессии. Исполнять задачи — только по [`BACKLOG-VPN-FULL-AUDIT-2026-05-28.md`](BACKLOG-VPN-FULL-AUDIT-2026-05-28.md) (статусы и gate).

---

## I. ТСПУ-обход и протокольный слой

### 1.1 Сильные стороны

- VLESS + Reality — оптимально для РФ; uTLS, живой SNI, shortId.
- SNI: microsoft, apple, github, bing, x5, vk, ozon.
- RELAY :443 — «незаметный» порт.

### 1.2 Уязвимости

**[P0] Корреляция IP:** 4× LV Direct на `176.126.162.158`; 3× relay inbound на `72.56.0.145` — блокировка одного IP убивает группу.

**[P0] fragment удалён без замены** (`patch_remove_fragment_defaults.py`) — для жёстких ISP (МТС, Билайн) нужен отдельный профиль `fragment_on`.

**[P1] Один Reality shortId** — риск обучения ТСПУ; ротация shortId на inbound.

**[P1] Только TCP** — нет xhttp/gRPC/QUIC fallback в Happ-шаблоне (xhttp убран из batch по Q-VPN-STAB-005).

**[P1] DNS metadata leak** — `1.1.1.1` / `UseIP`; split-tunnel + системный DNS для RU.

**[P2] Нет блока plain HTTP / QUIC через proxy.**

---

## II. Роутинг и логика трафика

### 2.1 Хорошее

- Порядок: torrent block → Intl IP → Intl domain → private → RU direct → catch-all.
- Убран `geosite:category-ru` из direct (leak-fix).
- IP-CIDR fallback TG/Meta (R1) для iOS background.
- `geoip:private` → direct.

### 2.2 Проблемы

**[P0] `regexp:.*\.ru$`** — слишком широко; лучше `geosite:ru` с контролируемым списком исключений.

**[P1] RU CDN / geoip:ru direct** — архитектурный выбор split-tunnel; документировать для пользователя.

**[P1] Meta/Instagram CIDR** — список может устареть; нужен периодический refresh.

**[P1] OpenAI geosite без IP-CIDR** — iOS background без sniffing.

---

## III. Relay и резервирование

**[P0] Один физический relay** — proxy-5/6/7 = один IP (иллюзия random).

**[P0] observatory=absent** — random без health-check; отключено из‑за `closed pipe` на RU probe.

**[P1] Relay NL :9443** — DPI; 0% сессий исторически.

**[P2] Нет CDN-fronted fallback** при полной блокировке relay IP.

*После gen=26:* catch-all и Intl используют **11 путей** (LV+relay+NL direct), не только relay — см. reconciliation.

---

## IV. Производительность

**[P0] policy 2/5 (исторически)** — сейчас **30/30** на live.

**[P2] bufferSize=64** — можно 128–512 для video burst.

**[P1] random без observatory** — при 11 путях ~9% на деградировавший; при 3 relay было ~33%.

**[P2] tcpNoDelay глобально** — компромисс latency vs bulk.

**[P1] DNS через direct к 1.1.1.1** — видимость запросов ТСПУ.

---

## V. Инфраструктура и мониторинг

### Сильные стороны

LUKS PG, pinned images, HA sub-page, healthchecks, Redis no persistence (cache), log rotation, pg_stat_statements.

### Проблемы (на дату аудита)

| ID | Тезис | Статус 28.05 |
|----|-------|----------------|
| P0 | ru-monitor.env MISSING | **Неверно** — файл на LV, логи OK |
| P0 | AMS swap=0 | **Неверно** — 2G swap |
| P0 | balancer.sh MISSING | **Неверно** — drift OK |
| P1 | Redis no persistence | Актуально — уточнить use-case |
| P1 | singbox.generator volume mount | Актуально при upgrade image |
| P1 | watchdog MISSING NL | **Неверно** — drift OK |
| P2 | Нет docker events → TG | Актуально |
| P2 | Нет latency probe per-outbound из RU | Частично — ru-monitor SNI only |

---

## VI. Клиентская совместимость (Happ)

- xhttp убран из Happ path — **OK**.
- 11+ named outbounds — риск ручного выбора (продукт: auto-only).
- iOS background — IP-CIDR partial fix.
- UDP-in-TCP overhead для QUIC apps.

---

## VII. Безопасность

- Caddy blocks swagger/health — OK.
- SSH nonstandard, ed25519 — OK.
- HSTS не на всех vhosts — P1.
- Panel API fingerprint — P1 (Caddy @blocked).
- `.secrets/` в рабочей копии — P1 hygiene.
- Relay firewall не в репо — P1 verify.

---

## VIII. Операционная зрелость

- Patch + snapshot — OK.
- MTTR 30–90 мин без auto-failover — P1.
- Drift 25 missing (drift-q084) — **устарело**; актуально 8/28 DRIFT.
- Один шаблон на всех — trial template TODO.

---

## IX. План действий (оригинал Claude)

### Немедленно

1. ru-monitor.env deploy  
2. verify template  
3. swap AMS  
4. balancer.sh LV  
5. watchdog NL  
6. multipath patch  
7. sub refresh users  

### Краткосрочно / средне / долго

См. полный перечень в [`BACKLOG-VPN-FULL-AUDIT-2026-05-28.md`](BACKLOG-VPN-FULL-AUDIT-2026-05-28.md) — единый источник исполнения.

---

## X. Матрица состояния (оригинал → актуализация)

| Слой | Claude 28.05 | После gen=26 / проверки |
|------|----------------|-------------------------|
| Relay | SPOF, 3 path catch-all | **11-path multipath**; relay IP всё ещё в пуле |
| Мониторинг | broken | **ru-monitor работает**, anti-flap |
| Policy | 2/5 | **30/30** |
| xhttp | P0 batch | **0 xhttp** live, batch LOW |
| Infra swap | 0 | **2G** |
| Drift | 25 missing | **8 DRIFT** compose/env |

---

*Архив. Исполнение: `BACKLOG-VPN-FULL-AUDIT-2026-05-28.md`.*
