# Rebuild operator keys on LV/AMS (keeps NL watchdog restricted line on LV).
$ErrorActionPreference = "Stop"
$SshDir = Join-Path $env:USERPROFILE ".ssh"
$Legacy = "IEkfuHotAdRA2WAov0JJwlnOxHbt579Zn27sfBIAoPa9"
$LvPub = (Get-Content (Join-Path $SshDir "bvpn_lv_ed25519.pub") -Raw).Trim() -replace "`r", ""
$AmsPub = (Get-Content (Join-Path $SshDir "bvpn_ams_ed25519.pub") -Raw).Trim() -replace "`r", ""

function Sync-Lv {
    Write-Host "[lv] rebuild authorized_keys (keep watchdog)..."
    $remote = @"
set -e
bak=/root/.ssh/authorized_keys.bak-`$(date +%Y%m%d%H%M)
cp -a /root/.ssh/authorized_keys "`$bak"
grep -v '$Legacy' "`$bak" | grep -v bender-bvpn_lv | grep -v '^[[:space:]]*$' > /root/.ssh/authorized_keys || true
grep 'bvpn-nl-watchdog-to-lv' "`$bak" >> /root/.ssh/authorized_keys || true
echo '$LvPub' >> /root/.ssh/authorized_keys
sed -i 's/\r$//' /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
head -c 900 /root/.ssh/authorized_keys
"@
    & ssh -o BatchMode=yes -o ConnectTimeout=20 bvpn-lv $remote
    if ($LASTEXITCODE -ne 0) { throw "lv sync failed" }
}

function Sync-Ams {
    Write-Host "[ams] rebuild authorized_keys..."
    $remote = @"
set -e
bak=/root/.ssh/authorized_keys.bak-`$(date +%Y%m%d%H%M)
cp -a /root/.ssh/authorized_keys "`$bak"
grep -v '$Legacy' "`$bak" | grep -v bender-bvpn_ams | grep -v '^[[:space:]]*$' > /root/.ssh/authorized_keys || true
grep 'root@vinni' "`$bak" >> /root/.ssh/authorized_keys || true
echo '$AmsPub' >> /root/.ssh/authorized_keys
sed -i 's/\r$//' /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
head -c 600 /root/.ssh/authorized_keys
"@
    & ssh -o BatchMode=yes -o ConnectTimeout=20 bvpn-ams $remote
    if ($LASTEXITCODE -ne 0) { throw "ams sync failed" }
}

Sync-Lv
Sync-Ams
Write-Host "Done sync."
