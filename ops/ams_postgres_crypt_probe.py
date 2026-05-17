#!/usr/bin/env python3
"""P1-RED-DATA-01: verify Postgres data dir is on LUKS mapper (run on AMS)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PG_MOUNT = Path("/mnt/remnawave-pgdata")
LUKS_IMG = Path("/opt/remnawave/postgres.luks.img")
MAPPER = "/dev/mapper/remnawave-pg"
OLD_VOL = Path("/var/lib/docker/volumes/remnawave_remnawave-db-data/_data")


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _mount_device(mount_point: Path) -> str | None:
    try:
        out = subprocess.run(
            ["findmnt", "-n", "-o", "SOURCE", str(mount_point)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    try:
        for line in _read("/proc/mounts").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == str(mount_point):
                return parts[0]
    except OSError:
        pass
    return None


def main() -> int:
    ok = True
    print("=== Postgres LUKS probe (P1-RED-DATA-01) ===")

    if not LUKS_IMG.is_file():
        print(f"FAIL: missing {LUKS_IMG}", file=sys.stderr)
        return 2

    if not PG_MOUNT.is_dir():
        print(f"FAIL: mount point {PG_MOUNT} missing", file=sys.stderr)
        return 2

    src = _mount_device(PG_MOUNT)
    if not src:
        print(f"FAIL: {PG_MOUNT} not mounted", file=sys.stderr)
        ok = False
    elif "remnawave-pg" not in src and MAPPER not in src:
        print(f"FAIL: {PG_MOUNT} mounted from {src}, expected LUKS mapper", file=sys.stderr)
        ok = False
    else:
        print(f"OK: {PG_MOUNT} <- {src}")

    if Path(MAPPER).exists():
        print(f"OK: mapper {MAPPER} present")
    else:
        print(f"FAIL: mapper {MAPPER} missing", file=sys.stderr)
        ok = False

    # Key must not live as plaintext on AMS (common mistakes)
    for bad in (
        "/root/postgres-luks.key",
        "/opt/remnawave/postgres.luks.key",
        "/etc/remnawave-luks.key",
    ):
        if Path(bad).is_file():
            print(f"FAIL: plaintext LUKS key on disk: {bad}", file=sys.stderr)
            ok = False

    if OLD_VOL.is_dir() and any(OLD_VOL.iterdir()):
        print(f"NOTE: legacy docker volume still has data at {OLD_VOL} (archive after verify)")

    try:
        proc = subprocess.run(
            ["docker", "exec", "remnawave-db", "pg_isready", "-U", "postgres"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode == 0:
            print("OK: remnawave-db pg_isready")
        else:
            print(f"FAIL: pg_isready ({proc.returncode}): {proc.stderr.strip()}", file=sys.stderr)
            ok = False
    except Exception as exc:
        print(f"WARN: pg_isready check: {exc}")

    if ok:
        print("POSTGRES_CRYPT_OK")
        return 0
    print("POSTGRES_CRYPT_FAIL", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
