"""Auto ownership calibration — pure summarization logic.

All functions operate on eager ``pl.DataFrame`` inputs and return
``dict[str, pl.DataFrame]``.  No file I/O, no config, no logging.
"""

import polars as pl

from tm1.steps.summaries.calibration.enums import CTRAMPCounty

COUNTY_LOOKUP: dict[int, str] = {c.id: c.label for c in CTRAMPCounty}

# Required bundle fields for this submodel.
REQUIRED_FIELDS = ("households", "ao_results", "taz_data")


def summarize(
    households: pl.DataFrame,
    ao_results: pl.DataFrame,
    taz_data: pl.DataFrame,
    *,
    sampleshare: float = 1.0,
) -> dict[str, pl.DataFrame]:
    """Produce auto-ownership calibration summaries.

    Args:
        households: Needs hh_id, home_taz.
        ao_results: Needs hh_id, auto_ownership (vehicle count 0-4).
        taz_data: Needs zone, county.
        sampleshare: Uniform weight = 1/sampleshare per record.

    Returns:
        dict with keys: ``county_summary``, ``taz_long``, ``taz_spread``.
    """
    weight = 1.0 / sampleshare

    # Join HH info onto AO results
    ao = ao_results.join(
        households.select("hh_id", "home_taz"),
        on="hh_id",
        how="left",
    )

    # Attach county
    taz_county = taz_data.select(
        pl.col("zone").cast(pl.Int64),
        pl.col("county").cast(pl.Int64),
    )
    ao = ao.join(
        taz_county.rename({"zone": "home_taz"}),
        on="home_taz",
        how="left",
    )
    ao = ao.with_columns(
        pl.col("county")
        .replace_strict(COUNTY_LOOKUP, default="Unknown")
        .alias("county_name"),
    )

    # -- County summary (County x AO pivot) --------------------------------
    county_grouped = (
        ao.group_by("county", "county_name", "auto_ownership")
        .agg(pl.len().alias("num_hh"))
        .with_columns((pl.col("num_hh") * weight).alias("num_hh"))
    )
    county_summary = (
        county_grouped.pivot(
            on="auto_ownership", index=["county", "county_name"], values="num_hh",
        )
        .fill_null(0.0)
        .sort("county")
    )
    # Ensure column names are strings
    county_summary = county_summary.rename(
        {c: str(c) for c in county_summary.columns if not isinstance(c, str)}
    )

    # -- TAZ long format ---------------------------------------------------
    taz_long = (
        ao.group_by("home_taz", "auto_ownership")
        .agg(pl.len().alias("num_hh"))
        .with_columns((pl.col("num_hh") * weight).alias("num_hh"))
        .rename({"auto_ownership": "num_vehicles"})
        .sort("home_taz", "num_vehicles")
    )

    # -- TAZ spread format -------------------------------------------------
    taz_spread = (
        taz_long.pivot(on="num_vehicles", index="home_taz", values="num_hh")
        .fill_null(0.0)
        .sort("home_taz")
    )
    taz_spread = taz_spread.rename(
        {c: str(c) for c in taz_spread.columns if not isinstance(c, str)}
    )

    return {
        "county_summary": county_summary,
        "taz_long": taz_long,
        "taz_spread": taz_spread,
    }
