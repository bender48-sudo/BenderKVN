#!/bin/bash
# P1-RED-SSH-01: remote audit from AMS panel (also reaches NL). Run: ssh bvpn-ams 'bash -s' < ops/ssh_audit_from_ams.sh
set -eu

LV_IP="${LV_IP:-176.126.162.158}"
NL_IP="${NL_IP:-91.90.192.17}"
NL_PORT="${NL_PORT:-3333}"

fail=0
declare -A seen

add_host() {
  local host="$1" text="$2"
  local n=0
  echo "=== $host ==="
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line//$'\r'/}"
    [ -z "$line" ] && continue
    case "$line" in \#*) continue ;; esac
    if [[ "$line" =~ (ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256)[[:space:]]+([A-Za-z0-9+/=]+) ]]; then
      blob="${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
      restricted=0
      [[ "$line" == command=* || "$line" == from=* ]] && restricted=1
      n=$((n + 1))
      if [ "$restricted" -eq 1 ]; then
        echo "  [restricted] ${blob:0:40}..."
      else
        echo "  [login] ${blob:0:40}..."
        if [ -n "${seen[$blob]:-}" ] && [ "${seen[$blob]}" != "$host" ]; then
          echo "FAIL: duplicate operator key on ${seen[$blob]} and $host"
          fail=1
        fi
        seen[$blob]="$host"
      fi
    fi
  done <<< "$text"
  echo "  ($n key lines)"
}

ak_ams="$(head -c 4096 /root/.ssh/authorized_keys 2>/dev/null || true)"
add_host "bvpn-ams" "$ak_ams"

ak_nl="$(ssh -i /root/.ssh/bvpn_nl -o BatchMode=yes -o ConnectTimeout=12 -p "$NL_PORT" \
  -o StrictHostKeyChecking=accept-new "root@${NL_IP}" \
  'head -c 4096 /root/.ssh/authorized_keys 2>/dev/null || true' 2>/dev/null || true)"
add_host "bvpn-nl" "$ak_nl"

ak_lv=""
if command -v timeout >/dev/null 2>&1; then
  ak_lv="$(timeout 12 ssh -o BatchMode=yes -o ConnectTimeout=8 -p 3333 \
    -o StrictHostKeyChecking=accept-new "root@${LV_IP}" \
    'head -c 4096 /root/.ssh/authorized_keys 2>/dev/null || true' 2>/dev/null || true)"
fi
if [ -n "$ak_lv" ]; then
  add_host "bvpn-lv" "$ak_lv"
else
  echo "=== bvpn-lv ==="
  echo "  (skip: no SSH path from AMS; audit LV from workstation)"
fi

if [ "$fail" -eq 0 ]; then
  echo "SSH_AUDIT_OK"
  exit 0
fi
echo "SSH_AUDIT_FAIL" >&2
exit 2
