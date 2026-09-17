import pandas as pd
from calib_report import tables, figures

# Canonical Purpose labels
CANONICAL_PURPOSE = ["work", "university", "school", "ind_disc", "ind_maint", "joint", "atwork"]

CANONICAL_TOUR_MODE = {
    1: "Drive Alone",
    2: "Shared Ride 2",
    3: "Shared Ride 3+",
    4: "Walk",
    5: "Bike",
    6: "Walk-Local",
    7: "Walk-LRT",
    8: "Walk-Ferry",
    9: "Walk-Express",
    10: "Walk-Heavy Rail",
    11: "Walk-Commuter Rail",
    12: "Drive-Local",
    13: "Drive-LRT",
    14: "Drive-Ferry",
    15: "Drive-Express",
    16: "Drive-Heavy Rail",
    17: "Drive-Commuter Rail",
    18: "Taxi",
    19: "TNC Single",
    20: "TNC Shared",
    21: "Other"
}

CHTS_MODE_MAP = {
    1: 4, # Walk
    2: 5, # Bike
    3: 1, # Drive Alone
    4: 2, # Shared Ride 2,
    5: 3, # Shared Ride 3+,
    6: 6, # Walk - Local
    7: 7, # Walk - LRT,
    8: 8, # walk - Ferry
    9: 9, # Walk - Express
    10: 10, # Walk - Heavy Rail
    11: 11, # Walk - Commuter Rail
    12: 12, # Drive - Local
    13: 13, # Drive - LRT
    14: 14, # Drive - Ferry
    15: 15, # Drive - Express
    16: 16, # Drive - Heavy Rail
    17: 17, # Drive - Commuter Rail
    18: 21, # School Bus -> Other
    19: 18, # Taxi
    20: 21 # Other
}

BATS_MODE_MAP = {
    1: 1, # Drive Alone 
    3: 2, # Shared Ride 2
    5: 3, # Shared Ride 3+
    7: 4, # Walk
    8: 5, # Bike
    9: 6, # Walk - Local
    10: 7, # Walk - LRT,
    11: 9, # Walk - Express
    12: 10, # Walk - Heavy Rail
    13: 11, # Walk - Commuter Rail
    14: 12, # Drive - Local
    15: 13, # Drive - LRT
    16: 15, # Drive - Express
    17: 16, # Drive - Heavy Rail
    18: 17, # Drive - Commuter Rail
    19: 18, # Taxi
    20: 19, # TNC Single
    21: 20, # TNC Shared
    22: 8, # walk - Ferry
    23: 14, # Drive - Ferry
}

AUTO_SUFFICIENCY_ORDER = [
    "Autos=0",
    "Autos<Workers",
    "Autos>=Workers"
]

def format_tour_mode_file(file, mode_map, mode_col="tour_mode") -> pd.DataFrame:
    """Format tour mode file to be standardized
    
    Parameters
    ----------
        file: File path to tour mode file
        mode_map (dict): Raw tour_mode value -> canonical tour mode code, source-specific
        mode_col (str): Raw tour mode column name; defaults to "tour_mode
    Returns
        df: Formatted dataFrame with canonical tour_mode code and tour_mode_label
    """

    df = pd.read_csv(file)

    # Standardize tour mode label
    df[mode_col] = df[mode_col].map(mode_map)
    df["tour_mode_label"] = df[mode_col].map(CANONICAL_TOUR_MODE)

    

    ## Standardize purpose
    return df


def build_tour_mode_purpose_table(df: pd.DataFrame, purpose: str, mode_col="tour_mode", as_share: bool = False):
    """Filter tour mode choice by purpose and pivot auto_sufficiency into columns
    
    Parameters
    ----------
        df (df): Tour Mode Choice DataFrame
        purpose (str): Simple Tour Purpose {work, university, school, ind_disc, ind_maint, joint, atwork}
        mode_col (str): Tour Mode column; defaults: "tour_mode"
        as_share (bool): Boolean; determines if format is as shares or not; defaults to False
            
    Returns
        pandas.DataFrame: DataFrame filtered by tour purpose and auto sufficiency as columns
    ----------

    Filters by purpose and pivots auto_suff into columns"""
    df_purpose = df[df["simple_purpose"].str.lower() == purpose]

    pivoted = df_purpose.pivot_table(
        index=mode_col,
        columns="auto_suff",
        values="num_tours_weighted",
        aggfunc="sum",
        fill_value=0
    )

    # Ensure auto-sufficency categories appear in the model order
    pivoted = pivoted.reindex(columns=AUTO_SUFFICIENCY_ORDER, fill_value=0)


    if as_share:
        pivoted = tables.to_shares(pivoted, axis = 0)
        formatted = tables.format_numeric(pivoted, num_fmt=".1%")
    else:
        formatted = tables.format_numeric(pivoted,num_fmt=",.0f")

    formatted = formatted.reset_index()
    formatted[mode_col] = formatted[mode_col].map(CANONICAL_TOUR_MODE)
    formatted = formatted.rename(columns={mode_col: "Tour Mode"})

    return formatted


def format_trip_mode_file(file, mode_map):
    df = pd.read_csv(file)

    df["tour_mode"] = df["tour_mode"].map(mode_map)
    df["tour_mode_label"] = df["tour_mode"].map(CANONICAL_TOUR_MODE)

    df["trip_mode"] = df["trip_mode"].map(mode_map)
    df["trip_mode_label"] = df["trip_mode"].map(CANONICAL_TOUR_MODE)

    return df

def build_trip_mode_purpose_table(df, purpose: str, as_share: bool = False):
    df_purpose = df[df["simple_purpose"].str.lower() == purpose]

    pivoted = df_purpose.pivot_table(
        index = "trip_mode",
        columns = "tour_mode",
        values = "num_trips_weighted",
        aggfunc = "sum",
        fill_value = 0
    )

    if as_share:
            pivoted = tables.to_shares(pivoted, axis = 0)
            formatted = tables.format_numeric(pivoted, num_fmt=".1%")
    else:
        formatted = tables.format_numeric(pivoted,num_fmt=",.0f")

    formatted = formatted.reset_index()
    formatted["trip_mode"] = formatted["trip_mode"].map(CANONICAL_TOUR_MODE)
    formatted = formatted.rename(columns = CANONICAL_TOUR_MODE)
    formatted = formatted.rename(columns={"trip_mode": "Trip Mode"})

    return formatted

