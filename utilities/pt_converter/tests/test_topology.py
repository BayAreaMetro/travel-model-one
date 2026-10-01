from __future__ import annotations

from pathlib import Path
import csv
import json
import tempfile
import unittest

from pt_converter.line_conversion import TransitLineReader
from pt_converter.topology import TopologyWriter, TransitLinkReader


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_trn"


class TopologyTests(unittest.TestCase):
    def test_reader_expands_modes_and_two_way_links(self) -> None:
        source = TransitLinkReader().read(FIXTURE / "transitLines.link")

        self.assertEqual(len(source.links), 2)
        self.assertEqual(len(source.directed_links()), 3)
        self.assertEqual(source.links[1].modes, (10, 11, 12))
        self.assertEqual(source.directed_links()[1].from_node, 2)
        self.assertTrue(source.directed_links()[1].generated_reverse)
        self.assertEqual(source.factors[0].nodes, (2,))

    def test_writer_preserves_the_network_builder_handoff(self) -> None:
        source = TransitLinkReader().read(FIXTURE / "transitLines.link")
        lines = TransitLineReader().read(FIXTURE / "transitLines.lin")
        with tempfile.TemporaryDirectory() as temp:
            model_directory = Path(temp)
            output = model_directory / "trn" / "pt"
            result = TopologyWriter().write(source, lines, output)
            report = json.loads(result.report_path.read_text(encoding="utf-8"))
            with result.directed_links_path.open(
                encoding="utf-8", newline=""
            ) as source_file:
                directed = list(csv.DictReader(source_file))

        self.assertEqual(report["source_link_count"], 2)
        self.assertEqual(report["directed_link_count"], 3)
        self.assertEqual(report["time_rule_count"], 1)
        self.assertEqual(report["speed_rule_count"], 1)
        self.assertEqual(
            {(row["A"], row["B"]) for row in directed},
            {("1", "2"), ("2", "1"), ("2", "3")},
        )


if __name__ == "__main__":
    unittest.main()
