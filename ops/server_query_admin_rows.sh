#!/usr/bin/env bash
set -euo pipefail
sudo docker exec -i remnawave-db psql -U postgres -d postgres <<'SQL'
SELECT COUNT(*) AS admin_rows FROM admin;
SELECT uuid, username, role FROM admin ORDER BY username;
SQL
