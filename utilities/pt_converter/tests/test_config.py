from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from pt_converter.config import load_config
from pt_converter.errors import ConfigurationError


class ConfigTests(unittest.TestCase):
    def write_config(self, directory: Path, payload: object) -> Path:
        path = directory / "config.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_loads_valid_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_config(
                Path(temp),
                {"config_version": 1, "source": "network_wrangler", "output_directory": "trn/pt"},
            )
            config = load_config(path)

        self.assertEqual(config.source, "network_wrangler")
        self.assertEqual(config.output_directory, Path("trn/pt"))

    def test_rejects_unknown_setting(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_config(
                Path(temp),
                {
                    "config_version": 1,
                    "source": "network_wrangler",
                    "output_directory": "trn/pt",
                    "mystery": True,
                },
            )
            with self.assertRaisesRegex(ConfigurationError, "Unknown configuration"):
                load_config(path)

    def test_rejects_legacy_files_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_config(
                Path(temp),
                {"config_version": 1, "source": "legacy_files", "output_directory": "trn/pt"},
            )
            with self.assertRaisesRegex(ConfigurationError, "Unsupported source"):
                load_config(path)

    def test_rejects_absolute_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_config(
                Path(temp),
                {"config_version": 1, "source": "network_wrangler", "output_directory": "/tmp/pt"},
            )
            with self.assertRaisesRegex(ConfigurationError, "must be relative"):
                load_config(path)
