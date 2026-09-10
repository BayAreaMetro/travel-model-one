"""Build source-derived parameter CSVs for airport passenger demand.
Author: Sujith Rapolu
Date: August 2026

Inputs
------
* ``parameters/`` - user-maintained configuration and assumption CSVs.
* ``input/gosling_summaries/`` - Gosling airport summary DBF files.
* ``input/TPS_TAZ_airport_TOD.xlsx`` - transit airport trips by TAZ.
* ``../../geographies/taz-superdistrict-county.csv`` - model TAZ geography.

Outputs
-------
* ``parameters/airport_non_transit_super_district_shares.csv``
* ``parameters/airport_non_transit_submode_shares.csv``
* ``parameters/airport_non_transit_zone_access_mode_shares.csv``
* ``parameters/airport_transit_zone_shares.csv``

Model year 2023 district and submode shares use the 2007 Gosling summaries;
model year 2050 uses the 2035b summaries. Non-transit within-district zonal
shares use the 2007 Gosling summaries.

Run::

    python build_parameters.py

Custom source paths are available through the command-line options shown with
``--help``.
"""

from __future__ import annotations

import argparse
import os
import re
import struct
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Default project layout
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
DEFAULT_PARAMETERS_DIR = HERE / "parameters"
DEFAULT_TAZ_LOOKUP = HERE.parent.parent / "geographies" / "taz-superdistrict-county.csv"
DEFAULT_GOSLING_DIR = HERE / "input" / "gosling_summaries"
DEFAULT_TRANSIT_SOURCE = HERE / "input" / "TPS_TAZ_airport_TOD.xlsx"

TOD_ORDER = ("EA", "AM", "MD", "PM", "EV")
ACCESS_MODES = ("ES", "PK", "RN", "TX", "LI", "VN", "HT", "CH")
AIRPORTS = ("OAK", "SFO", "SJC")
DIRECTIONS = ("from", "to")
EXPECTED_N_TAZ = 1454
SHARE_DECIMALS = 4

# Vehicle occupancies used to convert Gosling DBF vehicle-trip fields to
# person trips for Gosling-based distributions.
GOSLING_PERSONS_PER_VEHICLE = {"DA": 1.0, "S2": 2.0, "S3": 3.2}

# Source-year mapping for model-year district and submode distributions.
GOSLING_SUPER_DIST_SOURCE_BY_MODEL_YEAR = {2023: "2007", 2050: "2035b"}
GOSLING_ZONE_SHARE_SOURCE_YEAR = "2007"

# User-maintained configuration and assumption files.
INPUT_PARAMETER_FILES = {
    "airport_output_file_map": "airport_output_file_map.csv",
    "airport_passenger_targets": "airport_passenger_targets.csv",
    "vehicle_occupancy": "airport_non_transit_vehicle_occupancy.csv",
    "airport_non_transit_tod_shares": "airport_non_transit_tod_shares.csv",
    "airport_non_transit_access_mode_shares": "airport_non_transit_access_mode_shares.csv",
    "airport_transit_tod_shares": "airport_transit_tod_shares.csv",
    "airport_transit_mode_shares": "airport_transit_mode_shares.csv",
}

# Parameter files built from the source data.
OUTPUT_PARAMETER_FILES = {
    "super_district_shares": "airport_non_transit_super_district_shares.csv",
    "airport_non_transit_submode_shares": "airport_non_transit_submode_shares.csv",
    "airport_non_transit_zone_access_mode_shares": "airport_non_transit_zone_access_mode_shares.csv",
    "airport_transit_zone_shares": "airport_transit_zone_shares.csv",
}

SHARE_COLUMNS_BY_INPUT = {
    "airport_non_transit_tod_shares": ["share_tod"],
    "airport_non_transit_access_mode_shares": ["share_access_mode"],
    "airport_transit_tod_shares": ["share_tod"],
    "airport_transit_mode_shares": ["share_access_mode"],
}


