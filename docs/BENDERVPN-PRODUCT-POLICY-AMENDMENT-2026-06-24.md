# BenderVPN Product Policy — Amendment 2026-06-24

**Status:** owner-locked · **Amends:** [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) v1 (2026-06-09)  
**Source:** [`BENDERVPN-SESSION-BACKLOG-2026-06-24.md`](BENDERVPN-SESSION-BACKLOG-2026-06-24.md)

При конфликте с v1 — **эта поправка главнее** до публикации policy v2.

---

## PT overrides

| ID | v1 (устарело) | Amendment (2026-06-24) |
|----|---------------|-------------------------|
| **PT-03** | Soft invite-first; organic `/start` allowed | **Hard invite-only** — без инвайта входа нет; гейт в **боте**, не в мини-апке |
| **PT-06** | One config; new device via support | **Soft multi-device:** 2-е устройство = отдельный конфиг **+6,66 ₽/день** (не блок); шеринг URL → доплата |
| **PT-07** | No referral bonus promised | **User referral live economics approved:** друг +100 ₽; реферер 30% первого пополнения (impl gated `REF-PROGRAM-001`) |
| **PT-08** | 6,67 ₽/день | **6,66 ₽/день** (666 kopeks); 200 ₽ = ровно 30 дней — **DONE** repo |
| **PT-10** | TG + `/id` | + in-app ticket bridge; fallback **help@bendervpn.io** |

## New product truths (not in v1)

| ID | Truth |
|----|-------|
| **PT-13** | iOS: **INCY** primary; V2Ray Client+ / Изи VPN backup; UA edge branching (INCY→JSON, others→vless) |
| **PT-14** | Partner program separate from user referral: 50%+10%, withdrawal from 5000 ₽ — `PARTNER-PROGRAM-001` |
| **PT-15** | Fortune wheel: weighted sectors; ~1 spin / 10 paid days — `GAME-FORTUNE-001` (post-launch) |
| **PT-16** | Paid launch honest-gate: mobile stability + `delivery_path ≥ 2` + hot-spare + INCY auto-update |

## Pilot §3.2 — superseded

| v1 | Amendment |
|----|-----------|
| Organic `/start` allowed | **Removed** — invite-only at bot |
| Hard gate deferred | **Implement** `INVITE-GATE-HARD-001` before commercial scale |

## Copy until implemented

- Не обещать партнёрку/фортуну/мягкий лимит устройств в UI, пока нет backend (`PT-12` сохраняется).
- Реферальные проценты — только после `REF-PROGRAM-001` deploy + smoke.

---

**Next:** merge into `BENDERVPN-PRODUCT-POLICY.md` v2 when owner requests full policy refresh.
