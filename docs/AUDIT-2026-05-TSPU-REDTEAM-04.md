# ТСПУ red-team audit — раунд 3 («злой», внешние источники 2025–2026)

**ID:** **P2-RED-TSPU-AUDIT-04** (отчёт фазы 7; задачи **Q102+** ниже).  
**Дата:** 2026-05-19  
**Роль:** противник уровня **ТСПУ/DPI + РКН L3/L7**, не «чеклист закрытых Q».  
**База:** прод после Q099–100; сверка с **Q085**, **Q098**, полевыми отчётами и открытыми источниками.

**Прогоны:** smokes с рабочей станции + SSH LV + live pull подписки `p4n7q:8443/api/sub/…`.

---

## Executive summary (без скидок)

| Метрика | Q098 (раунд 2) | **Раунд 3 (сейчас)** |
|---------|----------------|----------------------|
| **Зрелость к ТСПУ** | 7,5 / 10 | **5,0 / 10** |
| **GTM 200 users** | условно | **нет** — P0 на fingerprint подписки |
| **GTM 10k** | — | **не готов** |
| **RU observability** | relay ❌ | relay ✅ (Q099) |
| **Иллюзия MUX** | «100% both» | **ложная** — XHTTP не в аудите, SNI не ротирован на проде |

**Вердикт:** инженерия **edge :8443**, RU probe и docs — реальный прогресс. Продуктовый **wire fingerprint** для DPI **не соответствует** закрытым Q058/Q054 и публичной модели угроз 2026: в выдаче подписки по-прежнему **кластер github/microsoft/bing/apple**, а **XHTTP** — маргинальный хвост (2 из 18 outbound в smoke-выборке).

**Регресс:** нет отката Q051–097 по edge; **регресс смысла Q058** — repo `REMNA_SERVER_SNI=www.yandex.ru`, **панель/шаблон на проде не переведены**.

---

## Внешние источники (что считать «нормой» ТСПУ в 2026)

