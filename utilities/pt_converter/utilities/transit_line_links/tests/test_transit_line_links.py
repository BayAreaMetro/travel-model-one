from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from transit_line_links import LineParseError, build_route_links, read_transit_lines


class TransitLineLinkTests(unittest.TestCase):
    def _read(self, content: str):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "routes.lin"
            path.write_text(content, encoding="utf-8")
            return read_transit_lines(path)

    def test_negative_nodes_and_two_way_route(self) -> None:
        lines = self._read(
            'LINE NAME="TEST", MODE=30, OWNER=1, ONEWAY=FALSE,\n'
            '    N=1,2,4,-6,-7\n'
        )

        links = build_route_links(lines)

        self.assertEqual(
            [(link.A, link.B, link.DIRECTION) for link in links],
            [
                (1, 2, 0),
                (2, 4, 0),
                (4, 6, 0),
                (6, 7, 0),
                (7, 6, 1),
                (6, 4, 1),
                (4, 2, 1),
                (2, 1, 1),
            ],
        )
        self.assertTrue(all(link.NAME == "TEST" for link in links))
        self.assertTrue(all(link.MODE == 30 for link in links))
        self.assertTrue(all(link.OPERATOR == 1 for link in links))

    def test_oneway_defaults_true_and_operator_keyword_is_supported(self) -> None:
        lines = self._read(
            'LINE NAME="PT LINE", MODE=120, OPERATOR=9,\n'
            '    N=10,-20,30\n'
        )

        links = build_route_links(lines)

        self.assertEqual(
            [(link.A, link.B, link.DIRECTION) for link in links],
            [(10, 20, 0), (20, 30, 0)],
        )
        self.assertEqual(links[0].OPERATOR, 9)

    def test_multiple_node_attributes_are_joined_without_attribute_values(self) -> None:
        lines = self._read(
            '; source comment with LINE NAME="NOT_A_LINE"\n'
            'LINE NAME="SEGMENTS", MODE=11, OWNER=2, ONEWAY=T,\n'
            '    N=1,2, ACCESS=2,1, N=-3,4, DELAY=0.5\n\n'
            'LINE NAME="SECOND", MODE=12, OWNER=3, N=8,9\n'
        )

        self.assertEqual(lines[0].nodes, (1, 2, -3, 4))
        self.assertEqual(len(lines), 2)
        self.assertEqual(
            [(link.A, link.B) for link in build_route_links(lines[:1])],
            [(1, 2), (2, 3), (3, 4)],
        )

    def test_repeated_nodes_are_preserved_as_self_links(self) -> None:
        lines = self._read('LINE NAME="LOOP", MODE=11, OWNER=2, N=1,1,2\n')
        links = build_route_links(lines)
        self.assertEqual([(link.A, link.B) for link in links], [(1, 1), (1, 2)])

    def test_invalid_line_fails_with_source_context(self) -> None:
        with self.assertRaisesRegex(LineParseError, "missing MODE"):
            self._read('LINE NAME="BAD", OWNER=2, N=1,2\n')

        with self.assertRaisesRegex(LineParseError, "Invalid ONEWAY"):
            self._read('LINE NAME="BAD", MODE=11, ONEWAY=MAYBE, N=1,2\n')


if __name__ == "__main__":
    unittest.main()
