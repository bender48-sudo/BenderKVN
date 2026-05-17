#!/usr/bin/env bash
# AMS (root): FAIL if JWT is inlined in compose (regression detector).
# Run: ssh bvpn-ams bash -s < ops/check-ams-subscription-token-layout.sh
set -eu
dc=/opt/remnawave/sub/docker-compose.yml
if [[ ! -r "$dc" ]]; then echo "fatal: missing $dc" >&2; exit 2; fi
if grep -qE '^\s*-\s*REMNAWAVE_API_TOKEN=eyJ' "$dc"; then
	echo "fatal: inlined JWT in $dc — run ops/sync-sub-token-ams.sh from workstation" >&2
	exit 1
fi
if ! grep -Fq '${REMNA_API_TOKEN}' "$dc"; then
	echo "fatal: $dc missing REMNAWAVE_API_TOKEN=\${REMNA_API_TOKEN}" >&2
	exit 1
fi
if [[ ! -r /opt/remnawave/sub/.env ]]; then
	echo "fatal: missing /opt/remnawave/sub/.env" >&2
	exit 1
fi
grep -q '^REMNA_API_TOKEN=' /opt/remnawave/sub/.env || {
	echo "fatal: no REMNA_API_TOKEN in sub/.env" >&2
	exit 1
}
exit 0