# ---------------------------------------------------------------------------
# Generic validation / CSV helpers
# ---------------------------------------------------------------------------
def _read_parameter_csv(parameters_dir: Path, key: str) -> pd.DataFrame:
    path = parameters_dir / INPUT_PARAMETER_FILES[key]
    if not path.exists():
        raise FileNotFoundError(f"Required parameter file not found: {path}")
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _require_columns(df: pd.DataFrame, file_name: str, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{file_name} is missing required columns: {missing}")


def _require_no_nulls(df: pd.DataFrame, file_name: str, columns: list[str]) -> None:
    bad = [c for c in columns if df[c].isna().any()]
    if bad:
        raise ValueError(f"{file_name} has missing values in required columns: {bad}")


def _require_unique(df: pd.DataFrame, file_name: str, keys: list[str]) -> None:
    dup = df.duplicated(keys, keep=False)
    if dup.any():
        examples = df.loc[dup, keys].head(5).to_dict("records")
        raise ValueError(
            f"{file_name} must be unique by {keys}; duplicate examples: {examples}"
        )


def _normalize_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ("file_name", "airport", "tod", "access_mode", "submode"):
        if col in out.columns:
            out[col] = out[col].astype(str).str.strip()
    if "direction" in out.columns:
        out["direction"] = out["direction"].astype(str).str.strip().str.lower()
    if "year" in out.columns:
        out["year"] = pd.to_numeric(out["year"], errors="raise").astype(int)
    return out


def _validate_share_values(
    df: pd.DataFrame,
    file_name: str,
    share_columns: list[str],
    require_four_decimals: bool = True,
) -> None:
    """Validate share values and enforce the four-decimal input convention."""
    for col in share_columns:
        values = pd.to_numeric(df[col], errors="coerce")
        if values.isna().any():
            raise ValueError(f"{file_name}.{col} contains non-numeric or missing values")
        if ((values < -1e-12) | (values > 1 + 1e-12)).any():
            raise ValueError(f"{file_name}.{col} contains values outside [0, 1]")
        if require_four_decimals:
            rounded = values.round(SHARE_DECIMALS)
            if not np.allclose(values, rounded, atol=1e-12, rtol=0):
                sample = values[~np.isclose(values, rounded, atol=1e-12, rtol=0)].head(5)
                raise ValueError(
                    f"{file_name}.{col} must be rounded to four decimals; "
                    f"examples with extra precision: {sample.tolist()}"
                )
        df[col] = values.astype(float)


def _validate_group_sum(
    df: pd.DataFrame,
    file_name: str,
    group_cols: list[str],
    share_col: str,
    expected: float = 1.0,
    tolerance: float = 1e-9,
) -> None:
    sums = df.groupby(group_cols, dropna=False)[share_col].sum()
    bad = sums[~np.isclose(sums.to_numpy(dtype=float), expected, atol=tolerance, rtol=0)]
    if not bad.empty:
        raise ValueError(
            f"{file_name}.{share_col} must sum to {expected} by {group_cols} "
            f"within ±{tolerance}; failing examples: {bad.head(5).to_dict()}"
        )


def _write_share_csv(df: pd.DataFrame, path: Path, share_columns: list[str]) -> None:
    """Write a CSV with share columns visibly formatted to exactly four decimals."""
    out = df.copy()
    for col in share_columns:
        out[col] = pd.to_numeric(out[col], errors="raise").round(SHARE_DECIMALS)
        out[col] = out[col].map(lambda value: f"{value:.{SHARE_DECIMALS}f}")
    out.to_csv(path, index=False)


# ---------------------------------------------------------------------------
# Primitive parameter inputs
# ---------------------------------------------------------------------------
def load_primitive_parameters(parameters_dir: Path) -> dict[str, pd.DataFrame]:
    """Load and validate the seven user-maintained primitive parameter CSVs."""
    p = {
        key: _normalize_text(_read_parameter_csv(parameters_dir, key))
        for key in INPUT_PARAMETER_FILES
    }

    required = {
        "airport_output_file_map": [
            "file_name", "airport", "direction", "year", "airport_taz", "taz_min", "taz_max"
        ],
        "airport_passenger_targets": [
            "file_name", "airport", "direction", "year", "target"
        ],
        "vehicle_occupancy": ["submode", "conversion_factor"],
        "airport_non_transit_tod_shares": ["airport", "direction", "tod", "share_tod"],
        "airport_non_transit_access_mode_shares": [
            "airport", "direction", "access_mode", "share_access_mode"
        ],
        "airport_transit_tod_shares": ["airport", "direction", "tod", "share_tod"],
        "airport_transit_mode_shares": ["airport", "direction", "share_access_mode"],
    }
    for key, columns in required.items():
        _require_columns(p[key], INPUT_PARAMETER_FILES[key], columns)
        _require_no_nulls(p[key], INPUT_PARAMETER_FILES[key], columns)

    _require_unique(
        p["airport_output_file_map"], INPUT_PARAMETER_FILES["airport_output_file_map"], ["file_name"]
    )
    _require_unique(
        p["airport_passenger_targets"], INPUT_PARAMETER_FILES["airport_passenger_targets"], ["file_name"]
    )
    _require_unique(
        p["vehicle_occupancy"], INPUT_PARAMETER_FILES["vehicle_occupancy"], ["submode"]
    )
    _require_unique(
        p["airport_non_transit_tod_shares"], INPUT_PARAMETER_FILES["airport_non_transit_tod_shares"],
        ["airport", "direction", "tod"],
    )
    _require_unique(
        p["airport_non_transit_access_mode_shares"],
        INPUT_PARAMETER_FILES["airport_non_transit_access_mode_shares"],
        ["airport", "direction", "access_mode"],
    )
    _require_unique(
        p["airport_transit_tod_shares"], INPUT_PARAMETER_FILES["airport_transit_tod_shares"],
        ["airport", "direction", "tod"],
    )
    _require_unique(
        p["airport_transit_mode_shares"], INPUT_PARAMETER_FILES["airport_transit_mode_shares"],
        ["airport", "direction"],
    )

    for key, share_cols in SHARE_COLUMNS_BY_INPUT.items():
        _validate_share_values(p[key], INPUT_PARAMETER_FILES[key], share_cols)

    # Share totals retain the rounded source assumptions rather than silently
    # renormalizing them.
    _validate_group_sum(
        p["airport_non_transit_tod_shares"], INPUT_PARAMETER_FILES["airport_non_transit_tod_shares"],
        ["airport", "direction"], "share_tod", tolerance=0.0011,
    )
    _validate_group_sum(
        p["airport_transit_tod_shares"], INPUT_PARAMETER_FILES["airport_transit_tod_shares"],
        ["airport", "direction"], "share_tod", tolerance=0.00011,
    )

    # Non-transit mode share + transit mode share must equal 100%.
    nt = (
        p["airport_non_transit_access_mode_shares"]
        .groupby(["airport", "direction"], as_index=False)["share_access_mode"]
        .sum()
        .rename(columns={"share_access_mode": "nontransit_share"})
    )
    tr = p["airport_transit_mode_shares"].rename(
        columns={"share_access_mode": "transit_share"}
    )
    totals = nt.merge(tr, on=["airport", "direction"], how="outer", validate="one_to_one")
    totals["total"] = totals["nontransit_share"] + totals["transit_share"]
    if not np.allclose(totals["total"], 1.0, atol=1e-9, rtol=0):
        raise ValueError(
            "Non-transit access-mode shares plus transit mode share must sum to 1.0; "
            f"failing rows: {totals.loc[~np.isclose(totals['total'], 1.0), :].to_dict('records')}"
        )

    # File map and target metadata must describe the same configured outputs.
    map_meta = p["airport_output_file_map"][["file_name", "airport", "direction", "year"]].sort_values("file_name")
    target_meta = p["airport_passenger_targets"][["file_name", "airport", "direction", "year"]].sort_values("file_name")
    if not map_meta.reset_index(drop=True).equals(target_meta.reset_index(drop=True)):
        raise ValueError("airport_passenger_targets.csv metadata does not match airport_output_file_map.csv")

    unsupported_years = sorted(
        set(p["airport_output_file_map"]["year"]) - set(GOSLING_SUPER_DIST_SOURCE_BY_MODEL_YEAR)
    )
    if unsupported_years:
        raise ValueError(
            "No Gosling super-district source-year mapping is defined for model year(s): "
            f"{unsupported_years}. Update GOSLING_SUPER_DIST_SOURCE_BY_MODEL_YEAR."
        )

    return p


# ---------------------------------------------------------------------------
# Geography input
# ---------------------------------------------------------------------------
def load_taz_lookup(path: Path) -> pd.DataFrame:
    """Read the authoritative TAZ -> super-district correspondence."""
    if not path.exists():
        raise FileNotFoundError(f"TAZ lookup not found: {path}")
    df = pd.read_csv(path)
    _require_columns(df, path.name, ["ZONE", "SD"])
    out = df[["ZONE", "SD"]].rename(columns={"ZONE": "zone", "SD": "district"}).copy()
    out["zone"] = pd.to_numeric(out["zone"], errors="raise").astype(int)
    out["district"] = pd.to_numeric(out["district"], errors="raise").astype(int)
    _require_unique(out, path.name, ["zone"])

    # Airport demand matrices use the internal TAZ system (1..1454). External
    # zones in the model geography are excluded from this airport calculation.
    out = out.loc[out["zone"].between(1, EXPECTED_N_TAZ)].copy()
    expected = set(range(1, EXPECTED_N_TAZ + 1))
    actual = set(out["zone"])
    if actual != expected:
        missing = sorted(expected - actual)[:10]
        raise ValueError(
            f"{path.name} must contain every internal zone 1..{EXPECTED_N_TAZ}; missing={missing}"
        )
    return out.sort_values("zone").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Numeric DBF reader for Gosling dBASE files
# ---------------------------------------------------------------------------
def _read_numeric_dbf(path: Path) -> pd.DataFrame:
    """Read the numeric and text field types used by the Gosling DBF files."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Gosling DBF not found: {path}")

    with path.open("rb") as stream:
        header = stream.read(32)
        if len(header) != 32:
            raise ValueError(f"Invalid DBF header: {path}")
        _, _, _, _, n_records, header_len, _ = struct.unpack("<BBBBLHH20x", header)
        n_fields = (header_len - 32 - 1) // 32

        fields: list[tuple[str, str, int, int]] = []
        for _ in range(n_fields):
            fd = stream.read(32)
            name_b, ftype_b, width, decimals = struct.unpack("<11sc4xBB14x", fd)
            name = name_b.rstrip(b"\x00").decode("latin1")
            fields.append((name, ftype_b.decode("latin1"), width, decimals))
        stream.read(1)

        data: dict[str, list[object]] = {name: [] for name, *_ in fields}
        for _ in range(n_records):
            deletion_flag = stream.read(1)
            if not deletion_flag:
                break
            deleted = deletion_flag == b"*"
            row_values: dict[str, object] = {}
            for name, ftype, width, decimals in fields:
                raw = stream.read(width).decode("latin1").strip()
                if ftype in {"N", "F"}:
                    if raw == "":
                        value: object = np.nan
                    else:
                        try:
                            value = float(raw)
                            if decimals == 0 and value.is_integer():
                                value = int(value)
                        except ValueError:
                            value = np.nan
                else:
                    value = raw
                row_values[name] = value
            if not deleted:
                for name in data:
                    data[name].append(row_values[name])

    return pd.DataFrame(data)


def _gosling_file_map(gosling_dir: Path) -> dict[str, Path]:
    """Return a case-insensitive lookup of DBF names in the Gosling input folder."""
    gosling_dir = Path(gosling_dir)
    if not gosling_dir.is_dir():
        raise FileNotFoundError(f"Gosling summary folder not found: {gosling_dir}")
    files = {
        path.name.lower(): path
        for path in gosling_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".dbf"
    }
    if not files:
        raise FileNotFoundError(f"No DBF files were found in: {gosling_dir}")
    return files


def _read_gosling_dbf(file_map: dict[str, Path], dbf_name: str) -> pd.DataFrame:
    path = file_map.get(dbf_name.lower())
    if path is None:
        available = sorted(file_map)[:10]
        raise FileNotFoundError(
            f"Gosling DBF '{dbf_name}' was not found. Example files: {available}"
        )
    return _read_numeric_dbf(path)


def _trip_columns(df: pd.DataFrame, source_name: str) -> list[str]:
    trip_cols = [c for c in df.columns if c not in {"ORIG", "DEST"}]
    bad = [c for c in trip_cols if re.fullmatch(r"[^_]+_[^_]+_[^_]+", str(c)) is None]
    if bad:
        raise ValueError(
            f"Unexpected trip-column names in {source_name}: {bad[:10]}. "
            "Expected TOD_ACCESSMODE_SUBMODE."
        )
    return trip_cols


# ---------------------------------------------------------------------------
# Derived Gosling parameters
# ---------------------------------------------------------------------------

def build_airport_non_transit_submode_shares(
    file_map: pd.DataFrame,
    gosling_dir: Path,
) -> pd.DataFrame:
    """Build DA/S2/S3 shares by airport, direction, model year, and access mode.

    The Gosling DBF trip fields are vehicle trips. Each field is converted to
    person trips using the DA/S2/S3 occupancies, summed across TAZs and time
    periods, and divided by the person-trip total for its access mode.
    """
    files = _gosling_file_map(gosling_dir)
    results: list[pd.DataFrame] = []

    configs = file_map[["airport", "direction", "year"]].drop_duplicates()
    for cfg in configs.itertuples(index=False):
        source_year = GOSLING_SUPER_DIST_SOURCE_BY_MODEL_YEAR[int(cfg.year)]
        dbf_name = f"{source_year}_{cfg.direction}{cfg.airport}.dbf"
        df = _read_gosling_dbf(files, dbf_name)
        trip_cols = _trip_columns(df, dbf_name)

        totals: list[dict[str, object]] = []
        for col in trip_cols:
            _, access_mode, submode = col.split("_")
            if access_mode not in ACCESS_MODES:
                continue
            if submode not in GOSLING_PERSONS_PER_VEHICLE:
                raise ValueError(f"Unexpected Gosling submode '{submode}' in {dbf_name}.{col}")
            vehicle_trips = pd.to_numeric(df[col], errors="coerce").fillna(0.0).sum()
            totals.append(
                {
                    "access_mode": access_mode,
                    "submode": submode,
                    "person_trips": float(vehicle_trips) * GOSLING_PERSONS_PER_VEHICLE[submode],
                }
            )

        summary = (
            pd.DataFrame(totals)
            .groupby(["access_mode", "submode"], as_index=False)["person_trips"]
            .sum()
        )
        summary["access_mode_total"] = summary.groupby("access_mode")["person_trips"].transform("sum")
        if (summary["access_mode_total"] <= 0).any():
            bad = summary.loc[summary["access_mode_total"] <= 0, "access_mode"].unique().tolist()
            raise ValueError(f"{dbf_name} has no positive person trips for access mode(s): {bad}")
        summary["share_submode"] = (summary["person_trips"] / summary["access_mode_total"]).round(SHARE_DECIMALS)
        summary.insert(0, "year", int(cfg.year))
        summary.insert(0, "direction", cfg.direction)
        summary.insert(0, "airport", cfg.airport)
        results.append(summary[["airport", "direction", "year", "access_mode", "submode", "share_submode"]])

    out = pd.concat(results, ignore_index=True)
    mode_order = {value: index for index, value in enumerate(ACCESS_MODES)}
    submode_order = {"DA": 0, "S2": 1, "S3": 2}
    out["_mode_order"] = out["access_mode"].map(mode_order)
    out["_submode_order"] = out["submode"].map(submode_order)
    out = out.sort_values(["year", "direction", "airport", "_mode_order", "_submode_order"])
    out = out.drop(columns=["_mode_order", "_submode_order"]).reset_index(drop=True)

    file_name = OUTPUT_PARAMETER_FILES["airport_non_transit_submode_shares"]
    _require_unique(out, file_name, ["airport", "direction", "year", "access_mode", "submode"])
    _validate_share_values(out, file_name, ["share_submode"], False)
    _validate_group_sum(
        out, file_name, ["airport", "direction", "year", "access_mode"],
        "share_submode", tolerance=0.00011,
    )
    return out

def build_super_district_shares(
    file_map: pd.DataFrame,
    taz_lookup: pd.DataFrame,
    gosling_dir: Path,
) -> pd.DataFrame:
    """Build super-district shares for each configured airport demand file.

    Gosling vehicle trips are converted to person trips with the source
    occupancies, assigned to super districts, and divided by the total person
    trips for each airport, direction, and source year.
    """
    files = _gosling_file_map(gosling_dir)
    results: list[pd.DataFrame] = []

    for cfg in file_map.itertuples(index=False):
        source_year = GOSLING_SUPER_DIST_SOURCE_BY_MODEL_YEAR[int(cfg.year)]
        dbf_name = f"{source_year}_{cfg.direction}{cfg.airport}.dbf"
        df = _read_gosling_dbf(files, dbf_name)
        _require_columns(df, dbf_name, ["ORIG", "DEST"])
        trip_cols = _trip_columns(df, dbf_name)
        zone_col = "DEST" if cfg.direction == "from" else "ORIG"

        person_trips = np.zeros(len(df), dtype=float)
        for col in trip_cols:
            _, _, submode = col.split("_")
            if submode not in GOSLING_PERSONS_PER_VEHICLE:
                raise ValueError(f"Unexpected Gosling submode '{submode}' in {dbf_name}.{col}")
            values = pd.to_numeric(df[col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
            person_trips += values * GOSLING_PERSONS_PER_VEHICLE[submode]

        zone_totals = pd.DataFrame(
            {
                "zone": pd.to_numeric(df[zone_col], errors="raise").astype(int),
                "person_trips": person_trips,
            }
        ).merge(taz_lookup, on="zone", how="left", validate="many_to_one")
        if zone_totals["district"].isna().any():
            missing = zone_totals.loc[zone_totals["district"].isna(), "zone"].unique()[:10]
            raise ValueError(f"{dbf_name} contains zones missing from the TAZ lookup: {missing.tolist()}")

        district = zone_totals.groupby("district", as_index=False)["person_trips"].sum()
        total = float(district["person_trips"].sum())
        if total <= 0:
            raise ValueError(f"{dbf_name} has no positive person trips")
        district["share"] = (district["person_trips"] / total).round(SHARE_DECIMALS)
        district.insert(0, "year", int(cfg.year))
        district.insert(0, "direction", cfg.direction)
        district.insert(0, "airport", cfg.airport)
        district.insert(0, "file_name", cfg.file_name)
        results.append(
            district[["file_name", "airport", "direction", "year", "district", "share"]]
        )

    out = pd.concat(results, ignore_index=True).sort_values(["file_name", "district"]).reset_index(drop=True)
    _require_unique(out, OUTPUT_PARAMETER_FILES["super_district_shares"], ["file_name", "district"])
    _validate_share_values(out, OUTPUT_PARAMETER_FILES["super_district_shares"], ["share"], False)
    _validate_group_sum(
        out, OUTPUT_PARAMETER_FILES["super_district_shares"], ["file_name"], "share", tolerance=0.00031
    )
    return out


def build_airport_non_transit_zone_access_mode_shares(
    taz_lookup: pd.DataFrame,
    gosling_dir: Path,
) -> pd.DataFrame:
    """Build within-super-district zonal shares by non-transit access mode.

    Trip fields are summed across time periods and vehicle occupancies for each
    access mode. Each zone is then divided by its district/access-mode total.
    """
    files = _gosling_file_map(gosling_dir)
    outputs: list[pd.DataFrame] = []

    for airport in AIRPORTS:
        for direction in DIRECTIONS:
            dbf_name = f"{GOSLING_ZONE_SHARE_SOURCE_YEAR}_{direction}{airport}.dbf"
            df = _read_gosling_dbf(files, dbf_name)
            _require_columns(df, dbf_name, ["ORIG", "DEST"])
            trip_cols = _trip_columns(df, dbf_name)
            zone_col = "DEST" if direction == "from" else "ORIG"

            zone = pd.to_numeric(df[zone_col], errors="raise").astype(int)
            by_mode = pd.DataFrame({"zone": zone})
            for mode in ACCESS_MODES:
                cols = [c for c in trip_cols if c.split("_")[1] == mode]
                if not cols:
                    raise ValueError(f"{dbf_name} has no trip columns for access mode {mode}")
                by_mode[f"trips_{mode.lower()}"] = (
                    df[cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).sum(axis=1)
                )

            # Some source files may contain more than one record for a zone.
            by_mode = by_mode.groupby("zone", as_index=False).sum().merge(
                taz_lookup, on="zone", how="left", validate="one_to_one"
            )
            if by_mode["district"].isna().any():
                missing = by_mode.loc[by_mode["district"].isna(), "zone"].unique()[:10]
                raise ValueError(f"{dbf_name} contains zones missing from the TAZ lookup: {missing.tolist()}")

            out = by_mode[["zone", "district"]].copy()
            for mode in ACCESS_MODES:
                trips_col = f"trips_{mode.lower()}"
                total = by_mode.groupby("district")[trips_col].transform("sum")
                share_col = f"zdist_share_{mode.lower()}"
                out[share_col] = np.where(total > 0, by_mode[trips_col] / total, 0.0)
                out[share_col] = out[share_col].round(SHARE_DECIMALS)

            out.insert(0, "direction", direction)
            out.insert(0, "airport", airport)
            outputs.append(out)

    out = pd.concat(outputs, ignore_index=True)
    out = out[[
        "airport", "direction", "zone", "district",
        *[f"zdist_share_{mode.lower()}" for mode in ACCESS_MODES],
    ]].sort_values(["airport", "direction", "district", "zone"]).reset_index(drop=True)

    file_name = OUTPUT_PARAMETER_FILES["airport_non_transit_zone_access_mode_shares"]
    _require_unique(out, file_name, ["airport", "direction", "zone"])
    share_cols = [f"zdist_share_{mode.lower()}" for mode in ACCESS_MODES]
    _validate_share_values(out, file_name, share_cols, False)

    # Zero-trip district/access-mode groups sum to zero; all other groups should
    # remain close to one after the stored zonal shares are summed.
    sums = out.groupby(["airport", "direction", "district"])[share_cols].sum()
    for col in share_cols:
        values = sums[col].to_numpy(dtype=float)
        ok = np.isclose(values, 0.0, atol=1e-12) | np.isclose(values, 1.0, atol=0.0041, rtol=0)
        if not ok.all():
            bad = sums.loc[~ok, col].head(5).to_dict()
            raise ValueError(f"{file_name}.{col} has invalid within-district totals: {bad}")
    return out


# ---------------------------------------------------------------------------
# XLSX reader and transit TAZ aggregation
# ---------------------------------------------------------------------------
_XLSX_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_XLSX_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _excel_column_index(cell_reference: str) -> int:
    match = re.match(r"([A-Z]+)", cell_reference.upper())
    if not match:
        raise ValueError(f"Could not parse spreadsheet cell reference: {cell_reference}")
    result = 0
    for char in match.group(1):
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result - 1


def _read_xlsx_matrix(path: Path, sheet_name: str) -> list[list[object]]:
    """Read cell values from one XLSX worksheet into a rectangular matrix."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Transit source workbook not found: {path}")

    with zipfile.ZipFile(path) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        sheets = workbook.find(f"{{{_XLSX_MAIN_NS}}}sheets")
        if sheets is None:
            raise ValueError(f"{path.name} has no worksheet list")

        rel_id = None
        for sheet in sheets:
            if sheet.attrib.get("name") == sheet_name:
                rel_id = sheet.attrib.get(f"{{{_XLSX_REL_NS}}}id")
                break
        if rel_id is None:
            raise ValueError(f"{path.name} is missing required sheet '{sheet_name}'")

        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        target = next((rel.attrib.get("Target") for rel in rels if rel.attrib.get("Id") == rel_id), None)
        if target is None:
            raise ValueError(f"Could not resolve sheet '{sheet_name}' in {path.name}")
        sheet_path = (
            target.lstrip("/")
            if target.startswith("/")
            else os.path.normpath(os.path.join("xl", target)).replace("\\", "/")
        )

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            shared_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for item in shared_root.findall(f"{{{_XLSX_MAIN_NS}}}si"):
                shared_strings.append(
                    "".join(node.text or "" for node in item.iter(f"{{{_XLSX_MAIN_NS}}}t"))
                )

        sheet_root = ET.fromstring(zf.read(sheet_path))
        row_dicts: list[dict[int, object]] = []
        max_col = -1
        for row in sheet_root.iter(f"{{{_XLSX_MAIN_NS}}}row"):
            values: dict[int, object] = {}
            for cell in row.findall(f"{{{_XLSX_MAIN_NS}}}c"):
                ref = cell.attrib.get("r")
                col_index = _excel_column_index(ref) if ref else len(values)
                cell_type = cell.attrib.get("t")
                value_node = cell.find(f"{{{_XLSX_MAIN_NS}}}v")

                if cell_type == "inlineStr":
                    inline = cell.find(f"{{{_XLSX_MAIN_NS}}}is")
                    value: object = (
                        "".join(node.text or "" for node in inline.iter(f"{{{_XLSX_MAIN_NS}}}t"))
                        if inline is not None else ""
                    )
                elif value_node is None:
                    value = None
                else:
                    raw = value_node.text or ""
                    if cell_type == "s":
                        value = shared_strings[int(raw)]
                    elif cell_type in {"str", "e"}:
                        value = raw
                    elif cell_type == "b":
                        value = raw == "1"
                    else:
                        try:
                            numeric = float(raw)
                            value = int(numeric) if numeric.is_integer() else numeric
                        except ValueError:
                            value = raw
                values[col_index] = value
                max_col = max(max_col, col_index)
            row_dicts.append(values)

    if not row_dicts or max_col < 0:
        raise ValueError(f"Sheet '{sheet_name}' in {path.name} is empty")
    return [[row.get(i) for i in range(max_col + 1)] for row in row_dicts]


