"""Trip mode choice calibration — pure summarization logic.

Produces trip-count summaries by (simple_purpose × trip_mode),
matching R script ``15_trip_mode_choice_TM.R``.
"""

import polars as pl

from tm1.steps.summaries.calibration.enums import CTRAMPModeType

REQUIRED_FIELDS = ("indiv_trip_data",)

# Purpose simplification: raw CTRAMP purpose → simple category
_SIMPLE_PURPOSE: dict[str, str] = {
    # CTRAMP purpose names
    "atwork_business": "At-Work",
    "atwork_eat": "At-Work",
    "atwork_maint": "At-Work",
    "eatout": "Discretionary",
    "escort_kids": "Maintenance",
    "escort_no kids": "Maintenance",
    "othdiscr": "Discretionary",
    "othmaint": "Maintenance",
    "school_grade": "School",
    "school_high": "School",
    "shopping": "Maintenance",
    "social": "Discretionary",
    "university": "University",
    "work_high": "Work",
    "work_low": "Work",
    "work_med": "Work",
    "work_very high": "Work",
    # ActivitySim purpose names
    "atwork": "At-Work",
    "escort": "Maintenance",
    "school": "School",
    "univ": "University",
    "work": "Work",
}

MODE_LABELS: dict[int, str] = {m.id: m.label for m in CTRAMPModeType}


def summarize(
    indiv_trip_data: pl.DataFrame,
    *,
    joint_trip_data: pl.DataFrame | None = None,
    weight_col: str | None = None,
    sampleshare: float = 1.0,
) -> dict[str, pl.DataFrame]:
    """Trip mode choice calibration summary.

    Returns dict with key ``trip_mode_summary``:
        Columns: simple_purpose, trip_mode, trip_mode_label, num_trips.
    """
    weight = 1.0 / sampleshare

    # Validate weight_col up front if specified
    if weight_col is not None and weight_col not in indiv_trip_data.columns:
        msg = (
            f"weight_col {weight_col!r} not found in indiv_trip_data "
            f"columns: {indiv_trip_data.columns}"
        )
        raise ValueError(msg)

    # Stack indiv + joint trips
    base_cols = ["hh_id", "tour_purpose", "trip_mode"]
    if weight_col is not None:
        base_cols.append(weight_col)

    indiv = indiv_trip_data.select(base_cols).with_columns(
        pl.lit(1).cast(pl.Int64).alias("num_participants"),
    )

    if joint_trip_data is not None:
        jcols = [c for c in base_cols if c in joint_trip_data.columns]
        if "num_participants" in joint_trip_data.columns:
            joint = joint_trip_data.select(jcols + ["num_participants"])
        else:
            joint = joint_trip_data.select(jcols).with_columns(
                pl.lit(1).alias("num_participants"),
            )
        trips = pl.concat([indiv, joint])
    else:
        trips = indiv

    trips = trips.with_columns(
        pl.col("tour_purpose")
        .replace_strict(_SIMPLE_PURPOSE, default="Other")
        .alias("simple_purpose"),
        pl.col("trip_mode")
        .cast(pl.Int64)
        .replace_strict(MODE_LABELS, default="Unknown")
        .alias("trip_mode_label"),
    )

    # Weight
    if weight_col is not None:
        w_expr = (pl.col(weight_col) * pl.col("num_participants")).sum()
    else:
        w_expr = (pl.lit(weight) * pl.col("num_participants")).sum()

    summary = (
        trips.group_by("simple_purpose", "trip_mode", "trip_mode_label")
        .agg(w_expr.alias("num_trips"))
        .sort("simple_purpose", "trip_mode")
    )

    return {"trip_mode_summary": summary}
