# P3-FLOW-01: deploy web/portal to LV (/start, /portal) + smoke.
# pwsh -File ops/deploy-user-portal-lv.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

python -m py_compile ops/smoke_public_bootstrap.py ops/smoke_telegram_miniapp.py ops/smoke_bot_portal_links.py ops/site_urls.py ops/portal_bundle_audit.py bot_src/portal_links.py

$Key = Join-Path $env:USERPROFILE ".ssh\bvpn_lv_ed25519"
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=40")

Write-Host "[deploy] scp portal ..."
& ssh @($Common + @("root@bvpn-lv", "mkdir -p /var/www/bvpn-portal"))
Push-Location (Join-Path $RepoRoot "web/portal")
try {
    & scp -r @($Common + @(
        "content", "assets", "media", "index.html", "setup.html", "guide.html",
        "root@bvpn-lv:/var/www/bvpn-portal/"
    ))
} finally {
    Pop-Location
}

Write-Host "[deploy] patch Caddy ..."
& scp @($Common + @("ops/patch-caddy-user-portal-lv.sh", "root@bvpn-lv:/tmp/"))
& ssh @($Common + @("root@bvpn-lv", @"
set -e
sed -i 's/\r$//' /tmp/patch-caddy-user-portal-lv.sh
bash /tmp/patch-caddy-user-portal-lv.sh
test -f /var/www/bvpn-portal/index.html
"@))

Write-Host "[deploy] smoke ..."
python ops/portal_bundle_audit.py
python ops/smoke_public_bootstrap.py
python ops/smoke_telegram_miniapp.py
python ops/smoke_bot_portal_links.py
python ops/smoke_portal_setup_video.py
Write-Host "DEPLOY_USER_PORTAL_LV_OK"
