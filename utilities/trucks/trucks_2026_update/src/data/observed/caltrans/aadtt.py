"""
AADTT: Average Annual Daily Truck Traffic processing pipeline.

Input
-----
path/   : one CSV per Caltrans district; hourly counts by vehicle class
               columns: CONTROLID, direction, year, month, day, hour, CNT2…CNT16

Output
------
observed_average_daily_counts.csv
    CONTROLID, direction, tod, truck_type,
    n_obs,           ← number of valid Tue/Wed/Thu observations
    mean_volume,
    std_volume,
    normality_stat,  ← Shapiro-Wilk W
    normality_p,
    is_normal        ← p > normality_alpha

Processing order
----------------
load_class_files
    → normalize_directions
    → filter_typical_weekday
    → apply_vehicle_classes_aggregation
    → apply_hour_aggregation
    → compute_averages
    → typical_day_volumes           (orchestrator)
"""
import logging

import yaml
import glob
import pandas as pd
from pathlib import Path
from src.utils import timeit


logger = logging.getLogger(__name__)

CLASS_COLUMNS = [
    "RECTYPE",
    "FIPS",
    "DISTRICT",
    "CONTROLNO",
    "CODE",
    "DIRECTION",
    "LANETRAV",
    "YEAR",
    "MONTH",
    "DAY",
    "HOUR",
    "TOTVOL",
    "CNT1",
    "CNT2",
    "CNT3",
    "CNT4",
    "CNT5",
    "CNT6",
    "CNT7",
    "CNT8",
    "CNT9",
    "CNT10",
    "CNT11",
    "CNT12",
    "CNT13",
    "CNT14",
    "CNT15",
]



# @timeit
def load_caltrans_2018_files(path: str, pattern: str) -> pd.DataFrame:
    """
    Glob all files matching pattern inside path and concatenate them.

    One CSV may be missing the header; in that case the column order is inferred
    from the standard Caltrans class layout.

    Parameters
    ----------
    path : str
        Folder containing one class CSV per Caltrans district.
    pattern : str
        Filename glob, e.g. '*.csv'.

    Returns
    -------
    pd.DataFrame
        Raw concatenated class data; one row per
        (CONTROLID, direction, year, month, day, hour).
    """

    frames: list[pd.DataFrame] = []

    files = sorted(glob.glob(str(Path(path) / pattern)))
    if not files:
        raise FileNotFoundError(f"No files found in {path} matching {pattern}")

    for file in files:
        # Read first line to detect header
        with open(file, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()

        has_header = first_line.upper().startswith("RECTYPE")

        if has_header:
            df = pd.read_csv(file)
        else:
            df = pd.read_csv(file, header=None)
            df.columns = CLASS_COLUMNS

        # Validate column consistency
        if list(df.columns) != CLASS_COLUMNS:
            raise ValueError(
                f"Unexpected column layout in {file}.\n"
                f"Expected: {CLASS_COLUMNS}\n"
                f"Found: {list(df.columns)}"
            )

        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["DISTRICT", "CONTROLNO", "DIRECTION"], how="any")

    logger.info("Loaded %d files from %s matching %s", len(files), path, pattern)
    logger.info("Total raw counts shape:: %s", df.shape)

    return df


