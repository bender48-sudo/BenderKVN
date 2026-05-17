# P5-COM-01: public HTML /status on LV + rebuild + smoke.
# pwsh -File ops/deploy-public-status-page-lv.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

python -m py_compile ops/build_status_mirror.py ops/public_status_page.py ops/smoke_public_status_page.py ops/site_urls.py

$Key = Join-Path $env:USERPROFILE ".ssh\bvpn_lv_ed25519"
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=40")

Write-Host "[deploy] scp scripts ..."
& scp @($Common + @(
    "ops/build_status_mirror.py",
    "ops/public_status_page.py",
    "ops/panel_client.py",
    "ops/load_env_file.py",
    "ops/site_urls.py",
    "ops/patch-caddy-public-status-lv.sh",
    "ops/incidents.public.example.json",
    "root@bvpn-lv:/tmp/"
))

Write-Host "[deploy] patch Caddy + build status HTML ..."
& ssh @($Common + @("root@bvpn-lv", @"
set -e
sed -i 's/\r$//' /tmp/patch-caddy-public-status-lv.sh
install -m 0755 /tmp/build_status_mirror.py /tmp/public_status_page.py /tmp/panel_client.py /tmp/load_env_file.py /tmp/site_urls.py /opt/scripts/
install -m 0644 /tmp/incidents.public.example.json /opt/scripts/
bash /tmp/patch-caddy-public-status-lv.sh
. /etc/bvpn/balancer.env 2>/dev/null || true
PYTHONPATH=/opt/scripts /usr/bin/python3 /opt/scripts/build_status_mirror.py -o /var/www/bvpn-status/status.json
test -f /var/www/bvpn-status/index.html
"@))

Write-Host "[deploy] smoke from workstation ..."
python ops/smoke_public_status_page.py
python ops/smoke_status_channels.py
Write-Host "DEPLOY_PUBLIC_STATUS_PAGE_LV_OK"
