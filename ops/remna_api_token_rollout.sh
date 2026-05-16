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
REMNA_API_TOKEN rollout — см. docs/RUNBOOK-REMNA-API-TOKEN.md

  help          это сообщение
  dry-run       чеклист и команды без SSH (план)
  verify-ams    SSH → ops/check-ams-subscription-token-layout.sh на AMS
  sync-ams-sub  SSH → ops/fix-ams-subscription-api-token.sh на AMS (shop → sub + compose fix)

Полная ротация токена = ручное обновление .env на AMS/LV + sync-ams-sub при необходимости + verify-ams.

EOF
}

print_dry_run() {
	cat <<'EOF'
=== DRY RUN (ничего не выполняется на серверах) ===

Опирайтесь на docs/RUNBOOK-REMNA-API-TOKEN.md и docs/SECRETS.md §3.

1. Панель: выпустить новый API JWT (role=API).
2. Bitwarden/1Password: сохранить как REMNA_API_TOKEN.
3. AMS /opt/remna-shop/.env        → REMNA_API_TOKEN=<new>
4. AMS /opt/remnawave/sub/.env       → то же (или выполните sync-ams-sub после shop)
5. AMS sub/docker-compose.yml      → только ${REMNA_API_TOKEN}; без eyJ... в YAML
6. LV  /etc/bvpn/balancer.env      → PANEL_TOKEN / REMNA_API_TOKEN
7. LV  /etc/bvpn/ru-monitor.env    → REMNA_API_TOKEN
8. docker compose --force-recreate   shop-bot + subscription-page на AMS
9. Smoke: HTTPS subscription 200, ru-monitor без 401, при возможности drift-check.py

Команды с этой машины (если есть bvpn-ams в ssh-config):

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
*)
	echo "unknown mode: ${MODE}; try: help" >&2
	exit 2
	;;
esac
