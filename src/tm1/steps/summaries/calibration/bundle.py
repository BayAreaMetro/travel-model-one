"""Typed data bundle for calibration summaries.

A ModelBundle holds all the "model tables" for one labeled dataset (e.g. a
CTRAMP run, an ActivitySim run, or a BATS survey).  Fields are Optional so
that a survey bundle can omit tables it doesn't produce — submodel functions
simply check whether the fields they need are present.

Weighting is **either** a uniform ``sampleshare`` expansion *or* explicit
per-table ``weight_cols`` — never both.  ``get_weight_col()`` returns the
column name for a given table, or *None* when uniform weighting is in effect.
"""

from dataclasses import dataclass, field

import polars as pl


@dataclass
class ModelBundle:
    """All tables for one labeled dataset.

    Attributes:
        label: Human-readable identifier (e.g. "CTRAMP_v161", "BATS_2023").
        sampleshare: Population fraction.  1.0 for census/survey, 0.5 for 50%
            synthetic-population sample, etc.
        weight_cols: Mapping of table_name → weight column name.  When
            non-empty, ``sampleshare`` must be 1.0.  No "default" fallback —
            every table that needs a weight must be listed explicitly.

    Convention: tables are stored as ``pl.LazyFrame`` so the actual read is
    deferred until a submodel ``.collect()``s only the columns it needs.
    Binary formats (TPP, OMX) are read eagerly then wrapped with ``.lazy()``.
    """

    # ---- identity --------------------------------------------------------
    label: str
    sampleshare: float = 1.0
    weight_cols: dict[str, str] = field(default_factory=dict)

    def get_weight_col(self, table_name: str) -> str | None:
        """Return the weight column for *table_name*, or *None* for uniform weighting."""
        return self.weight_cols.get(table_name)

    # ---- shared / geography ----------------------------------------------
    taz_data: pl.LazyFrame | None = None
    dist_skim: pl.LazyFrame | None = None

    # ---- population tables -----------------------------------------------
    persons: pl.LazyFrame | None = None
    households: pl.LazyFrame | None = None

    # ---- CTRAMP / ActivitySim model outputs ------------------------------
    wsloc_results: pl.LazyFrame | None = None
    ao_results: pl.LazyFrame | None = None
    cdap_results: pl.LazyFrame | None = None
    indiv_tour_data: pl.LazyFrame | None = None
    joint_tour_data: pl.LazyFrame | None = None
    indiv_trip_data: pl.LazyFrame | None = None
    joint_trip_data: pl.LazyFrame | None = None

    # ---- input paths (for provenance / logging) --------------------------
    source_paths: dict[str, str] = field(default_factory=dict)