def _aggregate_transit_taz_trips(source_path: Path, sheet_name: str, direction: str) -> pd.DataFrame:
    """Aggregate the transit source worksheet to airport trip totals by TAZ."""
    matrix = _read_xlsx_matrix(source_path, sheet_name)
    if len(matrix) < 4:
        raise ValueError(f"{source_path.name}:{sheet_name} does not contain the expected header rows")

    headers = [str(value).strip() if value is not None else "" for value in matrix[2]]
    zone_header = "Orig Tm1 Taz" if direction == "to" else "Dest Tm1 Taz"
    if zone_header not in headers:
        raise ValueError(f"{source_path.name}:{sheet_name} is missing '{zone_header}'")
    zone_col = headers.index(zone_header)

    airport_cols = {
        airport: [i for i, header in enumerate(headers) if header == airport]
        for airport in AIRPORTS
    }
    missing_airports = [airport for airport, cols in airport_cols.items() if not cols]
    if missing_airports:
        raise ValueError(
            f"{source_path.name}:{sheet_name} is missing airport columns: {missing_airports}"
        )

    records: list[dict[str, float | int]] = []
    current_zone: int | None = None
    for row in matrix[3:]:
        raw_zone = row[zone_col] if zone_col < len(row) else None
        if raw_zone not in (None, ""):
            try:
                current_zone = int(float(raw_zone))
            except (TypeError, ValueError):
                current_zone = None

        # The TAZ field is merged across detail rows; carry the top-left TAZ
        # value through the rows in that merged group. Rows before the first TAZ
        # are workbook totals and are not used in the TAZ distribution.
        if current_zone is None or not 1 <= current_zone <= EXPECTED_N_TAZ:
            continue

        record: dict[str, float | int] = {"zone": current_zone}
        for airport, cols in airport_cols.items():
            total = 0.0
            for col in cols:
                value = row[col] if col < len(row) else None
                if value in (None, ""):
                    continue
                try:
                    total += float(value)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Non-numeric airport trip value in {source_path.name}:{sheet_name}"
                    )
            record[airport] = total
        records.append(record)

    if not records:
        raise ValueError(f"No TAZ-level transit records found in {source_path.name}:{sheet_name}")

    aggregated = pd.DataFrame(records).groupby("zone", as_index=False)[list(AIRPORTS)].sum()

    # The source 'to airport' tabulation is reported to one decimal place before
    # the zonal distribution is calculated.
    if direction == "to":
        aggregated[list(AIRPORTS)] = aggregated[list(AIRPORTS)].round(1)
    return aggregated


