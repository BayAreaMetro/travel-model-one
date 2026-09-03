from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from pt_converter.line_conversion import (
    PTInputWriter,
    TransitLineReader,
    VehicleCatalogReader,
)


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_trn"
GOLDEN = Path(__file__).parent / "golden"


class LineConversionTests(unittest.TestCase):
    def test_reader_preserves_line_meaning(self) -> None:
        line = TransitLineReader().read(FIXTURE / "transitLines.lin")[0]

        self.assertEqual(line.name, "TEST_BUS")
        self.assertEqual(line.mode, 11)
        self.assertEqual(line.operator, 7)
        self.assertEqual(line.nodes, (1, 2, -3))
        self.assertIn("ACCESS=2, 1", line.node_text)

    def test_writer_translates_keywords_and_capacities(self) -> None:
        lines = TransitLineReader().read(FIXTURE / "transitLines.lin")
        vehicles = VehicleCatalogReader().read(FIXTURE)
        with tempfile.TemporaryDirectory() as temp:
            result = PTInputWriter().write(lines, vehicles, Path(temp))
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
        self.assertIn('MODE NUMBER=11, NAME="MODE_11"', system_text)
        self.assertIn('OPERATOR NUMBER=7, NAME="OPERATOR_7"', system_text)
        self.assertIn('NAME="Standard Bus", CRUSHCAP=60', system_text)
        self.assertNotIn("SEATCAP", system_text)
        self.assertEqual(report["lines_without_vehicle_mapping"], [])
        self.assertEqual(
            report["line_vehicle_assignments"][0]["distinct_vehicle_names"],
            ["Standard Bus"],
        )
        self.assertEqual(
            report["line_vehicle_assignments"][0]["am_vehicle"], "Standard Bus"
        )


if __name__ == "__main__":
    unittest.main()
