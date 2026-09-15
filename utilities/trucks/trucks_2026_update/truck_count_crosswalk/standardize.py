"""Flatten Caltrans annual truck AADT Excel workbooks into one CSV.

Caltrans publishes one workbook per year in two incompatible layouts:

legacy (2018 and earlier)
    No usable header row.  Columns sit in the fixed order given by
    ``LEGACY_LAYOUT`` and data starts on row 4.  Postmile ("R12.345") and
    verification ("2016 V") are each packed into a single cell.

modern (2019 onward)
    A header row of abbreviated names (RTE, TOT_TRK_AADT, ...) that vary from
    year to year, with postmile and verification split across own columns.

Both are read into the single output schema declared in ``SCHEMA``: one row per
count location per report year, written to a long CSV.

Point geometry comes from the separately published Caltrans truck AADT layer
(a GeoJSON of the same locations), joined on route and postmile so the counts
can be mapped.  That layer is a single-year snapshot, so coverage of the older
report years is partial; see ``read_locations``.

Processing order
----------------
build
    -> read_locations               (GeoJSON point layer, indexed by location)
    -> read_legacy / read_modern    (one workbook, dispatched on report year)
        -> data_sheet               (largest worksheet in the workbook)
        -> to_record                (provenance stamp + schema type coercion)
    -> add_locations                (attach longitude/latitude by location key)
    -> drop_repeated_rows           (collapse verbatim repeats of a printed row)
    -> flag_quality                 (mark suspect rows; never change a value)
    -> write to CSV, warn on missing report years
"""

import argparse
import csv
import json
import re
import sys
import warnings
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


import paths

EXPECTED_YEARS = set(range(2013, 2025))

# Postmile cells look like "R12.345" or "12.345M": optional alpha prefix, a
# signed decimal, optional alpha suffix.
POSTMILE_RE = re.compile(
    r"^\s*([A-Za-z]*)\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*([A-Za-z]*)\s*$"
)
# Legacy verification cells look like "2016 V" or "16" (code omitted).
VERIFICATION_RE = re.compile(r"(\d{1,4})\s*([A-Za-z])?")


def as_text(value: Any) -> str:
    """Collapse a cell to a whitespace-normalized string; ``None`` becomes ``""``."""
    return "" if value is None else re.sub(r"\s+", " ", str(value)).strip()


def as_float(value: Any) -> float | None:
    """Parse a cell as a float, tolerating thousands separators; blank becomes ``None``."""
    text = as_text(value).replace(",", "")
    return float(text) if text else None


def as_int(value: Any) -> int | None:
    """Parse a cell as a rounded integer; blank becomes ``None``."""
    number = as_float(value)
    return None if number is None else int(round(number))


@dataclass(frozen=True)
class Column:
    """One output column: its canonical name, value parser, and source spellings.

    ``aliases`` are the modern header abbreviations that map onto this column;
    columns with no aliases are derived during parsing rather than read directly.
    """

    name: str
    parse: Callable[[Any], Any] = as_text
    aliases: tuple[str, ...] = field(default=())


# The output schema, in CSV column order.  This is the single source of truth
# for the column list, their types, and the header aliases they answer to.
SCHEMA: tuple[Column, ...] = (
    Column("report_year", as_int),
    Column("route", as_int, ("RTE",)),
    Column("route_suffix", aliases=("RTE_SFX",)),
    Column("district", as_int, ("DIST",)),
    Column("county", aliases=("CNTY",)),
    Column("postmile_prefix", aliases=("POSTMILE_PFX", "PM_PFX")),
    Column("postmile", as_float, ("POSTMILE",)),
    Column("postmile_suffix", aliases=("POSTMILE_SFX", "PM_SFX")),
    Column("postmile_raw"),
    Column("leg", aliases=("LEG",)),
    Column("description", aliases=("DESCRIPTION",)),
    Column("longitude", as_float),
    Column("latitude", as_float),
    Column("vehicle_aadt", as_int, ("VEHICLE_AADT_TOTAL",)),
    Column("truck_aadt", as_int, ("TRUCK_AADT_TOTAL", "TOT_TRK_AADT")),
    Column("truck_percent_total", as_float, ("TRK_PERCENT_TOT",)),
    Column("truck_2_axle_aadt", as_int, ("TRK_2_AXLE",)),
    Column("truck_3_axle_aadt", as_int, ("TRK_3_AXLE",)),
    Column("truck_4_axle_aadt", as_int, ("TRK_4_AXLE",)),
    Column("truck_5_plus_axle_aadt", as_int, ("TRK_5_AXLE",)),
    Column("truck_2_axle_percent", as_float, ("TRK_2_AXLE_PCT",)),
    Column("truck_3_axle_percent", as_float, ("TRK_3_AXLE_PCT",)),
    Column("truck_4_axle_percent", as_float, ("TRK_4_AXLE_PCT",)),
    Column("truck_5_plus_axle_percent", as_float, ("TRK_5_AXLE_PCT",)),
    Column("eal_2way_thousands", as_float, ("EAL",)),
    Column("verification_year", as_int, ("YEAR_VER", "EST_YEAR", "EST/VER_YEAR")),
    Column("verification_code", aliases=("EST", "EST_CODE", "EST/VER_CODE")),
    Column("verification_status"),
    Column("source_file"),
    Column("source_sheet"),
    Column("source_row", as_int),
    Column("quality_flags"),
)

