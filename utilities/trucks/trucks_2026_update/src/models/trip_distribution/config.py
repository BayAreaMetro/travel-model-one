"""
config.py
---------
Central place for all constants. Edit here when inputs change
(e.g. new truck type names, different toll-part fraction, new time periods).
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple

# ── Truck types ────────────────────────────────────────────────────────────────
# These must match the column names in the PA parquet file and the
# table names inside the OMX skims and OD matrix.
TRUCK_TYPES = ["light_trucks", "medium_trucks", "heavy_trucks"]

# ── Blended impedance weights ──────────────────────────────────────────────────
# Blended time = AM_weight * t_AM + MD_weight * t_MD
# MTC convention: 1/3 AM peak, 2/3 midday (trucks make more trips midday)
BLEND_WEIGHTS: Dict[str, float] = {
    "AM": 1.0 / 3.0,
    "MD": 2.0 / 3.0,
}

# ── Toll blend fraction ────────────────────────────────────────────────────────
# Share of impedance from tolled skims vs free skims.
# Set to 0.0 to ignore toll skims entirely.
TRUCK_DISTRIB_LOS_TOLL_PART: float = 0.0

# ── OMX skim table names ───────────────────────────────────────────────────────
# Keys are (time_period, truck_type).
# Adjust if your OMX internal table names differ.
SKIM_TABLE_NAMES: Dict[Tuple[str, str], str] = {
    ("AM", "light_trucks"):  "timeLT",
    ("AM", "medium_trucks"): "timeMT",
    ("AM", "heavy_trucks"):  "timeHT",
    ("MD", "light_trucks"):  "timeLT",
    ("MD", "medium_trucks"): "timeMT",
    ("MD", "heavy_trucks"):  "timeHT",
}

# Toll skim table names (only used when TRUCK_DISTRIB_LOS_TOLL_PART > 0)
TOLL_SKIM_TABLE_NAMES: Dict[Tuple[str, str], str] = {
    ("AM", "light_trucks"):  "tolltimeLT",
    ("AM", "medium_trucks"): "tolltimeMT",
    ("AM", "heavy_trucks"):  "tolltimeHT",
    ("MD", "light_trucks"):  "tolltimeLT",
    ("MD", "medium_trucks"): "tolltimeMT",
    ("MD", "heavy_trucks"):  "tolltimeHT",
}

# ── OD matrix table names (inside the OD OMX file) ────────────────────────────
OD_TABLE_NAMES: Dict[str, str] = {
    "light_trucks":  "light_trucks",
    "medium_trucks": "medium_trucks",
    "heavy_trucks":  "heavy_trucks",
}

# ── TLFD bins ──────────────────────────────────────────────────────────────────
# Must match the bins in your observed TLFD CSV.
import numpy as np
TLFD_BINS = np.arange(0, 125, 5)   # [0,5), [5,10), ..., [120,125)

# ── Gravity model convergence ──────────────────────────────────────────────────
GRAVITY_MAX_ITERS: int = 99
GRAVITY_MAX_RMSE: float = 10.0

# ── Gamma calibration ─────────────────────────────────────────────────────────
# NCHRP 365-based starting values for (b, c) per truck type.
# a is fixed at 1.0 (cancels in gravity denominator).
GAMMA_INITIAL_PARAMS: Dict[str, Tuple[float, float]] = {
    "light_trucks":  (-0.50, -0.05),
    "medium_trucks": (-1.00, -0.03),
    "heavy_trucks":  (-1.20, -0.02),
}

# Search bounds for scipy optimizer: b in (-3, -0.01), c in (-0.5, -0.001)
GAMMA_BOUNDS = [(-3.0, -0.01), (-0.5, -0.001)]

# ── Output scaling ─────────────────────────────────────────────────────────────
# MTC convention: multiply final trip table by 100 for legacy consistency.
# Set to 1.0 to keep natural units.
OUTPUT_SCALE_FACTOR: float = 1.0
