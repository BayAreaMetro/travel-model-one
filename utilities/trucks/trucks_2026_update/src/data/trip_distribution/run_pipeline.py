from pathlib import Path
import pandas as pd
import numpy as np
import openmatrix as omx

from src.data.EDA.mtc_od import read_mtc_skims, read_mtc_trips
from src.data.EDA.trip_distributions import compute_weighted_histograms

blended_skim_defs = {
        "blended_time_vstrucks": {
            "skim": "TIMEVSM", 
            "toll_skim": "TOLLTIMEVSM",
            "weights": {"MD": 2/3, "AM": 1/3},
        },
        "blended_time_strucks": {
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
        "blended_distance_vstrucks": {
            "skim": "DISTVSM", 
            "toll_skim": "TOLLDISTVSM",
            "weights": {"MD": 1},
        },
        "blended_distance_strucks": {
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

def main() -> None:
    """
    Build trip distribution calibration inputs. 

    This function prepares the three core inputs required for gravity model
    calibration in src/models/trip_distribution:

    1. skims
        Recreates the blended highway skims used by the MTC truck model,
        including both toll and non-toll components. In addition to the
        legacy time-based impedance skims, this process generates
        distance-based blended skims to support evaluation of alternative
        impedance formulations, as discussed in:
        https://github.com/BayAreaMetro/travel-model-one/issues/99


    2. Production/Attraction (P/A) tables
       Aggregates truck trip productions and attractions by TAZ for small,
       medium, and large truck classes.

    3. Observed travel frequency distributions
        Computes observed trip time and trip length frequency distributions
        from the OD tables using blended travel time and distance skims.
        These distributions are used as calibration targets. Distributions
        are calculated using 1-minute and 1-mile bins to replicate the
        interval structure of the truck friction factors defined in
        2023_TM161_IPA_35/INPUT/nonres/truckFF.dat. 


    Workflow
    --------
    1. Read MTC highway skims and restrict them to the 1,454 internal TAZs.
    2. Create blended time and distance skims using blended_skim_defs config.
        Modify blended_skim_defs object to add/remove/edit blended skims. 
    3. Save blended skims to a new OMX file.
    4. Read Statewide truck OD matrices in long format restrict them to internal TAZs.
    5. Merge trips with blended skims.
    6. Aggregate truck trips into truck size categories.
    7. Compute observed frequency distributions for each truck type and blended skims.
    8. Generate TAZ-level production and attraction tables.

    Outputs
    -------
    All outputs are written to:

        data/processed/trip_distribution_inputs/

    Files produced:
        * mtc_blended_skims.omx
            Blended highway skims used for trip distribution.

        * observed_frequency_distribution_*.csv
            Observed travel time and distance frequency distributions for
            calibration and validation.

        * SW_trip_generation_TAZ1454.csv
        * SW_trip_generation_TAZ1454.parquet
            TAZ-level truck productions and attractions for the 1,454
            internal model zones.
    """
    
    internal_tazs = 1454 
    output_dir = Path("data/processed/trip_distribution_inputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # --------------
    # Output 1. Skims    
    # --------------- 
    skims_path = "data/interim/cube_io/mtc_skims/COM_HWYSKIM{tod}.omx"
    skims_out = Path(output_dir, f"mtc_blended_skims.omx")
    long_format_skims = read_mtc_skims(skims_path)
    long_format_skims = long_format_skims[(long_format_skims["origin"] <= internal_tazs) & (long_format_skims["destination"] <= internal_tazs)]
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

    # -------------------
    # Output 2: P/A Table 
    # --------------------
    trips_path = "data/interim/matrix_projection/sw_od_trips_with_mtc_format/TripsTrk{tod}x.omx"
    long_format_trips = read_mtc_trips(trips_path)
    long_format_trips = long_format_trips[(long_format_trips["origin"] <= internal_tazs) & (long_format_trips["destination"] <= internal_tazs)]
    long_format_trips["total_trips"] = long_format_trips.filter(regex=r'^(vstruck|struck|mtruck|ctruck)').sum(axis = 1)
    long_format_trips["very_small_trucks"] = long_format_trips.filter(regex=r'^(vstruck)').sum(axis = 1)
    long_format_trips["small_trucks"] = long_format_trips.filter(regex=r'^(struck)').sum(axis = 1)
    long_format_trips["medium_trucks"] = long_format_trips.filter(regex=r'^(mtruck)').sum(axis = 1)
    long_format_trips["large_trucks"] = long_format_trips.filter(regex=r'^(ctruck)').sum(axis = 1)

    productions = long_format_trips.groupby('origin')[["small_trucks", "medium_trucks", "large_trucks"]].sum().add_suffix("_production")
    productions.index.name = "TAZ1454"
    attractions = long_format_trips.groupby('destination')[["small_trucks", "medium_trucks", "large_trucks"]].sum().add_suffix("_attraction")
    attractions.index.name = "TAZ1454"
    pa = pd.concat([productions, attractions], axis = 1)
    pa.to_csv(Path(output_dir, "SW_trip_generation_TAZ1454.csv"))
    pa.to_parquet(Path(output_dir, "SW_trip_generation_TAZ1454.parquet"))

    #------------------------------------
    # Output 3. Frequency Distributions
    #-------------------------------------
    df = long_format_trips.merge(long_format_skims, how = "left", on = ["origin", "destination"]) 
    # df["total_trips"] = df.filter(regex=r'^(vstruck|struck|mtruck|ctruck)').sum(axis = 1)
    # df["very_small_trucks"] = df.filter(regex=r'^(vstruck)').sum(axis = 1)
    # df["small_trucks"] = df.filter(regex=r'^(struck)').sum(axis = 1)
    # df["medium_trucks"] = df.filter(regex=r'^(mtruck)').sum(axis = 1)
    # df["large_trucks"] = df.filter(regex=r'^(ctruck)').sum(axis = 1)

    frequency_distribution_pairs = [
        {"small_trucks": "blended_time_strucks"}, 
        {"medium_trucks": "blended_time_mtrucks"},
        {"large_trucks": "blended_time_ctrucks"},
        {"small_trucks": "blended_distance_strucks"},
        {"medium_trucks": "blended_distance_mtrucks"},
        {"large_trucks": "blended_distance_ctrucks"},
        ]
    
    for pair in frequency_distribution_pairs:
        # bins_width = 5 means five mile for distance, or five min for time
        frequency_distributions = compute_weighted_histograms(df, pair, bins_width = 5)
        name =  f"observed_frequency_distribution_{list(pair.values())[0]}.csv"
        out = Path(output_dir, name)
        frequency_distributions.to_csv(out, index = False)
    return None


if __name__ == "__main__":
    main()
