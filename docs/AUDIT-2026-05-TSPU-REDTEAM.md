# ТСПУ red-team audit — BenderVPN (2026-05-19)

**ID:** **P2-RED-TSPU-AUDIT-02** (Q085).  
**Роль:** внешний противник уровня ТСПУ/DPI (не code review).  
**База:** ~60 пользователей; прод после **Q079–084** (**:8443** на LV, бот AMS, portal/Mini App).

**Источники:** [`TSPU-OBSERVATIONS.md`](TSPU-OBSERVATIONS.md), [`TSPU-THREAT-MODEL.md`](TSPU-THREAT-MODEL.md), статический разбор репо + SSH **`bvpn-lv`** + smokes с рабочей станции агента (**не RU LTE**).

---

## Executive summary

Инженерный контур против ТСПУ **в целом зрелый для бета**: канонический edge **:8443** на проде, multi-origin подписки (**p4n7q** + **k9x2m1**), **100%** пользователей с primary+alt outbound (**alt_ob_share ≈56%**), `log_skip` на `/api/sub/*`, runbook VLESS-инцидента, block-probe и threat model в репо.

**Главные остаточные риски до GTM** — не «сломанный TLS», а **discovery и рассинхрон портов**:

1. **Grace `:2053` всё ещё слушает на LV** (4 server blocks) — целевой скан 3X-UI остаётся валидным вектором.
2. **Продуктовые утечки `:2053`** в боте и FAQ отправляют пользователей (и DPI) на устаревший fingerprint.
3. **Запасной bootstrap-домен** описан в runbook (**Q047**), но **не зарегистрирован** — при блоке apex пользователь без отдельной инструкции.
4. **Probes с агента ≠ RU LTE** — `TSPU_BLOCK_PROBE_OK` не заменяет проверку с Мегафон/МТС.
5. **Selfsteal / GitHub SNI** на **:9443** — осознанный KEEP (**Q057**), но остаётся дополнительная сигнатура для корреляции.

**Зрелость к ТСПУ:** **6,5 / 10** (бета OK; до 1k — **условно**, после закрытия P1 discovery + RU probe).  
**Рост 10k с текущим fingerprint:** **нет** без сегментации шаблонов, живого alt-apex и sunset **2053**.

**Регресс vs `TSPU-OBSERVATIONS`:** нет отката закрытых Q051–061 / Q079–084; новые факты — **UX/docs drift на :2053** и **конфликт XHTTP→18443** (решён в Q080, зафиксировать в runbook).

---

## Прогоны (приложение A)

| Smoke | Результат | Примечание |
|-------|-----------|------------|
| `transport_mux_audit.py` | **TRANSPORT_MUX_OK** — sample 20, both 100%, alt_ob_share **56.2%** | Panel API |
| `tspu_block_probe.py` | **TSPU_BLOCK_PROBE_OK** — :2053/:8443 tcp+tls OK | **Не с RU relay** |
| `smoke_sub_edge_port.py` | **SUB_EDGE_PORT_OK** — live :8443 portal + sub | |
| `portal_bundle_audit.py` | **PORTAL_BUNDLE_OK** | |
| SSH `bvpn-lv` Caddy | **3**×`:8443`, **4**×`:2053`, **3**×`log_skip` | Grace активен |

---

## Находки (P0–P3)

