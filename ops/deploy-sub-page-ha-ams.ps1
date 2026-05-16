# P6-RED-SUBHA-01: second subscription-page on AMS :3011 + DOCKER-USER for 3010/3011.
# From repo root:  pwsh -File ops/deploy-sub-page-ha-ams.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$ComposeTmpl = Join-Path $RepoRoot "compose\ams\remnawave-sub\docker-compose.yml.tmpl"
$Firewall = Join-Path $RepoRoot "ops\bvpn-docker-firewall.sh"
foreach ($f in @($ComposeTmpl, $Firewall)) {
    if (-not (Test-Path $f)) { throw "Missing: $f" }
}

$HostAms = "168.100.11.140"
$Port = 3344
$Key = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=40", "-o", "StrictHostKeyChecking=accept-new")

Write-Host "[deploy-sub-page-ha-ams] scp compose + firewall..."
& scp @($Common + @("-P", "$Port", $ComposeTmpl, "root@${HostAms}:/tmp/remnawave-sub-docker-compose.yml.tmpl"))
& scp @($Common + @("-P", "$Port", $Firewall, "root@${HostAms}:/tmp/bvpn-docker-firewall.sh"))

$sshCmd = @'
set -e
SUB=/opt/remnawave/sub
ts=$(date +%Y%m%d-%H%M%S)
test -f "$SUB/docker-compose.yml" && cp -a "$SUB/docker-compose.yml" "$SUB/docker-compose.yml.before-subha-$ts"
sed 's/\r$//' /tmp/remnawave-sub-docker-compose.yml.tmpl > "$SUB/docker-compose.yml"
cd "$SUB"
docker compose up -d
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'subscription-page' || true
sed 's/\r$//' /tmp/bvpn-docker-firewall.sh > /usr/local/sbin/bvpn-docker-firewall.sh
chmod +x /usr/local/sbin/bvpn-docker-firewall.sh
SUB_PORTS="3010 3011" /usr/local/sbin/bvpn-docker-firewall.sh
curl -fsS -m 5 -o /dev/null -w "local3010=%{http_code}\n" http://127.0.0.1:3010/api/sub/ || true
curl -fsS -m 5 -o /dev/null -w "local3011=%{http_code}\n" http://127.0.0.1:3011/api/sub/ || true
echo "AMS sub-page HA deploy done"
'@

Write-Host "[deploy-sub-page-ha-ams] ssh..."
& ssh @($Common + @("-p", "$Port", "root@${HostAms}", $sshCmd))
if ($LASTEXITCODE -ne 0) { throw "AMS deploy failed" }
Write-Host "Next: on bvpn-lv run ops/patch-caddy-sub-split-host-lv.sh"
