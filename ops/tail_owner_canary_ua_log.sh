#!/usr/bin/env bash
# Summarize owner-canary Caddy JSON log (G1 smoke): UA + HWID-related request headers.
# Usage on bvpn-lv:
#   bash ops/tail_owner_canary_ua_log.sh
#   bash ops/tail_owner_canary_ua_log.sh --since-minutes 120
#   bash ops/tail_owner_canary_ua_log.sh --since-minutes 120 --verbose
set -euo pipefail

LOG=/var/log/caddy/owner-canary-access.log
SINCE_MIN=60
VERBOSE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --since-minutes)
      SINCE_MIN="${2:-60}"
      shift 2
      ;;
    --verbose|-v)
      VERBOSE=1
      shift
      ;;
    *)
      echo "usage: $0 [--since-minutes N] [--verbose]" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$LOG" ]]; then
  echo "MISSING: $LOG (run patch-caddy-owner-canary-ua-log-lv.sh on LV first)" >&2
  exit 1
fi

python3 <<PY
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = Path("$LOG")
since = datetime.now(timezone.utc) - timedelta(minutes=int("$SINCE_MIN"))
verbose = int("$VERBOSE")

HWID_KEYS = (
    "x-hwid",
    "x-device-os",
    "x-device-model",
    "x-ver-os",
    "x-app-version",
    "x-client",
)


def header_first(headers: dict, name: str) -> str:
    if not isinstance(headers, dict):
        return "-"
    # Caddy JSON uses canonical Title-Case keys; match case-insensitively.
    want = name.lower()
    for k, v in headers.items():
        if str(k).lower() == want:
            if isinstance(v, list) and v:
                return str(v[0])
            if v:
                return str(v)
    return "-"


rows = []
ua_counter = Counter()
for line in log.read_text(encoding="utf-8", errors="replace").splitlines()[-8000:]:
    line = line.strip()
    if not line:
        continue
    try:
        rec = json.loads(line)
    except json.JSONDecodeError:
        continue
    req = rec.get("request") or {}
    uri = str(req.get("uri") or "")
    if "/owner-canary/" not in uri:
        continue
    ts_s = rec.get("ts")
    if isinstance(ts_s, (int, float)):
        ts = datetime.fromtimestamp(ts_s, tz=timezone.utc)
        ts_label = ts.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        ts = since
        ts_label = "?"
    if ts < since:
        continue
    headers = req.get("headers") or {}
    ua = header_first(headers, "User-Agent")
    if ua != "-":
        ua_counter[ua] += 1
    row = {
        "ts": ts_label,
        "remote_ip": req.get("remote_ip") or "?",
        "uri": uri,
        "ua": ua,
        "x_hwid": header_first(headers, "x-hwid"),
        "x_device_os": header_first(headers, "x-device-os"),
        "x_device_model": header_first(headers, "x-device-model"),
        "x_ver_os": header_first(headers, "x-ver-os"),
        "x_app_version": header_first(headers, "x-app-version"),
        "x_client": header_first(headers, "x-client"),
        "status": rec.get("status"),
    }
    rows.append(row)

print(f"owner-canary hits (last ${SINCE_MIN} min, uri contains /owner-canary/): {len(rows)}")
print()
print("UA summary:")
for u, n in ua_counter.most_common(30):
    print(f"  {n:4d}  {u}")
print()
if not rows:
    raise SystemExit(0)

if verbose:
    print("ts\tremote_ip\tstatus\tua\tx-hwid\tx-device-os\tx-device-model\tx-ver-os\tx-app-version\tx-client")
    for r in rows[-50:]:
        print(
            f"{r['ts']}\t{r['remote_ip']}\t{r.get('status','?')}\t{r['ua']}\t"
            f"{r['x_hwid']}\t{r['x_device_os']}\t{r['x_device_model']}\t"
            f"{r['x_ver_os']}\t{r['x_app_version']}\t{r['x_client']}"
        )
else:
    print("last hits (use --verbose for full table):")
    print("ts\tremote_ip\tua\tx-hwid\tx-device-os\tx-app-version")
    for r in rows[-15:]:
        print(
            f"{r['ts']}\t{r['remote_ip']}\t{r['ua'][:72]}\t"
            f"{r['x_hwid']}\t{r['x_device_os']}\t{r['x_app_version']}"
        )
PY
