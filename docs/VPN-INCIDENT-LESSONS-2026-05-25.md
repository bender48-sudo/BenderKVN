# Уроки инцидента VPN — 2026-05-25

Журнал ошибок и запретов при хотфиксах шаблона подписки и бота. Цель — **не повторять** при следующих правках (агент / Claude / ручной PATCH).

Связанные артефакты: **`docs/VPN-DIAGNOSTIC-2026-05-25.md`**, канонический откат **`ops/patch_restore_14_relay_no_obs.py`** (gen=20).

---

## 1. Ошибки, которые мы допустили

### Шаблон подписки (панель)

| # | Что сделали | Симптом | Почему плохо |
|---|-------------|---------|--------------|
| E1 | Включили / усилили **`burstObservatory`** + **`leastLoad`** (hicloud `generate_204`, короткий timeout) | Happ **`error_log`**: `closed pipe` на всех `proxy-*` при коннекте | Пинг на connect ломает туннель; клиент не поднимает рабочий outbound |
| E2 | **`patch_injecthosts_lv_direct_only`** / **`patch_fast_connect_lv_only`**: 14 → **4** хоста, **без Relay** | RU: в **`access_log`** трафик в `[socks >> proxy]`, приложения мёртвые | Из РФ прямой LV/NL :443 часто недоступен; нужен **RELAY 72.56.0.145** |
| E3 | **`patch_injecthosts_no_relay`**: observatory + leastLoad, без relay | То же + лишний ping-storm | Двойной удар: observatory + нет RU relay |
| E4 | **`patch_restore_happ_stable`** из снимка «stable» | Снова observatory → регрессия после «восстановления» | Снимок был **не** тем профилем, что реально работал у пользователей |
| E5 | Убрали **`fragment`** из `injectHosts.defaults` без A/B | Часть пользователей могла терять обход ТСПУ на direct | Делать только с probe + откатом; не «на всякий случай» в панике |
| E6 | **`leastLoad` → `random`** без рабочего observatory | VPN **поднимается**, но **медленно** (IG/TG/Google открываются, долго грузят) | **Random** гоняет blocked-apps трафик в **RELAY→LV/NL** (~6 из 14 outbounds) вместо выбора быстрейшего Direct |
| E7 | **`patch_routing_category_ru_leak`** — правильно по доступу, но без смены balancer | Заблокированные приложения **идут через VPN** (хорошо), но через **случайный** relay-hop (плохо по скорости) | Нужен balancer «сначала Direct, relay — fallback», не один random на все 14 |
| E8 | Несколько PATCH подряд **без** единого dry-run + **`probe_subscription.py`** между шагами | Часы простоя, gen 13→20, путаница в снимках | Один PATCH → probe → smoke → только потом следующий |
| E9 | Меняли **`handshake`** (4↔12) в разных патчах | Непредсказуемый connect latency | Не трогать без измерений; gen=20 оставляет **handshake=4** |

### Бот (AMS)

| # | Что сделали | Симптом | Почему плохо |
|---|-------------|---------|--------------|
| E10 | Задеплоили **`subscription_refresh.py`** с использованием **`SUB_REFRESH_JITTER_MAX_SEC`**, константу **не** добавили в репо/контейнер | Каждые 5 мин: `Monitor loop critical error: name 'SUB_REFRESH_JITTER_MAX_SEC' is not defined` | Падает **весь** monitor (auto-renew, expiry, очередь sub-refresh ~63 user) |
| E11 | Считали, что «пуш не дошёл» = только Telegram | Пользователь не обновил sub в Happ | Авто-очередь не работала из-за E10; нужен был hotfix + ручной notify для критичных |

### Диагностика / коммуникация

| # | Что сделали | Симптом | Почему плохо |
|---|-------------|---------|--------------|
| E12 | Считали Happ **`UnknownContentType`** / «0 servers» = битый JSON | Паника, лишние PATCH | Virtual Host = **1** custom JSON; норма для Append |
| E13 | Не различили «**не коннектится**» vs «**медленно**» | После gen=20 починили connect, осталась жалоба на скорость | Разные рычаги: relay/random vs observatory/leastLoad |

---

## 2. Запреты (checklist перед PATCH шаблона)

