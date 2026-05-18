# Бэклог продукта / маскировка / ТСПУ — инструкции для агента (Q051–062)

**Для владельца:** отдай агенту этот файл + **`docs/BACKLOG-QUEUE.md`**.  
**Gate:** **Q051–062** ✅ (**2026-05-18**). Следующий линейный блок — **флоу Q044–050** (**`AGENT-FLOW-BACKLOG.md`**).

## Gate (критично)

| Правило | Смысл |
|---------|--------|
| **Сначала Q051–062** | Контур **продукта** (маскировка, подписка, клиенты). **Не брать Q044–050 (флоу)** пока не закрыт **Q062** или владелец не сказал иначе. |
| **Один Q → один коммит → стоп** | **`docs/POLICY-SEQUENTIAL-WORK.md`**, **`.cursor/rules/sequential-backlog.mdc`** |
| **Флоу-инструкции** | **`docs/AGENT-FLOW-BACKLOG.md`** — только после продукта |
| **Контекст** | **`docs/TSPU-OBSERVATIONS.md`**, **`docs/EDGE-PORT-RECOMMENDATION.md`**, **`docs/PRODUCT-TIER-PROFILES.md`** |

```text
[КРИТИЧНО] Q051 → Q052 → … → Q062   ← продукт / ТСПУ
[ПОТОМ]    Q044 → Q045 → … → Q050   ← флоу / portal polish / веб-ЛК
[ПАРАЛЛЕЛЬНО, не NEXT] Q060 (P4)   ← RF egress, whitelist IP
[ВЛАДЕЛЕЦ] Q032                    ← возвраты в оферте
```

---

## Карта приоритетов

| Уровень | Q | Тема |
|---------|---|------|
| **P0 — критично** | **051**, **058**, **062** | Edge порт; SNI yandex; три тира в sub |
| **P1 — бета / ТСПУ** | 052, 054, 055, 056, 057, 061 | v2rayN; VLESS playbook; probe; VPN port; selfsteal; DNS |
| **P1 — знания** | 059 | Threat model wiki |
| **P2 — долгий горизонт** | 053 | Native app brief |
| **P4 — отдельный поток** | 060 | RF egress + whitelist IP |

---

## Q051 — P2-RED-EDGE-PORT-01 · edge **2053 → 8443**

