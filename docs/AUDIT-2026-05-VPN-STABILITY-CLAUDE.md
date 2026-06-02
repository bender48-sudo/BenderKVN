# Аудит стабильности VPN / Happ / балансировка — Claude (2026-05-25)

**Основание:** жалобы пользователей «VPN включён, но не работает»; Instagram/медиа отваливается; страница подписки «сначала ошибка → потом ок».
**Критическое ограничение:** пользователь **не** должен вручную выбирать NL/LV/turbo. Переключение — ответственность шаблона подписки + client-side балансировщиков.
**Источники:** `subscription_log.txt`, `access_log.txt` (2026-05-24), `python ops/probe_subscription.py`, `drift-q084.txt`, `docs/HAPP-MATRIX.md`, `docs/TRANSPORT-MUX-MATRIX.md`, `docs/NODE-POLICY-LV-NL.md`, `docs/PRODUCT-TIER-PROFILES.md`.

---

## 1. State Machine — Happ import pipeline

```
[sub-page HTTP 200, 11 562 bytes, Content-Type: application/json]
          │
          ▼
  Happ: batch-import parser
  итерирует по outbounds:
  • vless/tcp (Reality)  → OK
  • vless/xhttp          → ❌ UnknownContentType  ← ТОЧКА СБОЯ
          │
          ▼
  ImportResult(count=0)                           ← 1054 × за сессию
          │
          ▼
  UI: "0 серверов" / ошибка подписки             ← 537 × за сессию
          │
          ▼
  Happ fallback: Append custom config
  (полный xray-JSON загружается как один кастомный профиль)
  ImportResult(count=1)
          │
          ▼
  Xray engine запускает burstObservatory
  pings 18 outbounds каждые ~15 с
          │
          ▼
  leastLoad выбирает outbound с наименьшим score
          │
          ├─ proxy-6 / proxy-7 / proxy-8 флап   ← 435 / 244 / 327 обращений
          │   (близкие scores или один сломан)
          │
          └─ 194.221.250.50:443 — 524 retry     ← relay или битый outbound
             TCP connect OK, app-layer timeout?
```

**Единая точка фикса:** убрать `vless/xhttp` outbounds из шаблона подписки → batch import восстановится → count > 0 → пользователь снова видит именованные серверы + leastLoad работает внутри нормально импортированного конфига.

**Важное уточнение:** когда batch-import падает (count=0) → Happ загружает полный xray-JSON как «1 кастомный профиль» → **burstObservatory + leastLoad внутри xray всё равно работают.** VPN физически не умирает от xhttp-бага. Умирает UX (пользователь видит ошибку, паникует, удаляет конфиг) и доверие к продукту. Отдельный источник «VPN on but dead» — retry-шторм к `194.221.250.50:443` (см. Q-VPN-STAB-004).

---

## 2. Гипотезы первопричин (P0 → P1)

### P0-A: vless/xhttp ломает Happ batch-import

**Доказательства:**
- `probe_subscription.py` (2026-05-24): `vless/xhttp ×2` в outbounds (LV:8443 XHTTP-inbound).
- `subscription_log.txt`: `UnknownContentType` **1 054×** → всегда `count=0`.
- Регрессия по датам: Apr 05 → `count=4` (xhttp ещё не был в шаблоне); May 24 → `count=0` (xhttp добавлен в 2026).
- `docs/TRANSPORT-MUX-MATRIX.md` §XHTTP (2026): «скрипт `transport_mux_audit.py` пока **не** считает XHTTP — Q103».

**Механизм:** Happ итерирует по массиву outbounds, встречает `"network": "xhttp"`, не знает этот тип → выбрасывает ошибку для всего batch (не только для одного outbound) → `count=0`.

**Почему было count=4 в апреле:** тогда в шаблоне было 4 outbound типа vless/tcp, xhttp ещё не добавили. После добавления xhttp Happ стал падать на первом же нераспознанном outbound.

---

### P0-B: retry-шторм к 194.221.250.50:443

**Доказательства:**
- `access_log.txt`: 524 обращения к этому одному адресу (≈42% всех proxy-строк).
- Шаблон: TCP connect успешен (SYN-ACK доходит), но далее app-level timeout → Xray retry.
- Это либо RELAY→LV (порт 443), либо специфический outbound в LV с неправильным TLS/Reality fingerprint.

