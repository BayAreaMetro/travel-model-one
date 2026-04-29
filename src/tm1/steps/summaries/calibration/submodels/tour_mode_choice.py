"""Tour mode choice calibration — pure summarization logic.

Produces tour-count summaries by (simple_purpose × tour_mode × auto_sufficiency),
matching R script ``11_tour_mode_choice_TM.R``.
"""

import polars as pl

from tm1.steps.summaries.calibration.enums import CTRAMPModeType

REQUIRED_FIELDS = ("indiv_tour_data", "ao_results", "households")

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


def _auto_suff(ao: int, hworkers: int) -> str:
    if ao == 0:
        return "Zero-auto"
    if ao < hworkers:
        return "Autos < Workers"
    return "Autos >= Workers"


def summarize(
    indiv_tour_data: pl.DataFrame,
    ao_results: pl.DataFrame,
    households: pl.DataFrame,
    *,
    joint_tour_data: pl.DataFrame | None = None,
    weight_col: str | None = None,
    sampleshare: float = 1.0,
) -> dict[str, pl.DataFrame]:
    """Tour mode choice calibration summary.

    Returns dict with key ``tour_mode_summary``:
        Columns: simple_purpose, tour_mode, tour_mode_label, auto_suff, num_tours.
    """
    weight = 1.0 / sampleshare

    # Validate weight_col up front if specified
    if weight_col is not None and weight_col not in indiv_tour_data.columns:
        msg = (
            f"weight_col {weight_col!r} not found in indiv_tour_data "
            f"columns: {indiv_tour_data.columns}"
        )
        raise ValueError(msg)

    # Stack indiv + joint tours
    indiv_cols = ["hh_id", "tour_purpose", "tour_mode"]
    if weight_col is not None:
        indiv_cols.append(weight_col)
    indiv = indiv_tour_data.select(indiv_cols).with_columns(
        pl.lit(1).cast(pl.UInt32).alias("num_participants"),
    )

    if joint_tour_data is not None:
        jcols = ["hh_id", "tour_purpose", "tour_mode"]
        if weight_col is not None:
            if weight_col not in joint_tour_data.columns:
                msg = (
                    f"weight_col {weight_col!r} not found in joint_tour_data "
                    f"columns: {joint_tour_data.columns}"
                )
                raise ValueError(msg)
            jcols.append(weight_col)
        # joint tours: count participants via tour_participants if available
        if "tour_participants" in joint_tour_data.columns:
            joint = joint_tour_data.select(
                [c for c in jcols if c in joint_tour_data.columns]
                + ["tour_participants"],
            ).with_columns(
                pl.col("tour_participants")
                .cast(pl.Utf8)
                .str.split(" ")
                .list.len()
                .alias("num_participants"),
            ).drop("tour_participants")
        else:
            joint = joint_tour_data.select(
                [c for c in jcols if c in joint_tour_data.columns],
            ).with_columns(pl.lit(1).cast(pl.UInt32).alias("num_participants"))
        tours = pl.concat([indiv, joint])
    else:
        tours = indiv

    # Add auto sufficiency via AO + HH workers
    hh_info = households.select("hh_id", "home_taz")
    if "hworkers" in households.columns:
        hh_info = households.select("hh_id", "home_taz", "hworkers")
    elif "PERSONS" in households.columns:
        hh_info = households.select("hh_id", "home_taz").with_columns(
            pl.lit(1).alias("hworkers"),
        )
    else:
        hh_info = hh_info.with_columns(pl.lit(1).alias("hworkers"))

    ao = ao_results.select("hh_id", "auto_ownership")
    tours = tours.join(ao, on="hh_id", how="left")
    tours = tours.join(hh_info.select("hh_id", "hworkers"), on="hh_id", how="left")

    tours = tours.with_columns(
        pl.when(pl.col("auto_ownership").fill_null(0) == 0)
        .then(pl.lit("Zero-auto"))
        .when(
            pl.col("auto_ownership").fill_null(0)
            < pl.col("hworkers").fill_null(1)
        )
        .then(pl.lit("Autos < Workers"))
        .otherwise(pl.lit("Autos >= Workers"))
        .alias("auto_suff"),
        pl.col("tour_purpose")
        .replace_strict(_SIMPLE_PURPOSE, default="Other")
        .alias("simple_purpose"),
        pl.col("tour_mode")
        .replace_strict(MODE_LABELS, default="Unknown")
        .alias("tour_mode_label"),
    )

    # Weight column
    if weight_col is not None:
        w_expr = (pl.col(weight_col) * pl.col("num_participants")).sum()
    else:
        w_expr = (pl.lit(weight) * pl.col("num_participants")).sum()

    summary = (
        tours.group_by("simple_purpose", "tour_mode", "tour_mode_label", "auto_suff")
        .agg(w_expr.alias("num_tours"))
        .sort("simple_purpose", "tour_mode", "auto_suff")
    )

    return {"tour_mode_summary": summary}
