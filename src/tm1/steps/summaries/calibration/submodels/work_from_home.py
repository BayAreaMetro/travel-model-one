"""Work from home calibration — pure summarization logic.

All functions operate on eager ``pl.DataFrame`` inputs and return
``dict[str, pl.DataFrame]``.  No file I/O, no config, no logging.
"""

import polars as pl

from tm1.steps.summaries.calibration.enums import CTRAMPCounty

COUNTY_LOOKUP: dict[int, str] = {c.id: c.label for c in CTRAMPCounty}

# Required bundle fields for this submodel.
REQUIRED_FIELDS = ("cdap_results", "households", "taz_data")


def summarize(
    cdap_results: pl.DataFrame,
    households: pl.DataFrame,
    taz_data: pl.DataFrame,
    *,
    sampleshare: float = 1.0,
) -> dict[str, pl.DataFrame]:
    """Produce WFH calibration summaries.

    Args:
        cdap_results: Person-level data with ``hh_id``, ``person_type`` or
            ``ptype``, and ``work_from_home`` (0/1 or bool).
        households: Needs ``hh_id``, ``home_taz``.
        taz_data: Needs ``zone``, ``county``.
        sampleshare: Uniform weight = 1/sampleshare per record.

    Returns:
        dict with keys: ``county_summary``, ``overall_summary``.
    """
    weight = 1.0 / sampleshare

    # Determine person type column
    ptype_col = "person_type" if "person_type" in cdap_results.columns else "ptype"

    # Filter to workers only (ptype 1 or 2, or labels containing worker)
    workers = cdap_results.filter(_worker_filter(ptype_col))

    # Ensure work_from_home is numeric
    if "work_from_home" not in workers.columns:
        # No WFH data available — return empty summaries
        return {
            "county_summary": pl.DataFrame(schema={"county_name": pl.Utf8, "workers": pl.Float64, "wfh": pl.Float64, "wfh_rate": pl.Float64}),
            "overall_summary": pl.DataFrame(schema={"category": pl.Utf8, "workers": pl.Float64, "wfh": pl.Float64, "wfh_rate": pl.Float64}),
        }

    workers = workers.with_columns(
        pl.col("work_from_home").cast(pl.Int64).alias("wfh_flag"),
    )

    # Join home_taz from households
    workers = workers.join(
        households.select("hh_id", "home_taz"),
        on="hh_id",
        how="left",
    )

    # Join county from taz_data
    taz_county = taz_data.select(
        pl.col("zone").cast(pl.Int64),
        pl.col("county").cast(pl.Int64),
    )
    workers = workers.join(
        taz_county.rename({"zone": "home_taz"}),
        on="home_taz",
        how="left",
    )
    workers = workers.with_columns(
        pl.col("county")
        .replace_strict(COUNTY_LOOKUP, default="Unknown")
        .alias("county_name"),
    )

    # -- County summary ----------------------------------------------------
    county_summary = (
        workers.group_by("county", "county_name")
        .agg(
            (pl.len() * weight).alias("workers"),
            (pl.col("wfh_flag").sum() * weight).alias("wfh"),
        )
        .with_columns(
            (pl.col("wfh") / pl.col("workers")).alias("wfh_rate"),
        )
        .sort("county")
    )

    # -- Overall summary (by person type) ----------------------------------
    overall_summary = (
        workers.group_by(ptype_col)
        .agg(
            (pl.len() * weight).alias("workers"),
            (pl.col("wfh_flag").sum() * weight).alias("wfh"),
        )
        .with_columns(
            (pl.col("wfh") / pl.col("workers")).alias("wfh_rate"),
        )
        .rename({ptype_col: "category"})
        .with_columns(pl.col("category").cast(pl.Utf8))
        .sort("category")
    )

    # Add total row
    total = pl.DataFrame({
        "category": ["Total"],
        "workers": [county_summary["workers"].sum()],
        "wfh": [county_summary["wfh"].sum()],
        "wfh_rate": [county_summary["wfh"].sum() / county_summary["workers"].sum()],
    })
    overall_summary = pl.concat([overall_summary, total])

    return {
        "county_summary": county_summary,
        "overall_summary": overall_summary,
    }


def _worker_filter(ptype_col: str) -> pl.Expr:
    """Return filter expression for workers (FT=1, PT=2 or string labels)."""
    return (
        pl.col(ptype_col).is_in([1, 2])
        | pl.col(ptype_col).cast(pl.Utf8).str.contains("(?i)worker")
    )
