# TLS quarterly review — 2026 Q2 (P2-RED-TLS-01)

**Дата:** 2026-05-16  
**Исполнитель:** ops (automated audit + repo)

## Снимок (`tls_client_stack_audit.py`)

| Компонент | Значение |
|-----------|----------|
| **Xray bvpn-lv** | **26.3.27** (d2758a0, go1.26.1) |
| **Xray bvpn-nl** | **26.3.27** |
| **sing-box upstream (GitHub latest)** | **v1.13.12** (2026-05-15) |
| **Sub transport profiles** | **primary**, **alt** |
| **Sub stack (sample)** | protocols: **vless**; security: **reality**; flow: **xtls-rprx-vision** |
| **transport_mux_audit** | **TRANSPORT_MUX_OK** (sample 19, both profiles 100%, alt_ob_share≈56%) |

## uTLS / ECH / multiplexing

| Тема | Статус Q2 2026 | Решение |
|------|----------------|---------|
| **uTLS (клиент)** | Отслеживать через Happ / sing-box | Без смены шаблона; клиенты обновляются из store |
| **ECH** | Не в прод-шаблоне | Мониторить sing-box **1.14** stable; PoC — Q3 при необходимости |
| **multiplexing** | **TRANSPORT-MUX** на уровне портов/нод | Достаточно для текущей базы (~60 users) |

## Действия

- [x] Чеклист **`TLS-CLIENT-STACK-REVIEW.md`** пройден
- [ ] Апгрейд Xray — **не требуется** (LV=NL, актуальная 26.3.x)
- [ ] PATCH subscription template — **не требуется**
- [ ] Сообщение пользователям — **нет**

## Следующий обзор

**2026-08-16** (Q3) — повторить audit + новый файл `TLS-QUARTERLY-2026-Q3.md`.
