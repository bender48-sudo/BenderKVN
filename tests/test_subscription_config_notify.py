"""Tests for ops/subscription_config_notify.py generation bump."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"
if str(OPS) not in sys.path:
    sys.path.insert(0, str(OPS))

import subscription_config_notify as scn  # noqa: E402


class TestBumpGeneration(unittest.TestCase):
    def test_increments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub_config_generation.json"
            scn.GENERATION_FILE = path
            self.assertEqual(scn.bump_generation("first"), 1)
            self.assertEqual(scn.bump_generation("second"), 2)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["generation"], 2)
            self.assertEqual(data["reason"], "second")
            self.assertTrue(data["updated_at"])


if __name__ == "__main__":
    unittest.main()