**Последствие:** если leastLoad выбирает этот outbound (score «лучший» по ping, но app-layer мёртв) → все соединения через него зависают → пользователь видит «VPN работает, но всё тормозит/не открывается».

**Нужно:** идентифицировать IP → в `probe_subscription.py` `label()` нет записи для `194.221.250.50` → проверить `site_urls.RU_RELAY_HOST` и LV IP list.

---

### P1-A: leastLoad флап proxy-6/7/8

**Доказательства:**
- `access_log.txt`: proxy-6=435, proxy-8=327, proxy-7=244; proxy-7 впервые появился в 20:26:13 — это переключение балансировщика в реальном времени.
- При 1 кастомном профиле (Append custom) xray видит 18 outbounds; burstObservatory пингует каждые 15 с.

**Гипотеза:** scores proxy-6/7/8 близки (все на LV, latency 10-30 ms друг от друга) → leastLoad переключается при малейшем изменении. Это не «VPN умирает» — это балансировщик работает штатно, но при dead-outbound (P0-B) один из слотов ломает конкретные соединения.

---

### P1-B: AMS OOM-риск при sub-refresh-шторме

**Доказательства:**
- SSH snapshot AMS: RAM 1.9 GiB, ~95 MiB free, **swap = 0**.
- AMS хостит remnawave (панель) + dual sub-page (:3010/:3011).
- При массовой push-notify о новом шаблоне → все Happ разом запрашивают `/api/sub/` → память AMS исчерпывается → `502` или `503` → пользователь видит «страница подписки недоступна» → нет автообновления.

---

### P1-C: balancer.sh и watchdog.sh не запущены (drift)

**Доказательства:**
- `drift-q084.txt`: `balancer.sh` MISSING на bvpn-lv, `watchdog.sh` MISSING на bvpn-nl.
- Без balancer.sh нет TG-алертов о заполнении capacity (≥80%). Без watchdog.sh нет авто-перезапуска remnanode на NL при зависании.

---

### P1-D: NL сессии 0% (P6-SCALE-NL-VERIFY)

**Косвенные доказательства:**
- `access_log.txt`: только proxy-6/7/8 — все могут быть LV-outbounds. NL-outbounds (порт 9443) не видны в логе.
- При dead-RELAY к NL или при 9443-блокировке DPI → leastLoad депроритизирует NL-outbounds после первого провала observatory → весь трафик на LV.
- `docs/NODE-POLICY-LV-NL.md` P6-SCALE-NL-VERIFY: «7+ дней 0% на NL → аудит leastLoad, порядок outbounds».

---

## 3. Happ compatibility table

| Фича | Happ поддержка | Риск |
|------|---------------|------|
| vless/tcp (Reality, TLS) | ✅ Полная | Низкий — core protocol |
| vless/xhttp | ❌ Не в batch import | **P0** — ломает весь batch, count=0 |
| burstObservatory в custom-config | ✅ Работает внутри xray | Низкий — xray engine видит все outbounds |
| burstObservatory в batch-import | ⚠️ Не проверено | Средний — при count>0 нужно проверить |
| leastLoad strategy | ✅ Xray engine | Средний — флап при одинаковых scores |
| injectHosts count=16 (18 outbounds) | ⚠️ Работает технически | Средний — при batch-parse любой unrecognized → весь batch падает |
| JSON size ~11 KB | ✅ Норма | Низкий |
| Batch import full xray JSON | ❌ Сломан xhttp | **P0** — fallback to custom |
| Append custom (fallback) | ✅ Работает | Средний — UX «1 кастомный» вместо 18 named |
| RU-bypass routing rules | ✅ xray routing | Низкий — 20% direct ожидаемо |
| RELAY outbounds | ✅ vless/tcp | Низкий — если relay жив |

---

## 4. Auto-balance verdict: **PARTIAL (сломан UX, механика работает)**

**Что работает:**
- burstObservatory + leastLoad физически функционируют внутри xray-конфига, загруженного как custom profile.
- Трафик распределяется между proxy-6/7/8 (LV-outbounds) на основе latency.
- В логе нет явных reject/fail/timeout строк — VPN-туннель жив.

