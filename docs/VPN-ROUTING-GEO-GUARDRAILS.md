# Geo / routing — антипаттерны и guardrails (Happ)

**Назначение:** одна страница «почему geo снова сломалось» и **что проверять до PATCH** шаблона подписки.  
**Аудитория:** агент, владелец, любой патч `templateJson.routing` / `templateJson.dns`.

Связанные документы:

- **`docs/VPN-INCIDENT-LESSONS-2026-05-25.md`** — observatory, relay, balancer (другой класс ошибок)
- **`docs/RU-BYPASS.md`** — как безопасно добавлять RU-домены
- **`ops/happ_geosite_guard.py`** — автоматическая проверка
- **`ops/diagnose_happ_import.py`** — входит в **`vpn_verify_gate.py`**

---

## 1. Три подтверждённых инцидента (не повторять)

| # | Дата / gen | Что патчили | Симптом у пользователя | Корень |
|---|------------|-------------|------------------------|--------|
| **G1** | ~2026-05, routing | **`geosite:category-ru`** в direct-rule | Instagram / Telegram **то грузят, то нет**; в access_log RU apps → `[socks -> direct]` | category-ru **шире**, чем «только банки»; TG/IG CDN попадают в direct **до** intl pre-rule |
| **G2** | gen=39, **dns** | `dns.servers` с **`geosite:ru`** (split DNS) | Happ: **«Ошибка Geo файлов»**, ядро не стартует | Bundled **`geosite.dat` в Happ не содержит секцию `RU`** |
| **G3** | gen=50→51, **routing** | VPN-AUD-210: **`geosite:ru`** вместо `regexp:.*\.ru$` | Тот же crash: `code not found in geosite.dat: RU` | Тот же bundled geosite; gate не ловил routing (только server-side probe) |

**Общий урок:** в subscription template для **Happ** нельзя полагаться на geosite-коды из полного v2fly/Loyalsoldier dat. На клиенте — **урезанный** `geosite.dat`.

Откаты:

| Инцидент | Скрипт / действие |
|----------|-------------------|
| G1 | `ops/patch_routing_category_ru_leak.py` — убрать category-ru, Intl_Stealth pre-rule |
| G2 | `ops/patch_remove_dns_split.py` — убрать templateJson.dns с geosite |
| G3 | `ops/patch_routing_regexp_to_geosite_ru.py --rollback <snapshot>` |

---

## 2. Happ-safe vs Happ-unsafe (шпаргалка)

### Routing `routing.rules[].domain`

| Matcher | Happ | Прод сейчас | Комментарий |
|---------|------|-------------|-------------|
| `regexp:.*\.ru$` (+ punycode) | ✅ | ✅ R4 direct | Широко, но **работает** без geosite.dat |
| `geosite:ru` | ❌ **crash** | ❌ NO-GO | G3 |
| `geosite:category-ru` | ⚠️ стартует | ❌ убран | G1 — TG/IG leak; только с pre-rule и A/B |
| `geosite:telegram`, `instagram`, … | ✅ | ✅ Intl_Stealth R2 | **Должны быть выше** direct-rule |
| FQDN из `EXTRA_DIRECT_DOMAINS` | ✅ | ✅ | vk.com, yandex.com, банки .com |
| `geoip:ru` | ✅ | ✅ R5 | Нужен для IP в РФ |

### DNS `templateJson.dns`

| Подход | Happ | Прод |
|--------|------|------|
| Split DNS **regexp + FQDN** (`dns_split_config.py`) | ✅ | ✅ VPN-AUD-230 |
| **`geosite:ru`** в `dns.servers` | ❌ **crash** | ❌ G2 |
| Routing **`port:53 → direct`** | ⚠️ | ❌ gen=30 regression |

### Прочее

| Паттерн | Риск |
|---------|------|
| `domain: []` + `outboundTag: block` | Xray/iOS: `no effective fields` |
| `geoip:private` | iOS без PRIVATE в geoip.dat — только явные CIDR |

---

## 3. Канонический routing на проде (после откатов)

```
R2  Intl_Stealth  geosite:instagram, telegram, …  → relay-only pool
R4  direct        regexp .ru + EXTRA_DIRECT_DOMAINS (без geosite:ru/category-ru)
R5  direct        geoip:ru
catch-all         Super_Balancer / Intl_Direct (см. verify_vpn_balancer_profile)
```

Проверка режима: `python ops/verify_ru_bypass_status.py` → **`mode=normal_regexp`**, **`RU_BYPASS_STATUS_OK`**.

---

## 4. Checklist ПЕРЕД любым PATCH routing/dns

**Обязательно (агент):**

1. **Dry-run** патча + snapshot path в `.secrets/snapshots/`
2. **`python ops/happ_geosite_guard.py`** — exit 0, **`HAPP_GEOSITE_GUARD_OK`**
3. **`python ops/diagnose_happ_import.py`** — нет geosite:ru; batch_risk=LOW
4. **`python ops/verify_ru_bypass_status.py`**
5. **`python ops/probe_ru_bypass.py`** — RU → direct, telegram.org → **не** direct
6. **`python ops/vpn_verify_gate.py`** на **bvpn-lv** (полный gate)
7. **Один** PATCH → notify gen → **стоп**; не цепочка routing+dns+balancer

**После деплоя (владелец / РФ):**

8. Happ: **обновить подписку** → профиль **стартует без «Ошибка Geo файлов»**
9. IG/TG 5–10 мин (O-VPN-002)

**Запрещено без `--force-happ-incompatible` и staging Happ:**

- `--apply` на `patch_routing_regexp_to_geosite_ru.py`
- Любой новый `geosite:ru` в routing или dns
- Возврат `geosite:category-ru` в direct без Intl_Stealth **выше** и owner smoke

---

## 5. Как улучшать RU bypass без geosite:ru

| Цель | Безопасный путь | Небезопасный |
|------|-----------------|--------------|
| Новый RU-сервис | FQDN в **`EXTRA_DIRECT_DOMAINS`** → `ru_bypass_routing.py` | geosite:ru |
| Уже .ru домен | Уже покрыт regexp | — |
| Уже .com RU CDN | FQDN в EXTRA list | category-ru |
| Узкий список вместо regexp | Happ routing profile / отдельный tier (v2rayN) | geosite:ru в shared template |
| DNS split intl/RU | `patch_dns_split_config.py` (regexp only) | geosite в dns.servers |

**VPN-AUD-210 закрыт как REVERTED / NO-GO на Happ.** Альтернатива «regexp слишком широкий» — точечные FQDN + мониторинг access_log, не geosite:ru.

---

## 6. Команды verify (копипаст)

```bash
python ops/happ_geosite_guard.py
python ops/verify_ru_bypass_status.py
python ops/probe_ru_bypass.py
python ops/diagnose_happ_import.py
python ops/probe_subscription.py
# на LV:
python3 /opt/scripts/vpn_verify_gate.py
```

Откат template: snapshot в `.secrets/snapshots/template-before-*.json` или `--rollback` у патч-скрипта.

---

## 7. Журнал (добавлять строки при новом инциденте)

| Дата | ID | Что сломали | Fix |
|------|-----|-------------|-----|
| 2026-05 | G1 | category-ru → direct leak | `patch_routing_category_ru_leak.py` |
| 2026-05 | G2 | dns geosite:ru gen=39 | `patch_remove_dns_split.py` |
| 2026-06-03 | G3 | routing geosite:ru gen=50 | rollback gen=51; `--apply` blocked |

---

*При новом geo/routing PATCH — сначала прочитать §2–§4. Обновлять §7 только после подтверждённого инцидента на проде.*
