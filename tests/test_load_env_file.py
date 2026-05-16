"""Unit tests for ops/load_env_file.py (P5-ENG-02). Run: python -m unittest discover -s tests"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "ops"))

from load_env_file import load_env_file  # noqa: E402


class TestLoadEnvFile(unittest.TestCase):
    def test_quotes_comments_export(self) -> None:
        tmp = _REPO / "tests" / "_tmp_load_env_test.env"
        tmp.write_text(
            "# head\n"
            'export FOO="bar baz"\n'
            "BAZ=single'quote'edge\n"
            "EMPTY=\n"
            "IGNORE # only if no =\n"
            "HASH=ok # tail stripped by simple rule\n",
            encoding="utf-8",
        )
        try:
            d = load_env_file(tmp)
            self.assertEqual(d["FOO"], "bar baz")
            self.assertEqual(d["BAZ"], "single'quote'edge")
            self.assertEqual(d["EMPTY"], "")
            self.assertEqual(d["HASH"], "ok")
        finally:
            tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
