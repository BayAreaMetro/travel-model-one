"""Typed data bundle for calibration summaries.

A ModelBundle holds all the "model tables" for one labeled dataset (e.g. a
CTRAMP run, an ActivitySim run, or a BATS survey).  Fields are Optional so
that a survey bundle can omit tables it doesn't produce — submodel functions
simply check whether the fields they need are present.
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
        weight_col: If the data carries per-record weights (e.g. survey
            ``person_weight``), name that column here.  When *None* the
            summarize functions use ``1 / sampleshare`` as a uniform weight.

    Convention: tables are stored as ``pl.LazyFrame`` so the actual read is
    deferred until a submodel ``.collect()``s only the columns it needs.
    Binary formats (TPP, OMX) are read eagerly then wrapped with ``.lazy()``.
    """

    # ---- identity --------------------------------------------------------
    label: str
    sampleshare: float = 1.0
    weight_col: str | None = None

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

    # ---- input paths (for provenance / logging) --------------------------
    source_paths: dict[str, str] = field(default_factory=dict)
