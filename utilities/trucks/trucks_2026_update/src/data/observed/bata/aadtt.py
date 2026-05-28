import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_hour_aggregation(
    df: pd.DataFrame,
    tod_hours: dict[str, list[int]],
) -> pd.DataFrame:
    """
    Sum volumne across all hours belonging to the same TOD period.

    Parameters
    ----------
    df : pd.DataFrame
        Output of compute_hourly_averages.
    tod_hours : dict[str, list[int]]
        Maps each TOD label to the list of hours it covers,
        e.g. {'AM': [6, 7, 8, 9], 'EA': [3, 4, 5], ...}.

    Returns
    -------
    pd.DataFrame
        Aggregated dataframe by TOD period.
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
    """
    Filter the raw BATA 2023 data to include only 2023 records.

    Parameters
    ----------
    df : pd.DataFrame
        Raw BATA 2023 data.

    Returns
    -------
    pd.DataFrame
        Filtered dataframe containing only relevant records for AADTT estimation.
    """
    filtered = df[
        (df["Date"] >= "2023-01-01") &
        (df["Date"] <= "2023-12-31")
    ].copy()
    
    logger.info("filter_2023_data: pre_rows=%d post_rows=%d", len(df), len(filtered))
    return filtered


def map_vehicle_class(df: pd.DataFrame, mapping: dict, axle_col: str = "Axle") -> pd.DataFrame:
    """
    Map axle counts to truck classes using a config mapping.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame with an axle column.
    mapping : dict
        Mapping like {"struck": [2], "mtruck": [3], ...}
    axle_col : str
        Name of the axle column.

    Returns
    -------
    pd.DataFrame
        DataFrame with a new column 'truck_type'.
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
    """
    Placeholder for AADTT estimation logic.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame after hour aggregation and vehicle class mapping.

    Returns
    -------
    pd.DataFrame
        DataFrame with estimated AADTT values.
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
    """
    Placeholder for BATA AADTT estimation logic.

    Parameters
    ----------
    data : pd.DataFrame
        Input data for BATA AADTT estimation.

    Returns
    -------
    pd.DataFrame
        Empty dataframe with expected columns for consistency.
    """
    df = (data
          .pipe(filter_2023_data)
          .pipe(apply_hour_aggregation, tod_hours=cfg["tod_hours"])
          .pipe(map_vehicle_class, mapping = cfg["axle_to_truck_type_map"])
          .pipe(estimate_aadtt)
          )

    return df