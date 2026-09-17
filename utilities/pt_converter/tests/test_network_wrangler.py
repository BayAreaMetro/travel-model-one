from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from pt_converter.inventory import NetworkWranglerInputReader


class NetworkWranglerInputReaderTests(unittest.TestCase):
    def make_source_directory(self, root: Path) -> Path:
        source = root / "INPUT" / "trn"
        source.mkdir(parents=True)
        return source

    def test_inventory_classifies_files_and_preserves_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model_directory = Path(temp)
            source = self.make_source_directory(model_directory)
            (source / "transitLines.lin").write_text(
                'LINE NAME="B_LINE", MODE=12, OPERATOR=2, FREQ[1]=10, FREQ[5]=20, N=1,2\n'
                'LINE NAME="A_LINE", MODE=11, OPERATOR=1, FREQ[1]=15, N=3,-4\n',
                encoding="utf-8",
            )
            (source / "transitLines.access").write_text("1 2\n", encoding="utf-8")
            (source / "transitLines_AM.pnr").write_text("1 3\n", encoding="utf-8")
            (source / "BART.far").write_text("1,2,3\n", encoding="utf-8")
            (source / "transitLineToVehicle.csv").write_text(
                "line,vehicle\nTEST,BUS\n", encoding="utf-8"
            )
            (source / "transitPrefixToVehicle.csv").write_text(
                "prefix,vehicle\nTEST,BUS\n", encoding="utf-8"
            )

            inventory = NetworkWranglerInputReader().inspect(model_directory)
            lines = NetworkWranglerInputReader().read_transit_lines(
                source / "transitLines.lin"
            )
            payload = inventory.to_dict()

        self.assertEqual(payload["source_directory"], "INPUT/trn")
        self.assertEqual(payload["transit_lines"]["names"], ["A_LINE", "B_LINE"])
        self.assertEqual(payload["transit_lines"]["modes"], [11, 12])
        self.assertEqual(payload["transit_lines"]["operators"], [1, 2])
        self.assertEqual(payload["transit_lines"]["headway_periods"], [1, 5])
        self.assertEqual(lines[0].source_path, "transitLines.lin")
        self.assertEqual(lines[0].source_line, 1)
        self.assertEqual(lines[1].source_line, 2)
        types = {item["path"]: item["type"] for item in payload["files"]}
        self.assertEqual(types["transitLines.access"], "walk_access_connectors")
        self.assertEqual(types["transitLines_AM.pnr"], "park_and_ride_connectors")
        self.assertEqual(types["BART.far"], "fare")
        self.assertEqual(types["transitLineToVehicle.csv"], "line_to_vehicle")
        self.assertEqual(types["transitPrefixToVehicle.csv"], "prefix_to_vehicle")
        paths = [item["path"] for item in payload["files"]]
        self.assertEqual(paths, sorted(paths, key=str.casefold))

    def test_missing_transit_lines_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model_directory = Path(temp)
            self.make_source_directory(model_directory)

            inventory = NetworkWranglerInputReader().inspect(model_directory)

        self.assertEqual(inventory.transit_lines.count, 0)
        self.assertEqual(inventory.issues[0].code, "MISSING_TRANSIT_LINES")

    def test_inventory_serialization_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model_directory = Path(temp)
            source = self.make_source_directory(model_directory)
            (source / "transitLines.lin").write_text(
                'LINE NAME="TEST", MODE=11, FREQ[1]=10, N=1,2\n', encoding="utf-8"
            )
            reader = NetworkWranglerInputReader()

            first = json.dumps(reader.inspect(model_directory).to_dict(), sort_keys=True)
            second = json.dumps(reader.inspect(model_directory).to_dict(), sort_keys=True)

        self.assertEqual(first, second)
