# Phase 11: deploy node resilience scripts to AMS (when LV SSH unavailable).
# Cron + panel API from AMS using shop REMNA_API_TOKEN.
$ErrorActionPreference = "Stop"
$Repo = Split-Path $PSScriptRoot -Parent
$Ops = Join-Path $Repo "ops"
$HostAlias = if ($env:BVPN_AMS_HOST) { $env:BVPN_AMS_HOST } else { "bvpn-ams" }
$Remote = "/opt/scripts"
$ScpOpts = @("-o", "BatchMode=yes", "-o", "ConnectTimeout=20")

$files = @(
    "lv_nl_failover_common.py",
    "lv_node_down_nl_failover.py",
    "verify_nl_failover_sub.py",
    "lv_node_failover_auto.py",
    "run_lv_node_failover_auto_ams.sh",
    "install_ams_node_failover_cron.sh",
    "sync_injecthosts_connected.py",
    "run_sync_injecthosts_connected_ams.sh",
    "install_ams_sync_injecthosts_cron.sh",
    "site_urls.py",
    "subscription_fetch.py",
    "balancer_selectors.py",
    "trim_injecthosts_no_xhttp.py",
    "subscription_config_notify.py",
    "panel_client.py",
    "load_env_file.py",
    "verify_vpn_balancer_profile.py",
    "probe_subscription.py",
    "diagnose_happ_import.py",
    "transport_mux_audit.py",
    "subscription_origin_drift_probe.py",
    "smoke_sub_jurisdiction_backup.py",
    "patch-caddy-sub-backup-nl.sh"
)

foreach ($f in $files) {
    $src = Join-Path $Ops $f
    if (-not (Test-Path $src)) { throw "missing $src" }
    & scp @ScpOpts $src "${HostAlias}:${Remote}/"
    Write-Host "scp OK: $f"
}

ssh -o BatchMode=yes -o ConnectTimeout=30 $HostAlias @"
chmod 755 ${Remote}/run_lv_node_failover_auto_ams.sh ${Remote}/install_ams_node_failover_cron.sh ${Remote}/run_sync_injecthosts_connected_ams.sh ${Remote}/install_ams_sync_injecthosts_cron.sh ${Remote}/patch-caddy-sub-backup-nl.sh 2>/dev/null || true
bash ${Remote}/install_ams_node_failover_cron.sh
bash ${Remote}/install_ams_sync_injecthosts_cron.sh
set -a; source /opt/remna-shop/.env; set +a
export PANEL_URL=`${REMNA_BASE_URL:-http://127.0.0.1:3000}
export PANEL_TOKEN=`${REMNA_API_TOKEN}
python3 ${Remote}/lv_node_failover_auto.py
python3 ${Remote}/sync_injecthosts_connected.py
python3 ${Remote}/lv_node_down_nl_failover.py --status
"@
Write-Host "DEPLOY_AMS_NODE_RESILIENCE_OK"
