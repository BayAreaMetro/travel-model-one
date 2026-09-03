from __future__ import annotations

from pathlib import Path
import json
import shutil
import tempfile
import unittest

from pt_converter.api import ConversionRequest, convert_transit_network
from pt_converter.config import ConverterConfig
from pt_converter.errors import ConfigurationError


class ConversionTests(unittest.TestCase):
    def config(self, source: str) -> ConverterConfig:
        return ConverterConfig(1, source, Path("trn/pt"))

    def test_network_wrangler_inventory_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model_dir = Path(temp)
            source_dir = model_dir / "INPUT" / "trn"
            shutil.copytree(
                Path(__file__).parent / "fixtures" / "minimal_trn", source_dir
            )
            result = convert_transit_network(
                ConversionRequest(model_dir, self.config("network_wrangler"))
            )

            inventory_path = model_dir / "trn" / "pt" / "source_inventory.json"
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))

            self.assertEqual(result.action, "convert-network-wrangler-inputs")
            self.assertEqual(inventory["transit_lines"]["count"], 1)
            self.assertEqual(inventory["transit_lines"]["modes"], [11])
            self.assertEqual(inventory["transit_lines"]["operators"], [7])
            self.assertEqual(inventory["transit_lines"]["headway_periods"], [1, 2, 3, 4, 5])
            self.assertEqual(inventory["issues"], [])
            self.assertTrue((inventory_path.parent / "transitLines.lin").is_file())
            self.assertTrue((inventory_path.parent / "transitSystem.pts").is_file())
            self.assertTrue((inventory_path.parent / "line_conversion_report.json").is_file())

    def test_unsupported_source_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ConfigurationError, "Unsupported source"):
                convert_transit_network(
                    ConversionRequest(Path(temp), self.config("unsupported"))
                )
