import logging
from pathlib import Path

import pandas as pd

from src.utils import save
from src.data.EDA.mtc_od import mtc_od_long_format
from src.data.EDA.sw_od import sw_od_long_format
from src.data.EDA.trip_rates import compute_trip_rates_by_county, plot_rates
from src.data.EDA.trip_distributions import compute_trip_distributions
import src.data.EDA.configs as cfg

logger = logging.getLogger(__name__)

def aggregate_land_use_by_county(taz_df):
    cols = ['TOTHH', 'HHPOP', 'TOTPOP','EMPRES', 'TOTEMP', 
        'RETEMPN', 'FPSEMPN', 'HEREMPN', 'AGREMPN', 'MWTEMPN', 
        'OTHEMPN']

    taz_df["county"] = taz_df["COUNTY"].map(cfg.COUNTY_MAP)
    return taz_df.groupby("county")[cols].sum()


def county_od_matrix(long_df, counties=None):

    if counties is not None: 
        long_df = long_df[
            long_df["origin_county"].isin(counties) & 
            long_df["destination_county"].isin(counties) 
            ].copy()
    
    county_od = (
        long_df
            .groupby(['origin_county', 'destination_county'])['total_trips']
            .sum()
            .reset_index()
    )

    return county_od.pivot(
        index='origin_county',
        columns='destination_county',
        values='total_trips'
        ).fillna(0).round(0).astype(int)


def run_eda():
    tables_outpath = Path("data/interim/eda/")
    figures_outpath = Path("reports/eda/")
    tables_outpath.mkdir(parents=True, exist_ok=True)
    figures_outpath.mkdir(parents=True, exist_ok=True)

    taz_land_use = pd.read_csv("data/external/mtc/2023_TM161_IPA_35/landuse/tazData.csv")
    county_land_use = aggregate_land_use_by_county(taz_land_use)
    counties = list(cfg.COUNTY_MAP.values())
    rate_bases = {
        "TOTHH": "Trips per Household",
        "TOTEMP": "Trips per Employment",
        "TOTPOP": "Trips per Population"
    }

    #CSF2TDM
    sw_long = sw_od_long_format(cfg.SW_INPUT_PATHS)
    sw_county_od = county_od_matrix(sw_long, counties)
    sw_trip_rates = compute_trip_rates_by_county(
        od_long = sw_long, 
        value_cols = ["light_trucks", "medium_trucks", "heavy_trucks"],
        land_use=county_land_use,
        rate_bases=rate_bases
    )
    sw_trip_distributions = compute_trip_distributions(sw_long, cfg.SW_TRIP_DIST_CONFIG, outpath=figures_outpath)
    plot_rates(sw_trip_rates, outpath=figures_outpath)
    
    
    save(sw_county_od, Path(tables_outpath, "SW_county_od_matrix.parquet"))
    save(sw_trip_rates, Path(tables_outpath, "SW_trip_rates_by_county.parquet"))
    save(sw_trip_distributions, Path(tables_outpath, "SW_trip_distributions.parquet"))

    # MTC 
    mtc_long = mtc_od_long_format(cfg.MTC_INPUT_PATHS)
    mtc_county_od = county_od_matrix(mtc_long, counties)
    mtc_trip_rates = compute_trip_rates_by_county(
        od_long = mtc_long, 
        value_cols = ["very_small_trucks", "small_trucks", "medium_trucks", "large_trucks"],
        land_use=county_land_use,
        rate_bases=rate_bases
    )
    plot_rates(mtc_trip_rates, outpath=figures_outpath) 
    mtc_trip_distributions = compute_trip_distributions(mtc_long, cfg.MTC_TRIP_DIST_CONFIG, outpath=figures_outpath) 

    save(mtc_county_od, Path(tables_outpath, "TM1.6_county_od_matrix.parquet"))
    save(mtc_trip_rates, Path(tables_outpath, "TM1.6_trip_rates_by_county.parquet"))
    save(mtc_trip_distributions, Path(tables_outpath, "TM1.6_trip_distributions.parquet"))


def main() -> None:
    # parser = argparse.ArgumentParser(description="")
    # parser.add_argument(
    #     "--config", help="text",
    # )
    # args = parser.parse_args()
    run_eda()


if __name__ == "__main__":
    main()
