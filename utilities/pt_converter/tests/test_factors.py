from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from pt_converter.factors import FactorWriter, tm1_factor_source


class FactorWriterTests(unittest.TestCase):
    def test_tm1_catalog_has_fifteen_time_independent_classes(self) -> None:
        source = tm1_factor_source()

        self.assertEqual(len(source.classes), 15)
        self.assertEqual(source.classes[0].name, "wlk_loc_wlk")
        self.assertEqual(source.classes[4].name, "wlk_com_wlk")
        self.assertEqual(source.classes[5].name, "drv_loc_wlk")
        self.assertEqual(source.classes[14].name, "wlk_com_drv")

    def test_writer_translates_mode_and_access_factors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            result = FactorWriter().write(tm1_factor_source(), output, 9999)

            self.assertEqual(result.factor_count, 15)
            local = (output / "wlk_loc_wlk.fac").read_text(encoding="utf-8")
            self.assertEqual(
                local,
                ";;<<PT>><<FACTORS>>;;\n"
                "; User class 1: wlk/loc/wlk\n"
                "RUNFACTOR=9*2.0,70*1.0,20*1.5,10*1.5,10*1.5,10*1.5,10*1.5\n"
                "DELMODE=80-139\n"
                "DELACCESSMODE=2,6,7\n"
                "DELEGRESSMODE=1,2,7\n"
                "IWAITCURVE=1, NODES=1-9999\n"
                "XWAITCURVE=1, NODES=1-9999\n"
                "WAITFACTOR=2.8, NODES=1-9999\n"
                "SERVICEMODEL=FREQUENCY\n",
            )
            commuter = (output / "drv_com_wlk.fac").read_text(encoding="utf-8")
            self.assertNotIn("DELMODE", commuter)
            self.assertIn("DELACCESSMODE=1,6,7", commuter)
            report = json.loads(result.report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["factor_file_count"], 15)
            self.assertFalse(report["time_period_specific"])
            self.assertIn("BOARDPEN", report["not_directly_translated"])


if __name__ == "__main__":
    unittest.main()
