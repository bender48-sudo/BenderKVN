# P1-RED-SEC-01: deploy credential broker to LV + smoke.
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Key = Join-Path $env:USERPROFILE ".ssh\bvpn_lv_ed25519"
$Port = 3333
$HostLv = "176.126.162.158"
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", "-o", "StrictHostKeyChecking=accept-new", "-o", "IdentitiesOnly=yes")

$Files = @(
    "ops\remna_credential_broker.py",
    "ops\smoke_short_lived_token_lv.py",
    "ru-monitor.py",
    "balancer.sh"
)
foreach ($f in $Files) {
    python -c "import ast; ast.parse(open(r'$f', encoding='utf-8').read())" 2>$null
    if ($f -eq "balancer.sh") { continue }
    python -m py_compile (Join-Path $RepoRoot $f)
}

$remote = @(
    "remna_credential_broker.py:/opt/scripts/remna_credential_broker.py",
    "smoke_short_lived_token_lv.py:/opt/scripts/smoke_short_lived_token_lv.py",
    "ru-monitor.py:/opt/scripts/ru-monitor.py",
    "balancer.sh:/opt/scripts/balancer.sh"
)
foreach ($pair in $remote) {
    $localName = $pair.Split(":")[0]
    $dest = $pair.Split(":")[1]
    $local = Join-Path $RepoRoot ("ops\" + $localName)
    if ($localName -eq "ru-monitor.py") { $local = Join-Path $RepoRoot "ru-monitor.py" }
    if ($localName -eq "balancer.sh") { $local = Join-Path $RepoRoot "balancer.sh" }
    & scp @($Common + @("-P", "$Port", $local, "root@${HostLv}:/tmp/$localName"))
}

$sshCmd = @'
set -e
install -m 0755 /tmp/remna_credential_broker.py /opt/scripts/remna_credential_broker.py
install -m 0755 /tmp/smoke_short_lived_token_lv.py /opt/scripts/smoke_short_lived_token_lv.py
install -m 0755 /tmp/ru-monitor.py /opt/scripts/ru-monitor.py
install -m 0755 /tmp/balancer.sh /opt/scripts/balancer.sh
sed -i 's/\r$//' /opt/scripts/remna_credential_broker.py /opt/scripts/smoke_short_lived_token_lv.py /opt/scripts/ru-monitor.py /opt/scripts/balancer.sh
mkdir -p /var/lib/bvpn/credentials
chmod 700 /var/lib/bvpn/credentials
if [ ! -f /etc/bvpn/remna-credential-source.env ]; then
  grep -E '^REMNA_API_TOKEN=' /etc/bvpn/ru-monitor.env > /etc/bvpn/remna-credential-source.env || true
  chmod 600 /etc/bvpn/remna-credential-source.env
fi
python3 /opt/scripts/smoke_short_lived_token_lv.py
'@

Write-Host "[deploy] install + smoke..."
& ssh @($Common + @("-p", "$Port", "root@${HostLv}", $sshCmd))
if ($LASTEXITCODE -ne 0) { throw "deploy/smoke failed" }
Write-Host "Done. SHORT_LIVED_TOKEN_OK"
