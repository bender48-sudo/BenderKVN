#!/bin/bash
# P0-SEC-04: remove live /opt/remnawave from LV (legacy AMS secret duplicate).
# Run on bvpn-lv as root. Idempotent: exits 0 if /opt/remnawave already absent.

set -euo pipefail

ARCH_ROOT=/opt/_archive
LEGACY=/opt/remnawave

if [[ ! -d "$LEGACY" ]]; then
  echo "[archive_lv_remnawave_legacy] OK: no ${LEGACY} — nothing to archive."
  exit 0
fi

ts="$(date +%Y%m%d-%H%M%S)"
dest="${ARCH_ROOT}/remnawave-legacy-${ts}"
mkdir -p "$ARCH_ROOT"
mv "$LEGACY" "$dest"

chmod 700 "$dest"
find "$dest" -type d -exec chmod 700 {} +
find "$dest" -type f -exec chmod 600 {} +
if command -v chattr >/dev/null 2>&1; then
  chattr +i "$dest" || echo "[archive_lv_remnawave_legacy] WARN: chattr +i failed (ignore if unsupported FS)."
else
  echo "[archive_lv_remnawave_legacy] WARN: no chattr — skip immutable flag."
fi

echo "[archive_lv_remnawave_legacy] OK: moved to ${dest} (permissions tightened, dir +i if supported)."
ls -la "$ARCH_ROOT"
