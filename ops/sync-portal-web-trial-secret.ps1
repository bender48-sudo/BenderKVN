# Copy PORTAL_WEB_TRIAL_SECRET from LV portal-setup.env to AMS bot .env (one-time / after rotate).
# pwsh -File ops/sync-portal-web-trial-secret.ps1
$ErrorActionPreference = "Stop"
$KeyAms = Join-Path $env:USERPROFILE ".ssh\bvpn_ams_ed25519"
$KeyLv = Join-Path $env:USERPROFILE ".ssh\bvpn_lv_ed25519"
$secret = (ssh -i $KeyLv root@bvpn-lv "grep ^PORTAL_WEB_TRIAL_SECRET= /etc/bvpn/portal-setup.env").Trim()
if (-not $secret) { throw "PORTAL_WEB_TRIAL_SECRET missing on LV — run install-setup-verify-lv.sh first" }
ssh -i $KeyAms -p 3344 root@168.100.11.140 @"
set -e
ENV=/opt/remna-shop/.env
grep -q '^PORTAL_WEB_TRIAL_SECRET=' `$ENV 2>/dev/null && sed -i '/^PORTAL_WEB_TRIAL_SECRET=/d' `$ENV || true
echo '$secret' >> `$ENV
cd /opt/remna-shop && docker compose up -d remna-shop-bot
echo SYNC_PORTAL_WEB_TRIAL_SECRET_OK
"@
