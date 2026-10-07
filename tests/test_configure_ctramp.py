"""Tests for configure_ctramp's property parsing, patching and workbook edits.

The reference-run comparison covers the happy path end to end.  These cover the
semantics it cannot: the legacy regex quirks that are deliberately preserved,
the per-key format strings, and the failure modes that must be loud.
"""

from pathlib import Path

import pandas as pd
import pytest

from tm1.steps import configure_ctramp
from tm1.steps.configure_ctramp import (
    ConfigurationError,
    check_tazdata,
    get_property,
    patch_keys,
    write_occupancy_factors,
)

PARAMS = """# a comment
AutoOpCost      = 15.44
SmTruckOpCost   = 30.88
Mobility.AV.Share = 0
WFH_Calibration_constant = -0.340
Means_Based_Fare_PctOfPoverty_Threshold = 200
Taxi.da.share = 0.0
Taxi.s2.share = 0.53
Taxi.s3.share = 0.47
TNC.single.da.share = 0.0
TNC.single.s2.share = 0.53
TNC.single.s3.share = 0.47
TNC.shared.da.share = 0.0
TNC.shared.s2.share = 0.18
TNC.shared.s3.share = 0.82
"""


def test_get_property_reads_value() -> None:
    """A plain key returns its value as text."""
    assert get_property(PARAMS, "AutoOpCost") == "15.44"
    assert get_property(PARAMS, "WFH_Calibration_constant") == "-0.340"


def test_get_property_missing_is_fatal() -> None:
    """A missing property raises rather than defaulting -- silence would change results."""
    with pytest.raises(ConfigurationError, match="Nonexistent"):
        get_property(PARAMS, "Nonexistent")


def test_get_property_ignores_first_line() -> None:
    """The legacy pattern needs a leading newline, so a first-line key is invisible.

    Preserved deliberately: params.properties opens with a comment, so no real
    property is ever on line 1, and changing this would alter which keys resolve.
    """
    with pytest.raises(ConfigurationError):
        get_property("FirstLineKey = 5\nOther = 6\n", "FirstLineKey")


def test_patch_keys_is_case_insensitive_and_patches_every_match(tmp_path: Path) -> None:
    """IGNORECASE is load-bearing: Model_Year must also update MODEL_YEAR.

    The real mtcTourBased.properties carries both spellings and the reference run
    has both set to the model year, so an anchored or case-sensitive regex would
    silently leave the second one stale.
    """
    p = tmp_path / "x.properties"
    p.write_text("intro = 1\nModel_Year   = set_by_script\nMODEL_YEAR = 1999\n")
    patch_keys(p, {"Model_Year": "2023"})
    text = p.read_text()
    assert "Model_Year   = 2023" in text
    assert "MODEL_YEAR = 2023" in text


def test_patch_keys_no_match_is_fatal(tmp_path: Path) -> None:
    """A key that matches nothing is an error, never a silent no-op."""
    p = tmp_path / "x.properties"
    p.write_text("intro = 1\nSomeKey = 2\n")
    with pytest.raises(ConfigurationError, match="no line matched"):
        patch_keys(p, {"AbsentKey": "9"})


def test_patch_keys_preserves_surroundings(tmp_path: Path) -> None:
    """Only the value changes -- spacing, comments and other lines survive."""
    p = tmp_path / "x.block"
    p.write_text("intro\nAUTOOPC = xx.xx     ; year 2000 cents\nOTHER = keep\n")
    patch_keys(p, {"AUTOOPC": "15.44"})
    assert p.read_text() == (
        "intro\nAUTOOPC = 15.44     ; year 2000 cents\nOTHER = keep\n"
    )


@pytest.mark.parametrize(
    ("raw", "spec", "expected"),
    [
        ("15.44", ".2f", "15.44"),
        ("0", ".2f", "0.00"),
        ("-0.340", ".3f", "-0.340"),
        ("5.000", ".3f", "5.000"),
        ("200", "d", "200"),
        ("30.88", "", "30.88"),  # copied through, not reformatted
        ("0.5", "", "0.5"),
    ],
)
def test_format_matches_legacy(raw: str, spec: str, expected: str) -> None:
    """Per-key formats reproduce the legacy %-strings exactly."""
    assert configure_ctramp._format(raw, spec) == expected  # noqa: SLF001