| | |
|--|--|
| **Что** | Перенести **публичный HTTPS-край** (панель, `/api/sub/*`, `/start`, `/portal`, `/setup`, `/status`) с **`:2053`** на **`:8443`**. Grace: **2053** редирект или параллель **7–14 дней** + текст пользователям «обновить подписку». |
| **Зачем** | Убрать сигнатуру **дефолтной панели 3X-UI**; меньше сканов и внимания ТСПУ к URL подписки (бета). |
| **Почему** | **2053** — не «стандарт HTTPS», а известный порт xray-панелей ([Habr](https://habr.com/ru/articles/822597/)); на сервер бьют именно в **2053**. **8443** — alt-HTTPS, не палится как 3X-UI (**`EDGE-PORT-RECOMMENDATION.md`**). |
| **Не путать** | Это **не** VPN inbound на нодах (**:443/9443** — задача **Q056**). |
| **Done when** | Все URL в **`ops/site_urls.py`**, **`compose/**/panel.env.tmpl`**, **`Caddyfile-latvia-full.txt`**, бот, **`site.env.example`** → **:8443**; runbook **`RUNBOOK-P6-EDGE-PORT-MIGRATION.md`**; smoke **`SUB_EDGE_PORT_OK`** (sub **200**, portal **200**); §12. |
| **Verify** | `curl -fsSI https://k9x2m1.conntest.xyz:8443/portal/` → **200**; `curl -fsSI https://p4n7q.conntest.xyz:8443/api/sub/<shortId>` → **200**; BotFather URL обновляет **владелец** (чеклист в runbook). |
| **Файлы** | `ops/site_urls.py`, `Caddyfile-latvia-full.txt`, `ops/lv_patch_panel_caddy_k9.py`, `compose/ams/remnawave/panel.env.tmpl`, `bot_src/config.py`, `bot_src/portal_links.py`, `web/portal` (если хардкод), docs с **2053** → **8443** |
| **Commit** | `ops: P2-RED-EDGE-PORT-01 — migrate public edge 2053 to 8443 (TSPU)` |

---

## Q052 — P1-PRO-CLIENT-V2RAYN-01 · Windows v2rayN

| | |
|--|--|
| **Что** | Документировать и починить совместимость **v2rayN** с нашей подпиской; ветка **Windows** в portal/FAQ — **второй** клиент рядом с Happ. |
| **Зачем** | Бета: **v2rayN не коннектится** ни LTE, ни Wi‑Fi; без ПК-клиента теряем сегмент. |
| **Почему** | Happ закрывает mobile; на Windows часть пользователей на **v2rayN**; формат sub/UA/routing может отличаться. |
| **Done when** | **`docs/CLIENT-V2RAYN.md`** (шаги, версия, обновление sub); smoke на Win или чеклист владельца; **`V2RAYN_CLIENT_OK`** §12; portal `ru.json` — блок Win + v2rayN. |
| **Verify** | Импорт sub URL → connect → `ya.ru` / probe; нет регрессии Happ. |
| **Не делать** | Не менять шаблон ради v2rayN, если ломает Happ — snapshot + rollback. |
| **Commit** | `product: P1-PRO-CLIENT-V2RAYN-01 — Windows v2rayN compatibility` |

---

## Q053 — P5-PROD-NATIVE-APP-01 · своё приложение (brief)

| | |
|--|--|
| **Что** | Заполнить **`docs/NATIVE-APP-BACKLOG.md`**: MVP, go/no-go App Store, GeoIP на устройстве, сроки. **Без кода** в этом Q. |
| **Зачем** | Happ — компромисс App Store; долгосрок — свой клиент (tier-3 routing, доверие). |
| **Почему** | Референс и бета: routed WL только на **мобиле**; iOS NE **~15 MB** — нужно решение до разработки. |
| **Done when** | Brief полный; владелец go/no-go в §12. |
| **Commit** | `docs: P5-PROD-NATIVE-APP-01 — native app product brief` |

---

## Q054 — P2-RED-TSPU-VLESS-01 · палево VLESS, ~15 дней

| | |
|--|--|
| **Что** | Runbook **`RUNBOOK-TSPU-VLESS-INCIDENT.md`**: симптомы «спалили VLESS», бан ~15 дней на **конкретной** ТСПУ, действия (смена транспорта, alt outbound, не крутить всю базу на один fingerprint). |
| **Зачем** | Операторы и саппорт действуют по сценарию, а не экспериментируют на живой базе. |
| **Почему** | Наблюдение бета + [bbs#546](https://github.com/net4people/bbs/issues/546), [Habr DPI](https://habr.com/en/articles/990236/); MUX уже есть — нужна **процедура**. |
| **Done when** | Runbook + ссылка из **`RUNBOOK-INCIDENT.md`**; **`TSPU_VLESS_PLAYBOOK_OK`** §12. |
| **Commit** | `docs: P2-RED-TSPU-VLESS-01 — TSPU VLESS incident runbook` |

---

## Q055 — P1-RED-TSPU-BLOCK-01 · probe «в ЧС»

| | |
|--|--|
| **Что** | Скрипт/monitor: с **RU-сети** (relay) проверка — порты **>990**, обрыв **SSL handshake** на edge/sub. |
| **Зачем** | Раннее обнаружение режима «телнеты >990 режут, TLS рвётся» (наблюдение п.3). |
| **Почему** | `ru-monitor` смотрит SNI нод, не этот паттерн блокировки. |
| **Done when** | **`ops/tspu_block_probe.py`** (или расширение monitor); cron; **`TSPU_BLOCK_PROBE_OK`** §12. |
| **Commit** | `ops: P1-RED-TSPU-BLOCK-01 — RU TSPU block probe` |

---

## Q056 — P2-RED-VPN-INBOUND-PORT-01 · inbound VPN ≠ 443

| | |
|--|--|
| **Что** | Runbook смены **inbound-порта remnanode** (LV/NL) при бане **443** у хостера; обновление injectHosts / sub. |
| **Зачем** | «К хостеру пришли — забанили 443» лечится **другим портом** (наблюдение п.4). |
| **Почему** | [bbs#546](https://github.com/net4people/bbs/issues/546): на части ISP ломается **443+vision**; у нас alt **9443/8443** есть — нужна **процедура смены**, не разовый хак. |
| **Зависит от** | **Q051** (edge отдельно). |
| **Done when** | **`RUNBOOK-VPN-INBOUND-PORT.md`**; tabletop на тестовом inbound; **`VPN_INBOUND_PORT_OK`** §12. |
| **Commit** | `ops: P2-RED-VPN-INBOUND-PORT-01 — VPN inbound port migration runbook` |

---

## Q057 — P2-RED-SELFSTEAL-REVIEW-01 · decoy / selfsteal

| | |
|--|--|
| **Что** | Аудит **selfsteal** (Caddy :9443, 13 SNI, `selfsteal-monitor.py`): **go/no-go** — выключить, упростить или оставить. |
| **Зачем** | Наблюдение: «сайт-заглушка при прямом заходе **больше не имеет смысла**» (п.5). |
| **Почему** | Selfsteal — legacy anti-probe; может давать лишнюю сигнатуру и шум мониторинга. |
| **Done when** | Решение в **`docs/TSPU-OBSERVATIONS.md`** п.5 + §12 **`SELFSTEAL_REVIEW_OK`**; если off — план деплоя без регрессии. |
| **Не делать** | Не выключать на проде без rollback-плана и тишины в monitor. |
| **Commit** | `docs: P2-RED-SELFSTEAL-REVIEW-01 — selfsteal decoy go-no-go` |

---

## Q058 — P2-RED-SNI-ROTATE-01 · SNI → yandex.ru (P0)

| | |
|--|--|
| **Что** | В шаблоне Reality **убрать кластер github/bing/microsoft** как основной; внедрить **`www.yandex.ru`** (и политику ротации) по **`POLICY-SNI-MONITORING`**. |
| **Зачем** | Маскировка под **WL/РФ-контекст**; референс-конфиги все на **yandex.ru**. |
| **Почему** | П.6 наблюдений: «SNI под github **теряет смысл**»; [Xray #2283](https://github.com/XTLS/Xray-core/issues/2283). |
| **Done when** | Snapshot **`ru_bypass_routing.py`** стиль; patch template; **`transport_mux_audit.py`** OK; **`SNI_ROTATE_OK`** §12. |
| **Verify** | Probe sub: dest/SNI в выдаче; `ru-monitor` expectations обновлены при необходимости. |
| **Commit** | `ops: P2-RED-SNI-ROTATE-01 — rotate Reality SNI to yandex.ru cluster` |

---

## Q059 — P1-RED-TSPU-THREAT-MODEL-01 · wiki ТСПУ

| | |
|--|--|
| **Что** | **`docs/TSPU-THREAT-MODEL.md`**: п.7–9 (ТСПУ независимы, бан временный, массовый ручной, малый сервер реже); связь **NODE-POLICY**, GTM. |
| **Зачем** | Единая «правда» для саппорта и агентов; не переоткрывать в чатах. |
| **Почему** | 12 наблюдений без модели → хаотичные правки продукта. |
| **Done when** | Wiki + 1-стр шпаргалка в **`RUNBOOK-INCIDENT.md`**. |
| **Commit** | `docs: P1-RED-TSPU-THREAT-MODEL-01 — TSPU threat model wiki` |

---

## Q060 — P4-DNS-07/08 · RF egress + whitelist IP (параллельно P4)

| | |
|--|--|
| **Что** | **P4-DNS-07:** PoC **прокси/нода в РФ** для усечённого WL (весь не‑РФ режут). **P4-DNS-08:** источник **whitelist IP** не GitHub seed; регламент обновления. |
| **Зачем** | Tier **wl-direct / wl-routed** без RF-ноды не воспроизвести референс. |
| **Почему** | П.10–12 наблюдений; референс **158.160.x :80/:443**. |
| **Очередь** | **Не NEXT** в линейной Q051–062, если владелец не переназначил; можно параллельно потоку P4. |
| **Done when** | Wiki/PoC; go/no-go стоимости RF VPS §12. |
| **Commit** | `docs: P4-DNS-07/08 — RF egress PoC + whitelist IP source wiki` |

---

## Q061 — P1-RED-NODE-DNS-01 · DNS на нодах

| | |
|--|--|
| **Что** | Политика: Xray/ноды резолвят через **свой** DNS (AdGuard/unbound на VPS), не провайдерский. |
| **Зачем** | П.11: провайдер/ТСПУ **удаляют** записи заблокированных доменов. |
| **Почему** | AdGuard в compose есть, но **не задокументирован** как обязательный upstream для нод. |
| **Done when** | Runbook + probe «резолв ломается»; **`NODE_DNS_RESOLVER_OK`** §12. |
| **Commit** | `ops: P1-RED-NODE-DNS-01 — node DNS resolver policy` |

---

## Q062 — P1-PRO-SUB-TIER-01 · три тира в подписке (P0)

| | |
|--|--|
| **Что** | В одной подписке **3 именованных профиля** (remark в Happ): **turbo** (NL/LV, без routing), **wl-direct** (RF, **:80**, без flow), **wl-routed** (RF, **:443**, vision, routing на клиенте). FAQ: tier-3 **не на роутер**. |
| **Зачем** | Разные **ситуации сети** = разные маски; не один «BenderVPN Auto» на всех. |
| **Почему** | Референс-конфиги; «чем круче WL — тем ниже скорость». |
| **Зависит от** | **Q058** (SNI); **Q060** (RF нода) или заглушка + runbook до PoC. |
| **Done when** | **`PRODUCT-TIER-PROFILES.md`** актуален; probe sub показывает 3 tier; **`SUB_TIER_PROFILES_OK`** §12; ONBOARDING/FAQ — таблица «какой узел когда». |
| **Verify** | `transport_mux_audit.py` / `probe_users_subs.py` — выборка видит все tier. |
| **Commit** | `product: P1-PRO-SUB-TIER-01 — turbo/wl-direct/wl-routed subscription tiers` |

---

## После Q062 — флоу (не продукт)

| Q | ID | Кратко |
|---|-----|--------|
| 044 | P3-FLOW-09 | Ветки устройств portal |
| 045–047 | P3-FLOW-13/10/11 | a11y, метрики, запасной домен |
| 048–050 | P3-FLOW-15…17 | веб-ЛК |

Инструкции: **`docs/AGENT-FLOW-BACKLOG.md`**.

---

## Smoke общий (после каждого продуктового Q)

```powershell
python ops/portal_bundle_audit.py          # если трогали portal
python ops/transport_mux_audit.py        # если трогали template
python -m py_compile ops/*.py            # новые скрипты
python ops/drift-check.py                # после прод-деплоя
```

AMS/LV deploy — **`docs/RUNBOOK-AMS-SAFE-DEPLOY.md`**, **`docs/RUNBOOK-USER-BOOTSTRAP-SITE.md`**.

---

*Версия: 2026-05-18. Синхронизировать с **`BACKLOG-QUEUE.md`** при смене NEXT.*
