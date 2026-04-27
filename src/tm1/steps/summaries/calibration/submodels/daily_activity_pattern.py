"""Coordinated daily activity pattern (CDAP) calibration — pure summarization logic.

All functions operate on eager ``pl.DataFrame`` inputs and return
``dict[str, pl.DataFrame]``.  No file I/O, no config, no logging.
"""

import polars as pl

from tm1.steps.summaries.calibration.enums import CTRAMPPersonType

PERSON_TYPE_LOOKUP: dict[str, int] = {pt.label: pt.id for pt in CTRAMPPersonType}

# Required bundle fields for this submodel.
REQUIRED_FIELDS = ("cdap_results",)


def summarize(
    cdap_results: pl.DataFrame,
    *,
    weight_col: str | None = None,
    sampleshare: float = 1.0,
) -> dict[str, pl.DataFrame]:
    """Produce CDAP calibration summaries.

    Args:
        cdap_results: Activity pattern data with canonical columns
            ``person_type`` (int id or string label) and
            ``activity_pattern`` (H/M/N).  May also contain a weight column.
        weight_col: Per-record weight column.  When *None*, each record gets
            weight ``1 / sampleshare``.
        sampleshare: Used to derive uniform weight when *weight_col* is None.

    Returns:
        dict with key ``person_type_summary``: wide DataFrame with columns
        ``person_type``, ``H``, ``M``, ``N``.
    """
    df = cdap_results

    # Normalize person type column to integer IDs if it contains string labels
    if df.schema["person_type"] == pl.Utf8:
        df = df.with_columns(
            pl.col("person_type")
            .replace_strict(PERSON_TYPE_LOOKUP, default=None)
            .alias("person_type"),
        )

    # Assign weight
    if weight_col is None:
        weight = "_weight"
        df = df.with_columns(pl.lit(1.0 / sampleshare).alias(weight))
    else:
        weight = weight_col

    # Aggregate: person_type x activity_pattern -> sum of weights
    grouped = (
        df.filter(pl.col("person_type").is_not_null())
        .group_by("person_type", "activity_pattern")
        .agg(pl.col(weight).sum().alias("num_pers"))
    )

    # Pivot to wide: person_type x (H, M, N)
    wide = (
        grouped.pivot(on="activity_pattern", index="person_type", values="num_pers")
        .fill_null(0.0)
        .sort("person_type")
    )

    # Ensure H, M, N columns exist
    for col in ("H", "M", "N"):
        if col not in wide.columns:
            wide = wide.with_columns(pl.lit(0.0).alias(col))

    wide = wide.select("person_type", "H", "M", "N")

    return {"person_type_summary": wide}