1. **Не** включать `burstObservatory` / `observatory` без: timeout ≥10s, destination проверен на LV, Happ error_log без `closed pipe`, и плана отката.
2. **Не** убирать **Relay** UUID из `injectHosts` для RU-профиля (14 хостов: LV/NL Direct + RELAY×6 — эталон gen=20).
3. **Не** применять `patch_restore_happ_stable` и снимки с observatory как «рабочий stable».
4. **Не** менять routing + injectHosts + balancer в **одном** коммите без промежуточного probe.
5. **Не** деплоить бот-код, ссылающийся на новые константы, без `ast.parse` / `py_compile` и grep логов после restart.
6. **Не** накатывать compose/env AMS в хотфиксе VPN — только hot-patch Python или template API.
7. После любого template PATCH: **`python ops/probe_subscription.py`**, **`diagnose_happ_import.py`**, размер ~10.5 KB, 14 proxy, RELAY present, observatory absent.

---

## 3. Канонический рабочий профиль (gen=20)

- **14** outbounds: LV×4 + NL×4 + RELAY→LV×3 + RELAY→NL×3  
- **`burstObservatory`**: нет  
- **`Super_Balancer`**: `random` на `selector: ["proxy"]`  
- **`handshake`**: 4, **`fragment`**: нет  
- Routing: TG/IG/Google → balancer; `.ru` / geoip:ru → direct  

Восстановление: **`python ops/patch_restore_14_relay_no_obs.py --apply`**

---

## 4. Медленная скорость после инцидента (отдельный класс)

**Наблюдение:** до патчей «очень стабильно»; после gen=20 заблокированные приложения **открываются**, но **грузятся медленно**.

**Вероятная причина (E6+E7):**

- Раньше **`geosite:category-ru`** уводил часть трафика в **direct** (быстро, но Instagram/TG **не** работали).
- После **`patch_routing_category_ru_leak`** intl-приложения корректно идут в **`Super_Balancer`**, но balancer **`random`** по **всем 14** proxy, включая **RELAY** — лишний hop и jitter.

**Не откатывать** routing leak-fix ради скорости — вернутся «не пускает в приложения».

**Q132 footgun (2026-05-25):** нельзя менять `selector` у **`Super_Balancer`**, если на нём же висит catch-all **`network: tcp,udp`** — весь VPN (и пинг в Happ) начинает **random** по 8 Direct/NL (~×3 latency). Исправление: отдельный **`Intl_Direct`** для TG/IG/domain rules; **`Super_Balancer`** оставить **`["proxy"]`**.

**Следующий безопасный шаг (отдельная задача, не в панике):**

1. Два уровня: **`Intl_Direct`** только на **8 Direct** для geosite:instagram/telegram/…; **`Super_Balancer`** = `["proxy"]` на catch-all; RELAY — вручную из списка 14 или отдельный fallback-тег.
2. Либо вернуть **`leastLoad`** только с observatory: **gstatic/204**, timeout **10s**, interval **30s** — и проверить Happ **`error_log`** на `closed pipe` **до** prod.
3. Замер: Happ access_log — доля `RELAY` vs `LV:443 Direct` для доменов instagram.com / telegram.org у RU-клиента.

---

## 5. Команды verify (после любых правок)

```bash
python ops/probe_subscription.py
python ops/diagnose_happ_import.py
python ops/patch_restore_14_relay_no_obs.py          # dry-run: already on 14-relay profile
python ops/smoke_ams_safe_deploy.py --skip-sub-probe
python ops/_verify_sub_refresh_deploy.py             # бот: jitter=300, нет NameError
```

---

## 6. Исправлено на проде (2026-05-25)

| Компонент | Fix |
|-----------|-----|
| Template | gen=20, `patch_restore_14_relay_no_obs` |
| Bot AMS | `SUB_REFRESH_JITTER_MAX_SEC = 300`, `deploy-bot-sub-refresh-ams.ps1` |
| Скорость | **Открыто** — отдельный бэклог (§4), не откат gen=20 |

---

*Добавлять новые строки в §1 только при подтверждённом инциденте. Обновлять §3 в KNOWLEDGE-BASE при новом классе ошибок.*
