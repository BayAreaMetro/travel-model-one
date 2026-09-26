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
            self.assertTrue((inventory_path.parent / "links" / "transitNetworkLinks.csv").is_file())
            self.assertTrue(
                (inventory_path.parent / "links" / "transitNetworkDirectedLinks.csv").is_file()
            )
            self.assertTrue((inventory_path.parent / "links" / "transitLinkFactors.csv").is_file())
            self.assertTrue((inventory_path.parent / "links" / "link_conversion_report.json").is_file())
            self.assertTrue((inventory_path.parent / "ntlegs" / "transitAccess.NTL").is_file())
            self.assertTrue((inventory_path.parent / "ntlegs" / "generate_walk_funnels.block").is_file())
            self.assertTrue((inventory_path.parent / "ntlegs" / "generate_drive_funnel.block").is_file())
            self.assertTrue((inventory_path.parent / "ntlegs" / "walkAccessCrosswalk.csv").is_file())
            self.assertTrue((inventory_path.parent / "ntlegs" / "zoneAccessRules.csv").is_file())
            self.assertTrue((inventory_path.parent / "ntlegs" / "pnrFacilities.csv").is_file())
            self.assertTrue((inventory_path.parent / "ntlegs" / "connector_conversion_report.json").is_file())
            self.assertTrue((inventory_path.parent / "factors" / "wlk_loc_wlk.fac").is_file())
            self.assertTrue((inventory_path.parent / "factors" / "wlk_com_drv.fac").is_file())
            self.assertTrue((inventory_path.parent / "factors" / "factor_conversion_report.json").is_file())
            self.assertTrue((inventory_path.parent / "fares" / "transitFares.far").is_file())
            self.assertTrue((inventory_path.parent / "fares" / "fareZoneCrosswalk.csv").is_file())
            self.assertTrue((inventory_path.parent / "fares" / "fare_matrices.block").is_file())
            self.assertTrue((inventory_path.parent / "fares" / "fare_matrix_manifest.json").is_file())
            self.assertTrue((inventory_path.parent / "fares" / "fare_conversion_report.json").is_file())
            factor = (inventory_path.parent / "factors" / "wlk_loc_wlk.fac").read_text(
                encoding="utf-8"
            )
            self.assertIn("FARESYSTEM=1, MODE=11", factor)
            self.assertNotIn("MODE=1\n", factor)
            self.assertFalse((inventory_path.parent / "accessNetworkLinks.csv").exists())
            self.assertFalse((inventory_path.parent / "transferNetworkLinks.csv").exists())
            system = (inventory_path.parent / "transitSystem.pts").read_text(encoding="utf-8")
            self.assertIn(
                'MODE NUMBER=1, NAME="WALK ACCESS", LONGNAME="Walk access connector"',
                system,
            )
            self.assertIn(
                'MODE NUMBER=7, NAME="DRIVE EGRESS", LONGNAME="Drive egress connector"',
                system,
            )
            self.assertIn(
                'MODE NUMBER=11, NAME="B", LONGNAME="Broadway Shuttle"', system
            )
            self.assertNotIn("MODE NUMBER=120", system)
            self.assertFalse((inventory_path.parent / "buildPTNetwork.job").exists())

    def test_conversion_does_not_require_optional_name_crosswalks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model_dir = Path(temp)
            source_dir = model_dir / "INPUT" / "trn"
            shutil.copytree(
                Path(__file__).parent / "fixtures" / "minimal_trn", source_dir
            )
            for filename in (
                "transit_modes.csv",
                "transit_operators.csv",
                "transit_vehicle_types.csv",
            ):
                (source_dir / filename).unlink()

            convert_transit_network(
                ConversionRequest(model_dir, self.config("network_wrangler"))
            )
            system = (model_dir / "trn" / "pt" / "transitSystem.pts").read_text(
                encoding="utf-8"
            )

            self.assertIn('MODE NUMBER=11, NAME="MODE_11"', system)
            self.assertIn('OPERATOR NUMBER=7, NAME="OPERATOR_7"', system)
            self.assertIn('VEHICLETYPE NUMBER=1, NAME="VEHICLE_1"', system)

    def test_unsupported_source_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ConfigurationError, "Unsupported source"):
                convert_transit_network(
                    ConversionRequest(Path(temp), self.config("unsupported"))
                )
