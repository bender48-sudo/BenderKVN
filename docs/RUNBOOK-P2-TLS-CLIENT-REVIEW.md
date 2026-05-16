# Runbook: квартальный TLS / client stack review (P2-RED-TLS-01)

## Когда

Каждые **~90 дней** (см. **`docs/TLS-CLIENT-STACK-REVIEW.md`** — таблица периодов).

## Шаги (≈30 мин)

1. Из корня репо:
   ```bash
   python ops/tls_client_stack_audit.py
   python ops/transport_mux_audit.py
   ```
2. Скопировать вывод в **`docs/reviews/TLS-QUARTERLY-YYYY-QN.md`** (новый файл).
3. Открыть [sing-box releases](https://github.com/SagerNet/sing-box/releases) — 5 минут на security / fingerprint.
4. Если нужен апгрейд **remnanode** — только через **`RUNBOOK-AMS-SAFE-DEPLOY`** / node compose на LV/NL.
5. Если нужен PATCH шаблона — **`docs/HAPP-MATRIX.md`** (снапшот + `probe_routing.py`).
6. Строка в **`COMMERCIAL-BACKLOG.md` §12`**.

## Verify

- `TLS_CLIENT_STACK_AUDIT_OK`
- `TRANSPORT_MUX_OK` (если меняли sub/ноды)
- Review-файл в git

## Эскалация

Массовый DPI на одном fingerprint → сначала **alt transport** (**TRANSPORT-MUX-MATRIX**), не эксперимент с ECH на всей базе.
