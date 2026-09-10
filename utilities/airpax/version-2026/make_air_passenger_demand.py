"""Build airport passenger ground-access demand matrices for OAK, SFO, and SJC.
Author: Sujith Rapolu
Date: August 2026

Inputs
------
* ``parameters/*.csv`` - model configuration, assumptions, and derived shares.
* ``../../geographies/taz-superdistrict-county.csv`` - model TAZ geography.

Outputs
-------
* ``output/<file>.dbf`` - 12 non-transit vehicle-trip matrices and 12 transit
  person-trip matrices for model years 2023 and 2050.

Run
---
Use the existing parameter CSVs::

    python make_air_passenger_demand.py

Rebuild source-derived parameter CSVs first, then create demand matrices::

    python make_air_passenger_demand.py --rebuild-parameters

Custom paths are available through the command-line options shown with
``--help``.
"""

# %% imports ------------------------------------------------------------------
from __future__ import annotations

import argparse
import struct
import sys
from datetime import date
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd


# %% configuration ------------------------------------------------------------
HERE = Path(__file__).resolve().parent

# Default project paths.
DEFAULT_PARAMETERS_DIR = HERE / "parameters"
DEFAULT_GOSLING_DIR = HERE / "inputs" / "gosling_summaries"
DEFAULT_TRANSIT_SOURCE = HERE / "inputs" / "TPS_TAZ_airport_TOD.xlsx"
CORRESPONDENCE_CSV = HERE.parent.parent / "geographies" / "taz-superdistrict-county.csv"
OUTPUT_DIR = HERE / "output"

# Parameter tables read by the demand calculation. The TOD/access/submode
# combination tables are assembled in memory from these component files.
PARAMETER_FILES = {
    "airport_output_file_map": "airport_output_file_map.csv",
    "airport_passenger_targets": "airport_passenger_targets.csv",
    "super_district_shares": "airport_non_transit_super_district_shares.csv",
    "airport_non_transit_zone_access_mode_shares": "airport_non_transit_zone_access_mode_shares.csv",
    "airport_non_transit_submode_shares": "airport_non_transit_submode_shares.csv",
    "airport_non_transit_tod_shares": "airport_non_transit_tod_shares.csv",
    "airport_non_transit_access_mode_shares": "airport_non_transit_access_mode_shares.csv",
    "airport_transit_tod_shares": "airport_transit_tod_shares.csv",
    "airport_transit_mode_shares": "airport_transit_mode_shares.csv",
    "airport_transit_zone_shares": "airport_transit_zone_shares.csv",
    "vehicle_occupancy": "airport_non_transit_vehicle_occupancy.csv",
}

EXPECTED_N_TAZ = 1454
ACCESS_MODES = ("ES", "PK", "RN", "TX", "LI", "VN", "HT", "CH")
TOD_ORDER = ("EA", "AM", "MD", "PM", "EV")


