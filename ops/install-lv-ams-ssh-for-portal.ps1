# Install operator AMS key on LV so setup_verify can call portal-web-trial on AMS.
# pwsh -File ops/install-lv-ams-ssh-for-portal.ps1
$ErrorActionPreference = "Stop"
$KeyLocal = Join-Path $env:USERPROFILE ".ssh\bvpn_ams_ed25519"
$KeyLv = Join-Path $env:USERPROFILE ".ssh\bvpn_lv_ed25519"
if (-not (Test-Path $KeyLocal)) { throw "Missing $KeyLocal" }
if (-not (Test-Path $KeyLv)) { throw "Missing $KeyLv" }

Write-Host "[install-lv-ams-ssh] copy AMS ops key to LV..."
& scp -i $KeyLv -o BatchMode=yes $KeyLocal root@bvpn-lv:/root/.ssh/bvpn_ams_ed25519
if ($LASTEXITCODE -ne 0) { throw "scp key failed" }

$remote = @'
set -e
chmod 600 /root/.ssh/bvpn_ams_ed25519
ssh -i /root/.ssh/bvpn_ams_ed25519 -p 3344 -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new root@168.100.11.140 "echo LV_AMS_SSH_OK"
'@
& ssh -i $KeyLv -o BatchMode=yes root@bvpn-lv $remote
if ($LASTEXITCODE -ne 0) { throw "LV->AMS ssh test failed" }
Write-Host "INSTALL_LV_AMS_SSH_FOR_PORTAL_OK"