**Что сломано:**
1. Пользователь видит «0 серверов» при каждом обновлении подписки → вынужден смотреть на ошибку.
2. NL-outbounds могут де-факто исключены leastLoad (если они недостижимы через DPI) → нет geographic failover LV↔NL.
3. Если пользователь удалит кастомный профиль (логичное действие при «ошибке») → **ни одного сервера**.
4. После fix (убрать xhttp) batch-import вернёт count > 0 → пользователь снова видит named servers. Но leastLoad всё равно выбирает автоматически → продуктовое ограничение соблюдается.

**Почему не «полностью работает»:** auto-balance не смещает нагрузку LV↔NL когда нужно, а лишь выбирает «лучший» из живых. Если NL-порты блокированы DPI → leastLoad честно оставит всех на LV. Нет server-side механизма «принудительно слить трафик на NL».

---

## 5. Gap vs продуктовое ограничение

| Ситуация | Gap | Нарушение ограничения? |
|----------|-----|------------------------|
| Batch import fail (xhttp) → 1 custom profile | Пользователь не может управлять серверами UI-кнопками Happ | Нет (он их и не видит), но UX сломан |
| Batch import success → 18 named servers | Пользователь **может** вручную выбрать NL в Happ | Да — если мы явно не говорим «не трогай» |
| leastLoad депроритизировал NL из-за DPI | VPN перегружает LV; нет авто-failover на NL | Нет ручного выбора, но нет и failover |
| 194.221.250.50:443 broken outbound | leastLoad выбирает битый outbound, VPN умирает | Нет ручного выбора, но пользователь страдает |
| Нет push-notify после смены шаблона | Старый конфиг в Happ неограниченно долго | Нет ручного выбора, но авто-обновление не гарантировано |
| drift: балансировщик не запущен | Нет алертов о перегрузке LV | Нет прямого нарушения, но реакция на нагрузку слепая |

---

## 6. Fix plan

### Q-VPN-STAB-001 (P0) — Убрать vless/xhttp из шаблона подписки

**Изменение:** PATCH subscription template: удалить все outbounds с `"network": "xhttp"` (VLESS_XHTTP_LV, LV:8443 xhttp). Снимок перед изменением → `.secrets/snapshots/template-before-remove-xhttp-*.json`.
```bash
python ops/freeze_ams_node.py --dry-run   # проверить текущий template
# затем ручной PATCH через ops/panel_api.py или UI панели
python ops/probe_subscription.py          # убедиться: vless/xhttp отсутствует
```
**Verify:** `probe_subscription.py` → `vless/xhttp` count = 0; staging Happ import → `ImportResult(count > 0)`.
**Rollback:** `PATCH /api/subscription-templates` из `.secrets/snapshots/` последний snapshot.

---

### Q-VPN-STAB-002 (P0) — Идентифицировать и починить/убрать 194.221.250.50:443

**Изменение:** Добавить `194.221.250.50` в `label()` функцию `probe_subscription.py` и других ops-скриптов. Проверить на LV и NL, доступен ли этот IP через `curl -v` / `nc -zv`. Если это RELAY→LV с нерабочим Reality fingerprint → пересоздать или убрать из injectHosts этот UUID.
```bash
# Из ops-машины или LV:
curl -v --max-time 10 https://194.221.250.50:443
# Идентифицировать через panel API: найти outbound с этим IP
python ops/probe_subscription.py   # убедиться, что IP помечен как RELAY или OTHER
```
**Verify:** после fix — в `access_log` исчезают 500+ retry к этому IP; latency соединений стабилизируется.
**Rollback:** если это рабочий RELAY — добавить правильный fingerprint; если битый — восстановить UUID в injectHosts.

---

### Q-VPN-STAB-003 (P1) — Принудительное обновление подписки у всех пользователей

**Изменение:** После Q-VPN-STAB-001 отправить push-notify всем активным пользователям через бот (bump generation + notify). Только так старый xhttp-конфиг в Happ заменится новым.
```bash
# bot_src/subscription_refresh.py или subscription_config_notify
python bot_src/subscription_config_notify.py --all-active
```
**Verify:** sample 5 пользователей → в их Happ `count > 0` при следующем обновлении.
**Rollback:** N/A (notify одноразовый).

---

### Q-VPN-STAB-004 (P1) — Тюнинг burstObservatory: interval и subjectSelector

