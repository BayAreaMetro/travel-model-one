"""
io.py
-----
All file I/O in one place. Nothing here does computation — just loading
and basic shape/sanity checks so errors surface early with clear messages.

Expected inputs
---------------
PA parquet
    index : zone_id (int)
    columns: {truck_type}_productions, {truck_type}_attractions
             for each truck_type in TRUCK_TYPES

Skim OMX files  (one per time period: AM, MD)
    tables named per SKIM_TABLE_NAMES in config.py
    shape : (n_zones, n_zones)

OD OMX file
    tables named per OD_TABLE_NAMES in config.py
    shape : (n_zones, n_zones)

TLFD CSV
    columns: bin_start, {truck_type}_share  for each truck type
    bin_start values must match TLFD_BINS in config.py
"""

from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import openmatrix as omx

from .config import (
    TRUCK_TYPES,
    SKIM_TABLE_NAMES,
    TOLL_SKIM_TABLE_NAMES,
    OD_TABLE_NAMES,
    TRUCK_DISTRIB_LOS_TOLL_PART,
    BLEND_WEIGHTS,
    TLFD_BINS,
)


# ── Type aliases ───────────────────────────────────────────────────────────────
# All matrices are (n_zones, n_zones) float64 numpy arrays.
# PA vectors are (n_zones,) float64 numpy arrays.

PAData = Dict[str, Dict[str, np.ndarray]]   # {truck_type: {"P": ..., "A": ...}}
SkimData = Dict[str, np.ndarray]             # {truck_type: blended_time_matrix}
ODData = Dict[str, np.ndarray]               # {truck_type: od_matrix}
TLFDData = Dict[str, np.ndarray]             # {truck_type: share_array per bin}


def load_pa(path: Path) -> PAData:
    """
    Load productions and attractions from a parquet file.

    Expected columns: light_trucks_productions, light_trucks_attractions, etc.
    Index should be zone_id (used only for ordering; zones assumed sequential).
    """
    path = Path(path)
    df = pd.read_parquet(path)
    df = df.sort_index()

    result: PAData = {}
    for tt in TRUCK_TYPES:
        p_col = f"{tt}_productions"
        a_col = f"{tt}_attractions"

        missing = [c for c in [p_col, a_col] if c not in df.columns]
        if missing:
            raise ValueError(
                f"PA file {path.name} is missing columns: {missing}\n"
                f"Available columns: {list(df.columns)}"
            )

        P = df[p_col].to_numpy(dtype=np.float64)
        A = df[a_col].to_numpy(dtype=np.float64)

        # Basic sanity checks
        if np.any(P < 0) or np.any(A < 0):
            raise ValueError(f"Negative P or A values found for {tt}")
        if abs(P.sum() - A.sum()) / (P.sum() + 1e-9) > 0.05:
            print(
                f"  WARNING [{tt}]: P total ({P.sum():.0f}) and "
                f"A total ({A.sum():.0f}) differ by more than 5%."
            )

        result[tt] = {"P": P, "A": A}
        print(f"  PA loaded [{tt}]: {len(P)} zones, "
              f"P={P.sum():.0f}, A={A.sum():.0f}")

    return result


def _load_skim_matrix(
    omx_file: omx.File,
    table_name: str,
    file_label: str,
) -> np.ndarray:
    """Read one table from an open OMX file as float64."""
    if table_name not in omx_file.list_matrices():
        raise KeyError(
            f"Table '{table_name}' not found in {file_label}.\n"
            f"Available tables: {omx_file.list_matrices()}"
        )
    return np.array(omx_file[table_name], dtype=np.float64)


