#!/bin/bash
# Run ON Latvia (or any host with SSH+scp to AMS and local /opt/backups).
# From Windows: scp ops/pull-latest-dump-ams-to-lv.sh bvpn-lv:/tmp/ && ssh bvpn-lv "sed -i 's/\r$//' /tmp/pull-latest-dump-ams-to-lv.sh; bash /tmp/pull-latest-dump-ams-to-lv.sh"
# Pulls latest /opt/backups/remnawave-*.sql.gz from AMS and verifies SHA256.
set -euo pipefail
AMS_IP="${AMS_IP:-168.100.11.140}"
AMS_PORT="${AMS_PORT:-3344}"
SSH=(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 -p "${AMS_PORT}" "root@${AMS_IP}")
SCP=(scp -o StrictHostKeyChecking=no -o ConnectTimeout=20 -P "${AMS_PORT}")
LOCAL_DIR="${LOCAL_DIR:-/opt/backups}"
mkdir -p "${LOCAL_DIR}"
REMOTE="$("${SSH[@]}" 'ls -1t /opt/backups/remnawave-*.sql.gz 2>/dev/null | head -1' | tr -d '\r')"
if [[ -z "${REMOTE}" ]]; then
  echo "ERROR: no remnawave-*.sql.gz on ${AMS_IP}" >&2
  exit 1
fi
BASE="$(basename "${REMOTE}")"
LOCAL="${LOCAL_DIR}/${BASE}"
echo "Remote: ${AMS_IP}:${REMOTE}"
EXP="$("${SSH[@]}" "sha256sum \"$REMOTE\"" | tr -d '\r' | cut -d' ' -f1)"
echo "Expected SHA256: ${EXP}"
"${SCP[@]}" "root@${AMS_IP}:${REMOTE}" "${LOCAL}.partial"
mv -f "${LOCAL}.partial" "${LOCAL}"
GOT="$(sha256sum "${LOCAL}" | cut -d' ' -f1)"
echo "Local file:  ${LOCAL}"
echo "Got SHA256:  ${GOT}"
if [[ "${EXP}" != "${GOT}" ]]; then
  echo "ERROR: hash mismatch" >&2
  exit 1
fi
echo "OK — copy verified."
ls -lh "${LOCAL}"