COLUMNS = [column.name for column in SCHEMA]
HEADER_ALIASES = {alias: column.name for column in SCHEMA for alias in column.aliases}
PARSE_BY_NAME = {column.name: column.parse for column in SCHEMA}
REQUIRED_MODERN = {"route", "district", "county", "postmile", "truck_aadt"}

# Identifies a physical count location, and so the columns the GeoJSON point
# layer is joined on.  Caltrans reuses route/postmile across years, but does
# realign postmiles occasionally, which is why older years match less well.
JOIN_KEY = (
    "route", "route_suffix", "district", "county",
    "postmile_prefix", "postmile", "postmile_suffix", "leg",
)

# Fixed column order of the legacy sheets, which carry no usable header row.
# "verification_raw" is the combined "<year> <code>" cell, split during parsing.
LEGACY_LAYOUT: tuple[str, ...] = (
    "route", "district", "county", "postmile_raw", "leg", "description",
    "vehicle_aadt", "truck_aadt", "truck_percent_total", "truck_2_axle_aadt",
    "truck_3_axle_aadt", "truck_4_axle_aadt", "truck_5_plus_axle_aadt",
    "truck_2_axle_percent", "truck_3_axle_percent", "truck_4_axle_percent",
    "truck_5_plus_axle_percent", "eal_2way_thousands", "verification_raw",
)


# Quality thresholds.  A published truck percentage that disagrees with
# truck / vehicle by more than this many points means one of the three columns
# is wrong; a year this far from its own location's median is not traffic.
PERCENT_TOLERANCE = 2.0
SERIES_RATIO = 3.0

# Columns recording where a row came from rather than what it says.  Two rows
# that differ only in these are the same published figure printed twice.
PROVENANCE = frozenset({"source_file", "source_sheet", "source_row", "quality_flags"})


def drop_repeated_rows(records: list[dict[str, Any]]) -> int:
    """Remove rows that repeat an earlier row verbatim; return how many went.

    Caltrans occasionally prints a location twice on adjacent rows of the same
    workbook -- the Caldecott Tunnel in 2013, Route 90 at Anaheim in 2014 and
    2015, Route 135 at Santa Maria in 2021 and 2022.  Every published figure
    agrees down to the axle counts, so collapsing them loses nothing.

    Only *verbatim* repeats go.  A location-year that appears twice with
    different numbers is a genuine conflict, is left alone here, and is marked
    ``duplicate_row`` by ``flag_quality`` for someone to look at.
    """
    signatures, kept, dropped = set(), [], 0
    for record in records:
        signature = tuple(
            value for name, value in record.items() if name not in PROVENANCE
        )
        if signature in signatures:
            dropped += 1
            continue
        signatures.add(signature)
        kept.append(record)
    records[:] = kept
    return dropped


