# P1-RED-DNS-01: deploy dns_delegation_probe to LV + smoke.
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Files = @(
    @{ Local = "ops\dns_delegation_probe.py"; Remote = "/opt/scripts/dns_delegation_probe.py" },
    @{ Local = "ops\dns_critical_inventory.json"; Remote = "/opt/scripts/dns_critical_inventory.json" }
)

$Key = Join-Path $env:USERPROFILE ".ssh\bvpn_lv_ed25519"
$HostLv = "176.126.162.158"
$Port = 3333
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=25", "-o", "StrictHostKeyChecking=accept-new", "-o", "IdentitiesOnly=yes")

foreach ($f in $Files) {
    python -c "import ast; ast.parse(open(r'$($f.Local)', encoding='utf-8').read())"
    & scp @($Common + @("-P", "$Port", (Join-Path $RepoRoot $f.Local), "root@${HostLv}:$($f.Remote)"))
}

Write-Host "[deploy] smoke on LV..."
& ssh @($Common + @("-p", "$Port", "root@${HostLv}", "sed -i 's/\r$//' /opt/scripts/dns_delegation_probe.py /opt/scripts/dns_critical_inventory.json; python3 /opt/scripts/dns_delegation_probe.py"))
if ($LASTEXITCODE -ne 0) { throw "DNS delegation smoke failed" }
Write-Host "Done. DNS_DELEGATION_OK"