# %% parameter CSV loader -----------------------------------------------------
def load_parameters(parameters_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Load the model-ready parameter tables from a directory of CSV files."""
    parameters_dir = Path(parameters_dir)
    if not parameters_dir.is_dir():
        raise FileNotFoundError(f"Parameters directory not found: {parameters_dir}")

    out: dict[str, pd.DataFrame] = {}
    for logical_name, file_name in PARAMETER_FILES.items():
        path = parameters_dir / file_name
        if not path.exists():
            raise FileNotFoundError(
                f"Required parameter CSV not found: {path}. "
                "Run build_parameters.py if a generated parameter file is missing."
            )
        df = pd.read_csv(path)
        df.columns = [str(c).strip().upper() for c in df.columns]
        # The calculation uses SHARE_ACCESSMODE as its internal field name.
        if "SHARE_ACCESS_MODE" in df.columns:
            df = df.rename(columns={"SHARE_ACCESS_MODE": "SHARE_ACCESSMODE"})
        out[logical_name] = df
    return out


# %% minimal DBF writer / reader ---------------------------------------------
# dBASE-III writer/reader for the numeric airport matrix outputs.
def _truncate_unique(names: Sequence[str], width: int = 10) -> list[str]:
    seen: dict[str, int] = {}
    out: list[str] = []
    for raw in names:
        base = raw[:width]
        if base not in seen:
            seen[base] = 0
            out.append(base)
        else:
            seen[base] += 1
            suffix = str(seen[base])
            out.append(base[: max(0, width - len(suffix))] + suffix)
    return out


def write_dbf(df: pd.DataFrame, path: str | Path, decimals: int = 2) -> None:
    """Write *df* to a dBASE III file at *path*.

    ORIG / DEST become integer (``N``, width 10, 0 decimals).
    All other columns become float (``N``, width 19, ``decimals`` decimals).
    """
    path = Path(path)
    df = df.copy()
    df.columns = _truncate_unique([str(c).upper() for c in df.columns])

    fields: list[tuple[str, str, int, int]] = []
    for name in df.columns:
        if name in ("ORIG", "DEST"):
            fields.append((name, "N", 10, 0))
        else:
            fields.append((name, "N", 19, decimals))

    n_records = len(df)
    header_len = 32 + 32 * len(fields) + 1
    record_len = 1 + sum(f[2] for f in fields)

    today = date.today()
    with path.open("wb") as f:
        f.write(
            struct.pack(
                "<BBBBLHH20x",
                0x03, today.year - 1900, today.month, today.day,
                n_records, header_len, record_len,
            )
        )
        for name, ftype, width, dec in fields:
            name_b = name.encode("ascii")[:11].ljust(11, b"\x00")
            f.write(
                struct.pack("<11sc4xBB14x",
                            name_b, ftype.encode("ascii"), width, dec)
            )
        f.write(b"\x0D")

        int_fmt = "{:d}"
        for row in df.itertuples(index=False, name=None):
            f.write(b" ")
            for val, (_, _, width, dec) in zip(row, fields):
                if dec == 0:
                    if val is None or (isinstance(val, float) and np.isnan(val)):
                        val_i = 0
                    else:
                        val_i = int(val)
                    s = int_fmt.format(val_i)
                else:
                    if val is None or (isinstance(val, float) and np.isnan(val)):
                        val = 0.0
                    s = ("{:%d.%df}" % (width, dec)).format(float(val))
                s = s[-width:] if len(s) > width else s.rjust(width)
                f.write(s.encode("ascii"))
        f.write(b"\x1A")


def read_dbf(path: str | Path) -> pd.DataFrame:
    """Read a simple numeric dBASE III file; intended for QA of ``write_dbf``."""
    path = Path(path)
    with path.open("rb") as f:
        header = f.read(32)
        _, _, _, _, n_records, header_len, record_len = struct.unpack(
            "<BBBBLHH20x", header
        )
        n_fields = (header_len - 32 - 1) // 32
        fields = []
        for _ in range(n_fields):
            fd = f.read(32)
            name_b, ftype_b, width, dec = struct.unpack("<11sc4xBB14x", fd)
            name = name_b.rstrip(b"\x00").decode("ascii")
            fields.append((name, ftype_b.decode("ascii"), width, dec))
        f.read(1)

        data: dict[str, list] = {name: [] for name, *_ in fields}
        for _ in range(n_records):
            f.read(1)
            for name, ftype, width, dec in fields:
                raw = f.read(width).decode("ascii").strip()
                if ftype == "N":
                    if raw == "":
                        val: Any = 0
                    elif dec == 0:
                        val = int(raw)
                    else:
                        val = float(raw)
                else:
                    val = raw
                data[name].append(val)
    return pd.DataFrame(data)


# %% helper functions ---------------------------------------------------------
def _clean_names_upper(df: pd.DataFrame) -> pd.DataFrame:
    """Collapses whitespace / punctuation to underscores, uppercases, and drops
    leading/trailing underscores.
    """
    def _clean(c: str) -> str:
        s = str(c).strip()
        out: list[str] = []
        prev_us = False
        for ch in s:
            if ch.isalnum():
                out.append(ch.upper())
                prev_us = False
            else:
                if not prev_us:
                    out.append("_")
                prev_us = True
        return "".join(out).strip("_")

    df = df.copy()
    df.columns = [_clean(c) for c in df.columns]
    return df


def _to_share(x: Any) -> float:
    """Accept numbers like 0.05 or '5%' or 5 (percent) and return 0.05."""
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        v = float(x)
        return v / 100.0 if v > 1 else v
    s = str(x).strip().replace("%", "").replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return np.nan
    return v / 100.0 if v > 1 else v


def _conv_factor(access_mode: str, submode: str, conv_vec: dict[str, float]) -> float:
    """VN/HT/CH with S3 use a special factor; otherwise lookup by submode."""
    if submode == "S3" and access_mode in {"VN", "HT", "CH"}:
        key = "VN_HT_CH_S3"
        val = conv_vec.get(key)
        if not val:
            raise ValueError(f"Missing or invalid conversion factor for SUBMODE: {key}")
        return val
    val = conv_vec.get(submode)
    if not val:
        raise ValueError(f"Missing or invalid conversion factor for SUBMODE: {submode}")
    return val


# %% prepare parameter tables -------------------------------------------------
def load_and_prepare(parameters_dir: Path) -> dict:
    """Load parameter CSVs and assemble the combined share tables in memory."""
    raw = load_parameters(parameters_dir)

    zone_def = _clean_names_upper(raw["airport_output_file_map"])
    target_df = _clean_names_upper(raw["airport_passenger_targets"])
    zone_share = _clean_names_upper(raw["super_district_shares"])
    zone_share_detail = _clean_names_upper(raw["airport_non_transit_zone_access_mode_shares"])
    submode_share = _clean_names_upper(raw["airport_non_transit_submode_shares"])
    nontransit_tod = _clean_names_upper(raw["airport_non_transit_tod_shares"])
    nontransit_access = _clean_names_upper(raw["airport_non_transit_access_mode_shares"])
    transit_tod = _clean_names_upper(raw["airport_transit_tod_shares"])
    transit_mode = _clean_names_upper(raw["airport_transit_mode_shares"])
    transit_zone_share_raw = _clean_names_upper(raw["airport_transit_zone_shares"])
    conv_df = _clean_names_upper(raw["vehicle_occupancy"])

    required = {
        "airport_output_file_map.csv": (
            zone_def,
            ["FILE_NAME", "AIRPORT", "DIRECTION", "YEAR", "AIRPORT_TAZ",
             "TAZ_MIN", "TAZ_MAX"],
        ),
        "airport_passenger_targets.csv": (
            target_df, ["FILE_NAME", "AIRPORT", "DIRECTION", "YEAR", "TARGET"]
        ),
        "airport_non_transit_super_district_shares.csv": (
            zone_share,
            ["FILE_NAME", "AIRPORT", "DIRECTION", "YEAR", "DISTRICT", "SHARE"],
        ),
        "airport_non_transit_zone_access_mode_shares.csv": (
            zone_share_detail,
            ["AIRPORT", "DIRECTION", "ZONE", "DISTRICT"] +
            [f"ZDIST_SHARE_{m}" for m in ACCESS_MODES],
        ),
        "airport_non_transit_submode_shares.csv": (
            submode_share,
            ["AIRPORT", "DIRECTION", "YEAR", "ACCESS_MODE", "SUBMODE", "SHARE_SUBMODE"],
        ),
        "airport_non_transit_tod_shares.csv": (
            nontransit_tod, ["AIRPORT", "DIRECTION", "TOD", "SHARE_TOD"]
        ),
        "airport_non_transit_access_mode_shares.csv": (
            nontransit_access, ["AIRPORT", "DIRECTION", "ACCESS_MODE", "SHARE_ACCESSMODE"]
        ),
        "airport_transit_tod_shares.csv": (
            transit_tod, ["AIRPORT", "DIRECTION", "TOD", "SHARE_TOD"]
        ),
        "airport_transit_mode_shares.csv": (
            transit_mode, ["AIRPORT", "DIRECTION", "SHARE_ACCESSMODE"]
        ),
        "airport_transit_zone_shares.csv": (
            transit_zone_share_raw, ["AIRPORT", "DIRECTION", "ZONE", "ZSHARE_TR"]
        ),
        "airport_non_transit_vehicle_occupancy.csv": (
            conv_df, ["SUBMODE", "CONVERSION_FACTOR"]
        ),
    }
    for file_name, (df, cols) in required.items():
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise ValueError(f"{file_name} is missing columns: {missing}")

    conv_df = conv_df.dropna(subset=["SUBMODE"]).copy()
    conv_df["SUBMODE"] = conv_df["SUBMODE"].astype(str)
    if "VN_HT_CH_S3" not in set(conv_df["SUBMODE"]):
        print(
            "WARNING: airport_non_transit_vehicle_occupancy.csv has no "
            "SUBMODE='VN_HT_CH_S3'; VN/HT/CH S3 trips will use the default S3 factor."
        )

    frames = (
        zone_def, target_df, zone_share, zone_share_detail, submode_share,
        nontransit_tod, nontransit_access, transit_tod, transit_mode,
        transit_zone_share_raw,
    )
    for df in frames:
        if "DIRECTION" in df.columns:
            df["DIRECTION"] = df["DIRECTION"].astype(str).str.strip().str.lower()
        if "YEAR" in df.columns:
            df["YEAR"] = df["YEAR"].astype(str)

    zone_share["SHARE"] = zone_share["SHARE"].map(_to_share)
    for m in ACCESS_MODES:
        col = f"ZDIST_SHARE_{m}"
        zone_share_detail[col] = zone_share_detail[col].map(_to_share)
    submode_share["SHARE_SUBMODE"] = submode_share["SHARE_SUBMODE"].map(_to_share)
    nontransit_tod["SHARE_TOD"] = nontransit_tod["SHARE_TOD"].map(_to_share)
    nontransit_access["SHARE_ACCESSMODE"] = nontransit_access["SHARE_ACCESSMODE"].map(_to_share)
    transit_tod["SHARE_TOD"] = transit_tod["SHARE_TOD"].map(_to_share)
    transit_mode["SHARE_ACCESSMODE"] = transit_mode["SHARE_ACCESSMODE"].map(_to_share)
    transit_zone_share_raw["ZSHARE_TR"] = transit_zone_share_raw["ZSHARE_TR"].map(_to_share)

    # Expand the non-transit component shares to the file/TOD/access/submode
    # combinations used by the matrix calculation.
    file_meta = zone_def[["FILE_NAME", "AIRPORT", "DIRECTION", "YEAR"]].copy()
    col_share_raw = file_meta.merge(
        submode_share,
        on=["AIRPORT", "DIRECTION", "YEAR"],
        how="left",
        validate="one_to_many",
    )
    col_share_raw = col_share_raw.merge(
        nontransit_tod,
        on=["AIRPORT", "DIRECTION"],
        how="left",
        validate="many_to_many",
    )
    col_share_raw = col_share_raw.merge(
        nontransit_access,
        on=["AIRPORT", "DIRECTION", "ACCESS_MODE"],
        how="left",
        validate="many_to_one",
    )
    if col_share_raw[["SHARE_SUBMODE", "SHARE_TOD", "SHARE_ACCESSMODE"]].isna().any().any():
        raise ValueError("Missing non-transit share coverage while assembling parameter combinations")

    tod_order = {value: index for index, value in enumerate(TOD_ORDER)}
    mode_order = {value: index for index, value in enumerate(ACCESS_MODES)}
    submode_order = {"DA": 0, "S2": 1, "S3": 2}
    col_share_raw["_TOD_ORDER"] = col_share_raw["TOD"].map(tod_order)
    col_share_raw["_MODE_ORDER"] = col_share_raw["ACCESS_MODE"].map(mode_order)
    col_share_raw["_SUBMODE_ORDER"] = col_share_raw["SUBMODE"].map(submode_order)
    col_share_raw = col_share_raw.sort_values(
        ["FILE_NAME", "_TOD_ORDER", "_MODE_ORDER", "_SUBMODE_ORDER"]
    ).drop(columns=["_TOD_ORDER", "_MODE_ORDER", "_SUBMODE_ORDER"]).reset_index(drop=True)

    # Expand the transit TOD and overall mode shares to the transit output files.
    transit_share_raw = file_meta.merge(
        transit_tod,
        on=["AIRPORT", "DIRECTION"],
        how="left",
        validate="many_to_many",
    )
    transit_share_raw = transit_share_raw.merge(
        transit_mode,
        on=["AIRPORT", "DIRECTION"],
        how="left",
        validate="many_to_one",
    )
    if transit_share_raw[["SHARE_TOD", "SHARE_ACCESSMODE"]].isna().any().any():
        raise ValueError("Missing transit share coverage while assembling parameter combinations")
    transit_share_raw["FILE_NAME"] = "TR_" + transit_share_raw["FILE_NAME"].astype(str)
    transit_share_raw["ACCESS_MODE"] = "TR"
    transit_share_raw["_TOD_ORDER"] = transit_share_raw["TOD"].map(tod_order)
    transit_share_raw = transit_share_raw.sort_values(
        ["FILE_NAME", "_TOD_ORDER"]
    ).drop(columns=["_TOD_ORDER"]).reset_index(drop=True)

    return {
        "zone_def": zone_def,
        "target_df": target_df,
        "zone_share": zone_share,
        "zone_share_detail": zone_share_detail,
        "col_share_raw": col_share_raw,
        "transit_share_raw": transit_share_raw,
        "transit_zone_share_raw": transit_zone_share_raw,
        "conv_df": conv_df,
    }


# %% TAZ -> district correspondence ------------------------------------------
def load_taz_lookup(csv_path: Path) -> pd.DataFrame:
    """Return the internal TAZ-to-super-district mapping used by the model."""
    df = pd.read_csv(csv_path)
    if not {"ZONE", "SD"}.issubset(df.columns):
        raise ValueError(f"{csv_path.name} must contain ZONE and SD columns")
    lookup = df[["ZONE", "SD"]].rename(columns={"ZONE": "TAZ", "SD": "DISTRICT"})
    lookup["TAZ"] = lookup["TAZ"].astype(int)
    lookup["DISTRICT"] = lookup["DISTRICT"].astype(int)
    lookup = lookup.drop_duplicates("TAZ")

    # The authoritative correspondence includes 21 external zones (1455-1475).
    # The airport matrices use the 1..1454 internal TAZ system, matching the
    # supplied Gosling tables and airport_output_file_map.csv.
    lookup = lookup.loc[lookup["TAZ"].between(1, EXPECTED_N_TAZ)].copy()
    if set(lookup["TAZ"]) != set(range(1, EXPECTED_N_TAZ + 1)):
        raise ValueError(f"{csv_path.name} must contain every internal TAZ 1..{EXPECTED_N_TAZ}")
    return lookup.reset_index(drop=True)


# %% build expanded OD (TAZ-level) frame --------------------------------------
def build_expanded_od(zone_def: pd.DataFrame, taz_lookup: pd.DataFrame,
                      zone_share: pd.DataFrame,
                      zone_share_detail: pd.DataFrame) -> pd.DataFrame:
    """Build one ORIG/DEST row per TAZ for each configured airport demand file.

    For ``DIRECTION == 'from'`` ORIG = AIRPORT_TAZ, DEST = TAZ range.
    For ``DIRECTION == 'to'``   ORIG = TAZ range,  DEST = AIRPORT_TAZ.

    Joins the district super-share and the within-district access-mode zone
    shares so that each row carries a ``ROW_SHARE_<mode>`` value
    = DISTRICT_SHARE * ZDIST_SHARE_<mode>.
    """
    frames = []
    for _, row in zone_def.iterrows():
        taz_seq = np.arange(int(row["TAZ_MIN"]), int(row["TAZ_MAX"]) + 1)
        common = {
            "FILE_NAME": row["FILE_NAME"],
            "AIRPORT": row["AIRPORT"],
            "DIRECTION": row["DIRECTION"],
            "YEAR": str(row["YEAR"]),
        }
        if row["DIRECTION"] == "from":
            frame = pd.DataFrame({**common, "ORIG": int(row["AIRPORT_TAZ"]),
                                  "DEST": taz_seq})
        elif row["DIRECTION"] == "to":
            frame = pd.DataFrame({**common, "ORIG": taz_seq,
                                  "DEST": int(row["AIRPORT_TAZ"])})
        else:
            raise ValueError(f"Unexpected DIRECTION for {row['FILE_NAME']}")
        frames.append(frame)
    expanded = pd.concat(frames, ignore_index=True)

    lookup_o = taz_lookup.rename(columns={"TAZ": "ORIG", "DISTRICT": "ORIG_DISTRICT"})
    lookup_d = taz_lookup.rename(columns={"TAZ": "DEST", "DISTRICT": "DEST_DISTRICT"})
    expanded = expanded.merge(lookup_o, on="ORIG", how="left")
    expanded = expanded.merge(lookup_d, on="DEST", how="left")
    expanded["DISTRICT"] = np.where(
        expanded["DIRECTION"] == "from",
        expanded["DEST_DISTRICT"], expanded["ORIG_DISTRICT"],
    )
    expanded["ZONE"] = np.where(
        expanded["DIRECTION"] == "from", expanded["DEST"], expanded["ORIG"]
    )
    expanded["DISTRICT"] = expanded["DISTRICT"].astype("Int64")
    expanded["ZONE"] = expanded["ZONE"].astype(int)

    zs = zone_share[["FILE_NAME", "DISTRICT", "SHARE"]].copy()
    zs["DISTRICT"] = zs["DISTRICT"].astype("Int64")
    expanded = expanded.merge(zs, on=["FILE_NAME", "DISTRICT"], how="left")

    zsd = zone_share_detail.copy()
    zsd["ZONE"] = zsd["ZONE"].astype(int)
    zsd["DISTRICT"] = zsd["DISTRICT"].astype("Int64")
    key = ["AIRPORT", "DIRECTION", "ZONE", "DISTRICT"]
    keep = key + [f"ZDIST_SHARE_{m}" for m in ACCESS_MODES]
    expanded = expanded.merge(zsd[keep], on=key, how="left")

    for m in ACCESS_MODES:
        expanded[f"ROW_SHARE_{m}"] = expanded["SHARE"] * expanded[f"ZDIST_SHARE_{m}"]

    if expanded["SHARE"].isna().any():
        print("WARNING: some district SHARE values are missing after join.")
    for m in ACCESS_MODES:
        if expanded[f"ROW_SHARE_{m}"].isna().any():
            print(f"WARNING: some ROW_SHARE_{m} values are missing after join.")

    return expanded


# %% per-file builders --------------------------------------------------------
def build_nontransit_person_df(file_name: str, expanded_od: pd.DataFrame,
                               column_share: pd.DataFrame,
                               target_lookup: pd.DataFrame) -> pd.DataFrame:
    """Person-trip table for one non-transit FILE_NAME."""
    base = expanded_od[expanded_od["FILE_NAME"] == file_name].copy()
    tgt_rows = target_lookup.loc[target_lookup["FILE_NAME"] == file_name, "TARGET"]
    if len(tgt_rows) != 1:
        raise ValueError(f"Expected exactly one TARGET for {file_name}")
    tgt = float(tgt_rows.iloc[0])

    file_cs = column_share[column_share["FILE_NAME"] == file_name]

    out = base[["ORIG", "DEST"]].reset_index(drop=True).copy()
    for _, r in file_cs.iterrows():
        share_col = f"ROW_SHARE_{r['ACCESS_MODE']}"
        if share_col not in base.columns:
            raise ValueError(f"Missing {share_col} in expanded OD for {file_name}")
        out[r["COLUMN_NAME"]] = base[share_col].values * r["COLUMN_SHARE"] * tgt
    return out


def person_to_vehicle(person_df: pd.DataFrame, file_name: str,
                      column_share: pd.DataFrame,
                      conv_vec: dict[str, float]) -> pd.DataFrame:
    """Divide each column by the appropriate occupancy factor."""
    out = person_df.copy()
    for _, r in column_share[column_share["FILE_NAME"] == file_name].iterrows():
        out[r["COLUMN_NAME"]] = out[r["COLUMN_NAME"]] / _conv_factor(
            r["ACCESS_MODE"], r["SUBMODE"], conv_vec
        )
    return out


def build_transit_person_df(transit_file_name: str, transit_share: pd.DataFrame,
                            expanded_od: pd.DataFrame, target_lookup: pd.DataFrame,
                            transit_zone_share: pd.DataFrame) -> pd.DataFrame:
    """Person-trip table for one transit FILE_NAME.

    Uses the same OD expansion as the matching non-transit base file and
    multiplies by the transit zonal share and TOD share.
    """
    ts = transit_share[transit_share["TRANSIT_FILE_NAME"] == transit_file_name]
    ts = ts.assign(ORD=ts["COLUMN_NAME"].map({f"{t}_TR": i for i, t in enumerate(TOD_ORDER)}))
    ts = ts.sort_values("ORD")
    base_files = ts["BASE_FILE_NAME"].unique()
    if len(base_files) != 1:
        raise ValueError(f"Could not determine one base file for {transit_file_name}")
    base_file = base_files[0]

    base_rows = expanded_od.loc[expanded_od["FILE_NAME"] == base_file,
                                ["FILE_NAME", "AIRPORT", "DIRECTION",
                                 "ORIG", "DEST", "ZONE"]]
    if base_rows.empty:
        raise ValueError(f"No OD rows for base file {base_file}")

    base = base_rows.merge(
        transit_zone_share, on=["AIRPORT", "DIRECTION", "ZONE"], how="left"
    )
    if base["ROW_SHARE_TR"].isna().any():
        print(f"WARNING: some ROW_SHARE_TR values missing for {transit_file_name}")

    tgt_rows = target_lookup.loc[target_lookup["FILE_NAME"] == base_file, "TARGET"]
    if len(tgt_rows) != 1:
        raise ValueError(f"Expected exactly one TARGET for {base_file}")
    tgt = float(tgt_rows.iloc[0])

    out = base[["ORIG", "DEST"]].reset_index(drop=True).copy()
    for _, r in ts.iterrows():
        out[r["COLUMN_NAME"]] = base["ROW_SHARE_TR"].values * r["COLUMN_SHARE"] * tgt

    for col in (f"{t}_TR" for t in TOD_ORDER):
        if col not in out.columns:
            out[col] = 0.0
    return out[["ORIG", "DEST", *[f"{t}_TR" for t in TOD_ORDER]]]


# %% main driver --------------------------------------------------------------
def run(parameters_dir: Path = DEFAULT_PARAMETERS_DIR, csv_path: Path = CORRESPONDENCE_CSV,
        out_dir: Path = OUTPUT_DIR,
        decimals: int = 2) -> dict:
    """End-to-end pipeline; returns the in-memory tables for QA/debugging."""

    parameters_dir = Path(parameters_dir)
    if not parameters_dir.is_dir():
        raise FileNotFoundError(f"Parameters directory not found: {parameters_dir}")
    if not csv_path.exists():
        raise FileNotFoundError(f"TAZ correspondence CSV not found: {csv_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    p = load_and_prepare(parameters_dir)
    taz_lookup = load_taz_lookup(csv_path)

    expanded_od = build_expanded_od(
        p["zone_def"], taz_lookup, p["zone_share"], p["zone_share_detail"]
    )

    cs = p["col_share_raw"].copy()
    cs["COLUMN_NAME"] = cs["TOD"].astype(str) + "_" + cs["ACCESS_MODE"].astype(str) + "_" + cs["SUBMODE"].astype(str)
    cs["COLUMN_SHARE"] = cs["SHARE_TOD"] * cs["SHARE_ACCESSMODE"] * cs["SHARE_SUBMODE"]
    column_share = cs[["FILE_NAME", "COLUMN_NAME", "ACCESS_MODE",
                       "SUBMODE", "COLUMN_SHARE"]]

    ts = p["transit_share_raw"].copy()
    ts["TRANSIT_FILE_NAME"] = ts["FILE_NAME"].astype(str)
    ts["BASE_FILE_NAME"] = ts["TRANSIT_FILE_NAME"].str.replace(r"^TR_", "", regex=True)
    ts["COLUMN_NAME"] = ts["TOD"].astype(str) + "_TR"
    ts["COLUMN_SHARE"] = ts["SHARE_ACCESSMODE"] * ts["SHARE_TOD"]
    transit_share = ts[["TRANSIT_FILE_NAME", "BASE_FILE_NAME",
                        "COLUMN_NAME", "COLUMN_SHARE"]]

    target_lookup = p["target_df"][["FILE_NAME", "TARGET"]].copy()
    target_lookup["TARGET"] = target_lookup["TARGET"].astype(float)

    transit_zone_share = p["transit_zone_share_raw"].rename(
        columns={"ZSHARE_TR": "ROW_SHARE_TR"}
    )[["AIRPORT", "DIRECTION", "ZONE", "ROW_SHARE_TR"]]
    transit_zone_share["ZONE"] = transit_zone_share["ZONE"].astype(int)

    conv_vec = dict(zip(p["conv_df"]["SUBMODE"],
                        p["conv_df"]["CONVERSION_FACTOR"].astype(float)))

    # ---- Part A: non-transit vehicle-trip files ---------------------------
    nontransit_person: dict[str, pd.DataFrame] = {}
    nontransit_vehicle: dict[str, pd.DataFrame] = {}
    for f in p["zone_def"]["FILE_NAME"].unique():
        person_df = build_nontransit_person_df(f, expanded_od, column_share, target_lookup)
        if len(person_df) != EXPECTED_N_TAZ:
            print(f"WARNING: {f} person table has {len(person_df)} rows (expected {EXPECTED_N_TAZ})")
        nontransit_person[f] = person_df

        vehicle_df = person_to_vehicle(person_df, f, column_share, conv_vec)
        nontransit_vehicle[f] = vehicle_df

        out_file = out_dir / f"{f}.dbf"
        write_dbf(vehicle_df, out_file, decimals=decimals)
        print(f"Written: {out_file}")

    # ---- Part B: transit-only person-trip files ---------------------------
    transit_person: dict[str, pd.DataFrame] = {}
    for f in transit_share["TRANSIT_FILE_NAME"].unique():
        person_df = build_transit_person_df(
            f, transit_share, expanded_od, target_lookup, transit_zone_share
        )
        if len(person_df) != EXPECTED_N_TAZ:
            print(f"WARNING: transit {f} has {len(person_df)} rows (expected {EXPECTED_N_TAZ})")
        transit_person[f] = person_df

        out_file = out_dir / f"{f}.dbf"
        write_dbf(person_df, out_file, decimals=decimals)
        print(f"Written: {out_file}")

    return {
        "expanded_od": expanded_od,
        "column_share": column_share,
        "transit_share": transit_share,
        "nontransit_person_tables": nontransit_person,
        "nontransit_vehicle_tables": nontransit_vehicle,
        "transit_person_tables": transit_person,
    }


# %% CLI ---------------------------------------------------------------------
def _cli() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--params-dir", type=Path, default=DEFAULT_PARAMETERS_DIR,
        help="Directory containing parameter CSVs (default: ./parameters)",
    )
    ap.add_argument(
        "--csv", type=Path, default=CORRESPONDENCE_CSV,
        help="TAZ-to-super-district correspondence CSV",
    )
    ap.add_argument(
        "--out", type=Path, default=OUTPUT_DIR,
        help="Output directory for all DBFs (default: ./output)",
    )
    ap.add_argument("--decimals", type=int, default=2)
    ap.add_argument(
        "--rebuild-parameters", action="store_true",
        help="Rebuild source-derived parameter CSVs before creating demand matrices.",
    )
    ap.add_argument(
        "--gosling-dir", type=Path, default=DEFAULT_GOSLING_DIR,
        help="Gosling summary DBF directory used with --rebuild-parameters.",
    )
    ap.add_argument(
        "--transit-source", type=Path, default=DEFAULT_TRANSIT_SOURCE,
        help="Transit airport TAZ workbook used with --rebuild-parameters.",
    )
    args = ap.parse_args()

    if args.rebuild_parameters:
        from build_parameters import build_all_parameters

        build_all_parameters(
            parameters_dir=args.params_dir,
            taz_lookup_path=args.csv,
            gosling_dir=args.gosling_dir,
            transit_source_path=args.transit_source,
        )

    run(args.params_dir, args.csv, args.out, args.decimals)


# %% run (for `# %%` cell execution in VS Code) -------------------------------
if __name__ == "__main__":
    if any(a.startswith("-") for a in sys.argv[1:]) or len(sys.argv) > 1:
        _cli()
    else:
        run(DEFAULT_PARAMETERS_DIR)

