from __future__ import annotations

from pathlib import Path
import csv
from decimal import Decimal
import json
import tempfile
import unittest

from pt_converter.connectors import ConnectorInputReader, ConnectorWriter


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_trn"
GOLDEN = Path(__file__).parent / "golden"


class ConnectorTestsTests(unittest.TestCase):
    def test_all_ancillary_sources_are_parsed(self) -> None:
        source = ConnectorInputReader().read(FIXTURE)

        self.assertEqual(len(source.zone_access_rules), 1)
        self.assertEqual(len(source.walk_access_legs), 1)
        self.assertEqual(len(source.pnr_facilities), 5)
        self.assertEqual(source.walk_access_legs[0].cost_minutes, 6)
        self.assertEqual(source.pnr_facilities[1].zones, "1-100,200-300")
        self.assertEqual(source.pnr_facilities[1].time_minutes, Decimal("0.01"))
        self.assertEqual(source.pnr_facilities[1].distance_miles, Decimal("0.01"))

    def test_writer_creates_pt_legs_and_source_crosswalks(self) -> None:
        source = ConnectorInputReader().read(FIXTURE)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            result = ConnectorWriter().write(source, output)

            self.assertEqual(
                result.ntleg_path.read_text(encoding="utf-8"),
                (GOLDEN / "transitAccess.NTL").read_text(encoding="utf-8"),
            )
            report = json.loads(result.report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["pt_ntleg_count"], 7)
            self.assertEqual(report["zone_access_ntleg_count"], 1)
            self.assertEqual(report["pnr_ntleg_count"], 5)
            self.assertEqual(report["pnr_facility_count"], 5)
            self.assertIn("No network was constructed", report["task_3_responsibility"])
            with (output / "pnrFacilities.csv").open(newline="", encoding="utf-8") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 5)
            self.assertFalse((output / "accessNetworkLinks.csv").exists())
            self.assertFalse((output / "transferNetworkLinks.csv").exists())


if __name__ == "__main__":
    unittest.main()