| P | ID | Вектор | Что сейчас | Риск×вер. | Детект | Fix (мин → идеал) | Кто |
|---|-----|--------|------------|-----------|--------|-------------------|-----|
| **P1** | T-AUD-01 | Edge **:2053** grace | LV Caddy: **4** блока **:2053** + **3** на **:8443** | 4×4 | Скан 2053, access-log | Мин: редирект 301→8443 на 2053. Идеал: отключить 2053 после метрики обновлений подписки | Ops LV + владелец (коммуникация) | **Q087** |
| **P1** | T-AUD-02 | Discovery **:2053** в UX | `vpn_setup_wizard.py:76` → `…:2053/status`; **FAQ.md** :2053 `/status`, `/start/` | 4×5 | Пользователь/бот ссылается на мёртвый порт при блоке LTE | Мин: заменить на **:8443** везде в user-facing. Идеал: `site_urls.public_status_url()` единый источник | Агент **Q086** | **Q086** |
| **P1** | T-AUD-03 | Нет live **alt apex** | **Q047** runbook only; нет второго registrar+DNS в проде | 3×4 | Блок `k9x2m1` → нет зеркала в боте/FAQ | Мин: текст в FAQ «если не открывается — p4n7q:8443». Идеал: зарегистрировать alt domain + Caddy block | Владелец DNS + агент **Q088** | **Q088** |
| **P2** | T-AUD-04 | RU probe gap | `tspu_block_probe` OK с агента; **2053 tcp OK** с той же сети | 3×3 | Ложно-зелёный до LTE | Мин: 5 пунктов владельцу (ниже). Идеал: cron с RU VPS / owner phone | Владелец + **Q089** | **Q089** |
| **P2** | T-AUD-05 | Один TLD **conntest.xyz** | **p4n7q** и **k9x2m1** — один регистратор/зона; блок зоны режет оба | 3×3 | DNS/RU registry | Мин: messaging «второй хост p4n7q». Идеал: alt TLD из **P1-RED-DNS-01** | **Q088** | **Q088** |
| **P2** | T-AUD-06 | Публичный `/status` + JSON mirror | Операционная карточка + имена нод; полезно users, видно снаружи | 2×4 | GET :8443/status | Мин: без IP нод в HTML. Идеал: отдельный «user» vs «ops» JSON | Агент | **Q090** |
| **P2** | T-AUD-07 | Selfsteal **:9443** + `api.github.com` | Caddy template + **Q057 KEEP** | 2×3 | DPI SNI cluster | Мин: мониторинг только. Идеал: упростить decoy после change window | Ops | backlog |
| **P2** | T-AUD-08 | v2rayN / Windows | Док **Q052** есть; бета «не коннектится» в бэклоге | 3×3 | Support tickets | Мин: FAQ «ПК → v2rayN + обновить sub :8443». Идеал: smoke Win + шаблон sub | Продукт | существ. **Q052** |
| **P2** | T-AUD-09 | Tier switch UX | Тиры в подписке (**Q062**); нет self-service в боте | 2×3 | Ручная панель | Мин: support script. Идеал: кнопка «режим turbo/basic» | Продукт | **Q091** |
| **P3** | T-AUD-10 | Docs drift | `KNOWLEDGE-BASE.md`, `AGENT-FLOW-BACKLOG.md` — **:2053** | 2×2 | Внутренняя путаница | Правка ссылок на **:8443** | Агент | в **Q086** |
| **P3** | T-AUD-11 | `smoke_bot_portal_links` sample :2053 | Только parse test, не прод | 1×1 | — | Оставить или sample :8443 | Агент | опц. |
| **P3** | T-AUD-12 | XHTTP **18443** post-Q080 | Конфликт с Caddy :8443 решён API; не везде в user docs | 2×2 | Support | Строка в **`RUNBOOK-TSPU-VLESS-INCIDENT`** | Агент | doc |

**P0:** нет новых P0 при живом **:8443** и закрытой панели с интернета (**Q081**).

---

## Инвентарь по 5 векторам (кратко)

### 1. Сеть / fingerprint

| Аспект | Состояние | Риск |
|--------|-----------|------|
| Edge **8443** | Live, smokes OK | Низкий (канон) |
| Grace **2053** | Live 4 blocks | **Средний** — скан 3X-UI |
| MUX ≥2 профиля | **100%** users (audit sample) | Низкий |
| VPN inbound ≠443 only | **:443 + :9443** + XHTTP **18443** | Низкий–средний |
| SNI yandex (**Q058**) | Repo default; panel — верифицировать на LV | Средний если github в Reality |
| Sub shortId в URI | Публичный capability URL; **log_skip** ✅ | Средний при утечке логов |
| Multi-origin | **p4n7q** + **k9x2m1** :8443 — при блоке одного FQDN второй жив | Средний при блоке зоны |

### 2. Bootstrap / discovery

| Аспект | Состояние | Риск |
|--------|-----------|------|
| `/start/`, `/portal/` :8443 | OK live | Низкий |
| BotFather | Владелец → **:8443** (checklist) | Зависит от владельца |
| Утечки **:2053** | Бот wizard, FAQ | **Высокий** для UX и fingerprint |
| Backup domain | Runbook only | **Средний** |

### 3. Продукт / UX под блокировкой

| Сценарий | Поведение |
|----------|-----------|
| LTE режет VPN, Wi‑Fi OK | Бот: wizard ведёт на **:2053/status** → **ложный «сервис лежит»** |
| Happ iOS | Основной путь; tier в sub |
| Windows v2rayN | Док есть; полевая боль — support |
| Mini App | **:8443** в `config.py` default ✅ |

### 4. Наблюдаемость / палево

| Аспект | Состояние |
|--------|-----------|
| Caddy sub logs | **log_skip** на k9x2m1 ✅ |
| `/status`, `status.json` | Публичные; не секрет, но discovery |
| Selfsteal | KEEP **Q057** — осознанный tradeoff |

