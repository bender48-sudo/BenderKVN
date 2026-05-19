#!/usr/bin/env python3
"""Q086: admin_handlers FSM must check ADMIN_TELEGRAM_ID on edit paths."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
path = ROOT / "bot_src" / "admin_handlers.py"
text = path.read_text(encoding="utf-8")

needles = [
    "def _is_admin(",
    'if not _is_admin(callback.from_user.id):',
    "if not _is_admin(message.from_user.id):",
    '@admin_router.callback_query(F.data.startswith("admin_edit_"))',
]
missing = [n for n in needles if n not in text]
if missing:
    print("ADMIN_FSM_AUTHZ_FAIL: missing", missing, file=sys.stderr)
    raise SystemExit(1)
print("ADMIN_FSM_AUTHZ_OK")