def load_blended_skims(
    am_skim_path: Path,
    md_skim_path: Path,
) -> SkimData:
    """
    Load AM and MD skim files and compute the blended travel time per truck type.

    Blended time = (1/3)*AM + (2/3)*MD  [free portion]
                 + toll blend if TRUCK_DISTRIB_LOS_TOLL_PART > 0
    """
    am_skim_path = Path(am_skim_path)
    md_skim_path = Path(md_skim_path)

    result: SkimData = {}

    with omx.open_file(str(am_skim_path), "r") as f_am, \
         omx.open_file(str(md_skim_path), "r") as f_md:

        for tt in TRUCK_TYPES:
            # Free travel times
            t_am = _load_skim_matrix(f_am, SKIM_TABLE_NAMES[("AM", tt)], am_skim_path.name)
            t_md = _load_skim_matrix(f_md, SKIM_TABLE_NAMES[("MD", tt)], md_skim_path.name)

            free_blend = (
                BLEND_WEIGHTS["AM"] * t_am +
                BLEND_WEIGHTS["MD"] * t_md
            )

            if TRUCK_DISTRIB_LOS_TOLL_PART > 0:
                toll_am = _load_skim_matrix(
                    f_am, TOLL_SKIM_TABLE_NAMES[("AM", tt)], am_skim_path.name
                )
                toll_md = _load_skim_matrix(
                    f_md, TOLL_SKIM_TABLE_NAMES[("MD", tt)], md_skim_path.name
                )
                toll_blend = (
                    BLEND_WEIGHTS["AM"] * toll_am +
                    BLEND_WEIGHTS["MD"] * toll_md
                )
                blended = (
                    (1 - TRUCK_DISTRIB_LOS_TOLL_PART) * free_blend +
                    TRUCK_DISTRIB_LOS_TOLL_PART * toll_blend
                )
            else:
                blended = free_blend

            # Replace zeros/negatives on diagonal with small positive value
            blended = np.where(blended <= 0, 0.1, blended)

            result[tt] = blended
            print(f"  Skim loaded [{tt}]: shape={blended.shape}, "
                  f"mean_time={blended.mean():.1f} min")

    return result


def load_od_matrix(od_path: Path) -> ODData:
    """
    Load observed OD trip matrices from an OMX file.
    Used for validation and optionally for deriving P/A.
    """
    od_path = Path(od_path)
    result: ODData = {}

    with omx.open_file(str(od_path), "r") as f:
        for tt in TRUCK_TYPES:
            table = OD_TABLE_NAMES[tt]
            od = _load_skim_matrix(f, table, od_path.name)
            result[tt] = od
            print(f"  OD loaded [{tt}]: shape={od.shape}, "
                  f"total_trips={od.sum():.0f}")

    return result


def pa_from_od(od_data: ODData) -> PAData:
    """
    Derive P and A from OD matrix row/column sums.
    Temporary convenience function — replace with load_pa() once
    the trip generation model outputs are available.

    P_i = sum over j of T_ij  (row sum = origin totals)
    A_j = sum over i of T_ij  (col sum = destination totals)
    """
    result: PAData = {}
    for tt, od in od_data.items():
        P = od.sum(axis=1).astype(np.float64)
        A = od.sum(axis=0).astype(np.float64)
        result[tt] = {"P": P, "A": A}
        print(f"  PA from OD [{tt}]: P={P.sum():.0f}, A={A.sum():.0f}")
    return result


def load_observed_tlfd(tlfd_path: Path) -> TLFDData:
    """
    Load observed TLFD from CSV.

    Expected format:
        bin_start, light_trucks_share, medium_trucks_share, heavy_trucks_share

    bin_start values should match TLFD_BINS[:-1] (left edges of bins).
    Shares are normalized to sum to 1 per truck type.
    """
    tlfd_path = Path(tlfd_path)
    df = pd.read_csv(tlfd_path)

    result: TLFDData = {}
    n_bins = len(TLFD_BINS) - 1

    for tt in TRUCK_TYPES:
        col = f"{tt}_share"
        if col not in df.columns:
            raise ValueError(
                f"TLFD file missing column '{col}'. "
                f"Available: {list(df.columns)}"
            )

        shares = df[col].to_numpy(dtype=np.float64)

        if len(shares) != n_bins:
            raise ValueError(
                f"TLFD for {tt} has {len(shares)} bins, "
                f"expected {n_bins} (from TLFD_BINS in config.py)."
            )

        # Normalize in case shares don't exactly sum to 1
        shares = shares / shares.sum()
        result[tt] = shares
        print(f"  TLFD loaded [{tt}]: {n_bins} bins, "
              f"mean_time≈{_tlfd_mean(shares):.1f} min")

    return result


def _tlfd_mean(shares: np.ndarray) -> float:
    """Approximate mean travel time from TLFD shares and bin midpoints."""
    bin_mids = 0.5 * (TLFD_BINS[:-1] + TLFD_BINS[1:])
    return float(np.dot(shares, bin_mids))
