#!/bin/bash
# Run on AMS. Idempotent. Closes Docker-bypassed ports for the public
# subscription-page container, keeps Latvia panel reachability.
#
# Background: Docker writes its own ACCEPT rules into the FORWARD/DOCKER
# chains and bypasses UFW for any container started with `-p`. UFW's
# `ufw allow from 176.126.162.158 to any port 3010` lives in INPUT and
# therefore does NOT cover traffic to a docker-published port.
# DOCKER-USER is the official place to insert site rules — Docker leaves
# it empty by default and Netfilter consults it before DOCKER/DOCKER-NAT.

set -euo pipefail

WAN_IF="${WAN_IF:-eth0}"
LV_IP="${LV_IP:-176.126.162.158}"
# Space-separated list (P6-RED-SUBHA-01: 3010 primary + 3011 alt split-host).
SUB_PORTS="${SUB_PORTS:-${SUB_PORT:-3010}}"

# Ensure DOCKER-USER exists (it does on any host with Docker, but be safe)
iptables -L DOCKER-USER -n >/dev/null 2>&1 || iptables -N DOCKER-USER

apply_port() {
  local port="$1"
  while iptables -D DOCKER-USER -i "$WAN_IF" -p tcp --dport "$port" -s "$LV_IP" -j ACCEPT 2>/dev/null; do :; done
  while iptables -D DOCKER-USER -i "$WAN_IF" -p tcp --dport "$port" -j DROP   2>/dev/null; do :; done
  iptables -I DOCKER-USER 1 -i "$WAN_IF" -p tcp --dport "$port" -j DROP
  iptables -I DOCKER-USER 1 -i "$WAN_IF" -p tcp --dport "$port" -s "$LV_IP" -j ACCEPT
  echo "  port $port: ACCEPT from $LV_IP, DROP others"
}

echo "Applying DOCKER-USER rules for SUB_PORTS: $SUB_PORTS"
for port in $SUB_PORTS; do
  apply_port "$port"
done

echo "DOCKER-USER after apply:"
iptables -L DOCKER-USER -n --line-numbers