def flag_quality(records: list[dict[str, Any]]) -> dict[str, int]:
    """Mark suspect rows in place and return a tally by flag.

    Every flag is a statement about the *published* numbers, never a
    correction: Caltrans gives three related figures per row, so when they
    disagree the row is marked and left exactly as it was published.  Deciding
    which figure is wrong, and whether to act on it, is not this script's call.
    """
    tally: dict[str, int] = {}

    def mark(record, flag):
        record.setdefault("_flags", []).append(flag)
        tally[flag] = tally.get(flag, 0) + 1

    # Row-level: the three published figures should agree with each other.
    for record in records:
        vehicles, trucks = record["vehicle_aadt"], record["truck_aadt"]
        percent = record["truck_percent_total"]
        if vehicles and trucks is not None and trucks > vehicles:
            mark(record, "truck_exceeds_vehicle")
        if vehicles and trucks is not None and percent:
            implied = trucks / vehicles * 100.0
            if abs(implied - percent) > PERCENT_TOLERANCE:
                mark(record, "percent_disagrees")
        if percent and trucks == 0:
            mark(record, "zero_trucks_with_percent")

    # Series-level: compare each year against its own neighbours, which
    # separates two things a median comparison confuses.  One year unlike both
    # of its neighbours is an outlier -- Route 1 in Monterey reads 490,200 in
    # 2018 between years near 48,000.  A change that *persists* is a level
    # shift: Route 160 steps from 11,000 to 37,000 in 2018 and stays there, and
    # Route 116 sits at 12,700 for exactly three years before returning to
    # 3,100.  Neither is a typo, and neither side is declared wrong here.
    series: dict[tuple, list] = {}
    for record in records:
        key = tuple(record[name] for name in JOIN_KEY)
        series.setdefault(key, []).append(record)
    for members in series.values():
        seen_years: dict[int, int] = {}
        for record in members:
            year = record["report_year"]
            seen_years[year] = seen_years.get(year, 0) + 1
        ordered = sorted(members, key=lambda r: r["report_year"])
        values = [r["vehicle_aadt"] for r in ordered]
        for index, record in enumerate(ordered):
            if seen_years.get(record["report_year"], 0) > 1:
                mark(record, "duplicate_row")
            value = values[index]
            if not value or len(ordered) < 4:
                continue
            previous = values[index - 1] if index else None
            following = values[index + 1] if index + 1 < len(values) else None
            if previous and following:
                high = value > SERIES_RATIO * previous and value > SERIES_RATIO * following
                low = value * SERIES_RATIO < previous and value * SERIES_RATIO < following
                if high or low:
                    mark(record, "single_year_outlier")
                    continue
            if not previous:
                continue
            stepped = value > SERIES_RATIO * previous or value * SERIES_RATIO < previous
            # A step only counts if the new level holds, rather than snapping back.
            holds = following is None or abs(value - following) < abs(previous - following)
            if stepped and holds:
                mark(record, "level_shift")

    for record in records:
        record["quality_flags"] = "; ".join(record.pop("_flags", []))
    return tally


def year_from_filename(path: Path) -> int:
    """Return the four-digit report year embedded in a workbook filename."""
    match = re.search(r"(?:19|20)\d{2}", path.name)
    if not match:
        raise ValueError(f"No report year in filename: {path.name}")
    return int(match.group())


@contextmanager
def data_sheet(path: Path) -> Generator[Any, None, None]:
    """Yield a workbook's largest worksheet (by cell count), closing it afterwards.

    Caltrans workbooks carry cover sheets and notes tabs alongside the data;
    the data tab is reliably the biggest one.
    """
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        yield max(workbook.worksheets, key=lambda sheet: sheet.max_row * sheet.max_column)
    finally:
        workbook.close()


def canonical_name(header: Any) -> str | None:
    """Resolve a source header or GeoJSON property name to its schema column name.

    Returns ``None`` for anything the schema does not claim, which is how both
    the modern reader and the point layer discard columns they do not need.
    """
    return HEADER_ALIASES.get(as_text(header).upper().replace(" ", "_"))


def location_key(values: Mapping[str, Any]) -> tuple[Any, ...]:
    """Build the tuple identifying a count location, for joining counts to points.

    Both sides of the join are put through the same schema parsers and the same
    upper-casing here, so a location resolves to an equal key whether it came
    from a workbook cell, a CSV field, or a GeoJSON property.
    """
    key = []
    for name in JOIN_KEY:
        value = PARSE_BY_NAME[name](values.get(name))
        key.append(value.upper() if isinstance(value, str) else value)
    return tuple(key)


def is_data_row(route: Any) -> bool:
    """Report whether a row's route cell holds a number, marking it as real data.

    Both layouts interleave titles, notes, and blank separators with the data.
    """
    try:
        return as_text(route) != "" and as_int(route) is not None
    except ValueError:
        return False


