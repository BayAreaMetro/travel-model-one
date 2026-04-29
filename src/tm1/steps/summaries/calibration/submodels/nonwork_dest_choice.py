"""Non-work destination choice calibration — pure summarization logic.

Produces trip-length frequency distributions and average trip lengths
for each non-work tour purpose, matching R script ``09_nonwork_destination_choice_TM.R``.
"""

import polars as pl

REQUIRED_FIELDS = ("indiv_tour_data", "dist_skim")

# Purpose grouping: display_name → list of raw CTRAMP/ActivitySim tour_purpose values
PURPOSE_GROUPS: dict[str, list[str]] = {
    "Escort": ["escort_kids", "escort_no kids", "escort"],
    "Shopping": ["shopping"],
    "Maintenance": ["othmaint"],
    "Eating Out": ["eatout"],
    "Visiting": ["social"],
    "Discretionary": ["othdiscr"],
    "At-Work": ["atwork_business", "atwork_eat", "atwork_maint", "atwork"],
}

_MAX_DIST = 25


def _combine_tours(
    indiv: pl.DataFrame,
    joint: pl.DataFrame | None,
    weight_col: str | None,
    sampleshare: float,
) -> pl.DataFrame:
    """Stack individual + joint tours with a weight column.

    If *weight_col* is given it must exist in *indiv* (and *joint* if present).
    Otherwise a uniform ``_weight = 1/sampleshare`` column is created.
    """
    keep = ["hh_id", "tour_purpose", "orig_taz", "dest_taz"]
    if weight_col is not None:
        if weight_col not in indiv.columns:
            msg = (
                f"weight_col {weight_col!r} not found in indiv_tour_data "
                f"columns: {indiv.columns}"
            )
            raise ValueError(msg)
        keep.append(weight_col)

    tours = indiv.select(keep)
    if joint is not None:
        if weight_col is not None and weight_col not in joint.columns:
            msg = (
                f"weight_col {weight_col!r} not found in joint_tour_data "
                f"columns: {joint.columns}"
            )
            raise ValueError(msg)
        tours = pl.concat([tours, joint.select(keep)])

    if weight_col is None:
        tours = tours.with_columns(pl.lit(1.0 / sampleshare).alias("_weight"))
    return tours


def summarize(
    indiv_tour_data: pl.DataFrame,
    dist_skim: pl.DataFrame,
    *,
    joint_tour_data: pl.DataFrame | None = None,
    weight_col: str | None = None,
    sampleshare: float = 1.0,
) -> dict[str, pl.DataFrame]:
    """Produce non-work destination choice calibration summaries.

    Returns dict with keys:
        ``nwdc_avg_trip_lengths`` — average distance per purpose.
        ``nwdc_tlfd_{purpose}``  — TLFD (distbin × Total) per purpose.
    """
    weight = 1.0 / sampleshare
    tours = _combine_tours(indiv_tour_data, joint_tour_data, weight_col, sampleshare)
    wcol = weight_col if weight_col is not None else "_weight"

    # Join distances
    # Canonical skim columns after io.py renaming: orig, dest, dist
    dist_col = "DIST" if "DIST" in dist_skim.columns else "dist"
    skim = dist_skim.select(
        pl.col("orig").cast(pl.Int64),
        pl.col("dest").cast(pl.Int64),
        pl.col(dist_col).cast(pl.Float64).alias("DIST"),
    )
    tours = tours.join(
        skim,
        left_on=["orig_taz", "dest_taz"],
        right_on=["orig", "dest"],
        how="left",
    )

    results: dict[str, pl.DataFrame] = {}
    avg_rows: list[dict] = []

    for display_name, purposes in PURPOSE_GROUPS.items():
        subset = tours.filter(pl.col("tour_purpose").is_in(purposes))
        if subset.height == 0:
            continue

        key = display_name.lower().replace("-", "").replace(" ", "_")

        # Weighted average trip length
        avg_dist = (
            subset.select(
                (pl.col("DIST") * pl.col(wcol)).sum()
                / pl.col(wcol).sum(),
            )
            .item()
        )
        avg_rows.append({"purpose": display_name, "avg_trip_length": avg_dist})

        # TLFD: 1-mile bins from 1
        binned = (
            subset.filter(pl.col("DIST").is_not_null())
            .with_columns(
                pl.col("DIST").clip(0.5, _MAX_DIST + 0.5).round(0).cast(pl.Int64).alias("distbin"),
            )
            .group_by("distbin")
            .agg(pl.col(wcol).sum().alias("Total"))
        )

        # Ensure all bins present
        all_bins = pl.DataFrame({"distbin": list(range(1, _MAX_DIST + 1))})
        tlfd = all_bins.join(binned, on="distbin", how="left").fill_null(0).sort("distbin")
        results[f"nwdc_tlfd_{key}"] = tlfd

    results["nwdc_avg_trip_lengths"] = pl.DataFrame(avg_rows)
    return results
