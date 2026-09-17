from __future__ import annotations

from pathlib import Path
import csv
import json
import shutil
import tempfile
import unittest

from pt_converter.fares import FareInputReader, FareWriter
from pt_converter.line_conversion import TransitModeReader


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_trn"


class FareTests(unittest.TestCase):
    def test_flat_fare_is_assigned_only_to_transit_mode(self) -> None:
        source = FareInputReader().read(FIXTURE, {11})
        modes = TransitModeReader().read(FIXTURE / "transit_modes.csv")
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            result = FareWriter().write(source, modes, {11}, output)

            self.assertEqual(result.fare_system_by_mode, {11: 1})
            fares = result.fare_path.read_text(encoding="utf-8")
            self.assertIn("FARESYSTEM NUMBER=1", fares)
            self.assertIn("STRUCTURE=FLAT", fares)
            self.assertIn("IBOARDFARE=100", fares)
            report = json.loads(result.report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["fare_system_assignment"], "MODE only")
            self.assertEqual(report["nontransit_modes_assigned"], [])

    def test_od_fare_uses_network_node_numbers_as_fare_zones(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source_directory = Path(temp) / "source"
            shutil.copytree(FIXTURE, source_directory)
            (source_directory / "transit_faremat.block").write_text(
                'FAREMATI[11]="@token_model_dir@\\trn\\Test.far"\n',
                encoding="utf-8",
            )
            (source_directory / "Test.far").write_text(
                "100 200 250 ; example OD fare\n", encoding="utf-8"
            )
            source = FareInputReader().read(source_directory, {11})
            modes = TransitModeReader().read(source_directory / "transit_modes.csv")
            output = Path(temp) / "output"

            result = FareWriter().write(source, modes, {11}, output)

            fares = result.fare_path.read_text(encoding="utf-8")
            self.assertIn("STRUCTURE=FROMTO", fares)
            self.assertIn("FAREMATRIX=FMI.1.FMTEST", fares)
            self.assertIn("FAREZONES=NI.N", fares)
            with (output / "fareMatrix_Test.csv").open(
                newline="", encoding="utf-8"
            ) as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["FROM_FARE_ZONE"], "100")
            self.assertEqual(rows[0]["TO_FARE_ZONE"], "200")
            self.assertEqual(rows[0]["FARE"], "250")
            self.assertFalse((output / "fareZoneCrosswalk.csv").exists())

    def test_legacy_one_unit_sentinel_becomes_free_service(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source_directory = Path(temp) / "source"
            shutil.copytree(FIXTURE, source_directory)
            xfare = (source_directory / "xfare.far").read_text(encoding="utf-8")
            xfare = xfare.replace("10*0,100", "10*0,1")
            (source_directory / "xfare.far").write_text(xfare, encoding="utf-8")
            source = FareInputReader().read(source_directory, {11})
            modes = TransitModeReader().read(source_directory / "transit_modes.csv")
            output = Path(temp) / "output"

            result = FareWriter().write(source, modes, {11}, output)

            fares = result.fare_path.read_text(encoding="utf-8")
            self.assertIn("STRUCTURE=FREE", fares)
            self.assertNotIn("IBOARDFARE=1", fares)
            self.assertNotIn("FAREFROMFS=", fares)
            report = json.loads(result.report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["structures"]["FREE"], 1)

    def test_factor_writer_rejects_nt_fare_assignment(self) -> None:
        from pt_converter.errors import ValidationError
        from pt_converter.factors import FactorWriter, tm1_factor_source

        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValidationError, "NT mode 1"):
                FactorWriter().write(
                    tm1_factor_source(), Path(temp), 100, fare_system_by_mode={1: 1}
                )


if __name__ == "__main__":
    unittest.main()
