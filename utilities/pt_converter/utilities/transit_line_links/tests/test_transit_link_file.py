from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from transit_link_file import (
    LinkFileParseError,
    build_control_rows,
    build_link_rows,
    read_source_records,
)


class TransitLinkFileTests(unittest.TestCase):
    def _read(self, content: str):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "transitLines.link"
            path.write_text(content, encoding="utf-8")
            return read_source_records(path)

    def test_links_are_directed_and_comments_are_preserved(self) -> None:
        records = self._read(
            ";################ From: source/train.tpl\n"
            "; descriptive comment\n"
            "LINK NODES=10,20, DIST=250, MODES=120-121, ONEWAY=NO, "
            "TIME=5 ; Station A - Station B\n"
        )

        rows = build_link_rows(records)

        self.assertEqual([(row["A"], row["B"]) for row in rows], [(10, 20), (20, 10)])
        self.assertEqual([row["DIRECTION"] for row in rows], [0, 1])
        self.assertEqual([row["GENERATED_REVERSE"] for row in rows], [False, True])
        self.assertEqual(rows[0]["DIST"], 250.0)
        self.assertEqual(rows[0]["DISTANCE_MILES"], 2.5)
        self.assertEqual(rows[0]["MODES"], "120-121")
        self.assertEqual(rows[0]["MODES_EXPANDED"], "120,121")
        self.assertEqual(rows[0]["EFFECTIVE_SPEED_MPH"], 30.0)
        self.assertEqual(rows[0]["SOURCE_FILE"], "source/train.tpl")
        self.assertEqual(rows[0]["COMMENT"], "Station A - Station B")
        self.assertIn("descriptive comment", rows[0]["LEADING_COMMENTS"])

    def test_speed_and_unknown_attributes_are_preserved(self) -> None:
        records = self._read(
            "LINK NODES=1,2, DIST=100, MODES=30, ONEWAY=YES, "
            "SPEED=25, CUSTOM=value\n"
        )
        row = build_link_rows(records)[0]

        self.assertEqual(row["SPEED"], 25.0)
        self.assertIsNone(row["TIME"])
        self.assertEqual(row["EFFECTIVE_SPEED_MPH"], 25.0)
        self.assertEqual(row["CUSTOM"], "value")

    def test_factor_is_written_to_control_rows(self) -> None:
        records = self._read("FACTOR MAXWAITTIME=1, NODES=15536 ; control\n")
        controls = build_control_rows(records)

        self.assertEqual(len(controls), 1)
        self.assertEqual(controls[0]["RECORD_TYPE"], "FACTOR")
        self.assertEqual(controls[0]["MAXWAITTIME"], "1")
        self.assertEqual(controls[0]["NODES"], "15536")
        self.assertEqual(controls[0]["COMMENT"], "control")

    def test_missing_required_link_attribute_fails(self) -> None:
        records = self._read("LINK NODES=1,2, MODES=30, ONEWAY=YES, TIME=1\n")
        with self.assertRaisesRegex(LinkFileParseError, "missing: DIST"):
            build_link_rows(records)


if __name__ == "__main__":
    unittest.main()
