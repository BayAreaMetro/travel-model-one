"""Usual work and school location calibration — pure summarization logic.

All functions operate on eager ``pl.DataFrame`` inputs (already collected from
the bundle) and return ``dict[str, pl.DataFrame]``.  No file I/O, no config
objects, no logging side-effects.
"""

import polars as pl

from tm1.steps.summaries.calibration.enums import CTRAMPCounty

COUNTY_LOOKUP: dict[int, str] = {c.id: c.label for c in CTRAMPCounty}
COUNTY_IDS: list[int] = sorted(COUNTY_LOOKUP)
COUNTY_NAMES: list[str] = [COUNTY_LOOKUP[i] for i in COUNTY_IDS]

# Required bundle fields for this submodel.
REQUIRED_FIELDS = ("wsloc_results", "taz_data", "dist_skim")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def summarize(
    wsloc: pl.DataFrame,
    taz_data: pl.DataFrame,
    dist_skim: pl.DataFrame,
    *,
    weight_col: str | None = None,
    sampleshare: float = 1.0,
    max_bin: int = 80,
) -> dict[str, pl.DataFrame]:
    """Produce work/school location calibration summaries.

    Args:
        wsloc: wsLocResults table (canonical columns).  Needs at minimum
            home_taz, work_location, school_location, student_category.
            May also contain *weight_col*.
        taz_data: Must have zone and county columns.
        dist_skim: Three columns — orig, dest, dist.
        weight_col: Per-record weight column name (e.g. "person_weight").
            When *None*, each record gets weight ``1 / sampleshare``.
        sampleshare: Used to derive uniform weight when *weight_col* is None.
        max_bin: Upper limit for TLFD distance bins (exclusive).

    Returns:
        dict with keys: ``county_summary``, ``trip_tlfd_work``,
        ``trip_tlfd_univ``, ``trip_tlfd_school``, ``avg_trip_lengths``.
    """
    # -- uniform weight if no per-record column ----------------------------
    if weight_col is not None:
        if weight_col not in wsloc.columns:
            msg = (
                f"weight_col {weight_col!r} not found in wsloc_results "
                f"columns: {wsloc.columns}"
            )
            raise ValueError(msg)
    else:
        weight_col = "_weight"
        wsloc = wsloc.with_columns(pl.lit(1.0 / sampleshare).alias(weight_col))

    taz_county = taz_data.select(
        pl.col("zone").cast(pl.Int64),
        pl.col("county").cast(pl.Int64),
    )

    # -- attach county info for Home, Work, School -------------------------
    wsloc = _join_county(wsloc, taz_county, "home_taz", "home_county")
    wsloc = _join_county(wsloc, taz_county, "work_location", "work_county")
    wsloc = _join_county(wsloc, taz_county, "school_location", "school_county")

    # -- attach distances --------------------------------------------------
    wsloc = wsloc.join(
        dist_skim.select(
            pl.col("orig").cast(pl.Int64).alias("home_taz"),
            pl.col("dest").cast(pl.Int64).alias("work_location"),
            pl.col("dist").alias("work_dist"),
        ),
        on=["home_taz", "work_location"],
        how="left",
    )
    wsloc = wsloc.join(
        dist_skim.select(
            pl.col("orig").cast(pl.Int64).alias("home_taz"),
            pl.col("dest").cast(pl.Int64).alias("school_location"),
            pl.col("dist").alias("school_dist"),
        ),
        on=["home_taz", "school_location"],
        how="left",
    )

    # -- county summary (Home x Work) --------------------------------------
    county_summary = _county_summary(wsloc, weight_col)

    # -- trip length frequency distributions --------------------------------
    bins = list(range(1, max_bin))
    trip_tlfds: dict[str, pl.DataFrame] = {}
    avg_rows: list[dict] = []

    for trip_type, dist_col, filter_expr in _trip_type_filters():
        subset = wsloc.filter(filter_expr)
        tlfd, avgs = _build_tlfd(subset, dist_col, weight_col, bins)
        trip_tlfds[trip_type] = tlfd
        avg_rows.extend({"county": a[0], "trip_type": trip_type, "mean": a[1]} for a in avgs)

    # -- average trip lengths (county x trip_type pivot) --------------------
    avg_df = pl.DataFrame(avg_rows)
    if avg_df.height > 0:
        avg_trip_lengths = avg_df.pivot(on="trip_type", index="county", values="mean")
        # Ensure expected column order
        desired = ["county"] + [
            c for c in ("work", "univ", "school") if c in avg_trip_lengths.columns
        ]
        avg_trip_lengths = avg_trip_lengths.select(desired)
    else:
        avg_trip_lengths = pl.DataFrame({"county": [], "work": [], "univ": [], "school": []})

    return {
        "county_summary": county_summary,
        "trip_tlfd_work": trip_tlfds.get("work"),
        "trip_tlfd_univ": trip_tlfds.get("univ"),
        "trip_tlfd_school": trip_tlfds.get("school"),
        "avg_trip_lengths": avg_trip_lengths,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _join_county(
    df: pl.DataFrame,
    taz_county: pl.DataFrame,
    taz_col: str,
    county_col: str,
) -> pl.DataFrame:
    """Left-join county onto *df* via *taz_col*, naming result *county_col*."""
    return df.join(
        taz_county.rename({"zone": taz_col, "county": county_col}),
        on=taz_col,
        how="left",
    )


def _county_name(county_id: int) -> str:
    return COUNTY_LOOKUP.get(county_id, f"Unknown({county_id})")


def _county_summary(wsloc: pl.DataFrame, weight_col: str) -> pl.DataFrame:
    """Home county x Work county weighted cross-tabulation."""
    grouped = (
        wsloc.group_by("home_county", "work_county")
        .agg(pl.col(weight_col).sum().alias("num_pers"))
    )
    # Pivot to wide: home_county rows x work_county columns
    pivot = grouped.pivot(on="work_county", index="home_county", values="num_pers")

    # Ensure all counties present as rows and columns
    for cid in COUNTY_IDS:
        col = str(cid)
        if col not in pivot.columns:
            pivot = pivot.with_columns(pl.lit(0.0).alias(col))

    # Reorder and rename
    pivot = pivot.sort("home_county")
    # Add home_county_name
    pivot = pivot.with_columns(
        pl.col("home_county")
        .replace_strict(COUNTY_LOOKUP, default="Unknown")
        .alias("home_county_name"),
    )
    # Rename numeric county columns to names
    renames = {str(cid): COUNTY_LOOKUP[cid] for cid in COUNTY_IDS}
    pivot = pivot.rename(renames)
    # Select final column order
    cols = ["home_county_name", *COUNTY_NAMES]
    return pivot.select(cols).fill_null(0.0)


def _trip_type_filters() -> list[tuple[str, str, pl.Expr]]:
    """Return ``(trip_type, dist_col, filter_expr)`` triples."""
    return [
        ("work", "work_dist", pl.col("work_location") > 0),
        (
            "univ",
            "school_dist",
            (pl.col("school_location") > 0) & (pl.col("student_category") == "College or higher"),
        ),
        (
            "school",
            "school_dist",
            (pl.col("school_location") > 0)
            & (pl.col("student_category") == "Grade or high school"),
        ),
    ]


def _build_tlfd(
    subset: pl.DataFrame,
    dist_col: str,
    weight_col: str,
    bins: list[int],
) -> tuple[pl.DataFrame, list[tuple[str, float]]]:
    """Build per-county + Total TLFD for one trip type.

    Returns:
        Tuple of (tlfd DataFrame with distbin + county columns + Total,
        list of (county_name_or_Total, weighted_mean) pairs).
    """
    # Start with distbin scaffold
    tlfd = pl.DataFrame({"distbin": bins})
    avgs: list[tuple[str, float]] = []

    if subset.height == 0:
        return tlfd.with_columns(pl.lit(0.0).alias("Total")), avgs

    # Add home_county_name for grouping
    subset = subset.with_columns(
        pl.col("home_county")
        .replace_strict(COUNTY_LOOKUP, default="Unknown")
        .alias("home_county_name"),
    )

    for county_name in COUNTY_NAMES:
        county_data = subset.filter(pl.col("home_county_name") == county_name)
        if county_data.height == 0:
            continue
        hist = _weighted_histogram(county_data, dist_col, weight_col, bins)
        tlfd = tlfd.join(hist.rename({"count": county_name}), on="distbin", how="left")
        avg = _weighted_mean(county_data, dist_col, weight_col)
        avgs.append((county_name, avg))

    # Total
    hist = _weighted_histogram(subset, dist_col, weight_col, bins)
    tlfd = tlfd.join(hist.rename({"count": "Total"}), on="distbin", how="left")
    avg = _weighted_mean(subset, dist_col, weight_col)
    avgs.append(("Total", avg))

    return tlfd.fill_null(0.0), avgs


def _weighted_histogram(
    df: pl.DataFrame,
    value_col: str,
    weight_col: str,
    bins: list[int],
) -> pl.DataFrame:
    """Weighted histogram using polars cut + groupby."""
    max_bin = max(bins)
    binned = (
        df.filter(pl.col(value_col).is_not_null())
        .with_columns(
            pl.col(value_col).clip(0, max_bin).cast(pl.Int64).alias("_bin"),
        )
        # Bin value: floor to int, clamp to [1, max_bin]
        .with_columns(
            pl.when(pl.col("_bin") < 1).then(1).otherwise(pl.col("_bin")).alias("_bin"),
        )
        .group_by("_bin")
        .agg(pl.col(weight_col).sum().alias("count"))
    )
    # Join back to full bin list
    scaffold = pl.DataFrame({"distbin": bins})
    return scaffold.join(
        binned.rename({"_bin": "distbin"}),
        on="distbin",
        how="left",
    ).with_columns(pl.col("count").fill_null(0.0))


def _weighted_mean(df: pl.DataFrame, value_col: str, weight_col: str) -> float:
    """Weighted mean of *value_col* using *weight_col*."""
    result = df.filter(pl.col(value_col).is_not_null()).select(
        (pl.col(value_col) * pl.col(weight_col)).sum() / pl.col(weight_col).sum()
    )
    return result.item() if result.height > 0 else 0.0