def build_airport_transit_zone_shares(transit_source_path: Path) -> pd.DataFrame:
    """Build transit zonal shares from the airport transit TAZ source workbook."""
    outputs: list[pd.DataFrame] = []
    sheet_map = (("TAZ from Airport", "from"), ("TAZ to Airport", "to"))

    for sheet_name, direction in sheet_map:
        source = _aggregate_transit_taz_trips(transit_source_path, sheet_name, direction)
        complete = pd.DataFrame({"zone": np.arange(1, EXPECTED_N_TAZ + 1, dtype=int)}).merge(
            source, on="zone", how="left", validate="one_to_one"
        )
        complete[list(AIRPORTS)] = complete[list(AIRPORTS)].fillna(0.0)

        for airport in AIRPORTS:
            total = float(complete[airport].sum())
            zshare = (complete[airport] / total).round(SHARE_DECIMALS) if total > 0 else 0.0
            outputs.append(
                pd.DataFrame(
                    {
                        "airport": airport,
                        "direction": direction,
                        "zone": complete["zone"],
                        "zshare_tr": zshare,
                    }
                )
            )

    out = pd.concat(outputs, ignore_index=True).sort_values(
        ["airport", "direction", "zone"]
    ).reset_index(drop=True)
    file_name = OUTPUT_PARAMETER_FILES["airport_transit_zone_shares"]
    _require_unique(out, file_name, ["airport", "direction", "zone"])
    _validate_share_values(out, file_name, ["zshare_tr"], False)
    _validate_group_sum(
        out, file_name, ["airport", "direction"], "zshare_tr", tolerance=0.00171
    )
    return out


