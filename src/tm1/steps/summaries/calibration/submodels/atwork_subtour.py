"""At-work subtour calibration — TLFD and mode shares for at-work subtours only."""

import logging

import polars as pl

log = logging.getLogger(__name__)

REQUIRED_FIELDS = ("indiv_tour_data", "ao_results", "households", "dist_skim")

# All purpose labels that identify at-work subtours across CTRAMP and ActivitySim
_ATWORK_PURPOSES = ["atwork_business", "atwork_eat", "atwork_maint", "atwork"]

_MAX_DIST = 25


def summarize(
    indiv_tour_data: pl.DataFrame,
    ao_results: pl.DataFrame,
    households: pl.DataFrame,
    dist_skim: pl.DataFrame,
    *,
    weight_col: str | None = None,
    sampleshare: float = 1.0,
) -> dict[str, pl.DataFrame]:
    """At-work subtour calibration summaries.

    Returns dict with keys:
        ``atwork_tlfd`` — TLFD (distbin × Total) for at-work subtours.
        ``atwork_avg_trip_length`` — single-row average distance.
        ``atwork_mode_summary`` — mode shares by auto_sufficiency.
    """
    weight = 1.0 / sampleshare

    # Filter to at-work tours only
    tours = indiv_tour_data.filter(pl.col("tour_purpose").is_in(_ATWORK_PURPOSES))
    if tours.height == 0:
        found_purposes = indiv_tour_data["tour_purpose"].unique().sort().to_list()
        log.warning(
            "atwork_subtour: found 0 at-work tours in indiv_tour_data "
            "(n=%d). Expected tour_purpose in %s, but found: %s. "
            "This is expected for survey data but indicates a bug for "
            "model output.",
            indiv_tour_data.height, _ATWORK_PURPOSES, found_purposes,
        )
        return {}

    # --- Weight handling ---
    wcol = weight_col if weight_col is not None else "_weight"
    if weight_col is None:
        tours = tours.with_columns(pl.lit(weight).alias("_weight"))

    # --- TLFD: trip length frequency distribution ---
    dist_col = "DIST" if "DIST" in dist_skim.columns else "dist"
    skim = dist_skim.select(
        pl.col("orig").cast(pl.Int64),
        pl.col("dest").cast(pl.Int64),
        pl.col(dist_col).cast(pl.Float64).alias("DIST"),
    )
    tours_with_dist = tours.join(
        skim,
        left_on=["orig_taz", "dest_taz"],
        right_on=["orig", "dest"],
        how="left",
    )

    avg_dist = (
        tours_with_dist.select(
            (pl.col("DIST") * pl.col(wcol)).sum() / pl.col(wcol).sum(),
        ).item()
    )

    binned = (
        tours_with_dist.filter(pl.col("DIST").is_not_null())
        .with_columns(
            pl.col("DIST").clip(0.5, _MAX_DIST + 0.5).round(0).cast(pl.Int64).alias("distbin"),
        )
        .group_by("distbin")
        .agg(pl.col(wcol).sum().alias("Total"))
    )
    all_bins = pl.DataFrame({"distbin": list(range(1, _MAX_DIST + 1))})
    tlfd = all_bins.join(binned, on="distbin", how="left").fill_null(0).sort("distbin")

    # --- Mode shares by auto sufficiency ---
    ao = ao_results.select("hh_id", "auto_ownership")
    hh_info = households.select("hh_id")
    if "hworkers" in households.columns:
        hh_info = households.select("hh_id", "hworkers")
    else:
        hh_info = hh_info.with_columns(pl.lit(1).alias("hworkers"))

    mode_tours = tours.join(ao, on="hh_id", how="left")
    mode_tours = mode_tours.join(hh_info.select("hh_id", "hworkers"), on="hh_id", how="left")

    mode_tours = mode_tours.with_columns(
        pl.when(pl.col("auto_ownership").fill_null(0) == 0)
        .then(pl.lit("Zero-auto"))
        .when(
            pl.col("auto_ownership").fill_null(0)
            < pl.col("hworkers").fill_null(1)
        )
        .then(pl.lit("Autos < Workers"))
        .otherwise(pl.lit("Autos >= Workers"))
        .alias("auto_suff"),
    )

    # Weight expression
    if weight_col is not None:
        w_expr = pl.col(weight_col).sum()
    else:
        w_expr = pl.col("_weight").sum()

    mode_summary = (
        mode_tours.group_by("tour_mode", "auto_suff")
        .agg(w_expr.alias("num_tours"))
        .sort("tour_mode", "auto_suff")
    )

    return {
        "atwork_tlfd": tlfd,
        "atwork_avg_trip_length": pl.DataFrame([{"avg_trip_length": avg_dist}]),
        "atwork_mode_summary": mode_summary,
    }
