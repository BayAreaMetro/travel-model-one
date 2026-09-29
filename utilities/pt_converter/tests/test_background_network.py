from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

from pt_converter.background_network import BackgroundNetworkReader, BackgroundNetworkWriter


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_trn"


class BackgroundNetworkTests(unittest.TestCase):
    def test_reader_preserves_comments_and_source_values(self) -> None:
        source = BackgroundNetworkReader().read(FIXTURE)

        self.assertEqual(len(source.access_links), 1)
        self.assertEqual(source.access_links[0].context.comment, "station access")
        self.assertEqual(len(source.transfer_links), 2)
        self.assertEqual(str(source.transfer_links[1].distance_miles), "0.00")
        self.assertEqual(len(source.transit_only_links), 2)
        self.assertEqual(source.transit_only_links[0].context.leading_comments[0],
                         "A bidirectional fixed-time link and one directional speed-based link.")
        self.assertEqual(len(source.transit_link_controls), 1)

    def test_writer_creates_three_standardized_link_files(self) -> None:
        source = BackgroundNetworkReader().read(FIXTURE)
        with tempfile.TemporaryDirectory() as temp:
            result = BackgroundNetworkWriter().write(source, Path(temp))
            with result.access_path.open(encoding="utf-8", newline="") as stream:
                access = list(csv.DictReader(stream))
            with result.transfer_path.open(encoding="utf-8", newline="") as stream:
                transfers = list(csv.DictReader(stream))
            with result.transit_only_path.open(encoding="utf-8", newline="") as stream:
                transit_only = list(csv.DictReader(stream))
            report = json.loads(result.report_path.read_text(encoding="utf-8"))

        self.assertEqual(access[0]["A"], "100")
        self.assertNotIn("REV", access[0])
        self.assertEqual(transfers[1]["DISTANCE"], "0.00")
        self.assertEqual(
            {(row["A"], row["B"]) for row in transit_only},
            {("1", "2"), ("2", "1"), ("2", "3")},
        )
        reverse = next(row for row in transit_only if row["A"] == "2" and row["B"] == "1")
        self.assertEqual(reverse["GENERATED_REVERSE"], "Y")
        self.assertIn("bidirectional fixed-time", reverse["LEADING_COMMENTS"])
        self.assertEqual(report["access_link_count"], 1)
        self.assertEqual(report["transit_only_directed_link_count"], 3)


if __name__ == "__main__":
    unittest.main()