**Изменение:** Увеличить `pingInterval` с 15 с → 30–60 с (уменьшить шум), добавить `subjectSelector` только на proxy-* outbounds (исключить `direct`, `dns-out`, `block`). Проверить `probeURL` — должен быть реально доступный URL через прокси.
```json
"burstObservatory": {
  "subjectSelector": ["proxy"],
  "pingConfig": {"interval": "30s", "destination": "https://www.gstatic.com/generate_204"}
}
```
**Verify:** `access_log` — proxy-X стабилизируется, флапы реже; observatory scores не скачут.
**Rollback:** template PATCH restore из snapshot.

---

### Q-VPN-STAB-005 (P1) — Trim injectHosts: убрать RELAY→NL если NL-порты блокированы

**Изменение:** Проверить через `transport_mux_audit.py` долю `has_alt`. Если NL-outbounds не используются (0% сессий 7+ дней → P6-SCALE-NL-VERIFY) — убрать нерабочие RELAY→NL UUID из injectHosts, оставить только рабочие.
```bash
python ops/transport_mux_audit.py --json --sample 20
python ops/probe_subscription.py
```
**Verify:** В подписке остаются только рабочие NL-outbounds; leastLoad не выбирает мёртвые.
**Rollback:** вернуть UUID в injectHosts через ops/add_injecthosts.py.

---

### Q-VPN-STAB-006 (P1) — Добавить swap на AMS (OOM-защита)

**Изменение:** Создать 2 GB swapfile на AMS:
```bash
ssh bvpn-ams "fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo '/swapfile swap swap defaults 0 0' >> /etc/fstab"
```
**Verify:** `free -h` на AMS → swap = 2.0G.
**Rollback:** `swapoff /swapfile && rm /swapfile` + убрать из fstab.

---

### Q-VPN-STAB-007 (P1) — Развернуть balancer.sh на LV (drift fix)

**Изменение:** Скопировать `balancer.sh` на bvpn-lv:/opt/scripts/, настроить cron (ежечасно или ежедневно).
```bash
scp balancer.sh bvpn-lv:/opt/scripts/balancer.sh
ssh bvpn-lv "chmod +x /opt/scripts/balancer.sh && (crontab -l; echo '0 * * * * /opt/scripts/balancer.sh') | crontab -"
```
**Verify:** `drift-q084.sh` → balancer.sh STATUS = OK.
**Rollback:** `ssh bvpn-lv "crontab -l | grep -v balancer | crontab -"`.

---

### Q-VPN-STAB-008 (P1) — Развернуть watchdog.sh на NL (drift fix)

**Изменение:** Скопировать `watchdog.sh` на bvpn-nl:/opt/scripts/, настроить как systemd-service или cron каждые 5 мин.
```bash
scp ops/watchdog.sh bvpn-nl:/opt/scripts/watchdog.sh
```
**Verify:** `drift-q084.sh` → watchdog.sh STATUS = OK на bvpn-nl.
**Rollback:** остановить service / убрать cron.

---

### Q-VPN-STAB-009 (P2) — Отдельный sub-template для trial (P3-FLOW-21)

**Изменение:** Создать trial-шаблон: только primary outbounds (LV:443 ×2 + RELAY→LV:443 ×1), без NL, без xhttp. burstObservatory по 3 outbounds, interval=60 с. Платный шаблон — полный (без xhttp, но LV+NL).
**Verify:** Новый trial-пользователь получает sub с 3 outbounds; Happ import count=3; leastLoad авто-выбирает.
**Rollback:** Вернуть trial-пользователей на основной шаблон.

---

### Q-VPN-STAB-010 (P2) — Добавить xhttp в transport_mux_audit.py (Q103 gap)

**Изменение:** В `ops/transport_mux_audit.py` добавить классификацию `network=xhttp` как отдельный профиль (не primary, не alt). Пока xhttp убран из шаблона (Q-VPN-STAB-001) — это bookkeeping fix на будущее.
**Verify:** `python ops/transport_mux_audit.py` корректно считает xhttp, не смешивает с tcp.
**Rollback:** N/A (script only).

---

### Q-VPN-STAB-011 (P2) — Настройка Caddy rate-limit на sub-page при массовом notify

**Изменение:** Убедиться, что rate-limit 120/min/IP активен на обоих sub-page origins. Добавить jitter в push-notify scheduling (не всем одновременно, а с разбросом 0–5 мин).
```bash
python ops/subscription_ha_load_probe.py   # stress test обоих origins
```
**Verify:** при параллельной нагрузке 10 req/s → нет 429 или 502.
**Rollback:** откатить Caddyfile.

---

