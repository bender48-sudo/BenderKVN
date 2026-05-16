#!/usr/bin/env bash
set -euo pipefail
echo "=== \\dt public.* ==="
sudo docker exec remnawave-db psql -U postgres -d postgres -c "\dt public.*"
