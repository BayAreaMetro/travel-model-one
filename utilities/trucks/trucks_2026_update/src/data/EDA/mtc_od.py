from pathlib import Path

import pandas as pd
import numpy as np
import openmatrix as omx

from src.data.EDA.configs import COUNTY_MAP
from src.utils import save


def read_mtc_trips(path) -> pd.DataFrame:
    """Read MTC truck trip matrices from OMX files for all time-of-day periods.

    Opens one OMX file per period, reads every truck-type matrix, and
    concatenates all period/type combinations into a single flat DataFrame
    indexed by origin-destination TAZ pair.

    Parameters
    ----------
    path : str
        Path template containing a ``{tod}`` placeholder that is substituted
        for each time-of-day code (``"EA"``, ``"AM"``, ``"MD"``, ``"PM"``,
        ``"EV"``).

    Returns
    -------
    pd.DataFrame
        Long-format DataFrame with columns ``origin``, ``destination``, and
        one column per ``<truck_type>_<tod>`` combination (e.g.
        ``vstruck_AM``).  Origin and destination values are 1-based TAZ IDs
        ranging from 1 to 1475.
    """
    tods = ["EA", "AM", "MD", "PM", "EV"]
    n = 1475
    base = pd.DataFrame({
        "origin": np.repeat(np.arange(1, n + 1), n),
        "destination": np.tile(np.arange(1, n + 1), n),
    })
    
    for tod in tods:
        ref_path = path.format(tod=tod)
        omx_file = omx.open_file(ref_path, "r")
        for truck_type in omx_file.list_matrices():
            name = f"{truck_type}_{tod}"
            matrix = np.array(omx_file[truck_type])
            base[name] = matrix.ravel()
        omx_file.close()
    return base

def read_mtc_skims(path) -> pd.DataFrame:
    """Read MTC highway skim matrices for AM and MD periods from OMX files.

    Extracts distance and time skims for the four truck size classes
    (very-small, small, medium, large) across AM and MD periods and returns
    them flattened to a TAZ-pair DataFrame.

    Parameters
    ----------
    path : str
        Path template with a ``{tod}`` placeholder substituted for each
        period code (``"AM"``, ``"MD"``).

    Returns
    -------
    pd.DataFrame
        Long-format DataFrame with columns ``origin``, ``destination``, and
        one column per ``<MATRIX>_<tod>`` combination
        Origin and destination are 1-based TAZ IDs from 1 to 1475.
    """
    tods = ["AM", "MD"]
    n = 1475
    base = pd.DataFrame({
        "origin": np.repeat(np.arange(1, n + 1), n),
        "destination": np.tile(np.arange(1, n + 1), n),
    })
    
    matrices = [
         'DISTLRG', # distance large 
         'DISTMED', # distance medium 
         'DISTSML', # distance small
         'DISTVSM', # distance very small
         'TIMELRG', # travel time large
         'TIMEMED', # travel time medium
         'TIMESML', # travel time small
         'TIMEVSM', # travel time very small
    ]
    
    for tod in tods:
        ref_path = path.format(tod=tod)
        omx_file = omx.open_file(ref_path, "r")
        for matrix_name in matrices:
            name = f"{matrix_name}_{tod}"
            matrix = np.array(omx_file[matrix_name])
            base[name] = matrix.ravel()
        omx_file.close()
    return base

def get_taz_county_map(df):
    """Build a TAZ-to-county name mapping from the MTC land use table.

    Maps internal TAZ IDs to county names and marks external gateway 
    zones (TAZ 1455–1475) as ``"gateway"``.

    Parameters
    ----------
    df : pd.DataFrame
        Land use table with at minimum columns ``ZONE`` (TAZ ID) and
        ``COUNTY`` (integer county code as defined in ``COUNTY_MAP``).

    Returns
    -------
    dict
        Mapping of TAZ ID (int) to county name (str).  Gateway zones
        1455–1475 map to ``"gateway"``.
    """
    df["county"] = df["COUNTY"].map(COUNTY_MAP)
    d = dict(zip(df["ZONE"], df["county"]))
    d.update({k: "gateway" for k in range(1455, 1476)})
    return d
    

def mtc_od_long_format(input_paths: dict):
    """Build a long-format MTC OD table with truck trips, skims, and derived variables.

    Reads long format trip matrices and highway skims, joins them by origin-destination
    pair, attaches county labels from the land use file, and adds composite
    distance/time skims weighted 1/3 AM + 2/3 MD.

    Parameters
    ----------
    input_paths : dict
        Dictionary with the following keys:

        ``"od_omx"`` : str
            Path template (with ``{tod}``) to MTC truck trip OMX files.
        ``"skims"`` : str
            Path template (with ``{tod}``) to MTC highway skim OMX files.
        ``"land_use"`` : str
            Path to the TAZ land use CSV (``tazData.csv``).

    Returns
    -------
    pd.DataFrame
        One row per origin-destination TAZ pair with columns for all
        raw trip/skim matrices plus derived columns: ``origin_county``,
        ``destination_county``, ``total_trips``, ``very_small_trucks``,
        ``small_trucks``, ``medium_trucks``, ``large_trucks``,
        ``distance_comp_*``, ``time_comp_*``, and ``source`` (``"TM1.6"``).
    """
    trips = read_mtc_trips(input_paths["od_omx"])
    skims = read_mtc_skims(input_paths["skims"])
    lu =    pd.read_csv(input_paths["land_use"])
    taz_to_county = get_taz_county_map(lu) 

    # Merge trips and skims
    df = trips.merge(skims, how = "left", on = ["origin", "destination"]) 
    
    # --- ADDITIONAL VARIABLES ---
    # County name
    df["origin_county"] = df["origin"].map(taz_to_county)
    df["destination_county"] = df["destination"].map(taz_to_county)
    
    # Truck Trips 
    df["total_trips"] = df.filter(regex=r'^(vstruck|struck|mtruck|ctruck)').sum(axis = 1)
    df["very_small_trucks"] = df.filter(regex=r'^(vstruck)').sum(axis = 1)
    df["small_trucks"] = df.filter(regex=r'^(struck)').sum(axis = 1)
    df["medium_trucks"] = df.filter(regex=r'^(mtruck)').sum(axis = 1)
    df["large_trucks"] = df.filter(regex=r'^(ctruck)').sum(axis = 1)

    # Composite distance  
    df["distance_comp_very_small"] = (1/3) * df['DISTVSM_AM'] + (2/3) * df['DISTVSM_MD']
    df["distance_comp_small"] = (1/3) * df['DISTSML_AM'] + (2/3) * df['DISTSML_MD']
    df["distance_comp_medium"] = (1/3) * df['DISTMED_AM'] + (2/3) * df['DISTMED_MD']
    df["distance_comp_large"] = (1/3) * df['DISTLRG_AM'] + (2/3) * df['DISTLRG_MD']

    # Composite time  
    df["time_comp_very_small"] = (1/3) * df['TIMEVSM_AM'] + (2/3) * df['TIMEVSM_MD']
    df["time_comp_small"] = (1/3) * df['TIMESML_AM'] + (2/3) * df['TIMESML_MD']
    df["time_comp_medium"] = (1/3) * df['TIMEMED_AM'] + (2/3) * df['TIMEMED_MD']
    df["time_comp_large"] = (1/3) * df['TIMELRG_AM'] + (2/3) * df['TIMELRG_MD']
    df["source"] = "TM1.6"

    return df 