### Q-VPN-STAB-012 (P2) — Верификация NL-сессий (P6-SCALE-NL-VERIFY)

**Изменение:** Зайти в панель remnawave → проверить online-сессии на NL-ноде. Если 0 сессий при подключённой ноде → проверить порт 9443 с LV: `nc -zv 91.90.192.17 9443`. Если заблокирован DPI → убрать NL:9443 outbounds или добавить NL:443 как fallback.
**Verify:** После fix — в `access_log` появляются NL-tagged соединения.
**Rollback:** вернуть порты в шаблон.

---

### Q-VPN-STAB-013 (P2) — Smoke test sub-page HA после каждого деплоя

**Изменение:** Добавить `ops/smoke_sub_page_ha.sh` в CI/CD или деплой-чеклист. Запускать после любого PATCH шаблона.
```bash
bash ops/smoke_sub_page_ha.sh   # должен вывести SUB_PAGE_HA_SPLIT_HOST_OK
```
**Verify:** Оба origin возвращают 200 за <2 с.
**Rollback:** N/A.

---

### Q-VPN-STAB-014 (P3) — Деплой compose-templates на все ноды (mass drift fix)

**Изменение:** Системная ликвидация 25 MISSING из `drift-q084.txt` — все compose templates на LV/AMS/NL, ru-monitor.py, selfsteal-monitor.py, bvpn-docker-firewall.sh.
**Verify:** После деплоя `drift-q084.sh` → problems = 0.
**Rollback:** Per-item через снимки Docker volumes / git.

---

### Q-VPN-STAB-015 (P3) — Верификация AMS remnanode drain

**Изменение:** Подтвердить, что AMS remnanode (decom, P1-ARCH-AMS-DECOM) не отдаёт outbounds в sub. `probe_subscription.py` должен показать AMS=0.
**Verify:** `probe_subscription.py` → `summary: AMS=0`.
**Rollback:** Если AMS ещё нужен — вернуть в injectHosts, но запланировать decom.

---

## 7. Всё, что у нас есть для управления Happ (без доступа к клиенту)

| Рычаг | Как работает | Скрипт |
|-------|-------------|--------|
| PATCH sub template | Меняет xray-JSON для всех новых sub-запросов | `panel_api.py`, UI панели |
| injectHosts trim | Убирает UUID → убирает outbound из sub | `ops/add_injecthosts.py`, `freeze_ams_node.py` |
| Disable host в панели | Нода в maintenance → её outbounds исчезают из sub | UI панели / `panel_api.py` |
| Bump generation + push notify | Бот уведомляет → пользователь обновляет sub вручную | `subscription_config_notify.py` |
| routing rules в template | Прямой/proxied маршрут на уровне Xray (не клиентские кнопки) | `ops/ru_bypass_routing.py` |
| observatory config | interval, subjectSelector, probeURL — внутри xray config | PATCH template |
| balancer strategy | leastLoad / roundRobin / random — внутри xray config | PATCH template |
| Caddy rate limit | Замедляет refresh storms | Caddyfile |
| HA split-host | Переключение нагрузки sub-page между :3010/:3011 | `patch-caddy-sub-split-host-lv.sh` |

**Чего у нас нет:**
- Версионирование Happ на клиенте (не можем форсировать обновление).
- Управление Happ batch-parser (это код клиента).
- Гарантированная доставка push-notify (пользователь должен открыть бот).
- Серверная pre-фильтрация outbounds по health до выдачи sub (sub-page отдаёт всё из шаблона).
- happ:// deeplink для one-tap import (P3-FLOW-18, пока только HTTPS URL).

---

## 8. Целевой sub-template: trial vs paid

### Trial template (после Q-VPN-STAB-009)

```json
{
  "remarks": "BenderVPN Trial",
  "outbounds": [
    { "tag": "proxy-1", "protocol": "vless", "network": "tcp", "address": "176.126.162.158", "port": 443 },
    { "tag": "proxy-2", "protocol": "vless", "network": "tcp", "address": "176.126.162.158", "port": 443 },
    { "tag": "proxy-3", "protocol": "vless", "network": "tcp", "address": "<RELAY_IP>", "port": 443 }
  ],
  "burstObservatory": {
    "subjectSelector": ["proxy"],
    "pingConfig": { "interval": "60s", "destination": "https://www.gstatic.com/generate_204" }
  },
  "routing": {
    "balancers": [{ "tag": "balancer", "selector": ["proxy"], "strategy": { "type": "leastLoad" } }]
  }
}
```