# @timeit
def create_control_station_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a numeric ID for each unique (DISTRICT, CONTROLID, DIRECTION) combination.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: DISTRICT, CONTROLID, and DIRECTION.

    Returns
    -------
    pd.DataFrame
        Same shape as input; adds control_station_id column.
    """
    df["control_station_id"] = (
            df.groupby(by=["DISTRICT", "CONTROLNO", "DIRECTION"]) 
            .ngroup() + 1
        )
    logger.info("create_control_station_id: unique Control Station IDs=%d", df["control_station_id"].nunique())
    return df


# @timeit
def normalize_directions(df: pd.DataFrame, direction_map: dict) -> pd.DataFrame:
    """
    Replace raw direction codes with canonical N / S / E / W strings.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing a 'DIRECTION' column with raw codes.
    direction_map : dict
        Mapping from raw code to canonical string, e.g. {1: 'N', 3: 'E', ...}.

    Returns
    -------
    pd.DataFrame
        Same shape as input; 'direction' column values replaced.
    """
    df["direction"] = df["DIRECTION"].astype(int).map(direction_map)
    logger.info("Normalized directions; unique=%s", list(df["direction"].unique()))
    return df


# @timeit
def filter_typical_weekday(
    df: pd.DataFrame,
    weekdays: list[int],
    holidays: list[str],
) -> pd.DataFrame:
    """
    Keep only rows that fall on a typical weekday (e.g. Tue/Wed/Thu) and are
    not on a  holiday. 

    Parameters
    ----------
    df : pd.DataFrame
        Must contain YEAR, MONTH, DAY columns (integers).
    weekdays : list[int]
        Python weekday indices to keep (Mon=0 … Sun=6).
    holidays : list[str]
        ISO-format date strings to exclude, e.g. ['2018-07-04'].

    Returns
    -------
    pd.DataFrame
        Filtered subset of df.
    """
    # Build a datetime column
    
    # Year in 4-digt format
    df["year"] = df["YEAR"].where(df["YEAR"] >= 100, df["YEAR"] + 2000)


    dates = pd.to_datetime(
        dict(year=df["year"], month=df["MONTH"], day=df["DAY"])
    )

    # Filter by weekday
    mask_weekday = dates.dt.weekday.isin(weekdays)

    # Filter out holidays
    holiday_dates = pd.to_datetime(holidays)
    mask_holiday = ~dates.isin(holiday_dates)

    out = df[mask_weekday & mask_holiday]

    pct_loss = 100 * (1 - len(out) / len(df))
    logger.info("filter_typical_weekday: input_rows=%d output_rows=%d (%% loss=%.2f)", len(df), len(out), pct_loss)
    return out


# @timeit
def apply_vehicle_classes_aggregation(df: pd.DataFrame, vehicle_classes: dict[str, str]) -> pd.DataFrame:
    """
    Aggregate the count columns (CNT2 … CNT16) into broader vehicle classes (e.g. 'Car', 'Truck').

    Parameters
    ----------
    df : pd.DataFrame
        Wide-format class data with columns CNT2 … CNT16.
    vehicle_classes : dict[str, str]
        Mapping from vehicle class names to their corresponding column names (e.g. {'Car': 'CNT2', 'Truck': 'CNT3'}).

    Returns
    -------
    pd.DataFrame
    """
    
    for class_name, cols in vehicle_classes.items():
        if isinstance(cols, str):
            cols = [cols]

        missing = set(cols) - set(df.columns)
        if missing:
            raise KeyError(f"Missing columns for '{class_name}': {missing}")

        df[class_name] = df[cols].sum(axis=1)

    logger.info("apply_vehicle_classes_aggregation: added classes=%s", list(vehicle_classes.keys()))
    return df


def apply_tod_map(
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
    hour_to_tod = {
        hour: tod
        for tod, hours in tod_hours.items()
        for hour in hours
    }

    df["TOD"] = df["HOUR"].map(hour_to_tod)

    if df["TOD"].isna().any():
        unmapped = sorted(df.loc[df["TOD"].isna(), "HOUR"].unique())
        raise ValueError(f"Unmapped hours found: {unmapped}")
    
    return df 

def estimate_daily_volumnes(df):
    group_cols = ["control_station_id", "DISTRICT", "CONTROLNO", "direction", "YEAR", "MONTH", "DAY", "TOD"]
    value_cols = ["struck", "mtruck", "ctruck"]

    result = (
        df
        .groupby(group_cols, as_index=False)[value_cols]
        .sum()
    )
    return result



# @timeit
def estimate_average_volumes(df: pd.DataFrame, vehicle_cols: list[str], percentiles: list[float] = [0.025, 0.975]) -> pd.DataFrame:
    """
    Compute mean and standard deviation across the filtered weekday sample,
    grouped by (CONTROLID, direction, hour, truck_type).

    Parameters
    ----------
    df : pd.DataFrame
        Long-format filtered data with a numeric 'volume' column.
    vehicle_cols : list[str]
        List of vehicle class columns to include in the computation.
    percentiles : list[float]
        Percentiles to compute for the confidence interval.

    Returns
    -------
    pd.DataFrame
        One row per (CONTROLID, direction, hour, truck_type) with columns:
        n_obs, mean_volume, std_volume.
    """
    pct_labels = [f'p{int(p * 100):02d}' for p in percentiles]
    group_keys = ["control_station_id", "DISTRICT", "CONTROLNO", "direction", "TOD"] 

    
    long_df = df.melt(
        id_vars=group_keys,
        value_vars=vehicle_cols,
        var_name="vehicle_type",
        value_name="volume",
    )

    g = long_df.groupby(group_keys + ["vehicle_type"])["volume"]

    result = g.agg(
        n="count",
        mean="mean",
        std="std",
        **{label: lambda x, p=p: x.quantile(p) for p, label in zip(percentiles, pct_labels)},
        ).reset_index()
    
    
    # Ensure count is integer
    result["n"] = result["n"].astype(int)

    # Round all other numeric columns to 5 decimals
    stat_cols = result.columns.difference(group_keys + ["vehicle_type", "n"])
    result[stat_cols] = result[stat_cols].astype(float).round(5)

    return result


# @timeit
def add_estimate_quality_metrics(
    df: pd.DataFrame,
    pct_low: str = "p02",
    pct_high: str = "p97",
) -> pd.DataFrame:
    """
    Add quality diagnostics to aggregated volume estimates.

    Parameters
    ----------
    df : pd.DataFrame
        Output of `compute_averages`. Must contain:
        - n
        - mean
        - std
        - lower / upper percentile columns (e.g. p02, p97)
    pct_low : str
        Column name for lower percentile.
    pct_high : str
        Column name for upper percentile.

    Returns
    -------
    pd.DataFrame
        Same dataframe with added quality metrics:
        - cv: Relative variability (std / mean)
        - ci_width: Absolute width of the confidence interval (upper - lower)
        - ci_width_rel: Relative width (to the mean) of the confidence interval
        - rse: Relative standard error
        - quality_flag: Quality flag based on sample size
    """
    df = df.copy()

    # --- Variability metrics ---
    df["cv"] = (df["std"] / df["mean"]).round(5)

    # --- Confidence interval width ---
    df["ci_width"] = (df[pct_high] - df[pct_low]).round(5)
    df["ci_width_rel"] = (df["ci_width"] / df["mean"]).round(5)

    # --- Relative standard error ---
    df["rse"] = (df["std"] / (df["mean"] * df["n"] ** 0.5)).round(5)

    # --- Quality flag based on sample size ---
    df["quality_flag"] = pd.cut(
        df["n"],
        bins=[0, 5, 20, float("inf")],
        labels=["poor", "fair", "good"],
        right=False,
    )

    return df


# @timeit
def remove_outliers(df: pd.DataFrame, k: float = 3.0) -> pd.DataFrame:
    """
    Remove outliers from counts data using IQR-based method. 

    Parameters
    ----------
    df : pd.DataFrame
        Raw counts data with count columns CNT2 … CNT16.
    k : float
        IQR multiplier for outlier removal; Default is 3.0.

    Returns
    -------
    pd.DataFrame
        Same shape as input but with outliers removed (set to NaN).
    """
    df = df.copy()

    cnt_cols = [col for col in df.columns if col.startswith("CNT")]
    df["_total"] = df[cnt_cols].sum(axis=1)

    bounds = (
        df.groupby("control_station_id")["_total"]
        .agg(q75=lambda x: x.quantile(0.75),
             iqr=lambda x: x.quantile(0.75) - x.quantile(0.25),
             q25=lambda x: x.quantile(0.25))
    ).reset_index()

    bounds["_upper"] = bounds["q75"] + k * bounds["iqr"]
    merged = df.merge(bounds[["control_station_id", "_upper"]], on="control_station_id", how="left")
    out = merged[merged["_total"] <= merged["_upper"]].drop(columns=["_total", "_upper"])
    logger.info("remove_outliers: input_rows=%d output_rows=%d", len(df), len(out))
    return out


# @timeit
def estimate_caltrans_aadtt(cfg: dict) -> pd.DataFrame:
    """
    Returns the AADTT (Annual Average Daily Truck Traffic) and statistics by
    CONTROLID, direction, TOD, and truck type from the Caltrans 2018 counts data. 
    This dataset contains hourly counts by vehicle class for every day in 2018. 

    Parameters
    ----------
    cfg : dict
        Full configuration loaded from config.yaml.

    Returns
    -------
    pd.DataFrame
    """
    raw_counts = load_caltrans_2018_files(cfg["inputs"]['caltrans_2018'], "*.csv")

    counts = ( 
        raw_counts
        .pipe(create_control_station_id)
        .pipe(normalize_directions, direction_map=cfg['direction_map']['class_file'])
        .pipe(remove_outliers, k=cfg['outlier_k'])
        .pipe(filter_typical_weekday, weekdays=cfg['typical_weekday']['weekdays'], holidays=cfg['typical_weekday']['holidays'])
        .pipe(apply_tod_map, tod_hours=cfg['tod_hours'])
        .pipe(apply_vehicle_classes_aggregation, vehicle_classes=cfg['vehicle_class_map'])
        .pipe(estimate_daily_volumnes)
        .pipe(estimate_average_volumes, vehicle_cols=list(cfg['vehicle_class_map'].keys()), percentiles=cfg['normality_percentiles'])
        .pipe(add_estimate_quality_metrics, pct_low="p02", pct_high="p97")
    )
    return counts


