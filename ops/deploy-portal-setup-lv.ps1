# P3-FLOW-02: setup page + verify API on LV.
# pwsh -File ops/deploy-portal-setup-lv.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

python -m py_compile ops/portal_setup_token.py ops/setup_verify_service.py ops/smoke_portal_setup_page.py ops/site_urls.py

$Key = Join-Path $env:USERPROFILE ".ssh\bvpn_lv_ed25519"
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=40")

Write-Host "[deploy] portal files ..."
Push-Location (Join-Path $RepoRoot "web/portal")
try {
    & scp -r @($Common + @(
        "content", "assets", "index.html", "setup.html",
        "root@bvpn-lv:/var/www/bvpn-portal/"
    ))
} finally {
    Pop-Location
}

Write-Host "[deploy] scripts + systemd ..."
& scp @($Common + @(
    "ops/portal_setup_token.py",
    "ops/setup_verify_service.py",
    "ops/site_urls.py",
    "ops/load_env_file.py",
    "ops/install-setup-verify-lv.sh",
    "ops/patch-caddy-setup-api-lv.sh",
    "ops/patch-caddy-setup-pages-lv.sh",
    "root@bvpn-lv:/tmp/"
))

& ssh @($Common + @("root@bvpn-lv", @"
set -e
sed -i 's/\r$//' /tmp/install-setup-verify-lv.sh /tmp/patch-caddy-setup-api-lv.sh /tmp/patch-caddy-setup-pages-lv.sh
bash /tmp/install-setup-verify-lv.sh
bash /tmp/patch-caddy-setup-pages-lv.sh
bash /tmp/patch-caddy-setup-api-lv.sh
"@))

Write-Host "[deploy] smoke ..."
python ops/portal_bundle_audit.py
python ops/smoke_portal_setup_page.py
Write-Host "DEPLOY_PORTAL_SETUP_LV_OK"
