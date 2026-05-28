# VPN drift waive register (VPN-AUD-150)

**Date:** 2026-05-28  
**Drift-check:** `python ops/drift-check.py` → **20/28 OK**, **8 DRIFT** (all waived)  
**With waives:** exit **0** (`ops/drift_waives.json`)

## Policy

- **Never** auto-sync `remna-shop/.env` or `remnawave/.env` from local render during agent sessions (payment/bot WIP in repo ≠ prod).
- **Scripts** (`ru-monitor.py`, `balancer.sh`, …) must stay **OK** — if script DRIFT appears, fix via `deploy-node.sh` / SSH, not waive.
- **Subscription template** is **not** in drift-check (panel API); use `vpn_verify_gate.py` after template patches.

## Waived pairs (8)

| Host | Path | Why waived |
|------|------|------------|
| bvpn-lv | `/opt/adguard/docker-compose.yml` | Optional AdGuard; non-critical |
| bvpn-ams | `/opt/adguard/docker-compose.yml` | Same |
| bvpn-ams | `/opt/remnawave/docker-compose.yml` | Panel stack; deploy only via AMS runbook |
| bvpn-ams | `/opt/remnawave/.env` | Live panel secrets / domain pins |
| bvpn-ams | `/opt/remna-shop/docker-compose.yml` | Shop deploy path |
| bvpn-ams | `/opt/remna-shop/.env` | Live bot payment secrets |
| bvpn-lv | `/etc/bvpn/balancer.env` | MD5: vault render ≠ prod token file; function OK |
| bvpn-lv | `/etc/bvpn/ru-monitor.env` | MD5: token only; `REMNA_API_URL` :8443 on prod |

## When to remove a waive

1. Owner approves a **targeted** `render_compose` + deploy for that path only.
2. Post-deploy: `drift-check` raw **OK** for that row (remove waive entry).
3. `vpn_verify_gate.py` → `VPN_VERIFY_GATE_OK`.

## Related

- `docs/RUNBOOK-AMS-SAFE-DEPLOY.md`
- `docs/SECRETS.md`
- `docs/BACKLOG-VPN-FULL-AUDIT-2026-05-28.md` § VPN-AUD-150
