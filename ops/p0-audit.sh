#!/bin/bash
# Post-P0 audit. Run on both LV and AMS; results aggregated.

set +e

color() { printf '\n=== %s ===\n' "$1"; }
ok()    { printf '  OK   %s\n' "$1"; }
bad()   { printf '  FAIL %s\n' "$1"; }
warn()  { printf '  WARN %s\n' "$1"; }

color "Container state"
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'

color "Pinned-by-digest check (critical images)"
for c in remnanode remnawave remnawave-subscription-page; do
    if ! docker inspect "$c" >/dev/null 2>&1; then
        warn "$c not on this host (expected for cross-host check)"
        continue
    fi
    img=$(docker inspect --format '{{.Config.Image}}' "$c")
    if [[ "$img" == *"@sha256:"* ]]; then
        ok "$c pinned: $img"
    else
        bad "$c NOT pinned: $img"
    fi
done

color "Subscription endpoint accessibility (must be 200 from LV, blocked direct)"
if curl -fsS -o /dev/null --connect-timeout 5 "https://p4n7q.conntest.xyz:2053/api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2"; then
    ok "via Caddy 2053 -> 200"
else
    bad "via Caddy 2053 not 200"
fi

if [ "$(hostname -I 2>/dev/null | awk '{print $1}')" = "168.100.11.140" ]; then
    color "AMS-only: direct 3010 must be blocked from outside"
    # We test that DOCKER-USER drops non-LV; from AMS itself it's loopback so OK.
    if curl -fsS -o /dev/null --connect-timeout 3 "http://127.0.0.1:3010" 2>/dev/null; then
        ok "loopback 127.0.0.1:3010 (expected: works locally)"
    fi
    color "AMS-only: iptables DOCKER-USER rules for 3010"
    iptables -L DOCKER-USER -n -v 2>/dev/null | grep -E '3010|3010' | head -5 \
        && ok "DOCKER-USER has 3010 rules" \
        || bad "DOCKER-USER missing 3010 rules"
fi

color "TLS verification posture (we should NEVER need -k for panel/sub)"
if curl -fsS -o /dev/null --connect-timeout 5 "https://k9x2m1.conntest.xyz:2053/"; then
    ok "panel valid TLS (system CA accepts cert)"
else
    bad "panel TLS failed without -k"
fi
# Test sub TLS by hitting a path that exists (root yields 404 from Caddy — that's path, not TLS).
sub_code=$(curl -s -o /dev/null --connect-timeout 5 -w '%{http_code}' \
    "https://p4n7q.conntest.xyz:2053/api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2" 2>/dev/null)
if [ "$sub_code" = "200" ]; then
    ok "sub valid TLS (system CA accepts cert)"
else
    bad "sub TLS path returned $sub_code (TLS may be ok but path is unhealthy)"
fi

color "Token leak check (no Bearer should be in any running process)"
leaks=$(ps auxww 2>/dev/null | grep -E 'Bearer ' | grep -v 'grep ' | wc -l)
if [ "$leaks" -eq 0 ]; then
    ok "no Authorization: Bearer in any argv"
else
    bad "$leaks processes show Bearer in argv:"
    ps auxww | grep -E 'Bearer ' | grep -v 'grep ' | head -5
fi

color "Backup posture"
ls -la /opt/scripts/*.bak* 2>/dev/null | head -10 || warn "no script backups (expected on hosts that don't run scripts)"
ls -la /opt/remnawave/docker-compose.yml.bak* 2>/dev/null | head -5
ls -la /opt/remnanode/docker-compose.yml.bak* 2>/dev/null | head -5
ls -la /var/backups/remnawave/ 2>/dev/null | tail -3

color "Cron jobs that still run (monitor + ru-monitor + selfsteal + daily)"
crontab -l 2>/dev/null | grep -E 'monitor|daily' || warn "no cron entries on this host"

color "Done"
