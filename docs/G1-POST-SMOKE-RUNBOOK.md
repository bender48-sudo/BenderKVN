# G1 post-smoke — снять UA + проверить INCY HWID

**ID:** `G1-H1-SMOKE-001` (owner steps)  
**Когда:** сразу после того, как друг откроет canary URL в INCY / V2Ray Client+ / Изи VPN.  
**Режим:** read-only. **Не** включать enforce / billing / MODEL A.

Canary URL (одна строка):

`https://p4n7q.conntest.xyz:8443/owner-canary/canary-PIzWk8ql30ipVHyvB8S58rlr0dxcCH1m.json`

---

## Шаг 1 — Edge UA + HWID headers (обязательно)

На **bvpn-lv**:

```bash
bash ops/tail_owner_canary_ua_log.sh --since-minutes 60 --verbose
# или полные строки (только /owner-canary/):
grep '/owner-canary/' /var/log/caddy/owner-canary-access.log | tail -20 \
  | python3 -c "
import sys, json
for line in sys.stdin:
    r = json.loads(line)
    h = r.get('request',{}).get('headers',{})
    def g(k):
        for kk,v in h.items():
            if kk.lower()==k.lower():
                return (v[0] if isinstance(v,list) and v else v) or '-'
        return '-'
    print('\t'.join([
        str(r.get('ts','?')),
        r.get('request',{}).get('remote_ip','?'),
        g('User-Agent'),
        g('x-hwid'), g('x-device-os'), g('x-device-model'),
        g('x-ver-os'), g('x-app-version'), g('x-client'),
    ]))
"
```

**Записать в UA-map** (таблица ниже — дополнить реальными строками):

| Клиент (G1) | User-Agent (полная строка) | remote_ip | Примечание |
|-------------|------------------------------|-----------|------------|
| INCY | _ждём G1_ | | |
| V2Ray Client+ | _ждём G1_ | | |
| Изи VPN | _ждём G1_ | | |

**Важно:** canary — статический файл; UA здесь = то, что клиент шлёт при **импорте/обновлении** URL. Для HWID-реестра нужен шаг 2 (реальный `/api/sub`).

---

## Шаг 2 — INCY в HWID-реестре (критично)

Если друг импортировал **боевой** sub URL (шаг B1b в [`G1-H1-SMOKE-PACKAGE.md`](G1-H1-SMOKE-PACKAGE.md)), проверить owner или lab-user:

```bash
# на ПК с PANEL_TOKEN=REMNA_API_TOKEN_LV
python ops/_device_smoke_owner_probe.py
# или любой shortUuid lab-user после импорта на INCY
```

**Критерий PASS для INCY как основного iOS-детекта:**

| Сигнал | Ожидание если INCY шлёт x-hwid |
|--------|-------------------------------|
| `device_count` вырос после INCY-import | +1 (новый `hwid`) |
| `userAgent` в записи HWID | строка INCY из G1, не Happ |
| `platform` / `deviceModel` | заполнены (как у Happ) |

**Если INCY import только canary:** HWID **не** проверить — canary не идёт через Remna `/api/sub`. Для HWID нужен **один** fetch боевого `https://p4n7q…/api/sub/{short}` из INCY (достаточно добавить подписку, не обязательно подключать VPN).

**Вердикт (заполнить после G1):**

- [ ] INCY **шлёт** x-hwid → закрывает детект для основного iOS (Track A)
- [ ] INCY **не шлёт** x-hwid → основной iOS только Happ; INCY → Track B или отдельный конфиг
- [ ] V2Ray Client+ / Изи VPN — ожидаем **нет** в HWID; только Track B

---

## Шаг 3 — Дополнить матрицу (read-only)

После фиксации UA из шага 1:

```bash
# probe с реальным UA (без enforce)
python ops/probe_sub_hwid_headers.py --short <SHORT> --ua "<INCY UA from G1>"
```

Сохранить вывод локально (не в git).

---

## Шаг 4 — Решение (владелец)

| Исход | Следующий gate (не сейчас) |
|-------|----------------------------|
| INCY + HWID | Track A для Happ+INCY; G13 UA-branch |
| INCY без HWID | Track B для INCY; Happ остаётся HWID |
| V2Ray+/Изи без HWID | Track B only |

**СТОП** до отдельного OK на enforce / DEVICE-BILL / MODEL A.