def parse_postmile(value: Any) -> tuple[str, float, str, str]:
    """Split a packed postmile cell into ``(prefix, postmile, suffix, normalized)``."""
    raw = as_text(value).replace(" ", "").upper()
    match = POSTMILE_RE.fullmatch(raw)
    if not match:
        raise ValueError(f"Unrecognized postmile: {value!r}")
    prefix, number, suffix = match.groups()
    return prefix, float(number), suffix, raw


def parse_verification(year: Any, code: Any, report_year: int) -> tuple[int | None, str, str]:
    """Resolve a verification year/code pair into ``(year, code, status)``.

    Years are written with either two or four digits; a two-digit year is read
    as 20xx unless that would postdate the report year, in which case 19xx.
    The code is ``V`` (field verified) or ``E`` (estimated); anything else,
    including a blank, is reported as ``"unknown"``.
    """
    code = as_text(code).upper()[:1]
    status = {"V": "verified", "E": "estimated"}.get(code, "unknown")
    year = as_int(year)
    if year is not None and year < 100:
        year = 2000 + year if 2000 + year <= report_year + 1 else 1900 + year
    return year, code, status


def to_record(values: dict[str, Any], path: Path, sheet: Any, row_number: int, year: int) -> dict[str, Any]:
    """Stamp provenance onto a parsed row and coerce every column to its schema type.

    Keys absent from ``values`` (columns a given layout does not supply) come
    through as the parser's empty value: ``""`` for text, ``None`` for numbers.
    """
    values.update(
        report_year=year, source_file=path.name,
        source_sheet=sheet.title, source_row=row_number,
    )
    return {column.name: column.parse(values.get(column.name)) for column in SCHEMA}


def read_legacy(path: Path, year: int) -> list[dict[str, Any]]:
    """Read a 2018-or-earlier workbook, mapping its fixed column order onto the schema."""
    records = []
    with data_sheet(path) as sheet:
        rows = sheet.iter_rows(min_row=4, max_col=len(LEGACY_LAYOUT), values_only=True)
        for row_number, values in enumerate(rows, start=4):
            if not is_data_row(values[0]):
                continue
            row = dict(zip(LEGACY_LAYOUT, values))
            prefix, postmile, suffix, postmile_raw = parse_postmile(row["postmile_raw"])
            match = VERIFICATION_RE.fullmatch(as_text(row.pop("verification_raw")))
            if not match:
                raise ValueError(f"{path.name}:{row_number}: bad verification value")
            verification_year, code, status = parse_verification(match[1], match[2], year)
            row.update(
                route_suffix="", postmile_prefix=prefix, postmile=postmile,
                postmile_suffix=suffix, postmile_raw=postmile_raw,
                verification_year=verification_year, verification_code=code,
                verification_status=status,
            )
            records.append(to_record(row, path, sheet, row_number, year))
    return records


def read_modern(path: Path, year: int) -> list[dict[str, Any]]:
    """Read a 2019-or-later workbook, resolving its header row through ``HEADER_ALIASES``.

    Unrecognized headers are dropped; a workbook missing any of
    ``REQUIRED_MODERN`` is rejected rather than silently yielding blank columns.
    """
    records = []
    with data_sheet(path) as sheet:
        rows = sheet.iter_rows(values_only=True)
        headers = [canonical_name(value) for value in next(rows)]
        missing = REQUIRED_MODERN - set(filter(None, headers))
        if missing:
            raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
        for row_number, values in enumerate(rows, start=2):
            row = {key: value for key, value in zip(headers, values) if key}
            if not is_data_row(row.get("route")):
                continue
            verification_year, code, status = parse_verification(
                row.pop("verification_year", None), row.pop("verification_code", None), year,
            )
            prefix = as_text(row.get("postmile_prefix")).upper()
            suffix = as_text(row.get("postmile_suffix")).upper()
            row.update(
                postmile_raw=f"{prefix}{as_float(row.get('postmile')):g}{suffix}",
                verification_year=verification_year, verification_code=code,
                verification_status=status,
            )
            records.append(to_record(row, path, sheet, row_number, year))
    return records


