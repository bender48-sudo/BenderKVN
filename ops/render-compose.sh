#!/usr/bin/env bash
# Thin wrapper: same CLI as Python (see ops/render_compose.py).
# Usage:
#   ops/render-compose.sh compose/ams/remnawave/panel.env.tmpl [.secrets/vault.env]
#   ops/render-compose.sh --only SECRET_KEY_NODE_AMS compose/ams/remnanode/docker-compose.yml.tmpl
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$REPO_ROOT/ops/render_compose.py" "$@"