# ---------------------------------------------------------------------------
# Combined parameter tables
# ---------------------------------------------------------------------------
def build_airport_non_transit_tod_access_mode_submode_shares(p: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build the expanded non-transit file/TOD/access-mode/submode share table."""
    file_map = p["airport_output_file_map"][["file_name", "airport", "direction", "year"]].copy()
    submode = p["airport_non_transit_submode_shares"].copy()
    tod = p["airport_non_transit_tod_shares"].copy()
    access = p["airport_non_transit_access_mode_shares"].copy()

    base = file_map.merge(
        submode, on=["airport", "direction", "year"], how="left", validate="one_to_many"
    )
    if base["share_submode"].isna().any():
        missing = base.loc[base["share_submode"].isna(), ["file_name", "airport", "direction", "year"]]
        raise ValueError(f"Missing submode-share coverage: {missing.drop_duplicates().to_dict('records')[:10]}")

    out = base.merge(tod, on=["airport", "direction"], how="left", validate="many_to_many")
    out = out.merge(
        access,
        on=["airport", "direction", "access_mode"],
        how="left",
        validate="many_to_one",
    )
    if out[["share_tod", "share_access_mode"]].isna().any().any():
        raise ValueError("Missing TOD or access-mode lookup coverage while building non-transit shares")

    tod_order = {value: index for index, value in enumerate(TOD_ORDER)}
    mode_order = {value: index for index, value in enumerate(ACCESS_MODES)}
    submode_order = {"DA": 0, "S2": 1, "S3": 2}
    out["_tod_order"] = out["tod"].map(tod_order)
    out["_mode_order"] = out["access_mode"].map(mode_order)
    out["_submode_order"] = out["submode"].map(submode_order)
    out = out.sort_values(["file_name", "_tod_order", "_mode_order", "_submode_order"])

    keep = [
        "file_name", "airport", "direction", "year", "tod", "access_mode", "submode",
        "share_tod", "share_access_mode", "share_submode",
    ]
    out = out[keep].reset_index(drop=True)
    for col in ("share_tod", "share_access_mode", "share_submode"):
        out[col] = out[col].round(SHARE_DECIMALS)
    _require_unique(
        out, "combined non-transit shares",
        ["file_name", "tod", "access_mode", "submode"],
    )
    return out


def build_airport_transit_tod_access_shares(p: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build the transit file/TOD table used by the demand calculation."""
    file_map = p["airport_output_file_map"][["file_name", "airport", "direction", "year"]].copy()
    tod = p["airport_transit_tod_shares"].copy()
    mode = p["airport_transit_mode_shares"].copy()

    out = file_map.merge(tod, on=["airport", "direction"], how="left", validate="many_to_many")
    out = out.merge(mode, on=["airport", "direction"], how="left", validate="many_to_one")
    if out[["share_tod", "share_access_mode"]].isna().any().any():
        raise ValueError("Missing transit TOD or transit mode-share coverage")
    out["file_name"] = "TR_" + out["file_name"].astype(str)
    out["access_mode"] = "TR"
    out["_tod_order"] = out["tod"].map({value: index for index, value in enumerate(TOD_ORDER)})
    out = out.sort_values(["file_name", "_tod_order"])
    out = out[["file_name", "access_mode", "tod", "share_tod", "share_access_mode"]].reset_index(drop=True)
    out["share_tod"] = out["share_tod"].round(SHARE_DECIMALS)
    out["share_access_mode"] = out["share_access_mode"].round(SHARE_DECIMALS)
    _require_unique(out, "combined transit shares", ["file_name", "tod"])
    return out


# ---------------------------------------------------------------------------
# End-to-end parameter build
# ---------------------------------------------------------------------------
def build_all_parameters(
    parameters_dir: Path = DEFAULT_PARAMETERS_DIR,
    taz_lookup_path: Path = DEFAULT_TAZ_LOOKUP,
    gosling_dir: Path = DEFAULT_GOSLING_DIR,
    transit_source_path: Path = DEFAULT_TRANSIT_SOURCE,
    check_only: bool = False,
) -> dict[str, pd.DataFrame]:
    """Build and validate all source-derived parameter tables."""
    parameters_dir = Path(parameters_dir)
    parameters_dir.mkdir(parents=True, exist_ok=True)

    p = load_primitive_parameters(parameters_dir)
    taz_lookup = load_taz_lookup(Path(taz_lookup_path))

    submode_shares = build_airport_non_transit_submode_shares(
        p["airport_output_file_map"], Path(gosling_dir)
    )

    generated = {
        "super_district_shares": build_super_district_shares(
            p["airport_output_file_map"], taz_lookup, Path(gosling_dir)
        ),
        "airport_non_transit_submode_shares": submode_shares,
        "airport_non_transit_zone_access_mode_shares": build_airport_non_transit_zone_access_mode_shares(
            taz_lookup, Path(gosling_dir)
        ),
        "airport_transit_zone_shares": build_airport_transit_zone_shares(
            Path(transit_source_path)
        ),
    }

    # Build the two expanded share tables in memory to verify that all lookup
    # relationships are complete. They are reconstructed by the demand script
    # when needed and are not written as separate parameter files.
    combined_non_transit = build_airport_non_transit_tod_access_mode_submode_shares(
        {**p, "airport_non_transit_submode_shares": submode_shares}
    )
    combined_transit = build_airport_transit_tod_access_shares(p)

    expected_rows = {
        "super_district_shares": len(p["airport_output_file_map"]) * taz_lookup["district"].nunique(),
        "airport_non_transit_submode_shares": 216,
        "airport_non_transit_zone_access_mode_shares": len(AIRPORTS) * len(DIRECTIONS) * EXPECTED_N_TAZ,
        "airport_transit_zone_shares": len(AIRPORTS) * len(DIRECTIONS) * EXPECTED_N_TAZ,
    }
    for key, expected in expected_rows.items():
        actual = len(generated[key])
        if actual != expected:
            raise ValueError(
                f"{OUTPUT_PARAMETER_FILES[key]} has {actual} rows; expected {expected}"
            )
    if len(combined_non_transit) != 1080:
        raise ValueError(
            f"Combined non-transit share table has {len(combined_non_transit)} rows; expected 1080"
        )
    if len(combined_transit) != 60:
        raise ValueError(
            f"Combined transit share table has {len(combined_transit)} rows; expected 60"
        )

    if not check_only:
        _write_share_csv(
            generated["super_district_shares"],
            parameters_dir / OUTPUT_PARAMETER_FILES["super_district_shares"],
            ["share"],
        )
        _write_share_csv(
            generated["airport_non_transit_submode_shares"],
            parameters_dir / OUTPUT_PARAMETER_FILES["airport_non_transit_submode_shares"],
            ["share_submode"],
        )
        zone_cols = [f"zdist_share_{mode.lower()}" for mode in ACCESS_MODES]
        _write_share_csv(
            generated["airport_non_transit_zone_access_mode_shares"],
            parameters_dir / OUTPUT_PARAMETER_FILES["airport_non_transit_zone_access_mode_shares"],
            zone_cols,
        )
        _write_share_csv(
            generated["airport_transit_zone_shares"],
            parameters_dir / OUTPUT_PARAMETER_FILES["airport_transit_zone_shares"],
            ["zshare_tr"],
        )

        print("Parameter build complete:")
        print("  4 source-derived parameter files written")
        print(f"  {len(generated['super_district_shares']):,} super-district records")
        print(f"  {len(generated['airport_non_transit_submode_shares']):,} non-transit submode records")
        print(f"  {len(generated['airport_non_transit_zone_access_mode_shares']):,} non-transit zone records")
        print(f"  {len(generated['airport_transit_zone_shares']):,} transit zone records")
        print("  All validation checks passed")
    else:
        print("All parameter inputs and generated tables passed validation; no files written.")

    return {
        **p,
        **generated,
        "airport_non_transit_tod_access_mode_submode_shares": combined_non_transit,
        "airport_transit_tod_access_shares": combined_transit,
        "taz_lookup": taz_lookup,
    }


def _cli() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--parameters-dir", type=Path, default=DEFAULT_PARAMETERS_DIR)
    parser.add_argument("--taz-lookup", type=Path, default=DEFAULT_TAZ_LOOKUP)
    parser.add_argument("--gosling-dir", type=Path, default=DEFAULT_GOSLING_DIR)
    parser.add_argument("--transit-source", type=Path, default=DEFAULT_TRANSIT_SOURCE)
    parser.add_argument(
        "--check-only", action="store_true",
        help="Build and validate everything in memory without overwriting generated CSVs.",
    )
    args = parser.parse_args()
    build_all_parameters(
        parameters_dir=args.parameters_dir,
        taz_lookup_path=args.taz_lookup,
        gosling_dir=args.gosling_dir,
        transit_source_path=args.transit_source,
        check_only=args.check_only,
    )


if __name__ == "__main__":
    _cli()
