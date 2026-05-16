$ErrorActionPreference = 'Stop'

$raw = ssh bvpn-lv 'grep ^PANEL_TOKEN= /etc/bvpn/balancer.env'
if ($LASTEXITCODE -ne 0) { throw "ssh failed: $LASTEXITCODE" }

$line = ($raw | Out-String).Trim()
$value = $line.Substring($line.IndexOf('=') + 1).Trim().Trim('"').Trim("'")
$env:PANEL_TOKEN = $value
$env:PANEL_URL   = 'https://k9x2m1.conntest.xyz:2053'

$secretDirRel = Join-Path $PSScriptRoot '..\.secrets'
if (-not (Test-Path -LiteralPath $secretDirRel)) {
    New-Item -ItemType Directory -Path $secretDirRel -Force | Out-Null
}
$secretDir = (Resolve-Path -LiteralPath $secretDirRel).Path
$tokenPath = Join-Path $secretDir 'panel-token.txt'
Set-Content -LiteralPath $tokenPath -Value $value -NoNewline -Encoding ascii

Write-Host ("TOKEN_LEN=" + $env:PANEL_TOKEN.Length)
Write-Host ("URL=" + $env:PANEL_URL)
Write-Host ("TOKEN_FILE=" + $tokenPath)