### 5. Инцидент «спалили VLESS» (tabletop)

По **`RUNBOOK-TSPU-VLESS-INCIDENT.md`**: при **30% fail** за 1 ч — сегмент (не массовый rollout), alt outbound/tier, ops status, support шаблон; **ru-monitor** + **tspu_block_probe**; не крутить один шаблон всей базе (**Q054**, **Q059**). **Пробел:** нет автоматического счётчика «% fail по ISP» — только ручной triage.

---

## Уже закрыто (не переоткрывать без новых фактов)

| Q | Суть |
|---|------|
| **Q051 / Q080** | Edge **8443** на LV, live smokes |
| **Q054–055, 059** | VLESS runbook, block probe, threat model |
| **Q056–058, 061–062** | VPN port policy, selfsteal review, SNI default, node DNS, tiers |
| **Q066** | `log_skip` sub |
| **Q010–011** | Multi-origin sub, MUX matrix |
| **Q079–084** | Бот security AMS, panel UFW, SSH dedup, prod smokes, drift waive |

---

## Предложения Q086+ (для очереди; не менять NEXT без владельца)

| Q | ID | Done when | Verify | Commit (пример) |
|---|-----|-----------|--------|-----------------|
| **Q086** | **P2-RED-DISCOVERY-PORT-01** | User-facing URL только **:8443** (бот, FAQ, KB, journey) | grep без `:2053` в `bot_src/`, `FAQ.md` | `fix: P2-RED-DISCOVERY-PORT-01 — canonical :8443 in bot and FAQ` |
| **Q087** | **P2-RED-EDGE-SUNSET-2053-01** | 2053 → 301→8443 или off; коммуникация пользователям | curl :2053 → 301; scan noise ↓ | `ops: P2-RED-EDGE-SUNSET-2053-01 — grace sunset LV` |
| **Q088** | **P3-FLOW-11-LIVE-01** | Live alt apex + Caddy + строка в FAQ/бот | curl alt:8443/portal 200 | `ops: P3-FLOW-11-LIVE-01 — backup bootstrap domain live` |
| **Q089** | **P1-RED-TSPU-BLOCK-RU-01** | `tspu_block_probe` cron с RU egress + алерт | **TSPU_BLOCK_PROBE_RU_OK** с RU IP | `ops: P1-RED-TSPU-BLOCK-RU-01 — RU cron block probe` |
| **Q090** | **P5-COM-STATUS-TRIM-01** | `/status` без лишних ops-деталей для блокировщика | review HTML | `product: P5-COM-STATUS-TRIM-01 — trim public status page` |
| **Q091** | **P1-PRO-TIER-SWITCH-01** | Self-service tier hint в боте/portal | smoke/manual | `product: P1-PRO-TIER-SWITCH-01 — tier switch UX` |

---

## Top-5 на 2 недели

1. **Q086** — убрать **:2053** из бота и FAQ (быстрый win до GTM).
2. **Владелец LTE** — 5 проверок ниже; зафиксировать в §12.
3. **Q087** — план sunset **2053** (7–14 дней grace уже в runbook).
4. **Q088** — живое зеркало bootstrap (не только tabletop).
5. **Q089** — probe с реальной RU-сети.

---

## Владелец: проверить вручную с телефона (LTE)

1. **Mini App / portal** — открывается `https://k9x2m1.conntest.xyz:8443/portal/` на **LTE** (не только Wi‑Fi).
2. **Подписка** — обновить в Happ; URL в клиенте содержит **:8443**, не **:2053**.
3. **Запасной origin** — с LTE открыть `https://p4n7q.conntest.xyz:8443/` (тот же shortId path в боте «Моя настройка»).
4. **VPN connect** — 2–3 мин на LTE; при fail — переключить tier/alt в sub и повторить (не массовый reissue).
5. **`tspu_block_probe` с телефона** — нет удобного CLI; вместо этого: если portal **:8443** timeout на LTE, а **:2053** отвечает — зафиксировать скрин + ISP в support (сигнал блока edge).

---

## Tabletop Q054 (30% users fail, 1 час)

| T+ | Действие |
|----|----------|
| 0–15 мин | `/status` + ops JSON; **ru-monitor**; не mass template change |
| 15–45 min | Сегмент ISP; alt outbound; проверить **18443** XHTTP vs Reality |
| 45–60 min | Support macro; при блоке apex — **p4n7q**; эскалация владельцу если DNS зона |

---

*Следующий шаг по очереди — только по согласованию: **Q086** как NEXT.*
