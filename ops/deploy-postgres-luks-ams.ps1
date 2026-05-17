# P1-RED-DATA-01: deploy LUKS scripts + optional one-time enable on AMS.
param(
    [switch]$Enable,
    [switch]$ProbeOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Key = Join-Path $env:USERPROFILE ".ssh\bvpn_ams_ed25519"
$HostAms = "168.100.11.140"
$Port = 3344
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=40", "-o", "StrictHostKeyChecking=accept-new", "-o", "IdentitiesOnly=yes")

$Scripts = @(
    "ams_postgres_crypt_probe.py",
    "ams_postgres_luks_enable.sh",
    "ams_postgres_luks_unlock.sh"
)
foreach ($s in $Scripts) {
    & scp @($Common + @("-P", "$Port", (Join-Path $RepoRoot "ops\$s"), "root@${HostAms}:/opt/scripts/$s"))
    & ssh @($Common + @("-p", "$Port", "root@${HostAms}", "sed -i 's/\r$//' /opt/scripts/$s; chmod 755 /opt/scripts/$s"))
}

if ($ProbeOnly) {
    & ssh @($Common + @("-p", "$Port", "root@${HostAms}", "python3 /opt/scripts/ams_postgres_crypt_probe.py"))
    exit $LASTEXITCODE
}

if ($Enable) {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $luksPass = [Convert]::ToBase64String($bytes)
    Write-Host "[enable] stopping panel + migrating to LUKS (maintenance)..."
    $remote = "export CONFIRM=yes; read -r LUKS_PASS; export LUKS_PASS; bash /opt/scripts/ams_postgres_luks_enable.sh"
    $luksPass | & ssh @($Common + @("-p", "$Port", "root@${HostAms}", $remote))
    if ($LASTEXITCODE -ne 0) { throw "LUKS enable failed" }
    Write-Host ""
    Write-Host "=== SAVE TO BITWARDEN (BenderVPN/ams/postgres-luks-key) ===" -ForegroundColor Yellow
    Write-Host $luksPass
    Write-Host "=== Do not commit this passphrase. Delete shell history if needed. ===" -ForegroundColor Yellow
    $luksPass = $null
}

Write-Host "[probe] POSTGRES_CRYPT..."
& ssh @($Common + @("-p", "$Port", "root@${HostAms}", "python3 /opt/scripts/ams_postgres_crypt_probe.py"))
if ($LASTEXITCODE -ne 0) { throw "probe failed" }
Write-Host "Done."
