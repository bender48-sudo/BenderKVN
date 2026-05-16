# P2-RED-BOOT-01: status JSON mirror on LV (Caddy + cron + smoke).
# pwsh -File ops/deploy-status-mirror-lv.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

python -m py_compile ops/build_status_mirror.py ops/smoke_status_channels.py ops/site_urls.py

$Key = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=40")

Write-Host "[deploy] scp scripts ..."
& scp @($Common + @(
    "ops/build_status_mirror.py",
    "ops/panel_client.py",
    "ops/load_env_file.py",
    "ops/site_urls.py",
    "ops/patch-caddy-status-mirror-lv.sh",
    "ops/install-status-mirror-lv.sh",
    "root@bvpn-lv:/tmp/"
))

Write-Host "[deploy] patch Caddy + install cron ..."
& ssh @($Common + @("root@bvpn-lv", @"
set -e
sed -i 's/\r$//' /tmp/patch-caddy-status-mirror-lv.sh /tmp/install-status-mirror-lv.sh
install -m 0755 /tmp/build_status_mirror.py /tmp/panel_client.py /tmp/load_env_file.py /tmp/site_urls.py /opt/scripts/
bash /tmp/patch-caddy-status-mirror-lv.sh
bash /tmp/install-status-mirror-lv.sh /opt/scripts/build_status_mirror.py
"@))

Write-Host "[deploy] smoke from workstation ..."
python ops/smoke_status_channels.py
Write-Host "DEPLOY_STATUS_MIRROR_LV_OK"
