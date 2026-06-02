# Инструкция владельца — VPN post-gen=30 (2026-05-28)

**Контекст:** прод **stealth split** (TG/Meta → relay×6), edge **`:8443`**, split DNS (**VPN-AUD-230**). После любого bump шаблона — **обновить подписку в Happ**.

**Gate агента (LV):** `python3 /opt/scripts/vpn_verify_gate.py` → `VPN_VERIFY_GATE_OK`. Деплой скриптов: `ops/deploy_lv_vpn_ops.ps1`.

---

## 1. Обязательно (≈15 мин)

### O-VPN-002 / VPN-AUD-103 — smoke с телефона в РФ

1. Открой **Happ** → профиль **«🚀 BenderVPN Auto»**.
2. **Обновить подписку** (pull-to-refresh или «Update subscription»).
3. Убедись, что ссылка/порт **`:8443`**, не `:2053`.
4. **10 минут** обычного использования:
   - Instagram (лента, stories)
   - Telegram (чаты, медиа)
   - YouTube (1–2 ролика)
5. Запиши результат:
   - **OK** — всё стабильно, без «то грузит / то нет»
   - **FAIL** — что именно: приложение, Wi‑Fi/LTE, время, скрин если можно

Ответ можно коротко в Telegram себе / в §12 `COMMERCIAL-BACKLOG.md`: `VPN-AUD-103: OK` или симптом.

---

## 2. Критично для надёжности (не агент)

### O-VPN-001 / VPN-AUD-201 — второй RU relay VPS

Сейчас **все RELAY-пути** (`proxy-5..7`) на **одном IP** `72.56.0.145`. Блокировка этого IP = мёртвый relay для всех.

**Действие:** арендовать **второй VPS в другом DC/AS**, дать агенту root SSH (как для текущего relay). Это единственный fix для relay SPOF.

---

## 3. Коммуникация пользователям (если ещё не сделано)

### O-VPN-003

Если кто-то жаловался на медленный VPN или старый профиль:

1. В Happ **удалить** старый профиль BenderVPN.
2. В боте заново получить ссылку подписки (**`:8443`**).
3. Импортировать → подключиться.

После **gen≥30** в подписке **11 путей** (без мёртвых relay-NL `:9443`), DNS `:53` идёт **direct**.

---

## 4. Опционально (5 мин)

### O-VPN-007 — проверка Happ

- В списке **один** профиль «BenderVPN Auto», не 11 отдельных серверов.
- После refresh в логах/import — без массовых ошибок `UnknownContentType`.

### O-VPN-008 — regexp.ru vs geosite:ru

Пока **NO-GO** без твоего явного «go» — риск регрессии TG/IG. Задача VPN-AUD-210 в бэклоге.

---

## 5. Что уже сделано агентом (не трогать без runbook)

| Изменение | Зачем |
|-----------|--------|
| gen=30, RELAY-NL убраны | ~22% трафика не шло на dead paths |
| DNS port 53 → direct | меньше latency на resolve |
| Caddy p4n7q: **3010+3011** + health | failover при падении одного sub-page |
| **Souin cache 8m** на `/api/sub/*` | cache hit ~180ms; p50 load ~1.6s |
| `:8443` канонический edge | `:2053` только redirect |

**Откат Caddy (если что-то сломалось):** на `bvpn-lv` восстановить `/etc/caddy/Caddyfile.bak-pre-sub-ha-cache-*` и `/usr/bin/caddy.bak-pre-edge-*`, затем `systemctl restart caddy`.

---

## 6. Следующие задачи агента (тебе ничего не нужно)

- VPN-AUD-202 — `relay_failover_template.py` (авто-PATCH selector)
- VPN-AUD-160 — скрыть relay-NL hosts в панели
- VPN-AUD-370 — `/help_connect` recovery URL
- VPN-AUD-410 — trial sub-template

---

## 7. Быстрая проверка с ПК (опционально)

```bash
python ops/vpn_verify_gate.py          # VPN_VERIFY_GATE_OK
python ops/subscription_load_probe.py --url 'https://p4n7q.conntest.xyz:8443/api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2' --total 120 --concurrency 30 --json
bash ops/smoke_sub_page_ha.sh          # на Linux / через ssh bvpn-lv
```

Ожидание после cache: **p50 ~1.6s**, cache hit **~180ms**, p95 при stampede с одного IP ограничен rate limit **120/min** — для полного load test ждать 1 мин между прогонами или `--total 60 --concurrency 15`.

---

*Файл: `docs/OWNER-VPN-POST-GEN30-CHECKLIST.md`*
