# Align PORTAL_WEB_TRIAL_SECRET on LV with AMS bot (cabinet / telegram-setup API).
# pwsh -File ops/sync-portal-web-trial-secret-ams-to-lv.ps1
$ErrorActionPreference = "Stop"
$KeyAms = Join-Path $env:USERPROFILE ".ssh\bvpn_ams_ed25519"
$KeyLv = Join-Path $env:USERPROFILE ".ssh\bvpn_lv_ed25519"
$line = (ssh -i $KeyAms -p 3344 root@168.100.11.140 "grep '^PORTAL_WEB_TRIAL_SECRET=' /opt/remna-shop/.env").Trim()
if (-not $line) { throw "PORTAL_WEB_TRIAL_SECRET missing on AMS" }
ssh -i $KeyLv root@bvpn-lv @"
set -e
ENV=/etc/bvpn/portal-setup.env
grep -q '^PORTAL_WEB_TRIAL_SECRET=' `$ENV 2>/dev/null && sed -i '/^PORTAL_WEB_TRIAL_SECRET=/d' `$ENV || true
echo '$line' >> `$ENV
systemctl restart bvpn-setup-verify.service
sleep 1
systemctl is-active bvpn-setup-verify.service
curl -fsS -X POST -H 'Content-Type: application/json' -d '{\"telegram_id\":924498094}' http://127.0.0.1:8871/cabinet | head -c 120
echo
echo SYNC_PORTAL_WEB_TRIAL_SECRET_AMS_TO_LV_OK
"@