**Обоснование:** 3 outbounds → Happ batch-import count=3 → UI показывает серверы, leastLoad выбирает автоматически → пользователь не видит кнопки «выбрать LV/NL» → ограничение соблюдено. Нет xhttp → нет UnknownContentType.

### Paid template (после Q-VPN-STAB-001)

Текущий шаблон минус xhttp outbounds (удалить VLESS_XHTTP_LV / LV:8443 xhttp). Все остальные 14-16 outbounds (LV:443 ×4, RELAY→LV ×3, NL:443 ×4, RELAY→NL ×3) остаются. burstObservatory + leastLoad — как сейчас, но с увеличенным interval (Q-VPN-STAB-004).

**Возврат xhttp:** когда Happ добавит поддержку `network=xhttp` в batch parser — добавить обратно как третий транспорт (LV:8443 xhttp ×1-2). До тех пор — только в hidden/advanced профилях, не в основном шаблоне.

---

## 9. P3-FLOW-21 — Скрыть turbo/wl для trial users

**Контекст (из PRODUCT-TIER-PROFILES.md):** turbo = NL/LV max speed; wl-direct / wl-routed = RF egress, будущие уровни (Q062).

**Текущее состояние:**
- wl-direct и wl-routed **ещё не реализованы** (Q062 backlog). Скрывать нечего.
- turbo = просто всё то, что сейчас есть (NL + LV outbounds). Trial-пользователь и так получает «turbo» — это базовый продукт.

**Вывод P3-FLOW-21:** Релевантен только когда Q062 будет готов (RF egress нода + wl-профили в шаблоне). Сейчас реализовать невозможно — нет отдельных wl-outbounds в шаблоне. **Статус: BLOCKED on Q062.** Промежуточный шаг — Q-VPN-STAB-009 (trial template без NL), что фактически и есть «только turbo-primary» без alt-tier.

**После Q062:** в paid-шаблоне появятся wl-direct / wl-routed outbounds. Для trial — исключить их из шаблона через отдельный UUID-set в injectHosts (только turbo-tier UUIDs).

---

## 10. False positives (что работает)

| Что | Доказательство |
|-----|---------------|
| Sub-page отдаёт валидный JSON 200 | `probe_subscription.py`: HTTP 200, 11 562 bytes, JSON parseable |
| 18 outbounds с LV/NL паритетом | LV=8, NL=8 в probe — injectHosts настроен корректно |
| HA split-host работает | p4n7q→:3010, k9x2m1→:3011; smoke_sub_page_ha.sh → OK |
| RU bypass routing intent | 20% direct в access_log — это _правильно_ для geosite:ru трафика |
| burstObservatory + leastLoad в config | Присутствуют в JSON (probe confirmed); xray engine их исполняет |
| RELAY outbounds присутствуют | RELAY→LV ×3, RELAY→NL ×3 — запас для censored networks |
| Rate-limit на Caddy | 502×1, 429×1 за 11 560 строк лога = очень редко = хорошо |
| VPN-туннель физически жив | Нет reject/fail/timeout в access_log; трафик идёт через proxy-X |

---

## 11. NO-GO

1. **«Выберите NL вручную»** — нарушает hard product constraint.
2. **Оставить xhttp в шаблоне** — P0, ломает batch import каждый раз.
3. **Увеличить injectHosts до >18 outbounds** — больше вероятность встретить unrecognized transport и получить count=0.
4. **Убрать burstObservatory как «fix» флапа** — убирает автобалансировку, нарушает constraint.
5. **Убрать HA split-host для «упрощения»** — теряем failover sub-page.
6. **Игнорировать AMS RAM** — OOM во время stampede положит sub-page для всех.
7. **Деплой xhttp обратно без подтверждения Happ поддержки** — немедленный регресс к count=0.

---

*Verify loop после всех P0-фиксов:*
```bash
python ops/probe_subscription.py          # count outbounds, no xhttp
python ops/transport_mux_audit.py         # has_primary=100%, has_alt≥95%
python ops/subscription_ha_load_probe.py  # оба origins <500ms
bash ops/smoke_sub_page_ha.sh            # SUB_PAGE_HA_SPLIT_HOST_OK
# staging: импортировать sub в Happ → ImportResult(count > 0)
```
