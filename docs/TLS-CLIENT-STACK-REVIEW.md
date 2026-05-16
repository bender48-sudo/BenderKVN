# TLS / клиентский стек — квартальный обзор (P2-RED-TLS-01)

**Цель:** раз в квартал сверять **серверный Xray**, **клиентский sing-box** (Happ и др.) и возможности **uTLS / ECH / multiplexing**; внедрять критичные fingerprint-фиксы в шаблон подписки по **`docs/HAPP-MATRIX.md`**.

**Связь:** **`docs/TRANSPORT-MUX-MATRIX.md`** (порты primary/alt), **`ops/transport_mux_audit.py`**.

---

## Расписание

| Период | Срок | Артефакт |
|--------|------|----------|
| **2026 Q2** | **2026-05-16** | **`docs/reviews/TLS-QUARTERLY-2026-Q2.md`** |
| 2026 Q3 | до **2026-08-16** | новый файл `TLS-QUARTERLY-2026-Q3.md` |
| 2026 Q4 | до **2026-11-16** | … |

---

## Чеклист ревью (каждый квартал)

- [ ] **`python ops/tls_client_stack_audit.py`** → `TLS_CLIENT_STACK_AUDIT_OK`
- [ ] **`python ops/transport_mux_audit.py`** → `TRANSPORT_MUX_OK`
- [ ] Версии **Xray** на **LV** и **NL** (`remnanode`) — записать в review-файл
- [ ] [sing-box releases](https://github.com/SagerNet/sing-box/releases) — stable + критичные security/fingerprint notes
- [ ] Happ / поддерживаемые клиенты — есть ли релиз с **ECH** / новым **uTLS** (релиз-ноты, не обещать пользователям до теста)
- [ ] Подписка: протоколы (**vless+reality**), **flow**, **mux** — без неожиданных регрессий
- [ ] Нужен ли PATCH шаблона? → снапшот **`HAPP-MATRIX`** + smoke **`probe_routing.py`**
- [ ] Строка в **`docs/COMMERCIAL-BACKLOG.md` §12`**

---

## Автоматический сбор

```bash
python ops/tls_client_stack_audit.py
python ops/tls_client_stack_audit.py --json > /tmp/tls-audit.json
```

---

## Когда менять шаблон

| Сигнал | Действие |
|--------|----------|
| CVE / fingerprint bypass в Xray или sing-box | Оценить апгрейд образа **remnanode** + клиентский advisory пользователям |
| Новый transport в sing-box stable | PoC на тестовом пользователе, затем injectHosts / template |
| DPI бьёт **:443** | Сначала **alt** профиль (**TRANSPORT-MUX-MATRIX**), не смена TLS стека |

---

## Runbook

**`docs/RUNBOOK-P2-TLS-CLIENT-REVIEW.md`**
