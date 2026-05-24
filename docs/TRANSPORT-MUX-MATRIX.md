# Матрица транспортных профилей (P2-RED-MUX-01)

**Задача:** не один JA3/Reality‑шаблон на всю базу — минимум **два независимых транспортных профиля** в выдаче подписки.

Связь: **`docs/HAPP-MATRIX.md`**, **`docs/NODE-POLICY-LV-NL.md`**, аудит **`ops/transport_mux_audit.py`**.

---

## 1. Профили (прод, 2026-05)

| ID | Имя | Ноды / порты | Назначение |
|----|-----|----------------|------------|
| **A** | **primary** | **LV:443**, **RELAY→443** | Основной Reality (типичный HTTPS/SNI), наименьшая задержка для РФ |
| **B** | **alt** | **NL:9443**, **LV:8443**, **RELAY→9443** | Альтернативный порт/край; другой fingerprint на wire, запас при таргете **:443** |

Оба профиля присутствуют в **одной** Happ‑подписке (пользователь выбирает узел в клиенте). Это **mux на уровне продукта**, не отдельный URL подписки.

**XHTTP (2026):** inbound **VLESS_XHTTP_LV** (`network=xhttp`, порт **8443** на wire) — **третий** транспорт при блоке vision+Reality ([`AUDIT-2026-05-TSPU-REDTEAM-04.md`](AUDIT-2026-05-TSPU-REDTEAM-04.md)). Скрипт **`transport_mux_audit.py`** пока **не** считает XHTTP — см. **Q103**.

**Не в матрице:** **AMS** prod‑VPN (**drain**, P1-ARCH-AMS-DECOM) — outbounds AMS в подписке не целевые.

---

## 2. Классификация outbound (для скриптов)

Правила в **`ops/transport_mux_audit.py`** (`TRANSPORT_PROFILE_RULES`):

- **primary** — `LV:443`, `RELAY→LV` (порт 443)
- **alt** — `NL:*`, `LV:8443`, `RELAY→NL` (порт 9443)

---

## 3. Метрики

| Метрика | Смысл | Порог «OK» для P2-RED-MUX-01 |
|---------|--------|------------------------------|
| **has_primary** | У пользователя в sub ≥1 outbound профиля **A** | 100% active |
| **has_alt** | У пользователя в sub ≥1 outbound профиля **B** | ≥95% active (допуск на legacy) |
| **alt_outbound_share** | Доля outbounds профиля **B** среди всех non-direct outbounds в выборке | >0 (мультиплекс есть) |
| **users_with_both** | % active users с **A** и **B** одновременно | ≥95% |

Фактическое **подключение** к alt (сессии на :9443) — панель / ноды; отдельный аудит **`NODE-POLICY-LV-NL.md`**.

---

## 4. Проверка

```bash
# из корня репо, нужен PANEL_TOKEN или .secrets/panel-token.txt
python ops/transport_mux_audit.py
python ops/transport_mux_audit.py --json --sample 30
python ops/diagnose_happ_import.py   # Happ batch-import risk (Q-VPN-STAB-002)
python ops/probe_subscription.py     # Content-Type + outbound summary
```

Exit **0** и строка **`TRANSPORT_MUX_OK`** — матрица на проде согласована.

---

## 5. Инцидент DPI / один порт заблокирован

1. Подтвердить **`has_alt`** у выборки (`transport_mux_audit.py`).
2. Инструкция пользователю: переключить узел на **NL** или порт **9443** (см. **`docs/FAQ.md`** — дополнить при массовом инциденте).
3. Если alt отсутствует в sub — squads / injectHosts / template (**`HAPP-MATRIX`** rollback).

---

## 6. Связанные файлы

- **`ops/probe_subscription.py`** — разбор одного пользователя (by transport, Content-Type)
- **`ops/diagnose_happ_import.py`** — Happ batch-import A/B (xhttp risk)
- **`ops/probe_users_subs.py`** — LV/NL/AMS по нодам
- **`docs/RUNBOOK-P6-SUBSCRIPTION-MULTI-ORIGIN.md`** — несколько **HTTP origin** (другое измерение)
