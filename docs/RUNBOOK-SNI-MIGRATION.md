# Runbook: миграция Reality SNI (P2-DOC-SNI-MIGRATION-01)

**Связь:** **Q105** live SNI `yandex.ru`; **Q138**; откат — `ops/patch_restore_14_relay_no_obs.py`.

## Когда менять

- ТСПУ начал резать текущий `REMNA_SERVER_SNI` / dest в подписке.
- Red-team отчёт помечает SNI как P1 (см. `docs/AUDIT-2026-05-TSPU-REDTEAM.md`).

## Чеклист (без смены routing + injectHosts в одном PATCH)

1. Снимок template: `python ops/panel_client.py` или snapshot в `.secrets/snapshots/`.
2. Обновить **panel inbound** Reality `serverNames` + `REMNA_SERVER_SNI` в `/opt/remna-shop/.env` и compose tmpl.
3. **Не** трогать `injectHosts` / balancer в том же коммите наката.
4. Dry-run → apply один patch; `python ops/smoke_live_sub_sni.py`.
5. `python ops/probe_subscription.py` — **200**, 14 proxy, RELAY в sub.
6. Запись в `docs/COMMERCIAL-BACKLOG.md` §12.

## Verify

**`LIVE_SUB_SNI_OK`** + пользовательский smoke Happ (IG/TG открываются).
