#!/bin/bash
# P2-RED-SUB-01 smoke on bvpn-lv: two origins, same body hash. Exit 0 on success.
set -euo pipefail
PROBE_SUFFIX="${SUB_MONITOR_PROBE_SUFFIX:-api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2}"
PRIMARY="${SUB_PUBLIC_ORIGIN:-https://p4n7q.conntest.xyz:2053}"
ALT="${SUB_ALT_PUBLIC_ORIGIN:-https://k9x2m1.conntest.xyz:2053}"
U1="${PRIMARY%/}/${PROBE_SUFFIX}"
U2="${ALT%/}/${PROBE_SUFFIX}"

c1=$(curl -s -o /dev/null -w "%{http_code}" -m 20 "$U1")
c2=$(curl -s -o /dev/null -w "%{http_code}" -m 20 "$U2")
h1=$(curl -fsS -m 20 "$U1" | sha256sum | awk '{print $1}')
h2=$(curl -fsS -m 20 "$U2" | sha256sum | awk '{print $1}')

echo "primary $U1 HTTP $c1 sha256=$h1"
echo "alt     $U2 HTTP $c2 sha256=$h2"

if [ "$c1" != "200" ] || [ "$c2" != "200" ]; then
  echo "FAIL: expected HTTP 200 on both origins" >&2
  exit 1
fi
if [ "$h1" != "$h2" ]; then
  echo "FAIL: body drift between origins" >&2
  exit 2
fi
echo "SUB_MULTI_ORIGIN_OK"
