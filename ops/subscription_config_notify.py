"""Bump subscription config generation and signal AMS bot to notify users.

After any PATCH to subscription-templates that changes user-facing config,
call ``after_template_patch(reason)``. That increments a monotonic generation
counter, persists it locally, and (by default) pushes the value into the shop
bot SQLite on AMS so the scheduler can message users who have not been notified
for this generation yet.

See ``bot_src/subscription_refresh.py`` and ``ops/push_sub_config_generation_ams.py``.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATION_FILE = ROOT / ".secrets" / "sub_config_generation.json"


def load_state() -> dict:
    if GENERATION_FILE.exists():
        return json.loads(GENERATION_FILE.read_text(encoding="utf-8"))
    return {"generation": 0, "reason": "", "updated_at": ""}


def save_state(state: dict) -> None:
    GENERATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    GENERATION_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def bump_generation(reason: str) -> int:
    state = load_state()
    gen = int(state.get("generation", 0)) + 1
    new_state = {
        "generation": gen,
        "reason": reason,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    save_state(new_state)
    return gen


def push_to_ams(generation: int, reason: str) -> None:
    script = ROOT / "ops" / "push_sub_config_generation_ams.py"
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--generation",
            str(generation),
            "--reason",
            reason,
        ],
        check=True,
    )


def after_template_patch(reason: str, *, push_ams: bool = True) -> int:
    """Call after a successful subscription-template PATCH on panel."""
    gen = bump_generation(reason)
    print(f"[sub-config] generation -> {gen} ({reason})")
    if push_ams:
        push_to_ams(gen, reason)
    return gen


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reason", default="manual", help="audit label for this bump")
    ap.add_argument(
        "--no-push",
        action="store_true",
        help="only bump local .secrets file, do not update AMS bot DB",
    )
    ap.add_argument(
        "--show",
        action="store_true",
        help="print current generation and exit",
    )
    args = ap.parse_args()

    if args.show:
        st = load_state()
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return

    after_template_patch(args.reason, push_ams=not args.no_push)


if __name__ == "__main__":
    main()
