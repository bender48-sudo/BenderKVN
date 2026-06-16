"""Tests for ops/generate_mobile_capture_template.py."""
from __future__ import annotations

import re
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from generate_mobile_capture_template import (  # noqa: E402
    default_output_path,
    render_template,
)


def test_render_template_has_no_secret_placeholders():
    md = render_template(day="2026-06-16")
    assert "vless://" not in md
    assert "api/sub/" not in md
    assert "2026-06-16" in md
    assert "CLIENT-MOBILE-DAILY-CAPTURE-001" in md
    assert "access_percent_day" in md


def test_render_template_invalid_date():
    try:
        render_template(day="bad-date")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_default_output_under_local():
    p = default_output_path("2026-06-16")
    assert p.parts[0] == ".local"
    assert p.name == "mobile_capture_notes_2026-06-16.md"


def test_template_stdout_integration(tmp_path: Path, capsys):
    from generate_mobile_capture_template import main
    import sys as _sys

    # --stdout avoids writing; run via subprocess-like main
    old = _sys.argv
    try:
        _sys.argv = ["generate_mobile_capture_template.py", "--date", "2026-06-16", "--stdout"]
        assert main() == 0
    finally:
        _sys.argv = old
    out = capsys.readouterr().out
    assert "MOBILE_CAPTURE_TEMPLATE_OK" in out
    assert re.search(r"[0-9a-f]{32}", out) is None
