import argparse
import logging
import time
from pathlib import Path

import pandas as pd
import geopandas as gpd

from src.utils import setup_logging, load_config, save 

logger = logging.getLogger(__name__)


import pandas as pd

def clean_output(df, link_col="link_id"):
    """
    Enrich a long-format dataframe by propagating:
      - geometry across all rows of each link_id
      - count_location_id across all rows of each link_id

    Parameters
    ----------
    df : pandas.DataFrame or GeoDataFrame
        Input dataframe containing both observed and simulated rows.
    link_col : str
        Column used to join (default: 'link_id').

    Returns
    -------
    pandas.DataFrame or GeoDataFrame
        Enriched dataframe with geometry and count_location_id filled.
    """

    out = df.copy()

    # --- Build lookup tables ---
    geom_lookup = (
        out[[link_col, "geometry", "ROUTENUM", "ROUTEDIR", "DISTANCE"]]
        .dropna(subset=["geometry"])
        .drop_duplicates(subset=[link_col])
    )

    count_lookup = (
        out[[link_col, "count_location_id"]]
        .dropna(subset=["count_location_id"])
        .drop_duplicates(subset=[link_col])
    )

    # --- Merge lookups back ---
    out = out.merge(
        geom_lookup,
        on=link_col,
        how="left",
        suffixes=("", "_geom")
    )

    out = out.merge(
        count_lookup,
        on=link_col,
        how="left",
        suffixes=("", "_count")
    )

    # --- Fill missing values ---
    if "geometry_geom" in out.columns:
        out["geometry"] = out["geometry"].combine_first(out["geometry_geom"])

    if "ROUTEDIR_geom" in out.columns:
        out["ROUTEDIR"] = out["ROUTEDIR"].combine_first(out["ROUTEDIR_geom"])

    if "ROUTENUM_geom" in out.columns:
        out["ROUTENUM"] = out["ROUTENUM"].combine_first(out["ROUTENUM_geom"])

    if "DISTANCE_geom" in out.columns:
        out["DISTANCE"] = out["DISTANCE"].combine_first(out["DISTANCE_geom"])

    if "count_location_id_count" in out.columns:
        out["count_location_id"] = out["count_location_id"].combine_first(
            out["count_location_id_count"]
        )

    drop_cols = [
        "geometry_geom", 
        "ROUTEDIR_geom", 
        "ROUTENUM_geom", 
        "DISTANCE_geom"
        "count_location_id_count"] 
    # --- Clean up ---
    cols_to_drop = [c for c in drop_cols if c in out.columns]
    out = out.drop(columns=cols_to_drop)

    # --- calculate VTM (volumne * distance)
    out["vmt"] = out["volume"] * out["DISTANCE"]

    # --- Final output columns
    out_cols = [
        "count_location_id",
        "link_id","tod", 
        "ROUTENUM", 
        "ROUTEDIR",
        "DISTANCE",
        "truck_type_1", 
        "truck_type_2", 
        "volume",
        "vmt",
        "type",
        "source", 
        "geometry",
        ]
    out = out[out_cols]
    
    # --- Column rename (10 character max limit for shapefiles)
    rename_dict = {
        "count_location_id": "cnt_loc_id",
        "truck_type_1": "trk_typ_1",
        "truck_type_2": "trk_typ_2",
        "ROUTENUM": "route", 
        "ROUTEDIR": "direction",
        "DISTANCE": "distance",
    }
    out = out.rename(columns = rename_dict) 
    return out


def summarize_predicted_counts(model_cfg: dict, cfg: dict) -> gpd.GeoDataFrame:
    scenario_name = model_cfg["name"]
    scenario_path = Path(model_cfg["path"])
    
    loaded_network =  gpd.read_file(scenario_path/ f"hwy/avgload5period/avgload5period_links.shp")
    
    loaded_network["link_id"] = (
        loaded_network["A"].astype(str) + "-" +
        loaded_network["B"].astype(str)
    )

    tods = ["EA", "AM", "MD", "PM", "EV"]
    truck_types = {"HV" : ("HV", "HVT"), "SM": ("SM", "SMT")}

    cols = []
    for tod in tods:
        for truck_type, (notoll, toll) in truck_types.items():
            name = f"VOL_{tod}_{truck_type}"
            loaded_network[name] = loaded_network[[f"VOL{tod}_{notoll}", f"VOL{tod}_{toll}"]].sum(axis = 1)
            cols.append(name)

    
    df_long = loaded_network.melt(
        id_vars=["link_id", "ROUTENUM", "ROUTEDIR", "DISTANCE", "geometry"],
        value_vars=cols,
        var_name="var",
        value_name="volume"
    )

    df_long["tod"] = df_long["var"].str[4:6]
    df_long["truck_type_2"] = df_long["var"].str[-2:]
    df_long["type"] = "simulated"
    df_long["source"] = scenario_name
    return df_long


def run(config_path: str = "configs/evaluation.yaml") -> gpd.GeoDataFrame: 
    """
    Compares observed truck counts with predicted counts from multiple model runs 
    specified in the configuration file, and produces a consolidated GeoDataFrame 
    for analysis.

    Parameters
    ----------
    config_path : str
        Path to the YAML configuration file.
    """
    log_path = setup_logging(log_dir="data/logs", log_name="evaluation")
    cfg = load_config(config_path)
    t0  = time.perf_counter()
    logger.info("=" * 60)
    logger.info("Starting Evaluation Data Processing pipeline")
    logger.info("Config: %s", config_path)
    logger.info("=" * 60)

    if log_path:
        logger.info("Log file: %s", log_path)

    model_runs = cfg["model_runs"]

    # Read observed data 
    observed = pd.read_csv(cfg["observed_data"])
    
    # Scenario Results: 
    summaries = [observed]
    for run in model_runs:
        logger.info("  → run: %s", run["name"])
        scenario_summary = summarize_predicted_counts(run, cfg)
        summaries.append(scenario_summary)

    out = pd.concat(summaries, axis=0)
    out = clean_output(out)
    out = gpd.GeoDataFrame(out, geometry="geometry")
    out = out.set_crs(cfg["network_crs"])
    save(out, Path(cfg["output"]), crs = "EPSG:4326")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Evaluation Data Processing pipeline.")
    parser.add_argument(
        "--config", default="configs/evaluation.yaml",
        help="Path to YAML config file (default: configs/evaluation.yaml)",
    )
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
