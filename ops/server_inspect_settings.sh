#!/usr/bin/env bash
set -euo pipefail
sudo docker exec -i remnawave-db psql -U postgres -d postgres <<'SQL'
\d remnawave_settings
SELECT id, LENGTH(settings::text) FROM remnawave_settings LIMIT 5;
SQL
