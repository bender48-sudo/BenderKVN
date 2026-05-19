# CodeRabbit — промпт для аудита раунд 2 (2026-05)

**Когда:** после **Q086–097** (фаза 6) и деплоя LV/AMS.  
**Контекст:** закрыты Q063–078, Q085 TSPU, post-deploy review; нужен **свежий** проход по коду и ops.

---

## Промпт (скопировать в CodeRabbit)

```
Repo: BenderVPN commercial VPN (~60 users, target 200 GTM).

Context (already fixed — do NOT re-report as open unless regression):
- Q063–078: payments webhooks, support authz, scheduler TZ, log_skip, panel bind, setup RL, etc.
- Q086–097 phase 6: admin FSM authz, removed crypto debug print, closed public :2054 in Caddy template, cabinet no bind_url leak, canonical :8443 in bot/FAQ, 2053→8443 redirect on LV, p4n7q backup portal on :8443, HSTS/CSP on edge, Mini App/cabinet flow.
- Prior audits: docs/AUDIT-2026-05-SECURITY.md, docs/POST-DEPLOY-REVIEW-2026-05.md, docs/AUDIT-2026-05-TSPU-REDTEAM.md.

Scope: FULL repository review with focus on:
1) Security regressions in bot_src/ (handlers, admin_handlers, webhook_server, portal_cabinet, support_handler, scheduler).
2) Secrets in logs/prints/env templates; .env committed paths.
3) AuthZ: admin FSM, support group, cabinet/setup APIs, web trial bind flow.
4) Payment integrity: webhook idempotency, amount verify, CryptoBot POST-only.
5) Ops: Caddyfile-latvia-full.txt public surface (:8443 only?), compose templates, deploy scripts.
6) Do NOT flag :2053 in user-facing bot/FAQ if already :8443 — grep first.

Deliverables:
- Severity table P0/P1/P2/P3 with file:line
- Separate "false positive / already fixed" section referencing Q IDs above
- Maturity score 1–10 for Security, Ops, Product, TSPU/edge
- Max 15 actionable NEW items for backlog (Q102+), each with suggested verify command/smoke
- GTM readiness: ready / conditional / not ready (one paragraph)

Constraints: no vault secrets; suggest fixes not drive-by refactors.
```

---

## После ответа CodeRabbit

1. Сохранить сырой вывод → `docs/AUDIT-2026-05-SECURITY-02.md` (или дополнить §12).  
2. Валидация агентом: сверка с кодом, отсечь дубли Q063–097.  
3. Новые Q → **`BACKLOG-QUEUE.md`** фаза 7.

**Verify агента:** `python ops/smoke_product_backlog_static.py` + целевые smokes из таблицы.
