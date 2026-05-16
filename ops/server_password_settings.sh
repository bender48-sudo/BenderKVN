#!/usr/bin/env bash
set -euo pipefail
sudo docker exec -i remnawave-db psql -U postgres -d postgres <<'SQL'
SELECT password_settings FROM remnawave_settings WHERE id = 1;
SQL
