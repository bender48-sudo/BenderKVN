# Phase 11: sync LV node failover + injectHosts sync scripts and install cron.
$ErrorActionPreference = "Stop"
$Repo = Split-Path $PSScriptRoot -Parent
$Ops = Join-Path $Repo "ops"
$HostAlias = if ($env:BVPN_LV_HOST) { $env:BVPN_LV_HOST } else { "bvpn-lv" }
$Remote = "/opt/scripts"

$files = @(
    "lv_nl_failover_common.py",
    "lv_node_down_nl_failover.py",
    "verify_nl_failover_sub.py",
    "lv_node_failover_auto.py",
    "run_lv_node_failover_auto.sh",
    "install_lv_node_failover_cron.sh",
    "sync_injecthosts_connected.py",
    "run_sync_injecthosts_connected.sh",
    "install_sync_injecthosts_cron.sh",
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
    "smoke_sub_jurisdiction_backup.py"
)

foreach ($f in $files) {
    $src = Join-Path $Ops $f
    if (-not (Test-Path $src)) { throw "missing $src" }
    scp -o BatchMode=yes $src "${HostAlias}:${Remote}/"
}
ssh -o BatchMode=yes $HostAlias @"
chmod 755 ${Remote}/run_lv_node_failover_auto.sh ${Remote}/install_lv_node_failover_cron.sh ${Remote}/run_sync_injecthosts_connected.sh ${Remote}/install_sync_injecthosts_cron.sh 2>/dev/null || true
bash ${Remote}/install_lv_node_failover_cron.sh
bash ${Remote}/install_sync_injecthosts_cron.sh
python3 ${Remote}/lv_node_failover_auto.py
python3 ${Remote}/sync_injecthosts_connected.py
"@
Write-Host "DEPLOY_LV_NODE_RESILIENCE_OK"
