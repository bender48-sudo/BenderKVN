# Deploy AMS private ops scripts to LV (168.100.11.52:22 via bvpn_ams_ed25519).
# Fixes backup pull + recovery watch without BitLaunch public .140.
# From repo root:  pwsh -File ops/deploy_ams_ops_private_to_lv.ps1
# Optional: -RunWatch  runs one recovery cycle after install.

param(
    [switch]$RunWatch,
    [switch]$SkipAmsBackupBootstrap
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$LvHost = "176.126.162.158"
$LvPort = "3333"
$LvKey = Join-Path $env:USERPROFILE ".ssh\bvpn_lv_ed25519"
if (-not (Test-Path $LvKey)) { throw "Missing LV key: $LvKey" }

$Bundle = @(
    "ams_ops_env.sh",
    "pull-latest-dump-ams-to-lv.sh",
    "watch_ams_public_ssh_recovery.sh",
    "push_sub_config_generation_ams.py",
    "install_ams_public_ssh_watch_cron.sh",
    "pg_dump_remnawave.sh",
    "install-remnawave-backup-cron.sh"
)
foreach ($f in $Bundle) {
    $p = Join-Path $RepoRoot "ops\$f"
    if (-not (Test-Path $p)) { throw "Missing: $p" }
}

bash -n (Join-Path $RepoRoot "ops\ams_ops_env.sh")
bash -n (Join-Path $RepoRoot "ops\pull-latest-dump-ams-to-lv.sh")
bash -n (Join-Path $RepoRoot "ops\watch_ams_public_ssh_recovery.sh")
bash -n (Join-Path $RepoRoot "ops\install_ams_public_ssh_watch_cron.sh")
bash -n (Join-Path $RepoRoot "ops\install-remnawave-backup-cron.sh")
bash -n (Join-Path $RepoRoot "ops\pg_dump_remnawave.sh")

$AmsHost = "168.100.11.52"
$AmsPort = "22"
$AmsKey = Join-Path $env:USERPROFILE ".ssh\bvpn_ams_ed25519"
if (-not (Test-Path $AmsKey)) {
    $AmsKey = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
}
$CommonAms = @(
    "-i", $AmsKey,
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=45",
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "IdentitiesOnly=yes"
)

$CommonLv = @(
    "-i", $LvKey,
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=45",
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "IdentitiesOnly=yes"
)

Write-Host "[deploy-ams-ops-lv] upload bundle to /tmp/bvpn-ams-ops..."
& ssh @($CommonLv + @("-p", $LvPort, "root@${LvHost}", "rm -rf /tmp/bvpn-ams-ops && mkdir -p /tmp/bvpn-ams-ops"))
foreach ($f in $Bundle) {
    & scp @($CommonLv + @("-P", $LvPort, (Join-Path $RepoRoot "ops\$f"), "root@${LvHost}:/tmp/bvpn-ams-ops/$f"))
}

Write-Host "[deploy-ams-ops-lv] install to /opt/scripts + cron..."
$RemoteInstall = @'
set -euo pipefail
for f in /tmp/bvpn-ams-ops/*; do sed -i 's/\r$//' "$f"; done
cp -a /tmp/bvpn-ams-ops/ams_ops_env.sh /tmp/bvpn-ams-ops/pull-latest-dump-ams-to-lv.sh \
  /tmp/bvpn-ams-ops/watch_ams_public_ssh_recovery.sh /tmp/bvpn-ams-ops/push_sub_config_generation_ams.py \
  /opt/scripts/
chmod 644 /opt/scripts/ams_ops_env.sh /opt/scripts/push_sub_config_generation_ams.py
chmod 755 /opt/scripts/pull-latest-dump-ams-to-lv.sh /opt/scripts/watch_ams_public_ssh_recovery.sh
bash /tmp/bvpn-ams-ops/install_ams_public_ssh_watch_cron.sh
CFG=/root/.ssh/config
MARK="Host bvpn-ams"
if ! grep -qF "$MARK" "$CFG" 2>/dev/null; then
  cat >>"$CFG" <<'EOF'

# AMS panel (BitLaunch private VPC) — added by deploy_ams_ops_private_to_lv.ps1
Host bvpn-ams
    HostName 168.100.11.52
    Port 22
    User root
    IdentityFile ~/.ssh/bvpn_ams_ed25519
    IdentitiesOnly yes
EOF
  chmod 600 "$CFG"
  echo "added bvpn-ams to ssh config"
else
  echo "bvpn-ams ssh config already present"
fi
echo "--- probe LV->AMS ---"
ssh -i /root/.ssh/bvpn_ams_ed25519 -o BatchMode=yes -o ConnectTimeout=12 -o IdentitiesOnly=yes \
  -p 22 root@168.100.11.52 'echo LV_AMS_PRIVATE_SSH_OK'
'@
& ssh @($CommonLv + @("-p", $LvPort, "root@${LvHost}", $RemoteInstall))
if ($LASTEXITCODE -ne 0) { throw "LV install failed (exit $LASTEXITCODE)" }

if (-not $SkipAmsBackupBootstrap) {
    Write-Host "[deploy-ams-ops-lv] bootstrap AMS pg_dump + backup cron..."
    & scp @($CommonAms + @("-P", $AmsPort, (Join-Path $RepoRoot "ops\pg_dump_remnawave.sh"), (Join-Path $RepoRoot "ops\install-remnawave-backup-cron.sh"), "root@${AmsHost}:/tmp/"))
    $RemoteAms = @'
set -euo pipefail
mkdir -p /opt/scripts /opt/backups
sed -i 's/\r$//' /tmp/pg_dump_remnawave.sh /tmp/install-remnawave-backup-cron.sh
install -m 755 /tmp/pg_dump_remnawave.sh /opt/scripts/pg_dump_remnawave.sh
bash /tmp/install-remnawave-backup-cron.sh ams
/bin/bash /opt/scripts/pg_dump_remnawave.sh
ls -lh /opt/backups/remnawave-*.sql.gz | tail -1
'@
    & ssh @($CommonAms + @("-p", $AmsPort, "root@${AmsHost}", $RemoteAms))
    if ($LASTEXITCODE -ne 0) { throw "AMS pg_dump bootstrap failed (exit $LASTEXITCODE)" }

    Write-Host "[deploy-ams-ops-lv] install LV pull backup cron..."
    & scp @($CommonLv + @("-P", $LvPort, (Join-Path $RepoRoot "ops\install-remnawave-backup-cron.sh"), "root@${LvHost}:/tmp/install-remnawave-backup-cron.sh"))
    & ssh @($CommonLv + @("-p", $LvPort, "root@${LvHost}", "sed -i 's/\r$//' /tmp/install-remnawave-backup-cron.sh; bash /tmp/install-remnawave-backup-cron.sh lv"))
    if ($LASTEXITCODE -ne 0) { throw "LV backup cron install failed (exit $LASTEXITCODE)" }
}

if ($RunWatch) {
    Write-Host "[deploy-ams-ops-lv] run watch once (pull + push if needed)..."
    & ssh @($CommonLv + @("-p", $LvPort, "root@${LvHost}", "bash /opt/scripts/watch_ams_public_ssh_recovery.sh; tail -20 /var/log/bvpn-ams-public-ssh-watch.log; echo '---'; cat /var/lib/bvpn/ams-public-ssh-watch.state"))
}

Write-Host "AMS_OPS_PRIVATE_LV_OK"
