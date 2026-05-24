# VPN Stability — Phase 1 Diagnostic Resolution (2026-05-25)

**Scope:** Q-VPN-STAB-001 … 004 (диагностика, без prod PATCH).  
**Tools:** `ops/probe_subscription.py`, `ops/diagnose_happ_import.py`, `ops/transport_mux_audit.py`, `ops/subscription_fetch.py`.

---

## Executive summary

| Вопрос | Ответ | Влияние на продукт |
|--------|--------|-------------------|
| Content-Type ломает Happ? | **Нет** — `application/json; charset=utf-8` на live sub | Q-VPN-STAB-006 ↓ приоритет |
| xhttp ломает batch-import? | **Да (HIGH)** — proxy-5/proxy-13 `network=xhttp` | Q-VPN-STAB-005 **блокирует UX «0 серверов»** |
| VPN физически мёртв без fix? | **Нет** — Append custom + leastLoad работают | Fix = доверие/UX, не uptime туннеля |
| NL в подписке? | **Да** — LV=8, NL=8, sample 5/5 users with NL outbounds | Auto-balance LV↔NL возможен в xray |
| Регрессия только из-за xhttp? | **Частично** — batch2=0 с **8 апр**; xhttp в sub **сейчас** подтверждён как risk | Нужен Happ UA filter, не слепое удаление из template |

**Рекомендация Phase 2:** **Q-VPN-STAB-005** — Happ-only filter (panel template trim или sub-page UA), **не** удалять xhttp из infra/template для v2rayN/TSPU.

---

## Q-VPN-STAB-001 · Content-Type

**Live (2026-05-25):**
```
Happ GET HTTP 200, 11562 bytes
Content-Type: application/json; charset=utf-8
```

**Вывод:** заголовок корректный. `UnknownContentType` в Happ **не объясняется** missing/wrong Content-Type на текущем prod.  
**Продукт:** probe теперь ловит регрессию заголовка при будущих деплоях — **preventive**, не hotfix.

---

## Q-VPN-STAB-002 · diagnose_happ_import.py

**Variant A (live):**
- 18 outbounds, 2× `vless/xhttp` (LV + NL)
- `batch_risk=HIGH`
- `proxy-5` (LV xhttp), `proxy-13` (NL xhttp) → `FAIL UnknownContentType(network=xhttp)`
- `burstObservatory`: yes, `leastLoad`: yes

**Variant B (simulated strip xhttp):**
- 16 outbounds, `batch_risk=LOW`, 16/16 parseable
- 14 proxy tcp + direct/dns (non-proxy parseable)

**Продукт:** после Q-VPN-STAB-005 Happ должен видеть **~14–16 named proxy paths** вместо flash «0 servers» + 1 custom profile.

---

## Q-VPN-STAB-003 · A/B xhttp

| | Variant A (live) | Variant B (no xhttp) |
|--|------------------|----------------------|
| Outbounds | 18 | 16 |
| Parseable | 16 | 16 |
| Failed | 2 (xhttp) | 0 |
| batch_risk | **HIGH** | **LOW** |

**Исторический контекст (`subscription_log.txt` владельца):**
- **5–8 апр:** batch2 `count=4…20` при ~6–12 KB ответа
- **8 апр 23:29+:** batch2 `count=0`, fallback custom
- **1 мая+:** стабильно batch1/2 `count=0`, Append custom `count=1–2`
- **24 мая:** 11560 bytes, xhttp×2, batch2=0

**Вывод:** xhttp **объясняет текущий** HIGH risk; полная регрессия апреля могла включать рост JSON/формата. Для prod fix достаточно **Happ-only** strip xhttp.

**Manual verify (optional):** `python ops/diagnose_happ_import.py --write-ab /tmp/sub-no-xhttp.json` → импорт B в Happ на устройстве → ожидать `count > 0`.

---

## Q-VPN-STAB-004 · transport_mux_audit

**Sample=5 (2026-05-25):**
```
has_primary=5/5 has_alt=5/5 both=100%
outbounds: primary=35 alt=35 xhttp=10 has_xhttp=5/5
node totals: LV=25 RELAY=30 NL=25
TRANSPORT_MUX_OK
INFO: xhttp present — Happ batch-import risk
```

**NL=0 warning:** не сработал (все 5 users имеют NL outbounds).  
**Продукт:** MUX primary+alt **здоров**; проблема в Happ parser, не в отсутствии NL/LV в sub.

---

## Что **не** улучшает диагностика сама по себе

- Мониторинг без Phase 2 **не убирает** «0 серверов» у пользователей.
- `leastLoad` уже работает через custom profile — **стабильность VPN** для части пользователей уже есть; pain = UX + panic delete.

---

## Next (Phase 2)

1. **Q-VPN-STAB-005** — Happ UA filter (приоритет #1 для UX)
2. **Q-VPN-STAB-008** — push-notify после deploy filter
3. **Q-VPN-STAB-009** — copy «0 servers ≠ сломан» (параллельно)
4. Q-VPN-STAB-006 — только если Content-Type регрессирует (сейчас OK)

**Verify loop после Phase 2:**
```bash
python ops/probe_subscription.py          # xhttp=0 для Happ UA (после filter)
python ops/diagnose_happ_import.py        # batch_risk=LOW, exit 0
python ops/transport_mux_audit.py
bash ops/smoke_sub_page_ha.sh
```

---

## Phase 2 applied (2026-05-25)

| Metric | Before | After |
|--------|--------|-------|
| Sub size | 11562 B | 10359 B |
| Outbounds | 18 (2 xhttp) | 16 tcp |
| batch_risk | HIGH | **LOW** |
| LV/NL | 8/8 | 7/7 tcp |

**Speed:** no regression — xhttp paths were dead in Happ; tcp 443 + relay intact.  
**Servers:** LV+NL connected; 67 active users, 44% soft cap.  
**Notify:** generation=2 pushed to AMS bot DB (SSH: use `bvpn-ams` / `bvpn_ams_ed25519`, not legacy `id_ed25519`).