def test_write_occupancy_factors(tmp_path: Path) -> None:
    """Three rows in the legacy's %5.2f fixed width, occupancy-major."""
    out = tmp_path / "taxi_tnc_occ_factors.csv"
    write_occupancy_factors(PARAMS, out)
    assert out.read_text().splitlines() == [
        "1, 0.00, 0.00, 0.00",
        "2, 0.53, 0.53, 0.18",
        "3, 0.47, 0.47, 0.82",
    ]


def _tazdata(tmp_path: Path, cordon: int, cost: float) -> Path:
    p = tmp_path / "tazData.csv"
    pd.DataFrame({"ZONE": [1, 2], "CORDON": [cordon, cordon],
                  "CORDONCOST": [cost, cost]}).to_csv(p, index=False)
    return p


def _tolls(tmp_path: Path, tollclass: int, tollam_da: float) -> Path:
    p = tmp_path / "tolls.csv"
    pd.DataFrame({"tollclass": [tollclass], "tolltype": ["cordon"],
                  "tollam_da": [tollam_da]}).to_csv(p, index=False)
    return p


def test_check_tazdata_accepts_consistent_cordon(tmp_path: Path) -> None:
    """CORDONCOST is in cents, tollam_da in dollars; 300 cents == $3.00."""
    check_tazdata(_tazdata(tmp_path, 10, 300.0), _tolls(tmp_path, 10, 3.0))


def test_check_tazdata_rejects_inconsistent_cordon(tmp_path: Path) -> None:
    """A cordon priced differently in the two files is a hard stop."""
    with pytest.raises(ConfigurationError, match="does not match"):
        check_tazdata(_tazdata(tmp_path, 10, 300.0), _tolls(tmp_path, 10, 5.0))


def test_check_tazdata_requires_columns(tmp_path: Path) -> None:
    """Missing CORDON/CORDONCOST columns fail before anything is patched."""
    p = tmp_path / "tazData.csv"
    pd.DataFrame({"ZONE": [1]}).to_csv(p, index=False)
    with pytest.raises(ConfigurationError, match="CORDON"):
        check_tazdata(p, _tolls(tmp_path, 10, 3.0))


def test_check_tazdata_no_cordons_is_fine(tmp_path: Path) -> None:
    """No cordon toll classes means nothing to cross-check (the 2023 base case)."""
    p = tmp_path / "tolls.csv"
    pd.DataFrame({"tollclass": [2001], "tolltype": ["bridge"],
                  "tollam_da": [3.5]}).to_csv(p, index=False)
    check_tazdata(_tazdata(tmp_path, 10, 300.0), p)


def test_patch_workbook_round_trip(tmp_path: Path) -> None:
    """Writing a marker cell survives the xlrd -> xlwt round-trip and reopens."""
    xlwt = pytest.importorskip("xlwt")
    xlrd = pytest.importorskip("xlrd")

    book = xlwt.Workbook()
    sheet = book.add_sheet("Sheet1")
    sheet.write(0, 1, "costPerMile")
    sheet.write(0, 4, 1.11)
    sheet.write(1, 1, "other")
    sheet.write(1, 4, 2.22)
    path = tmp_path / "book.xls"
    book.save(str(path))

    hits = configure_ctramp._patch_workbook(  # noqa: SLF001
        path, 1, "costPerMile", 4, 15.44, "align: horiz left"
    )
    assert hits == 1

    reread = xlrd.open_workbook(str(path))
    sheet0 = reread.sheet_by_index(0)
    assert sheet0.cell(0, 4).value == pytest.approx(15.44)
    assert sheet0.cell(1, 4).value == pytest.approx(2.22)  # untouched


def test_patch_workbook_missing_marker_is_fatal(tmp_path: Path) -> None:
    """A workbook with no marker cell means the layout changed -- fail loudly."""
    xlwt = pytest.importorskip("xlwt")
    book = xlwt.Workbook()
    book.add_sheet("Sheet1").write(0, 1, "somethingElse")
    path = tmp_path / "book.xls"
    book.save(str(path))

    with pytest.raises(ConfigurationError, match="no cell in column"):
        configure_ctramp._patch_workbook(  # noqa: SLF001
            path, 1, "costPerMile", 4, 15.44, "align: horiz left"
        )
