# Фаза 16 — качество продукта (VPN path / sub / Happ)

**Контекст:** после relay-NL :443 inject (фазы 14–15). Приоритет — стабильность пути пользователя, не инфра «на будущее».

**Очередь:** `docs/BACKLOG-QUEUE.md` (Q184+).

---

## Verify gate

```bash
python ops/probe_injecthosts_sub_parity.py --via-lv   # INJECT_SUB_PARITY_OK
python ops/vpn_verify_gate.py                        # или на LV
```

**Inject hosts:** `isDisabled=false`, **`isHidden=true`** (иначе Remnawave не экспортирует UUID из `injectHosts`).

---

## Задачи

| Q | ID | P | Done when | Verify |
|---|-----|---|-----------|--------|
| 184 | **VPN-AUD-281** | P0 | relay-NL :443 в inject с `isHidden=true`; live sub = inject count | **INJECT_SUB_PARITY_OK**, **vless_proxy=16**, gen+notify |
| 185 | **VPN-AUD-282** | P1 | `probe_injecthosts_sub_parity` в `vpn_verify_gate` | gate падает при parity≠16 |
| 186 | **VPN-AUD-283** | P1 | Post-gen54 sample: 5 users sub bytes / proxy count | журнал §12 |
| 187 | **VPN-AUD-310** | P1 | ru-monitor → auto selector trim (cooldown) | runbook + dry-run |

**Владелец:** **O-VPN-002** smoke телефон после 16-path.

---

## NO-GO

1. `isHidden=false` на хостах в `injectHosts.values`.
2. NL в **Intl_Stealth** без A/B.
3. Возврат RELAY→NL :9443 в inject.
