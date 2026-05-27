# Сверка полного аудита Claude (2026-05-28) с продом

**Цель:** не дублировать уже закрытое; оставить в работе только актуальные P0/P1.  
**Проверка:** `python ops/verify_vpn_balancer_profile.py`, SSH LV/AMS, `python ops/drift-check.py` (2026-05-28).

---

## Уже закрыто (в аудите Claude — устарело)

| Тезис Claude | Факт на 28.05 |
|--------------|----------------|
| Super_Balancer только `proxy-5..7`, SPOF catch-all | **gen=26:** Super + Intl = **11 путей** (`RU_MULTIPATH_SELECTOR`). `VPN_BALANCER_PROFILE_OK` |
| «33% трафика на 3 relay» (§4.3) | **~9%** при random по 11 (3 relay + 4 LV + 4 NL) |
| `uplinkOnly=2`, `downlinkOnly=5` на live | Live sub: **30/30** |
| `ru-monitor.env` MISSING → монитор мёртв | **Файл есть** на LV; логи пишутся; `ru-monitor.py` md5 = репо |
| `balancer.sh` MISSING на LV | **Есть**; drift-check **OK** для скрипта |
| `watchdog.sh` MISSING на NL | drift-check **OK** `/opt/scripts/watchdog.sh` |
| AMS swap=0 | **2G swapfile** активен (`swapon`) |
| Немедленно #6: `patch_balancer_direct_first_intl --apply` | **Сделано** (`82a9808`, gen=26) |
| Intl = Super, оба relay-only (§2 / §8) | **Разведено:** оба multipath; правила разные (domain vs catch-all) |

---

## По-прежнему верно (брать в backlog)

### Критично / высокий приоритет

1. **Один IP LV** — 4 Direct inbound на `176.126.162.158`; один **relay IP** `72.56.0.145` для 3 inbound — корреляция для ТСПУ (§I.1.2, §III).
2. **Нет observatory** — `random` без health-check; осознанно отключено (`closed-pipe` на RU). Нужен **server-side** failover (ru-monitor → не переключает шаблон), не слепой burstObservatory.
3. **Второй relay (Q120)** — единственный долгосрочный fix SPOF relay-IP.
4. **Relay NL :9443** в подписке (proxy-12..14) — не в multipath pool, но в injectHosts; DPI-риск для тех, кто вручную выберет.
5. **AMS RAM** — ~94 MiB free + swap есть; при sub-stampede риск остаётся (меньше чем «swap=0», но не идеал).
6. **`regexp:.*\.ru$`** в direct-rule — широкий bypass (§II.2); см. `ops/ru_bypass_routing.py` / leak-fix — отдельная задача на `geosite:ru` без поломки TG/IG.
7. **fragment убран** — trade-off Reality vs DPI; per-ISP шаблоны — среднесрок (§I.1.2).
8. **DNS** — 1.1.1.1 direct, metadata leak для TG (§I.1.2, §4.5) — валидно.
9. **`.secrets/` в рабочей копии** — гигиена; не путать с vault templates в репо.

### Drift (актуально 28.05)

`drift-check`: **20/28 OK**, 8 DRIFT (compose adguard, remnawave panel.env, remna-shop, **ru-monitor.env tmpl vs prod hash**).  
**Не** опираться на `drift-q084.txt` как на текущий прод.

---

## Рекомендации Claude — пересмотренный «сегодня»

| # | Claude | Статус |
|---|--------|--------|
| 1 | Задеплоить ru-monitor.env | **Проверить render** — файл есть, hash drift с tmpl |
| 2 | verify template | **`python ops/verify_vpn_balancer_profile.py`** |
| 3 | swap AMS | **Уже есть 2G** |
| 4–5 | balancer / watchdog | **На LV/NL скрипты OK** по drift |
| 6 | multipath patch | **Done gen=26** |
| 7 | policy 30/30 + sub refresh | **Live OK**; пуш пользователям обновить sub |

---

## Ссылки в репо

| Документ | Содержание |
|----------|------------|
| `docs/AUDIT-2026-05-27-INSTAGRAM-RELAY.md` | IG/relay, gen=25→26 |
| `docs/AUDIT-2026-05-VPN-STABILITY-CLAUDE.md` | черновик Claude (локально, может быть вне git) |
| `docs/AUDIT-2026-05-VPN-STABILITY-RESOLUTION.md` | xhttp/Happ phase-1 |
| `ops/balancer_selectors.py` | канон 11 paths |
| `ops/verify_vpn_balancer_profile.py` | smoke |

---

## Для следующего аудита Claude

1. Запускать **`verify_vpn_balancer_profile.py`** и печатать **оба** balancer selector.  
2. Не цитировать **catch-all relay-only** без проверки gen.  
3. Мониторинг: **`tail /var/log/bvpn-ru-monitor.log`**, не только drift-q084.  
4. Матрица §X: строки Relay/Мониторинг/Производительность policy — **обновить** под gen=26.
