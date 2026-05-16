#!/usr/bin/env bash
# Helpers for REMNA_API_TOKEN rollout (AMS sub-page 502 regression guard).
#
# Usage (from repo root or any cwd):
#   bash ops/remna_api_token_rollout.sh help
#   bash ops/remna_api_token_rollout.sh dry-run
#   bash ops/remna_api_token_rollout.sh verify-ams
#   bash ops/remna_api_token_rollout.sh sync-ams-sub
#
# Requires: SSH host "bvpn-ams" in ~/.ssh/config (BatchMode=yes).
set -euo pipefail

OPS_DIR=$(cd "$(dirname "$0")" && pwd)

print_help() {
	cat <<'EOF'
REMNA machine JWT (переменная в файлах: REMNA_API_TOKEN=) — см. docs/RUNBOOK-REMNA-API-TOKEN.md

На проде возможны ДВА разных JWT: AMS (shop + sub) и LV (balancer + ru-monitor).
В drift/vault шаблонах: REMNA_API_TOKEN_AMS / REMNA_API_TOKEN_LV (docs/SECRETS.md §1).

  help          это сообщение
  dry-run       чеклист и команды без SSH (план)
  verify-ams    SSH → ops/check-ams-subscription-token-layout.sh на AMS
  sync-ams-sub  SSH → ops/fix-ams-subscription-api-token.sh на AMS (shop → sub + compose fix)
  sync-lv-from-ams  pwsh ops/sync-lv-remna-token-from-ams.ps1 (AMS shop JWT → LV balancer + ru-monitor)

Полный апдейт: см. runbook (только AMS / только LV / оба). verify-ams/sync — helpers для AMS sub.

EOF
}

print_dry_run() {
	cat <<'EOF'
=== DRY RUN (ничего не выполняется на серверах) ===

См. docs/RUNBOOK-REMNA-API-TOKEN.md и docs/SECRETS.md §1 (два значения на проде возможны).

Если меняете только AMS (бот + subscription-page к панели):
  1. Панель → новый API JWT (role=API).
  2. Секрет-хранилище: пометьте как AMS machine token.
  3. AMS /opt/remna-shop/.env     → REMNA_API_TOKEN=<new>
  4. AMS /opt/remnawave/sub/.env  → то же (или sync-ams-sub после правки shop)
  5. AMS sub/docker-compose.yml   → только REMNAWAVE_API_TOKEN=${REMNA_API_TOKEN}; без eyJ… в YAML
  6. docker compose --force-recreate remna-shop-bot + subscription-page на AMS
  LV не трогаем.

Если меняете только LV (balancer / ru-monitor):
  1. Панель → отдельный API JWT (или тот же сознательно).
  2. LV /etc/bvpn/balancer.env     → PANEL_TOKEN и REMNA_API_TOKEN = новое
  3. LV /etc/bvpn/ru-monitor.env   → REMNA_API_TOKEN = новое

Если выравниваете один JWT везде — выполните ОБА блока с ОДНИМ значением.

Общие проверки:
  · Smoke: HTTPS subscription 200, ru-monitor без 401
  · При наличии SSH: python ops/drift-check.py
  · Обновить локальный vault: python ops/extract_vault.py (после SCP prod-compose)

Команды с этой машины (bvpn-ams в ssh-config):

  bash ops/remna_api_token_rollout.sh verify-ams
  bash ops/remna_api_token_rollout.sh sync-ams-sub

EOF
}

ssh_ams_run_stdin() {
	local script_path=$1
	ssh -o BatchMode=yes bvpn-ams "bash -s" <"${script_path}"
}

MODE=${1:-help}
case "${MODE}" in
help|-h|--help) print_help ;;
dry-run | dry_run) print_dry_run ;;
verify-ams | verify)
	echo "SSH bvpn-ams -> check-ams-subscription-token-layout.sh"
	ssh_ams_run_stdin "${OPS_DIR}/check-ams-subscription-token-layout.sh"
	echo "verify-ams: OK"
	;;
sync-ams-sub | sync)
	echo "SSH bvpn-ams -> fix-ams-subscription-api-token.sh"
	bash "${OPS_DIR}/sync-sub-token-ams.sh"
	echo "sync-ams-sub: done"
	;;
sync-lv-from-ams)
	exec pwsh -NoProfile -File "${OPS_DIR}/sync-lv-remna-token-from-ams.ps1"
	;;
*)
	echo "unknown mode: ${MODE}; try: help" >&2
	exit 2
	;;
esac
