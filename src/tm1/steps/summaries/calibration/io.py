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
from pathlib import Path

import numpy as np
import polars as pl

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Canonical column maps  (format → table → {source_col: canonical_col})
# Only columns that actually differ from canonical need to be listed.
# Columns already in canonical form pass through untouched.
# ---------------------------------------------------------------------------

COLUMN_MAPS: dict[str, dict[str, dict[str, str]]] = {
    "ctramp": {
        "taz_data": {"ZONE": "zone", "COUNTY": "county"},
        "dist_skim": {"DIST": "dist"},
        "households": {"HHID": "hh_id", "TAZ": "home_taz"},
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
    },
    # TODO: populate when ActivitySim column names are finalised
    "activitysim": {
        "taz_data": {"ZONE": "zone", "COUNTY": "county"},
        "dist_skim": {"DIST": "dist"},
    },
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def read_skim(path: str | Path) -> pl.LazyFrame:
    """Read a distance-skim file and return a 3-column LazyFrame (orig, dest, DIST).

    Dispatches by file extension:
    * ``.csv`` — expects columns ``orig``, ``dest``, ``DIST``.
    * ``.tpp`` — Cube binary; uses ``cubeio.tpp``.
    * ``.omx``  — OpenMatrix; uses ``openmatrix``.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_skim_csv(path)
    if suffix == ".tpp":
        return _read_skim_tpp(path)
    if suffix == ".omx":
        return _read_skim_omx(path)
    msg = f"Unsupported skim format: {suffix}"
    raise ValueError(msg)


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
        weight_col=cfg.weight_col,
        source_paths={k: str(v) for k, v in cfg.paths.items()},
    )

    for table_name, raw_path in cfg.paths.items():
        resolved = Path(raw_path)
        if table_name == "dist_skim":
            lf = read_skim(resolved)
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

        setattr(bundle, table_name, lf)

    return bundle