| Источник | Вывод для BenderVPN |
|----------|---------------------|
| [Habr: как ТСПУ ловит VLESS](https://habr.com/ru/articles/1009542/) | **4 слоя:** сигнатура → **JA3/JA4** → активное зондирование → **поведенческий анализ** (длины пакетов, uplink/downlink). Reality **не спасает**, если стек/паттерн не браузерный. |
| [Habr: блокировки XRay/VLESS](https://habr.com/ru/articles/969618/) | Волны с **дек 2025**; **:443** жёстче случайных high ports; массовые жалобы на vision+Reality. |
| [Habr: DPI архитектура](https://habr.com/ru/articles/1027012/) | ТСПУ **децентрализованы по операторам** — один RU relay ≠ картина страны. |
| [Habr: белые списки L3+L7](https://habr.com/ru/articles/1027276/) | С **апр 2026** — реестр **~75k IP** «корпоративных» VPN; **L3 CIDR** + **L7 SNI** одновременно. VPS вне списка — риск при режиме «только whitelist». |
| [Kommersant / реестр VPN IP](https://www.kommersant.ru/doc/7659315) | Коммерческий VPS **не в списке** → при ужесточении мобильного режима **bootstrap и edge на LV/NL IP** могут стать недоступны **без** RF egress / DNS PoC. |
| [Lantern corpus: TSPU inline RST](https://corpus.lantern.io/findings/2024-xue-tspu-russia__inline-blocking-mechanism/) | In-line **RST/inject** — не только «тихий drop». |
| [Lantern corpus: ECH block](https://corpus.lantern.io/findings/2025-niere-encrypted__russia-tspu-ech-direct-block/) | **ECH** к Cloudflare режется — не опора для обхода. |
| [net4people/bbs#546](https://github.com/net4people/bbs/issues/546) | **443+vision** ломается на части ISP; нужны **alt порты/транспорты**. |
| [BlockPulse / Habr sandbox](https://habr.com/ru/sandbox/281182/) | **Региональная** карта протоколов; **XHTTP/SplitHTTP** чаще живее чистого VLESS+Reality в 2026 — но тоже не серебряная пуля. |
| **`docs/TSPU-OBSERVATIONS.md`** (бета) | ~15d бан на **конкретной** ТСПУ; скан **:2053**; **>990** telnet/SSL; слабая связность ТСПУ. |

---

## Live checks (2026-05-19, раунд 3)

| Check | Результат | Комментарий |
|-------|-----------|-------------|
| `TSPU_REDTEAM_OK` | ✅ | **Не доказывает** устойчивость VPN — только edge/sub smokes |
| `TSPU_BLOCK_PROBE_RU_OK` | ✅ LV→relay | TCP/TLS **k9x2m1:8443** с RU; **не** VLESS inbound |
| `TRANSPORT_MUX_OK` | ✅ | Считает только **Reality vnext** — **слепой к XHTTP** |
| Live sub outbounds (smoke user) | ⚠️ | **18** outbound: SNI **`api.github.com`**, **`www.microsoft.com`**, **`www.apple.com`**, **`www.bing.com`** + selfsteal-домены; **XHTTP:8443** ×2 |
| `REMNA_SERVER_SNI` в repo | `www.yandex.ru` | **Не отражён** в live sub |
| LV Caddy selfsteal | ⚠️ | Блок **`api.github.com:9443`** reverse_proxy — **палит github на edge** |
| `:2053` grace | ⚠️ | Слушает, **301→8443** — скан 3X-UI fingerprint сохранён |
| Tier RF / whitelist SKU | ❌ | **Q060** wiki only; tiers 2–3 без RF egress |

---

## Находки P0–P3 (приоритет = риск × вероятность × масштаб GTM)

### P0 — блокер роста / «спалим базу»

| ID | Вектор | Доказательство | Почему зло | Минимум | Идеал | Q |
|----|--------|----------------|------------|---------|-------|---|
| **T24-01** | **SNI github-кластер в live sub** | Pull sub: `sni=api.github.com`, microsoft, apple, bing на **:443** vision | Прямое попадание в [Habr 1009542](https://habr.com/ru/articles/1009542/) слой 2–4; **Q058 закрыт в репо, не на панели** | Snapshot template; patch Reality dest → **www.yandex.ru**; forced sub refresh сегментом | Политика SNI: только yandex/neutral RF; smoke **`LIVE_SUB_SNI_OK`** | **Q102** |
| **T24-02** | **Один доминирующий fingerprint на GTM** | Default `REMNA_FLOW=xtls-rprx-vision`, primary **LV:443**; MUX «both» не гарантирует выбор alt | Массовый GTM → **один паттерн** → ручной/авто бан по [TSPU-OBS #8](TSPU-OBSERVATIONS.md) | Сегментировать новых пользователей по outbound; FAQ «сначала alt / XHTTP» | 3-й профиль sub: **xhttp-first** для RU ISP | **Q103** |

### P1 — высокий риск до 10k

| ID | Вектор | Доказательство | Действие | Q |
|----|--------|----------------|----------|---|
| **T24-03** | **MUX audit слепой к XHTTP** | `transport_mux_audit.py` только `vnext`; XHTTP 2/18 не в метрике | Расширить классификацию; порог **has_xhttp**; portal «при LTE: узел XHTTP» | **Q103** |
| **T24-04** | **Selfsteal github :9443** | LV Caddy `api.github.com:9443` | Убрать github из decoy или заменить на neutral; согласовать с Q057 | **Q104** |
| **T24-05** | **Whitelist L3 апр 2026** | [Habr 1027276](https://habr.com/ru/articles/1027276/), [Коммерсант](https://www.kommersant.ru/doc/7659315) | Runbook «режим whitelist»: RF egress, DNS bootstrap, не обещать portal с NL IP | **Q105** |
| **T24-06** | **Один RU relay** | `72.56.0.145` only | 2-й relay другого ISP/региона; агрегация в status | **Q106** |
| **T24-07** | **Нет playbooks под волну VLESS 2026** | Runbook не ставит **XHTTP первым** | Обновить `RUNBOOK-TSPU-VLESS-INCIDENT.md` + FAQ | **Q103** |

### P2 — средний

| ID | Вектор | Действие | Q |
|----|--------|----------|---|
| **T24-08** | Grace **:2053** слушает | Метрика 301 hits; план off после N дней | ops |
| **T24-09** | RF tiers не в проде | **Q060** go/no-go или снять tier из маркетинга | product |
| **T24-10** | Нет проверки **JA3/uTLS** на нодах | `tls_client_stack_audit.py` на NL/LV inbound | **Q107** |
| **T24-11** | QUIC/Hysteria не в MUX | Опциональный UDP профиль (Hysteria2) для ISP с TCP-only DPI | R&D |

### P3 — хвост

| ID | Вектор | Действие |
|----|--------|----------|
| **T24-12** | ECH не использовать | Зафиксировать в TLS quarterly |
| **T24-13** | Crowd telemetry | Интеграция с BlockPulse-style отчётами пользователей (ISP+город) |
| **T24-14** | `alt_ob_share` 56% | Не путать с **активными сессиями** на alt |

---

## Tabletop: «ТСПУ включил слой 4 на Мегафоне Москва»

| T+ | Симптом | Текущая реакция продукта | Пробел |
|----|---------|--------------------------|--------|
| 0–5m | vision+443 timeout, portal :8443 OK | Wizard → status :8443 ✅ | Sub всё ещё предлагает **github SNI** на 443 |
| 5–30m | RU probe OK, VPN dead | `ru-monitor` SNI HTTP, не VLESS | Нет алерта по **inbound success rate** |
| 30m | Массовые тикеты | MUX «переключи NL/9443» | **XHTTP** не в FAQ первым; нет auto-hint в боте |
| 24h | GTM посты | — | Один fingerprint → риск **T24-02** |

---

## Что усилить в продукте (короткий план)

1. **Q102 (срочно):** панель — Reality **www.yandex.ru** (и убрать github/microsoft/bing из template); verify live sub.  
2. **Q103:** MUX 2.0 — XHTTP в audit + UX «LTE не коннектит → узел **LV XHTTP 8443**».  
3. **Q104:** selfsteal без `api.github.com:9443`.  
4. **Q105:** runbook **whitelist L3** + связка с P4-DNS / RF egress.  
5. **Q106:** второй RU probe (СПб/Юг) + cron aggregate.  
6. **Q107:** квартальный JA3 на нодах (uTLS / sing-box parity).

---

## Verify (агент / ops)

```bash
python ops/smoke_tspu_redteam.py          # edge only
python ops/smoke_live_sub_sni.py          # после Q102 — должен быть LIVE_SUB_SNI_OK
ssh root@bvpn-lv python3 /opt/scripts/tspu_block_probe_ru.py
python ops/_audit_sub_transports.py       # ручной разбор outbound (dev)
```

---

## Оценка готовности

| Цель | Вердикт |
|------|---------|
| **200 users GTM** | **Условно** — только если Q102 на проде + LTE чеклист владельца |
| **10k** | **Нет** без MUX XHTTP-first, multi-region probe, whitelist playbook |
| **Аудит «злой»** | **Пройден** — предыдущий 7,5/10 **завышен** из‑за smokes без live sub SNI |

---

## Очередь

| Q | ID | Статус предложения |
|---|-----|-------------------|
| — | **P2-RED-TSPU-AUDIT-04** | Этот отчёт (в коммите с очередью) |
| **102** | **P2-RED-SNI-LIVE-01** | **NEXT** — panel SNI |
| **103** | **P2-RED-MUX-XHTTP-01** | MUX + incident + FAQ |
| **104** | **P2-RED-SELFSTEAL-SNI-01** | Убрать github :9443 |
| **105** | **P2-RED-WHITELIST-L3-01** | Runbook whitelist |
| **106** | **P2-RED-TSPU-PROBE-MULTI-01** | 2-й RU relay |
| **107** | **P2-RED-TLS-JA3-01** | JA3 audit inbound |

**Q101** (CodeRabbit security) — **параллельно**, не заменяет Q102–107.
