from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from pt_converter.cli import main


class CliTests(unittest.TestCase):
    def test_version(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as result:
            main(["--version"])
        self.assertEqual(result.exception.code, 0)
        self.assertEqual("0.1.0\n", output.getvalue())

    def test_network_wrangler_entry_point(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source_dir = temp_path / "INPUT" / "trn"
            shutil.copytree(
                Path(__file__).parent / "fixtures" / "minimal_trn", source_dir
            )
            config = temp_path / "config.json"
            config.write_text(
                json.dumps(
                    {
                        "config_version": 1,
                        "source": "network_wrangler",
                        "output_directory": "trn/pt",
                    }
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(["--model-dir", temp, "--config", str(config)])

        self.assertEqual(status, 0)
        self.assertIn("converted 1 transit line(s)", output.getvalue())

    def test_bad_config_returns_two_without_traceback(self) -> None:
        errors = io.StringIO()
        with tempfile.TemporaryDirectory() as temp, redirect_stderr(errors):
            status = main(["--model-dir", temp, "--config", str(Path(temp) / "missing.json")])

        self.assertEqual(status, 2)
        self.assertIn("Configuration file does not exist", errors.getvalue())
