"""EDA pipeline — comparative analysis of MTC TM1.6 and CSF2TDM truck trip models.

Purpose
-------
Orchestrates a side-by-side exploratory analysis of truck trip demand from two
independent travel demand models:

* **MTC TM1.6** — the regional model, with four truck classes (very-small,
  small, medium, large) across five time-of-day periods.
* **CSF2TDM** (statewide) — Caltrans' California Statewide Freight
  Travel Demand Model, with three truck classes (light, medium, heavy) from a
  single scenario year (2020).

The pipeline produces three comparable outputs for each model: a county OD
matrix, trip rates by county, and travel distance/time distributions.

Inputs
------
All input paths are defined in ``src.data.EDA.configs``.

MTC TM1.6
    * **Trip matrices** — one OMX file per time period (EA, AM, MD, PM, EV),
      1475 × 1475 TAZ grid.  Contains vstruck, struck, mtruck, ctruck matrices.
    * **Highway skims** — one OMX file per period (AM, MD), same TAZ grid.
      Contains distance and travel-time matrices for each truck size class.
    * **Land use** — ``tazData.csv`` from the 2023 TM1.6 IPA run, used for
      county mapping and trip-rate denominators (households, employment,
      population).

CSF2TDM (statewide)
    * **Trip matrix** — single OMX (``TRIPS_FFM_2020.omx``), 7000 × 7000 TAZ
      grid.  Contains LT, MT1, MT2, HT matrices.  Filtered to MTC TAZs and
      five TLN gateway nodes (ports and airports).
    * **Highway skims** — HDF5 file with AM and Mid-day distance/time skims for
      truck classes, read in chunks and filtered to MTC pairs.
    * **TAZ-to-county mapping** — ``taz_MPO_region.csv`` from Caltrans, used
      to identify which of the 7000 statewide TAZs belong to the MTC region.

Outputs
-------
Tables saved to ``data/interim/eda/`` (Parquet):
    * ``SW_county_od_matrix.parquet`` — 9×9 county OD matrix (CSF2TDM).
    * ``SW_trip_rates_by_county.parquet`` — trip rates per HH/emp/pop by county
      and truck class (CSF2TDM).
    * ``SW_trip_distributions.parquet`` — binned distance and time distributions
      by truck class for the 9-county region and each TLN origin (CSF2TDM).
    * ``TM1.6_county_od_matrix.parquet`` — same structure for MTC TM1.6.
    * ``TM1.6_trip_rates_by_county.parquet`` — same structure for MTC TM1.6.
    * ``TM1.6_trip_distributions.parquet`` — same structure for MTC TM1.6.

Figures saved to ``reports/eda/`` (PNG):
    * Trip-rate line charts by county, one figure per metric
      (trips/HH, trips/employment, trips/population).
    * Distance and time distribution charts, one figure per plot configuration
      (region-wide + individual TLN origins).

Notes
-----
* The CSF2TDM matrix is filtered to MTC TAZs and five TLN gateway zones
  (ports of SF, Redwood City, Oakland; SFO and OAK airports) before any
  computation.
* Composite skims are computed as a weighted average of AM (weight 1/3) and
  MD/Mid-day (weight 2/3) to be consistent with TM1.6 implementation. 
* Trip rates include a ``REGION`` summary row aggregating all nine Bay Area
  counties.
* Run via ``python -m src.data.EDA.pipeline`` from the project root. 
"""
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
    """Aggregate TAZ-level land use variables to county totals.

    Maps each TAZ to its county using ``COUNTY_MAP`` and sums household,
    population, and employment columns within each county.

    Parameters
    ----------
    taz_df : pd.DataFrame
        TAZ-level land use table with a ``COUNTY`` integer column and
        socioeconomic columns such as ``TOTHH``, ``TOTEMP``, etc.

    Returns
    -------
    pd.DataFrame
        County-indexed DataFrame with summed values for
        ``TOTHH``, ``HHPOP``, ``TOTPOP``, ``EMPRES``, ``TOTEMP``,
        ``RETEMPN``, ``FPSEMPN``, ``HEREMPN``, ``AGREMPN``,
        ``MWTEMPN``, and ``OTHEMPN``.
    """
    cols = ['TOTHH', 'HHPOP', 'TOTPOP','EMPRES', 'TOTEMP',
        'RETEMPN', 'FPSEMPN', 'HEREMPN', 'AGREMPN', 'MWTEMPN', 
        'OTHEMPN']

    taz_df["county"] = taz_df["COUNTY"].map(cfg.COUNTY_MAP)
    return taz_df.groupby("county")[cols].sum()


def county_od_matrix(long_df, counties=None):
    """Pivot long OD trip data into a county-to-county matrix.

    Optionally restricts to trips where both origin and destination counties
    are in ``counties``, then groups by county pair and pivots to a
    wide matrix of total trips.

    Parameters
    ----------
    long_df : pd.DataFrame
        Long-format OD DataFrame with columns ``origin_county``,
        ``destination_county``, and ``total_trips``.
    counties : list of str or None, optional
        If provided, only OD pairs where both endpoints are in this list
        are included.  If ``None``, all county pairs are used.

    Returns
    -------
    pd.DataFrame
        Square matrix indexed by origin county with destination counties
        as columns and integer total trip counts as values.  Missing
        pairs are filled with 0.
    """
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
    """Run the full EDA pipeline for statewide and MTC truck trip data.

    Loads input data, computes county OD matrices, trip rates by county,
    and trip distributions for both the CSF2TDM statewide model and the
    MTC TM1.6 model.  Saves tabular outputs as Parquet files and
    distribution plots as PNG figures.

    Output directories created if absent:

    * ``data/interim/eda/`` — Parquet tables
    * ``reports/eda/`` — PNG figures

    Returns
    -------
    None
    """
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
    run_eda()


if __name__ == "__main__":
    main()
