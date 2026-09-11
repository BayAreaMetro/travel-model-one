from __future__ import annotations

from pathlib import Path
import json
import shutil
import tempfile
import unittest

from pt_converter.line_conversion import (
    PTInputWriter,
    TransitLineReader,
    TransitModeReader,
    TransitOperatorReader,
    VehicleCatalogReader,
)
from pt_converter.errors import TranslationError


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_trn"
GOLDEN = Path(__file__).parent / "golden"


class LineConversionTests(unittest.TestCase):
    def test_published_mode_table_contains_named_tm1_modes(self) -> None:
        modes = TransitModeReader().read(
            FIXTURE / "transit_modes.csv"
        )
        names = {mode.number: mode.name for mode in modes}

        self.assertEqual(names[30], "AC Transit - Local")
        self.assertEqual(names[120], "BART & E-BART")

    def test_mode_table_rejects_long_or_duplicate_short_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "transit_modes.csv"
            path.write_text(
                "mode_number,short_name,mode_name,mode_category\n"
                "1,NAME THAT IS TOO LONG,First,Support\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(TranslationError, "exceeds 14 characters"):
                TransitModeReader().read(path)

            path.write_text(
                "mode_number,short_name,mode_name,mode_category\n"
                "1,WALK,First,Support\n"
                "2,walk,Second,Support\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(TranslationError, "duplicate short_name"):
                TransitModeReader().read(path)

    def test_operator_table_rejects_long_or_duplicate_short_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "transit_operators.csv"
            path.write_text(
                "operator_number,short_name,operator_name\n"
                "1,OPERATOR NAME TOO LONG,First operator\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(TranslationError, "exceeds 14 characters"):
                TransitOperatorReader().read(path)

            path.write_text(
                "operator_number,short_name,operator_name\n"
                "1,AGENCY,First operator\n"
                "2,agency,Second operator\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(TranslationError, "duplicate short_name"):
                TransitOperatorReader().read(path)

    def test_vehicle_table_rejects_long_or_duplicate_short_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "trn"
            shutil.copytree(FIXTURE, source)
            table = source / "transit_vehicle_types.csv"
            table.write_text(
                "vehicle_type,short_name,vehicle_name\n"
                "Standard Bus,VEHICLE NAME TOO LONG,Standard Bus\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(TranslationError, "exceeds 14 characters"):
                VehicleCatalogReader().read(source)

            table.write_text(
                "vehicle_type,short_name,vehicle_name\n"
                "Standard Bus,BUS,Standard Bus\n"
                "standard bus,bus,Duplicate Bus\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(TranslationError, "duplicate short_name"):
                VehicleCatalogReader().read(source)

    def test_reader_preserves_line_meaning(self) -> None:
        line = TransitLineReader().read(FIXTURE / "transitLines.lin")[0]

        self.assertEqual(line.name, "TEST_BUS")
        self.assertEqual(line.mode, 11)
        self.assertEqual(line.operator, 7)
        self.assertEqual(line.nodes, (1, 2, -3))
        self.assertIn("ACCESS=2, 1", line.node_text)
        self.assertEqual(
            line.comments_before,
            ("; Source: tests/fixtures/minimal_trn/example.tpl",),
        )
        self.assertEqual(line.comments_within, ("; important node note",))

    def test_writer_translates_keywords_and_capacities(self) -> None:
        lines = TransitLineReader().read(FIXTURE / "transitLines.lin")
        vehicles = VehicleCatalogReader().read(FIXTURE)
        modes = TransitModeReader().read(
            FIXTURE / "transit_modes.csv"
        )
        operators = TransitOperatorReader().read(
            FIXTURE / "transit_operators.csv"
        )
        with tempfile.TemporaryDirectory() as temp:
            result = PTInputWriter().write(
                lines, vehicles, modes, operators, Path(temp)
            )
            line_text = result.line_path.read_text(encoding="utf-8")
            system_text = result.system_path.read_text(encoding="utf-8")
            report = json.loads(result.report_path.read_text(encoding="utf-8"))

            self.assertEqual(
                line_text,
                (GOLDEN / "transitLines.lin").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                system_text,
                (GOLDEN / "transitSystem.pts").read_text(encoding="utf-8"),
            )

        self.assertIn("HEADWAY[2]=12.35", line_text)
        self.assertIn("OPERATOR=7", line_text)
        self.assertNotIn("FREQ[", line_text)
        self.assertNotIn("OWNER=", line_text)
        self.assertTrue(line_text.startswith(";;<<PT>><<LINE>>;;\n"))
        self.assertNotIn("Source control marker", line_text)
        self.assertIn(
            'MODE NUMBER=11, NAME="B", LONGNAME="Broadway Shuttle"', system_text
        )
        self.assertIn(
            'MODE NUMBER=1, NAME="WALK ACCESS", LONGNAME="Walk access connector"',
            system_text,
        )
        self.assertIn(
            'MODE NUMBER=120, NAME="BR", LONGNAME="BART & E-BART"', system_text
        )
        self.assertIn(
            'MODE NUMBER=3, NAME="XFER", '
            'LONGNAME="Stop-to-stop or stop-to-station transfer"',
            system_text,
        )
        self.assertIn(
            'OPERATOR NUMBER=7, NAME="BWAY SHUTTLE", '
            'LONGNAME="Broadway Shuttle"',
            system_text,
        )
        self.assertIn(
            'NAME="STD BUS", LONGNAME="Standard Bus", CRUSHCAP=60', system_text
        )
        self.assertIn(
            'WAITCRVDEF NUMBER=1, NAME="HALF HEADWAY", '
            'LONGNAME="Wait equals half the headway",',
            system_text,
        )
        self.assertIn("CURVE=1-0.50, 180-90.00", system_text)
        self.assertNotIn("Generated from finalized Network Wrangler inputs", system_text)
        self.assertTrue(system_text.startswith(";;<<PT>><<SYSTEM>>;;\n"))
        self.assertNotIn("SEATCAP", system_text)
        self.assertEqual(report["lines_without_vehicle_mapping"], [])
        self.assertEqual(
            report["line_vehicle_assignments"][0]["distinct_vehicle_names"],
            ["Standard Bus"],
        )
        self.assertEqual(
            report["line_vehicle_assignments"][0]["am_vehicle"], "Standard Bus"
        )
        self.assertEqual(
            report["operator_definitions"],
            [
                {
                    "number": 7,
                    "name": "BWAY SHUTTLE",
                    "long_name": "Broadway Shuttle",
                }
            ],
        )
        self.assertEqual(report["mode_definition_count"], 10)
        self.assertEqual(
            report["wait_curve_definitions"][0]["curve"],
            [[1, 0.5], [180, 90.0]],
        )


if __name__ == "__main__":
    unittest.main()
