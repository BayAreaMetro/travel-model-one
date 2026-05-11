"""Unified data readers for calibration summaries.

Handles CSV, TPP (Cube binary), and OMX skim formats behind a single
interface.  All readers return ``pl.LazyFrame`` so downstream code can
select only the columns it needs before collecting.

Column names are normalised to **canonical** (snake_case, platform-neutral)
names on load via :data:`COLUMN_MAPS` so that downstream summarize functions
never need to know the source format.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
import polars as pl

from tm1.steps.summaries.ctramp_output import MODE_TO_INT, PTYPE_LABELS

log = logging.getLogger(__name__)

# Cache for expensive skim reads keyed by resolved absolute path.
# Populated by read_skim(); cleared between runs if needed.
_skim_cache: dict[str, pl.LazyFrame] = {}


# ---------------------------------------------------------------------------
# Canonical column maps  (format → table → {source_col: canonical_col})
# Only columns that actually differ from canonical need to be listed.
# Columns already in canonical form pass through untouched.
# ---------------------------------------------------------------------------

COLUMN_MAPS: dict[str, dict[str, dict[str, str]]] = {
    "ctramp": {
        "taz_data": {"ZONE": "zone", "COUNTY": "county"},
        "dist_skim": {"DIST": "dist"},
        "households": {"HHID": "hh_id", "TAZ": "home_taz", "taz": "home_taz"},
        "persons": {
            "HHID": "hh_id",
            "PersonID": "person_id",
            "PersonType": "person_type",
            "ActivityString": "activity_pattern",
        },
        "ao_results": {"HHID": "hh_id", "AO": "auto_ownership"},
        "wsloc_results": {
            "HHID": "hh_id",
            "PersonID": "person_id",
            "HomeTAZ": "home_taz",
            "WorkLocation": "work_location",
            "SchoolLocation": "school_location",
            "StudentCategory": "student_category",
            "EmploymentCategory": "employment_category",
        },
        "cdap_results": {
            "HHID": "hh_id",
            "PersonID": "person_id",
            "PersonType": "person_type",
            "ActivityString": "activity_pattern",
        },
        "indiv_tour_data": {},
        "joint_tour_data": {},
        "indiv_trip_data": {},
        "joint_trip_data": {},
    },
    # TODO: populate when ActivitySim column names are finalised
    "activitysim": {
        "taz_data": {"ZONE": "zone", "COUNTY": "county"},
        "dist_skim": {"DIST": "dist"},
        "households": {
            "household_id": "hh_id",
            "home_zone_id": "home_taz",
            "num_workers": "hworkers",
        },
        "ao_results": {
            "household_id": "hh_id",
        },
        "cdap_results": {
            "household_id": "hh_id",
            "person_id": "person_id",
            "cdap_activity": "activity_pattern",
        },
        "wsloc_results": {
            "household_id": "hh_id",
            "person_id": "person_id",
            "home_zone_id": "home_taz",
            "workplace_zone_id": "work_location",
            "school_zone_id": "school_location",
        },
        "indiv_tour_data": {
            "household_id": "hh_id",
            "primary_purpose": "tour_purpose",
            "origin": "orig_taz",
            "destination": "dest_taz",
        },
        "joint_tour_data": {
            "household_id": "hh_id",
            "primary_purpose": "tour_purpose",
            "origin": "orig_taz",
            "destination": "dest_taz",
        },
        "indiv_trip_data": {
            "household_id": "hh_id",
            "primary_purpose": "tour_purpose",
        },
        "joint_trip_data": {
            "household_id": "hh_id",
            "primary_purpose": "tour_purpose",
        },
    },
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def read_skim(path: str | Path) -> pl.LazyFrame:
    """Read a distance-skim file and return a 3-column LazyFrame (orig, dest, DIST).

    Results are cached by resolved path so the same skim file is only read once
    even when multiple datasets reference it.

    Dispatches by file extension:
    * ``.csv`` — expects columns ``orig``, ``dest``, ``DIST``.
    * ``.tpp`` — Cube binary; uses ``cubeio.tpp``.
    * ``.omx``  — OpenMatrix; uses ``openmatrix``.
    """
    path = Path(path)
    cache_key = str(path.resolve())
    if cache_key in _skim_cache:
        log.info("Using cached skim: %s", path)
        return _skim_cache[cache_key]

    suffix = path.suffix.lower()
    if suffix == ".csv":
        lf = _read_skim_csv(path)
    elif suffix == ".tpp":
        lf = _read_skim_tpp(path)
    elif suffix == ".omx":
        lf = _read_skim_omx(path)
    else:
        msg = f"Unsupported skim format: {suffix}"
        raise ValueError(msg)

    _skim_cache[cache_key] = lf
    return lf


def scan_csv(path: str | Path, **kwargs: object) -> pl.LazyFrame:
    """Thin wrapper around ``pl.scan_csv`` with sensible defaults."""
    return pl.scan_csv(path, **kwargs)


# ---------------------------------------------------------------------------
# Internal skim readers
# ---------------------------------------------------------------------------

def _read_skim_csv(path: Path) -> pl.LazyFrame:
    log.info("Reading CSV skim: %s", path)
    return pl.scan_csv(path).select("orig", "dest", "DIST")


def _read_skim_tpp(path: Path) -> pl.LazyFrame:
    log.info("Reading TPP skim: %s", path)
    from cubeio import tpp  # noqa: PLC0415

    skims = tpp.read_tpp(str(path))
    n_zones = skims["zones"]
    taz_ids = np.arange(1, n_zones + 1)
    orig, dest = np.meshgrid(taz_ids, taz_ids, indexing="ij")
    df = pl.DataFrame({
        "orig": orig.ravel(),
        "dest": dest.ravel(),
        "DIST": skims["data"]["DIST"].ravel(),
    })
    return df.lazy()


def _read_skim_omx(path: Path) -> pl.LazyFrame:
    log.info("Reading OMX skim: %s", path)
    import openmatrix as omx  # noqa: PLC0415

    f = omx.open_file(str(path), "r")
    try:
        dist = np.array(f["DIST"])
        n_zones = dist.shape[0]
        taz_ids = np.arange(1, n_zones + 1)
        orig, dest = np.meshgrid(taz_ids, taz_ids, indexing="ij")
        df = pl.DataFrame({
            "orig": orig.ravel(),
            "dest": dest.ravel(),
            "DIST": dist.ravel(),
        })
    finally:
        f.close()
    return df.lazy()


# ---------------------------------------------------------------------------
# Bundle loader
# ---------------------------------------------------------------------------

def load_bundle(dataset_cfg: object) -> object:
    """Build a :class:`ModelBundle` from a :class:`DatasetConfig`.

    Each key in ``dataset_cfg.paths`` is matched to a ``ModelBundle`` field.
    ``dist_skim`` is handled via :func:`read_skim`; everything else via
    :func:`scan_csv`.  After loading, columns are renamed to canonical names
    according to :data:`COLUMN_MAPS` and ``dataset_cfg.format``.
    """
    from .bundle import ModelBundle  # noqa: PLC0415

    cfg = dataset_cfg
    fmt = getattr(cfg, "format", "ctramp")
    format_maps = COLUMN_MAPS.get(fmt, {})

    bundle = ModelBundle(
        label=cfg.label,
        sampleshare=cfg.sampleshare,
        weight_cols=cfg.weight_cols,
        source_paths={k: str(v) for k, v in cfg.paths.items()},
    )

    for table_name, raw_path in cfg.paths.items():
        resolved = Path(raw_path)
        if not resolved.exists():
            msg = f"Dataset '{cfg.label}': file not found for '{table_name}': {resolved}"
            raise FileNotFoundError(msg)
        t0 = time.perf_counter()
        if table_name == "dist_skim":
            lf = read_skim(resolved)
            log.info("Read skim %s (%.1fs)", resolved.name, time.perf_counter() - t0)
        else:
            log.info("Scanning %s: %s", table_name, resolved)
            lf = scan_csv(resolved)

        # Apply column renames for this format + table
        col_map = format_maps.get(table_name, {})
        if col_map:
            existing = set(lf.collect_schema().names())
            rename = {k: v for k, v in col_map.items() if k in existing}
            if rename:
                lf = lf.rename(rename)

        # ActivitySim-specific post-rename transforms
        if fmt == "activitysim":
            lf = _apply_asim_transforms(table_name, lf)

        # Validate that table_name is a declared ModelBundle field
        _known = {
            "taz_data", "dist_skim", "persons", "households",
            "wsloc_results", "ao_results", "cdap_results",
            "indiv_tour_data", "joint_tour_data",
            "indiv_trip_data", "joint_trip_data",
        }
        if table_name not in _known:
            msg = (
                f"Dataset '{cfg.label}' has path key '{table_name}' which is not "
                f"a recognized ModelBundle field. Known fields: {sorted(_known)}"
            )
            raise ValueError(msg)
        setattr(bundle, table_name, lf)

    return bundle


# ---------------------------------------------------------------------------
# ActivitySim post-rename transforms
# ---------------------------------------------------------------------------

_PTYPE_TO_STUDENT_CAT: dict[int, str] = {
    3: "College or higher",         # University student
    6: "Grade or high school",      # Driving-age student
    7: "Grade or high school",      # Non-driving-age student
    # ptype 8 (preschool) excluded: CTRAMP labels them "Not student" even
    # though they receive a SchoolLocation.  Omitting keeps comparison
    # apples-to-apples.
}


def _apply_asim_transforms(table_name: str, lf: pl.LazyFrame) -> pl.LazyFrame:
    """Convert ActivitySim-specific values to canonical after column renames."""
    cols = set(lf.collect_schema().names())

    if table_name == "cdap_results":
        # ptype int → string label for CDAP
        if "ptype" in cols:
            lf = lf.with_columns(
                pl.col("ptype")
                .replace_strict(PTYPE_LABELS, default="Unknown")
                .alias("person_type"),
            )

    elif table_name == "wsloc_results":
        # Derive student_category from ptype
        if "ptype" in cols:
            lf = lf.with_columns(
                pl.col("ptype")
                .replace_strict(_PTYPE_TO_STUDENT_CAT, default=None)
                .alias("student_category"),
            )

    elif table_name == "indiv_tour_data":
        # Filter to non-joint tours only
        if "tour_category" in cols:
            lf = lf.filter(pl.col("tour_category") != "joint")
        if "tour_mode" in cols:
            lf = lf.with_columns(
                pl.col("tour_mode")
                .replace_strict(MODE_TO_INT, default=0)
                .cast(pl.Int64),
            )

    elif table_name == "joint_tour_data":
        # Filter to joint tours only
        if "tour_category" in cols:
            lf = lf.filter(pl.col("tour_category") == "joint")
        if "tour_mode" in cols:
            lf = lf.with_columns(
                pl.col("tour_mode")
                .replace_strict(MODE_TO_INT, default=0)
                .cast(pl.Int64),
            )
        # Rename number_of_participants → num_participants for submodel compat
        if "number_of_participants" in cols:
            lf = lf.rename({"number_of_participants": "num_participants"})

    elif table_name in ("indiv_trip_data", "joint_trip_data"):
        if "trip_mode" in cols:
            lf = lf.with_columns(
                pl.col("trip_mode")
                .replace_strict(MODE_TO_INT, default=0)
                .cast(pl.Int64),
            )

    return lf
