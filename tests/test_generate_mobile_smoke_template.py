"""Tests for ops/generate_mobile_smoke_template.py."""
from __future__ import annotations

import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from generate_mobile_smoke_template import TEMPLATE  # noqa: E402


def test_template_has_required_sections():
    assert "CLIENT-STABILITY-MOBILE-SMOKE-001" in TEMPLATE
    assert "Do not paste subscription URLs" in TEMPLATE
    assert "PASS / SOFT PASS / FAIL" in TEMPLATE
    assert "ya.ru" in TEMPLATE
    assert "vless://" not in TEMPLATE
