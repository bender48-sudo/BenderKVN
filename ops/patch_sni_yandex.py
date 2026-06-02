#!/usr/bin/env python3
"""Q102 / P0 TSPU: ensure Reality SNI is www.yandex.ru (not github/microsoft cluster).

Wraps panel host rotation + live sub verification.

Usage:
    python ops/patch_sni_yandex.py              # dry-run hosts + live SNI check
    python ops/patch_sni_yandex.py --apply      # PATCH forbidden hosts + verify
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--include-hidden", action="store_true")
    args = ap.parse_args()

    rotate_cmd = [sys.executable, str(OPS / "rotate_panel_host_sni.py")]
    if args.apply:
        rotate_cmd.append("--apply")
    if args.include_hidden:
        rotate_cmd.append("--include-hidden")

    print("=== panel hosts SNI ===")
    rc = subprocess.run(rotate_cmd, cwd=str(ROOT))
    if rc.returncode != 0:
        return rc.returncode

    print("\n=== live subscription SNI ===")
    smoke_cmd = [sys.executable, str(OPS / "smoke_live_sub_sni.py")]
    rc2 = subprocess.run(smoke_cmd, cwd=str(ROOT))
    if rc2.returncode != 0:
        if not args.apply:
            print("\nDry-run: pass --apply to rotate panel hosts, then re-run smoke")
        return rc2.returncode

    if args.apply:
        print("\nPATCH_SNI_YANDEX_OK")
    else:
        print("\nDry-run OK. Apply: python ops/patch_sni_yandex.py --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
