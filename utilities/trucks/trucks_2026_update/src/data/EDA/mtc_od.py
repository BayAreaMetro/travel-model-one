from pathlib import Path

import pandas as pd
import numpy as np
import openmatrix as omx

from src.data.EDA.configs import COUNTY_MAP
from src.utils import save


def read_mtc_trips(path) -> pd.DataFrame:
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
    tods = ["AM", "MD"]
    n = 1475
    base = pd.DataFrame({
        "origin": np.repeat(np.arange(1, n + 1), n),
        "destination": np.tile(np.arange(1, n + 1), n),
    })
    
    matrices = [
         'DISTLRG',
         'DISTMED',
         'DISTSML',
         'DISTVSM',
         'TIMELRG',
         'TIMEMED',
         'TIMESML',
         'TIMEVSM',
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
    df["county"] = df["COUNTY"].map(COUNTY_MAP)
    d = dict(zip(df["ZONE"], df["county"]))
    d.update({k: "gateway" for k in range(1455, 1476)})
    return d
    

def mtc_od_long_format(input_paths: dict):
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