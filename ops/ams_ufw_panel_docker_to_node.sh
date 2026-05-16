#!/bin/bash
# One-off on Amsterdam (or any host where Remnawave panel Docker talks to remnanode:2222 on same machine).
set -euo pipefail
ufw allow from 172.17.0.0/16 to any port 2222 proto tcp comment 'panel Docker default bridge -> remnanode' || true
ufw allow from 172.18.0.0/16 to any port 2222 proto tcp comment 'panel Docker compose -> remnanode' || true
ufw reload
ufw status numbered | grep -E '2222|172\.(17|18)' || ufw status numbered
