from pathlib import Path
import pandas as pd
import numpy as np
import openmatrix as omx
from datetime import datetime

from src.data.EDA.mtc_od import read_mtc_skims, read_mtc_trips
from src.data.EDA.trip_distributions import compute_weighted_histograms
# from src.data.trip_distribution.mtc_blended_skims import create_blended_skims

blended_skim_defs = {
        "blended_time_vstruck": {
            "skim": "TIMEVSM", 
            "toll_skim": "TOLLTIMEVSM",
            "weights": {"MD": 2/3, "AM": 1/3},
        },
        "blended_time_struck": {
            "skim": "TIMESML", 
            "toll_skim": "TOLLTIMESML",
            "weights": {"MD": 2/3, "AM": 1/3},
        },
        "blended_time_mtrucks": {
            "skim": "TIMEMED", 
            "toll_skim": "TOLLTIMEMED",
            "weights": {"MD": 2/3, "AM": 1/3},
        },
        "blended_time_ctrucks": {
            "skim": "TIMELRG", 
            "toll_skim": "TOLLTIMELRG",
            "weights": {"MD": 2/3, "AM": 1/3},
        },
        "blended_distance_vstruck": {
            "skim": "DISTVSM", 
            "toll_skim": "TOLLDISTVSM",
            "weights": {"MD": 1},
        },
        "blended_distance_struck": {
            "skim": "DISTSML", 
            "toll_skim": "TOLLDISTSML",
            "weights": {"MD": 1},
        },
        "blended_distance_mtrucks": {
            "skim": "DISTMED", 
            "toll_skim": "TOLLDISTMED",
            "weights": {"MD": 1},
        },
        "blended_distance_ctrucks": {
            "skim": "DISTLRG", 
            "toll_skim": "TOLLDISTLRG",
            "weights": {"MD": 1},
        },
    }

def run() -> None:
    """ Produces inputs for the trip distribution calibration. 
    The trip distribution calibration needs three main inputs: 

    1. Skims: create_blended_skims - MTC model uses a specific time-based blended skims. We recreate particular skim here
    2. Production/Attraction tables: 
    3. A observered Travel Lenght Function distribution. It borrows the code used in the EDA to compute the observred distribution. 

    
    This pipeline takes observed SW OD tables, and MTC skims, 
    and process to get trip production/attraction tables, and a 
    long format skims with blended skims, and observed TLFD for 
    calibration and validation of the gravity model. This 
    outputs aim to be standardized for use in both the calibration and application


     Returns
     -------
     None
     """
    
    n = 1454 # Number of internal TAZs 
    today = datetime.now().strftime("%Y_%m_%d")
    output_dir = Path("data/processed/trip_generation_inputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # MTC Customize Skims 
    # today = datetime.now().strftime("%Y_%m_%d")
    # input_path_template = "data/interim/cube_io/mtc_skims/COM_HWYSKIM{tod}.omx"
    # skims_out = Path(output_dir, f"mtc_blended_skims_{today}.omx")
    # create_blended_skims(input_path_template, skims_out)


    # Skims     
    
    skims_path = "data/interim/cube_io/mtc_skims/COM_HWYSKIM{tod}.omx"
    skims_out = Path(output_dir, f"mtc_blended_skims_{today}.omx")
    long_format_skims = read_mtc_skims(skims_path)
    long_format_skims = long_format_skims[(long_format_skims["origin"] <= n) & (long_format_skims["destination"] <= n)]
    skims_omx_out = omx.open_file(skims_out, "w")

    # Same as in TRUCK_DISTRIB_LOS_TOLL_PART in
    # 2023_TM161_IPA_35\CTRAMP\scripts\block\hwyParam.block"
    toll_share = 0.5 
    for output_col, cfg in blended_skim_defs.items():

        non_toll = sum(
            weight * long_format_skims[f"{cfg['skim']}_{tod}"]
            for tod, weight in cfg["weights"].items()
            )

        toll = sum(
            weight * long_format_skims[f"{cfg['toll_skim']}_{tod}"]
            for tod, weight in cfg["weights"].items()
            )

        long_format_skims[output_col] = (
            non_toll * (1 - toll_share)
            + toll * toll_share
            )
        
        skims_omx_out[output_col] = np.array(long_format_skims.pivot(index = "origin", columns = "destination", values = output_col))

    skims_omx_out.close()

    # Trips 
    trips_path = "data/interim/matrix_projection/sw_od_trips_with_mtc_format/TripsTrk{tod}x.omx"
    long_format_trips = read_mtc_trips(trips_path)
    long_format_trips = long_format_trips[(long_format_trips["origin"] <= n) & (long_format_trips["destination"] <= n)]

    # Merge trips and skims
    df = long_format_trips.merge(long_format_skims, how = "left", on = ["origin", "destination"]) 
    df["total_trips"] = df.filter(regex=r'^(vstruck|struck|mtruck|ctruck)').sum(axis = 1)
    df["very_small_trucks"] = df.filter(regex=r'^(vstruck)').sum(axis = 1)
    df["small_trucks"] = df.filter(regex=r'^(struck)').sum(axis = 1)
    df["medium_trucks"] = df.filter(regex=r'^(mtruck)').sum(axis = 1)
    df["large_trucks"] = df.filter(regex=r'^(ctruck)').sum(axis = 1)

    # Compute all frequency Distribution Pairs 
    frequency_distribution_pairs = [
        {"small_trucks": "blended_time_struck"}, 
        {"medium_trucks": "blended_time_mtrucks"},
        {"large_trucks": "blended_time_ctrucks"},
        {"small_trucks": "blended_distance_struck"},
        {"medium_trucks": "blended_distance_mtrucks"},
        {"large_trucks": "blended_distance_ctrucks"},
        ]
    
    for pair in frequency_distribution_pairs:
        frequency_distributions = compute_weighted_histograms(
            df, 
            pair, 
            bins_width = 5, # 5 miles for distance, or 5 mins for time
            )
        name =  f"observed_frequency_distribution_{list(pair.values())[0]}.csv"
        out = Path(output_dir, name)
        frequency_distributions.to_csv(out, index = False)

    # Save P/A Table 
    productions = df.groupby('origin')[["small_trucks", "medium_trucks", "large_trucks"]].sum().add_suffix("_production")
    productions.index.name = "TAZ1454"
    attractions = df.groupby('destination')[["small_trucks", "medium_trucks", "large_trucks"]].sum().add_suffix("_attraction")
    attractions.index.name = "TAZ1454"
    pa = pd.concat([productions, attractions], axis = 1)
    pa.to_csv(Path(output_dir, "SW_trip_generation_TAZ1454.csv"))
    pa.to_parquet(Path(output_dir, "SW_trip_generation_TAZ1454.parquet"))
    return None




def main() -> None:
    """Entry point for the EDA pipeline script.

    Returns
    -------
    None
    """
    # parser = argparse.ArgumentParser(description="")
    # parser.add_argument(
    #     "--config", help="text",
    # )
    # args = parser.parse_args()
    run()


if __name__ == "__main__":
    main()
