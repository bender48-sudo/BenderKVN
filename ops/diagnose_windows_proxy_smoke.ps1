# CLIENT-SMOKE-002: read-only Windows snapshot for Happ Proxy mode diagnostics.
# Usage (from repo root):
#   pwsh -File ops/diagnose_windows_proxy_smoke.ps1 -Phase BenderProxyFail -ProfileLabel BenderVPN-Auto
#   pwsh -File ops/diagnose_windows_proxy_smoke.ps1 -Phase ControlProxyPass -ProfileLabel ControlVPN
#
# Output: .secrets/diagnostics/proxy-smoke-<timestamp>-<Phase>.txt (gitignored)
# Does NOT: change routes, DNS, adapters, proxy, or VPN state.

param(
    [ValidateSet("Before", "BenderProxyFail", "ControlProxyPass", "AfterRecovery")]
    [string]$Phase = "BenderProxyFail",
    [string]$ProfileLabel = "unknown"
)

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$OutDir = Join-Path $RepoRoot ".secrets\diagnostics"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$OutFile = Join-Path $OutDir "proxy-smoke-$ts-$Phase.txt"

function Write-Section($title) {
    "`n======== $title ========`n" | Out-File -FilePath $OutFile -Append -Encoding utf8
}

function Redact-Line([string]$line) {
    $s = $line
    $s = $s -replace 'vless://[^\s]+', 'vless://[REDACTED]'
    $s = $s -replace 'https?://[^\s]*api/sub/[^\s]+', 'https://[REDACTED]/api/sub/[REDACTED]'
    $s = $s -replace 'happ://[^\s]+', 'happ://[REDACTED]'
    $s = $s -replace 'eyJ[A-Za-z0-9_-]{20,}', '[REDACTED_JWT]'
    $s = $s -replace '\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', '[REDACTED_UUID]'
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
    "CLIENT-SMOKE-002 Proxy mode diagnostic snapshot",
    "Phase: $Phase",
    "ProfileLabel: $ProfileLabel",
    "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')",
    "Computer: $env:COMPUTERNAME",
    "User: $env:USERNAME",
    "WARNING: Do not commit this file. Contains local network state.",
    "No routes/DNS/proxy/VPN were modified by this script.",
    "Ensure Happ TUN is OFF for Proxy-mode tests."
) | Out-File -FilePath $OutFile -Encoding utf8

Run-Capture "Windows proxy settings (registry UserSettings)" {
    $path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    Get-ItemProperty -Path $path |
        Select-Object ProxyEnable, ProxyServer, AutoConfigURL, ProxyOverride |
        Format-List | Out-String
}

Run-Capture "netsh winhttp show proxy" { netsh winhttp show proxy }

Run-Capture "ipconfig /all" { ipconfig /all }

Run-Capture "Get-DnsClientServerAddress (IPv4)" {
    Get-DnsClientServerAddress -AddressFamily IPv4 |
        Format-Table InterfaceAlias, ServerAddresses -Auto | Out-String
}

Run-Capture "nslookup google.com" { nslookup google.com 2>&1 }

Run-Capture "nslookup mail.google.com" { nslookup mail.google.com 2>&1 }

Run-Capture "curl -I https://www.google.com (max 15s)" {
    curl.exe -I -m 15 -sS https://www.google.com 2>&1
}

Run-Capture "curl -I https://mail.google.com (max 15s)" {
    curl.exe -I -m 15 -sS https://mail.google.com 2>&1
}

Run-Capture "Test-NetConnection www.google.com:443" {
    Test-NetConnection www.google.com -Port 443 -WarningAction SilentlyContinue |
        Format-List | Out-String
}

Write-Host "CLIENT_SMOKE_002_PROXY_CAPTURE_OK phase=$Phase file=$OutFile"
Write-Host "Do not commit .secrets/diagnostics/ output."
