# Remove legacy shared operator key (same pubkey on LV+AMS). Run AFTER new keys work.
# Shared blob from id_ed25519 (comment "vpn") — see docs/SSH-KEY-INVENTORY.md
$ErrorActionPreference = "Stop"
$LegacyMarker = "IEkfuHotAdRA2WAov0JJwlnOxHbt579Zn27sfBIAoPa9"
$Hosts = @("bvpn-lv", "bvpn-ams")

foreach ($h in $Hosts) {
    Write-Host "[clean] $h ..."
    $remote = @"
set -e
cp -a /root/.ssh/authorized_keys /root/.ssh/authorized_keys.bak-`$(date +%Y%m%d%H%M)
grep -v '$LegacyMarker' /root/.ssh/authorized_keys.bak-`$(date +%Y%m%d%H%M) > /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
wc -l /root/.ssh/authorized_keys
"@
    & ssh -o BatchMode=yes -o ConnectTimeout=20 $h $remote
    if ($LASTEXITCODE -ne 0) { throw "clean failed on $h" }
}
Write-Host "Done. Run: python ops/ssh_audit.py"
