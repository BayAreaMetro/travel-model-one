from __future__ import annotations

from pathlib import Path
import unittest


class RunModelEntrypointTests(unittest.TestCase):
    def test_converter_is_called_once_before_iteration_zero(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        text = (repo_root / "model-files" / "RunModel.bat").read_text(encoding="utf-8")

        call = "python CTRAMP\\utilities\\pt_converter\\run.py"
        self.assertEqual(text.count(call), 1) # Tests that PT-converter is called only once
        self.assertLess(text.index(call), text.index("set ITER=0")) # Tests PT-converter is called before iteration 0
