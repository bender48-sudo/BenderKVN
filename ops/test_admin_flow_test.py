#!/usr/bin/env python3
"""Smoke: admin flow test module imports and report helpers."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
mod = ROOT / "bot_src" / "admin_flow_test.py"
guide = ROOT / "bot_src" / "admin_flow_guide.py"
admin_h = ROOT / "bot_src" / "admin_handlers.py"
kb = ROOT / "bot_src" / "keyboards.py"

for p in (mod, guide, admin_h, kb):
    ast.parse(p.read_text(encoding="utf-8"))

text = admin_h.read_text(encoding="utf-8")
for needle in (
    "admin_flow_test_menu",
    "admin_flow_smoke_all",
    "admin_flow_g_nb_1",
    "admin_demo_hint_trial",
    "admin_flow_guide",
    "_render_admin_flow_guide",
):
    if needle not in text:
        print(f"FAIL: missing {needle} in admin_handlers.py", file=sys.stderr)
        raise SystemExit(1)

kb_text = kb.read_text(encoding="utf-8")
for needle_kb in (
    "admin_flow_test_menu",
    "admin_flow_g_nb_1",
    "create_admin_guide_nb_step1_keyboard",
    "admin_demo_hint_trial",
):
    if needle_kb not in kb_text:
        print(f"FAIL: keyboards missing {needle_kb}", file=sys.stderr)
        raise SystemExit(1)

mod_text = mod.read_text(encoding="utf-8")
for fn in (
    "run_all_smokes",
    "smoke_existing_user",
    "smoke_newbie_logic",
    "smoke_email_web",
    "sim_newbie_header",
):
    if f"def {fn}" not in mod_text and f"async def {fn}" not in mod_text:
        print(f"FAIL: missing {fn}", file=sys.stderr)
        raise SystemExit(1)
print("ADMIN_FLOW_TEST_OK")
