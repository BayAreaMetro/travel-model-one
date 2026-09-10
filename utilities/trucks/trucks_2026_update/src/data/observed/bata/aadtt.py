import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_hour_aggregation(
    df: pd.DataFrame,
    tod_hours: dict[str, list[int]],
) -> pd.DataFrame:
    """Sum axle counts across all hours belonging to the same time-of-day period.

    Maps each row's ``Hour`` value to a TOD label and sums ``Count`` within
    each (Plaza, Date, Axle, TOD) group.  Raises if any hour has no matching
    TOD period.

    Parameters
    ----------
    df : pd.DataFrame
        Row-level BATA toll plaza data with at least columns ``Hour``,
        ``Plaza``, ``Date``, ``Axle``, and ``Count``.
    tod_hours : dict[str, list[int]]
        Maps each TOD label to the list of clock hours it covers,
        e.g. ``{'AM': [6, 7, 8, 9], 'EA': [3, 4, 5]}``.

    Returns
    -------
    pd.DataFrame
        Aggregated counts with columns ``Plaza``, ``Date``, ``Axle``,
        ``TOD``, and ``Count``.  One row per unique combination.

    Raises
    ------
    ValueError
        If any hour in ``df`` does not appear in ``tod_hours``.
    """
    
    # Build an hour -> TOD lookup
    hour_to_tod = {
        hour: tod
        for tod, hours in tod_hours.items()
        for hour in hours
    }

    # Map each row's hour to a TOD label
    df["TOD"] = df["Hour"].map(hour_to_tod)

    # guard against unmapped hours
    if df["TOD"].isna().any():
        unmapped = sorted(df.loc[df["TOD"].isna(), "Hour"].unique())
        raise ValueError(f"Unmapped hours found: {unmapped}")
    
    # Group by columsn 
    group_by = ["Plaza", "Date", "Axle", "TOD"]

    result = df.groupby(group_by, as_index=False).agg({"Count": "sum"}).reset_index(drop=False)
    logger.info("apply_hour_aggregation: pre_rows=%d post_rows=%d", len(df), len(result))
    return result

def filter_2023_data(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows whose ``Date`` falls within the 2023 calendar year.

    Parameters
    ----------
    df : pd.DataFrame
        Raw BATA toll plaza data with a ``Date`` column parseable as a date
        string (``"YYYY-MM-DD"`` format or equivalent).

    Returns
    -------
    pd.DataFrame
        Subset of ``df`` where ``Date`` is between 2023-01-01 and 2023-12-31
        inclusive.
    """
    filtered = df[
        (df["Date"] >= "2023-01-01") &
        (df["Date"] <= "2023-12-31")
    ].copy()
    
    logger.info("filter_2023_data: pre_rows=%d post_rows=%d", len(df), len(filtered))
    return filtered


def map_vehicle_class(df: pd.DataFrame, mapping: dict, axle_col: str = "Axle") -> pd.DataFrame:
    """Map axle-count values to truck-class labels using a mapping lookup.

    Inverts the ``mapping`` dict (truck-class → axle list) to produce a
    per-axle lookup and assigns the result to a new ``vehicle_type`` column.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing an axle column (default name ``"Axle"``).
    mapping : dict
        Mapping from truck-class name to the list of axle values that belong
        to it, e.g. ``{"struck": [2], "mtruck": [3], "ctruck": [4, 5, 6]}``.
    axle_col : str, optional
        Name of the column holding axle counts.  Default is ``"Axle"``.

    Returns
    -------
    pd.DataFrame
        Input DataFrame with an added ``vehicle_type`` column containing
        the mapped truck-class name.  Rows whose axle value is not in
        ``mapping`` receive ``NaN``.
    """

    # Invert mapping: axle → class
    axle_to_class = {}
    for truck_type, axles in mapping.items():
        for axle in axles:
            axle_to_class[axle] = truck_type

    #  Map column
    df["vehicle_type"] = df[axle_col].map(axle_to_class)

    return df

def estimate_aadtt(df: pd.DataFrame) -> pd.DataFrame:
    """Compute mean daily truck volume by plaza, TOD period, and vehicle type.

    First sums counts within each (Plaza, Date, TOD, vehicle_type) day, then
    averages those daily totals across all dates to produce the mean volume
    per plaza / TOD / type combination.

    Parameters
    ----------
    df : pd.DataFrame
        TOD-aggregated data with columns ``Plaza``, ``Date``, ``TOD``,
        ``vehicle_type``, and ``Count``.

    Returns
    -------
    pd.DataFrame
        One row per (Plaza, TOD, vehicle_type) with columns ``Plaza``,
        ``TOD``, ``vehicle_type``, and ``mean_volume``.
    """
    daily_volume = (
        df.groupby(["Plaza", "Date", "TOD", "vehicle_type"])
        .agg(total_volume=("Count", "sum"))
        .reset_index()
        )
    
    avg_volume = (
        daily_volume.groupby(["Plaza", "TOD", "vehicle_type"])
        .agg(mean_volume=("total_volume", "mean"))
        .reset_index()
    )
    return avg_volume


def estimate_bata_aadtt(data, cfg) -> pd.DataFrame:
    """Run the full BATA AADTT estimation pipeline on raw toll plaza data.

    Chains together filtering, TOD aggregation, vehicle-class mapping, and
    mean daily volume estimation into a single step.

    Parameters
    ----------
    data : pd.DataFrame
        Raw BATA Excel data with columns ``Date``, ``Hour``, ``Plaza``,
        ``Axle``, and ``Count``.
    cfg : dict
        Configuration dict with the following keys used here:

        ``"tod_hours"`` : dict[str, list[int]]
            Hour-to-TOD mapping forwarded to :func:`apply_hour_aggregation`.
        ``"axle_to_truck_type_map"`` : dict
            Axle-to-class mapping forwarded to :func:`map_vehicle_class`.

    Returns
    -------
    pd.DataFrame
        Mean daily truck volumes by plaza, TOD, and vehicle type.
        Columns: ``Plaza``, ``TOD``, ``vehicle_type``, ``mean_volume``.
    """
    df = (data
          .pipe(filter_2023_data)
          .pipe(apply_hour_aggregation, tod_hours=cfg["tod_hours"])
          .pipe(map_vehicle_class, mapping = cfg["axle_to_truck_type_map"])
          .pipe(estimate_aadtt)
          )

    return df