def read_locations(path: Path) -> dict[tuple[Any, ...], tuple[float, float]]:
    """Index the Caltrans truck AADT point layer by location key.

    The layer's properties use the same abbreviations as the modern workbooks,
    so they resolve through ``canonical_name``.  It publishes each location
    about twice over: the duplicates are attribute-identical but geocoded to
    slightly different points (median ~13 m apart, worst case ~490 m), so they
    are collapsed to their centroid.

    The layer is a single-year snapshot rather than a time series, which caps
    how well it covers the earlier report years.

    Returns
    -------
    dict
        Maps ``location_key(...)`` to a ``(longitude, latitude)`` pair in
        WGS 84 decimal degrees.
    """
    features = json.loads(path.read_text(encoding="utf-8"))["features"]
    points: dict[tuple[Any, ...], list[tuple[float, float]]] = {}
    for feature in features:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point":
            continue
        properties = {}
        for name, value in feature.get("properties", {}).items():
            column = canonical_name(name)
            if column:
                properties[column] = value
        longitude, latitude = geometry["coordinates"][:2]
        points.setdefault(location_key(properties), []).append((longitude, latitude))
    return {
        key: (round(sum(x for x, _ in pts) / len(pts), 6), round(sum(y for _, y in pts) / len(pts), 6))
        for key, pts in points.items()
    }


def add_locations(records: list[dict[str, Any]], locations: dict[tuple[Any, ...], tuple[float, float]]) -> int:
    """Attach longitude/latitude to each record in place; return how many matched.

    Unmatched records keep empty coordinates rather than being dropped, so the
    count series stays complete whether or not a location can be mapped.
    """
    matched = 0
    for record in records:
        longitude, latitude = locations.get(location_key(record), (None, None))
        record["longitude"], record["latitude"] = longitude, latitude
        matched += longitude is not None
    return matched


def build(input_dir: Path, output_path: Path, locations_path: Path) -> list[dict[str, Any]]:
    """Read every workbook in ``input_dir``, locate the rows, and write the combined CSV.

    One workbook per report year is expected; a duplicate year is an error and
    a gap in ``EXPECTED_YEARS`` is a warning.  Rows are sorted into a stable
    year/district/route/county/postmile/leg order.  The share of rows matched
    to a point is reported per year, since it degrades for the earlier years.
    """
    paths = sorted(input_dir.glob("*.xlsx"))
    if not paths:
        raise FileNotFoundError(f"No .xlsx files in {input_dir}")
    if not locations_path.exists():
        raise FileNotFoundError(f"No point layer at {locations_path}")

    locations = read_locations(locations_path)
    print(f"{len(locations):,} count locations <- {locations_path.name}")

    records, years, located = [], set(), 0
    for path in paths:
        year = year_from_filename(path)
        if year in years:
            raise ValueError(f"Multiple workbooks found for {year}")
        years.add(year)
        rows = (read_legacy if year <= 2018 else read_modern)(path, year)
        matched = add_locations(rows, locations)
        located += matched
        records.extend(rows)
        print(f"{year}: {len(rows):,} rows <- {path.name} ({matched / len(rows):.1%} located)")

    repeated = drop_repeated_rows(records)
    if repeated:
        print(f"dropped {repeated:,} rows repeating an earlier row verbatim")

    tally = flag_quality(records)
    if tally:
        flagged = sum(1 for row in records if row["quality_flags"])
        print(f"quality: {flagged:,} of {len(records):,} rows flagged (nothing repaired)")
        for flag, count in sorted(tally.items(), key=lambda item: -item[1]):
            print(f"  {flag:<26} {count:,}")

    records.sort(key=lambda row: (
        row["report_year"], row["district"], row["route"], row["county"],
        row["postmile"], row["leg"],
    ))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)

    missing = sorted(EXPECTED_YEARS - years)
    if missing:
        print(f"WARNING: missing report years: {missing}", file=sys.stderr)
    print(f"Wrote {len(records):,} rows to {output_path} ({located / len(records):.1%} located)")
    return records


def main() -> None:
    """Parse command-line arguments and run the build."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=paths.RAW_COUNTS)
    parser.add_argument("--output", type=Path, default=paths.COUNTS_CSV)
    parser.add_argument("--locations", type=Path, default=paths.LOCATIONS_GEOJSON,
                        help="GeoJSON point layer joined to the counts for mapping")
    args = parser.parse_args()
    build(args.input_dir.resolve(), args.output.resolve(), args.locations.resolve())


if __name__ == "__main__":
    warnings.filterwarnings("ignore", message="Unknown extension is not supported")
    warnings.filterwarnings("ignore", message="Cannot parse header or footer")
    main()
