#!/usr/bin/env bash
# Runtime + document Valkey eviction on AMS (P6-SCALE-05).
# Persisted in compose tmpl; survives restart after safe-deploy recreate.
set -euo pipefail

CONTAINER=remnawave-redis
MAXMEM_BYTES=268435456  # 256mb
POLICY=allkeys-lru

echo "[valkey] current policy:"
docker exec "$CONTAINER" valkey-cli CONFIG GET maxmemory
docker exec "$CONTAINER" valkey-cli CONFIG GET maxmemory-policy

echo "[valkey] apply maxmemory=${MAXMEM_BYTES} policy=${POLICY}"
docker exec "$CONTAINER" valkey-cli CONFIG SET maxmemory "$MAXMEM_BYTES"
docker exec "$CONTAINER" valkey-cli CONFIG SET maxmemory-policy "$POLICY"

echo "[valkey] after:"
docker exec "$CONTAINER" valkey-cli CONFIG GET maxmemory
docker exec "$CONTAINER" valkey-cli CONFIG GET maxmemory-policy
docker exec "$CONTAINER" valkey-cli INFO memory | grep -E 'used_memory_human|maxmemory_human'

echo "APPLY_VALKEY_EVICTION_AMS_OK"
