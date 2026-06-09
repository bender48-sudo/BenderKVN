# INCIDENT-003: read-only Windows network snapshot for VPN sleep/resume diagnostics.
# Usage (from repo root):
#   pwsh -File ops/diagnose_windows_vpn_resume.ps1 -Phase Before
#   pwsh -File ops/diagnose_windows_vpn_resume.ps1 -Phase AfterBroken
#   pwsh -File ops/diagnose_windows_vpn_resume.ps1 -Phase AfterRecovery
#
# Output: .secrets/diagnostics/vpn-resume-<timestamp>-<Phase>.txt (gitignored)
# Does NOT: change routes, DNS, adapters, or VPN state. No admin mutations.

param(
    [ValidateSet("Before", "AfterBroken", "AfterRecovery")]
    [string]$Phase = "Before"
)

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$OutDir = Join-Path $RepoRoot ".secrets\diagnostics"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$OutFile = Join-Path $OutDir "vpn-resume-$ts-$Phase.txt"

function Write-Section($title) {
    "`n======== $title ========`n" | Out-File -FilePath $OutFile -Append -Encoding utf8
}

function Redact-Line([string]$line) {
    $s = $line
    $s = $s -replace 'vless://[^\s]+', 'vless://[REDACTED]'
    $s = $s -replace 'https?://[^\s]*api/sub/[^\s]+', 'https://[REDACTED]/api/sub/[REDACTED]'
    $s = $s -replace 'eyJ[A-Za-z0-9_-]{20,}', '[REDACTED_JWT]'
    $s = $s -replace '(BOT_TOKEN|PORTAL_WEB_TRIAL_SECRET|REMNA_API_TOKEN)=[^\s]+', '$1=[REDACTED]'
    $s
}

function Run-Capture($label, [scriptblock]$block) {
    Write-Section $label
    try {
        $out = & $block 2>&1 | ForEach-Object { Redact-Line "$_" }
        $out | Out-File -FilePath $OutFile -Append -Encoding utf8
    } catch {
        "ERROR: $($_.Exception.Message)" | Out-File -FilePath $OutFile -Append -Encoding utf8
    }
}

Write-Section "META"
@(
    "INCIDENT-003 VPN sleep/resume diagnostic snapshot",
    "Phase: $Phase",
    "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')",
    "Computer: $env:COMPUTERNAME",
    "User: $env:USERNAME",
    "WARNING: Do not commit this file. Contains local network state.",
    "No routes/DNS/VPN were modified by this script."
) | Out-File -FilePath $OutFile -Encoding utf8

Run-Capture "ipconfig /all" { ipconfig /all }
Run-Capture "route print" { route print }
Run-Capture "netsh interface show interface" { netsh interface show interface }

Run-Capture "Get-NetAdapter" {
    Get-NetAdapter | Format-Table Name, InterfaceDescription, Status, LinkSpeed -Auto | Out-String
}

Run-Capture "Get-NetIPConfiguration" {
    Get-NetIPConfiguration | Format-List | Out-String
}

Run-Capture "Get-DnsClientServerAddress (IPv4)" {
    Get-DnsClientServerAddress -AddressFamily IPv4 |
        Format-Table InterfaceAlias, ServerAddresses -Auto | Out-String
}

Run-Capture "Get-NetRoute 0.0.0.0/0" {
    Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue |
        Format-Table DestinationPrefix, NextHop, InterfaceAlias, RouteMetric -Auto | Out-String
}

Run-Capture "Test-NetConnection 1.1.1.1:443" {
    Test-NetConnection 1.1.1.1 -Port 443 -WarningAction SilentlyContinue |
        Format-List | Out-String
}

Run-Capture "nslookup google.com" { nslookup google.com 2>&1 }

Run-Capture "Test-NetConnection www.google.com:443" {
    Test-NetConnection www.google.com -Port 443 -WarningAction SilentlyContinue |
        Format-List | Out-String
}

Write-Host "DIAG_VPN_RESUME_OK phase=$Phase file=$OutFile"
Write-Host "Do not commit .secrets/diagnostics/ output."
