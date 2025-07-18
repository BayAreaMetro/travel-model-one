#!/usr/bin/env python3
"""
This script is used for computing accessible jobs. 
The final output is a single CSV file named "NPA_Metrics_Goal_1A_to_1F.csv".
Function tally_access_to_jobs_v3() is modified based on scenarioMetrics.py function tally_access_to_jobs_v2.

The script reads the following input files:
- main/householdData_*.csv (household file), * is the highest numbered file in the main folder
- INPUT/metrics/taz_coc_crosswalk.csv (EPC_18 data)
- INPUT/metrics/taz1454_epcPBA50plus_2024_02_29.csv (EPC_22 data)
- database/TimeSkimsDatabaseAM.csv (time-skim data)
- landuse/tazData.csv (TAZ employment/socioeconomic data)

The script writes the following output files:
- metrics/accessed_jobs_by_origin_zone.csv (debug file)
- metrics/NPA_Metrics_Goal_1A_to_1F.csv with columns:
  + epc_category:              one of N/A, all_taz, epc_22, epc_18
  + auto_hh_category:          one of N/A, TOTHH, zero_car_hh, car_light_hh
  + wtrn_45_acc_jobs_weighted: jobs accessible within 45 minutes of transit weighted by persons (for EPC) or households (for auto_hh_category)
  + total_jobs_weighted:       total jobs weighted by persons (for EPC) or households (for auto_hh_category)
  + wtrn_45_acc_accessible_job_share: wtrn_45_acc_jobs_weighted/total_jobs_weighted
  + acc_jobs_to_all_jobs_ratio

Goal 1 scripts asana task: https://app.asana.com/1/11860278793487/project/1205004773899709/task/1209227244858523?focus=true
"""

import os
import pathlib
from pathlib import Path
import numpy as np
import pandas as pd
import logging


def process_households():
    """
    Process the household file to count "zero‐car" and "car‐light" households by TAZ and return the results
    via a dataframe with columns, TAZ, 
    """
    # Find the highest numbered householdData file in the main folder
    household_files = list(pathlib.Path("main").glob("householdData_*.csv"))

    # Extract numbers from filenames and find the highest
    file_numbers = [int(f.stem.split('_')[-1]) for f in household_files if f.stem.split('_')[-1].isdigit()]
    input_file = pathlib.Path(f"main/householdData_{max(file_numbers)}.csv")
    logger.info(f"Reading household file: {input_file}")
    df = pd.read_csv(input_file, usecols=['hh_id', 'taz', 'autos', 'workers','sampleRate'])
    
    df['zero_car'] = 0
    df['car_light'] = 0
    df.loc[df['autos'] == 0, 'zero_car'] = 1.0/df.sampleRate
    df.loc[df['autos'] < df['workers'], 'car_light'] = 1.0/df.sampleRate
    
    household_autos_df = df.groupby("taz").agg(
        zero_car_hh = pd.NamedAgg(column='zero_car', aggfunc='sum'),
        car_light_hh = pd.NamedAgg(column='car_light', aggfunc='sum'),
    ).reset_index(drop=False)
    logger.info(f"Household processing completed; household_autos_df.head():\n{household_autos_df.head()}")
    return household_autos_df

def tally_access_to_jobs_v3(household_autos_df, access_type):
    """
    Tally accessible jobs by reading time‐skim data, TAZ employment/socioeconomic data, and the household counts. 
    The function updates metrics_dict with person‐and household–weighted accessible jobs.
    This function is modified based on scenarioMetrics.py function tally_access_to_jobs_v2.

    access_type: either 'walkToTransit' (only consider wTrnW) or 'walkDriveToTransit' (either wTrnW or dTrnW)

    Returns pandas.DataFrame with columns
    epc_category, auto_hh_category, trn_45_acc_jobs_weighted, total_jobs_weighted, trn_45_acc_accessible_job_share
    """
    logger.info("\nTallying accessible jobs (v3)...")
    # Read travel‐time (time‐skim) data
    tt_file = pathlib.Path("database") / "TimeSkimsDatabaseAM.csv"
    logger.info(f"Reading travel time data from: {tt_file}")
    traveltime_df = pd.read_csv(tt_file)[['orig', 'dest', 'da', 'daToll', 'wTrnW', 'dTrnW', 'bike', 'walk']]
    traveltime_df.replace(-999.0, np.nan, inplace=True)
    if access_type == 'walkToTransit':
        # transit access is defined as within 45 minutes of walking to transit
        traveltime_df['trn_45'] = (traveltime_df['wTrnW'] <= 45).astype(int)
    elif access_type == 'walkDriveToTransit':
        # transit access is defined as within 45 minutes of either walking or driving to transit
        traveltime_df['trn_45'] = ((traveltime_df['wTrnW'] <= 45) | (traveltime_df['dTrnW'] <= 45)).astype(int)

    # Read TAZ employment and socioeconomic data
    taz_file = pathlib.Path("landuse") / "tazData.csv"
    logger.info(f"Reading TAZ data from: {taz_file}")
    taz_df = pd.read_csv(taz_file)[['ZONE','TOTHH', 'TOTPOP', 'EMPRES', 'TOTEMP']]
    total_emp = taz_df['TOTEMP'].sum()
    total_pop = taz_df['TOTPOP'].sum()
    total_hh  = taz_df['TOTHH'].sum()
    logger.info(f"Regional TOTEMP={taz_df['TOTEMP'].sum():,}")
    logger.info(f"Regional TOTPOP={taz_df['TOTPOP'].sum():,}")
    logger.info(f"Regional TOTHH={taz_df['TOTHH'].sum():,}")
    # metrics_dict.update({"total_jobs": total_emp, "total_pop": total_pop, "total_hh": total_hh})

    # read taz -> county mapping
    taz_county_df = pd.read_csv(
        pathlib.Path(__file__).parent.parent.parent.parent / "geographies" / "taz-superdistrict-county.csv",
        usecols=['ZONE','COUNTY_NAME']
    )
    taz_county_df.rename(columns={'COUNTY_NAME':'county_name'}, inplace=True)
    taz_df = pd.merge(left=taz_df, right=taz_county_df, how='left', validate='one_to_one')
    COUNTIES_LIST = taz_county_df['county_name'].drop_duplicates().tolist()
    if 'External' in COUNTIES_LIST: COUNTIES_LIST.remove('External')

    # Merge employment counts to time-skims (matching destination TAZ)
    traveltime_df = traveltime_df.merge(taz_df[['ZONE','TOTEMP']], left_on="dest", right_on="ZONE", how="left")
    traveltime_df.drop(columns="ZONE", inplace=True)
    traveltime_df['trn_45*TOTEMP'] = traveltime_df['trn_45']*traveltime_df['TOTEMP']  # employment within 45 min
    traveltime_df['wTrnW'] = pd.to_numeric(traveltime_df['wTrnW'])
    traveltime_df['dTrnW'] = pd.to_numeric(traveltime_df['dTrnW'])
    logger.info(f"traveltime_df.head():\n{traveltime_df.head()}")

    # Aggregate accessible jobs to origins
    accessiblejobs_df = traveltime_df.groupby('orig').agg(
        wTrnW_mean         = pd.NamedAgg(column='wTrnW', aggfunc='mean'),
        dTrnW_mean         = pd.NamedAgg(column='dTrnW', aggfunc='mean'),
        trn_45_TOTEMP_sum = pd.NamedAgg(column='trn_45*TOTEMP', aggfunc='sum')
    ).rename(columns={'trn_45_TOTEMP_sum':'sum(trn_45*TOTEMP)'}).reset_index()
    logger.info(f"accessiblejobs_df.head():\n{accessiblejobs_df.head()}")

    # --------------------------- Merge concerned socioeconomic data ---------------------------
    # Read Equity Priority Communities (EPC) file
    epc_22_df = pd.read_csv(pathlib.Path("INPUT/metrics/taz1454_epcPBA50plus_2024_02_29.csv"), usecols=['TAZ1454','taz_epc'])
    epc_18_df = pd.read_csv(pathlib.Path("INPUT/metrics/taz_coc_crosswalk.csv"))
    logger.info(f"Read epc_22:\n{epc_22_df.head()}")
    logger.info(f"Read epc_18_df:\n{epc_18_df.head()}")

    taz_df.rename(columns={'ZONE':'TAZ1454'}, inplace=True)
    taz_df = taz_df.merge(epc_22_df, on="TAZ1454", validate="one_to_one").rename(columns={"taz_epc": "taz_epc_22"})
    taz_df = taz_df.merge(epc_18_df, on="TAZ1454", validate="one_to_one").rename(columns={"taz_coc": "taz_epc_18"})
    logger.info(f"Found {taz_df['taz_epc_22'].sum()} TAZs in epc_22s")
    logger.info(f"Found {taz_df['taz_epc_18'].sum()} TAZs in epc_18s")
    logger.info(f"taz_df.head():\n{taz_df.head()}")

    taz_df = pd.merge(
        left=taz_df,
        right=household_autos_df.rename(columns={'taz':'TAZ1454'}),
        on='TAZ1454',
        validate='one_to_one'
    )
    logger.info(f"taz_df.head():\n{taz_df.head()}")
    # make sure no NaNs
    nan_rows = taz_df[taz_df.isnull().any(axis=1)]
    assert(len(nan_rows)==0)

    # Merge concerned socioeconomic info into aggregated accessible jobs (match origin TAZ)
    accessiblejobs_df = accessiblejobs_df.merge(
        taz_df[['TAZ1454', 'county_name', 'TOTPOP', 'TOTHH', 'taz_epc_22', 'taz_epc_18', 'zero_car_hh', 'car_light_hh']],
        left_on='orig', right_on='TAZ1454', how='left', validate="one_to_one")
    logger.info(f"accessiblejobs_df.head():\n{accessiblejobs_df.head()}")
    # columns are now: orig, wTrnW_mean, dTrnW_mean, TOTEMP_sum , trn_45_TOTEMP_sum, 
    #                  TAZ1454, TOTPOP, TOTHH, taz_epc_22, taz_epc_18, zero_car_hh, car_light_hh

    # Save a debug file (optional)
    if access_type == 'walkToTransit':
        debug_out = pathlib.Path("metrics", "accessed_jobs_by_origin_zone_walkToTransit(intermediate_file).csv")
    elif access_type == 'walkDriveToTransit':
        debug_out = pathlib.Path("metrics", "accessed_jobs_by_origin_zone_walkDriveToTransit(intermediate_file).csv")
    accessiblejobs_df.to_csv(debug_out, index=False)
    logger.info(f"Debug file written to {debug_out}")
    
    # TODO: Why are the weightings done differently for EPCs vs auto ownership categories?
    # TODO: It seems like they could be done similarly...
    # TODO: And given that this is about job accessibility, maybe EMPRES would make more sense?
    # --------------------------- Compute population‐weighted accessible jobs ---------------------------
    accessiblejobs_df['sum(trn_45*TOTEMP)*TOTPOP'] = accessiblejobs_df['sum(trn_45*TOTEMP)'] * accessiblejobs_df['TOTPOP']
    logger.info(f"accessiblejobs_df.head():\n{accessiblejobs_df.head()}")

    metrics_dict_list = []
    for geography in ["all_taz", "epc_22", "epc_18"] + COUNTIES_LIST:
        metrics_dict = {}

        metrics_dict['county'] = 'all counties'
        metrics_dict['epc_category'] = 'N/A'
        if geography.startswith("epc"):
            metrics_dict['epc_category'] = geography
        elif geography != 'all_taz':
            metrics_dict['county'] = geography

        metrics_dict['auto_hh_category'] = 'N/A'

        # select for within EPC or within county
        if geography == "all_taz":
            sub_df = accessiblejobs_df
            totalpop_subset = total_pop
        elif geography.startswith("epc"):
            sub_df = accessiblejobs_df[accessiblejobs_df[f"taz_{geography}"] == 1]
            totalpop_subset = taz_df.loc[taz_df[f"taz_{geography}"] == 1, "TOTPOP"].sum()
        else:
            sub_df = accessiblejobs_df[accessiblejobs_df['county_name'] == geography]
            totalpop_subset = taz_df.loc[taz_df['county_name'] == geography, "TOTPOP"].sum()

        # metrics_dict[f"trn_45_acc_jobs{suffix}"] = sub_df['trn_45'].sum()
        metrics_dict["trn_45_acc_jobs_weighted"] = sub_df['sum(trn_45*TOTEMP)*TOTPOP'].sum()
        metrics_dict["total_jobs_weighted"]       = total_emp * totalpop_subset
        metrics_dict["trn_45_acc_accessible_job_share"]  = \
            metrics_dict["trn_45_acc_jobs_weighted"] / metrics_dict["total_jobs_weighted"]

        metrics_dict_list.append(metrics_dict)

        # ratio of EPC / all -- the first one (index=zero) is region-wide
        metrics_dict["acc_jobs_to_all_jobs_ratio"] = \
            metrics_dict["trn_45_acc_accessible_job_share"] / metrics_dict_list[0]["trn_45_acc_accessible_job_share"]

    metrics_df = pd.DataFrame(metrics_dict_list)
    logger.info(f"metrics_df:\n{metrics_df}")

    # --------------------------- Compute household‐weighted accessible jobs ---------------------------
    accessiblejobs_df['sum(trn_45*TOTEMP)*TOTHH'] = accessiblejobs_df['sum(trn_45*TOTEMP)'] * accessiblejobs_df['TOTHH']

    metrics_dict_list = []
    for auto_hh_category in ["TOTHH","zero_car_hh", "car_light_hh"]:
        metrics_dict = {}
        metrics_dict['county'] = 'all counties'
        metrics_dict['epc_category'] = 'N/A'
        metrics_dict['auto_hh_category'] = auto_hh_category

        trn_45_weighted_hh = accessiblejobs_df[auto_hh_category] * accessiblejobs_df['sum(trn_45*TOTEMP)']
        TOTEMP_weighted_hh  = accessiblejobs_df[auto_hh_category] * total_emp
            
        metrics_dict["trn_45_acc_jobs_weighted"] = trn_45_weighted_hh.sum()
        metrics_dict["total_jobs_weighted"] = TOTEMP_weighted_hh.sum()
        metrics_dict["trn_45_acc_accessible_job_share"] = \
            metrics_dict["trn_45_acc_jobs_weighted"] / metrics_dict["total_jobs_weighted"]

        metrics_dict_list.append(metrics_dict)

        # ratio of auto_hh_category / all -- the first one (index=zero) is auto_hh_category=TOTHH
        # TODO: This is inconsistent with how the script previously did it, as it used the person-weighted denominator
        # TODO: However, I think this is more logical
        metrics_dict["acc_jobs_to_all_jobs_ratio"] = \
            metrics_dict["trn_45_acc_accessible_job_share"] / metrics_dict_list[0]["trn_45_acc_accessible_job_share"]


    metrics_df = pd.concat([metrics_df, pd.DataFrame(metrics_dict_list)])
    logger.info(f"metrics_df:\n{metrics_df}")

    logger.info("Tallying accessible jobs completed.")
    return metrics_df


# ---------------------------
# Main routine
# ---------------------------

if __name__ == '__main__':
    pd.set_option('display.width', 500)
    pd.set_option('display.precision', 10)

    MODEL_DIR = pathlib.Path(".")

    # Set up logging
    log_file = MODEL_DIR / "metrics" / 'NPA_metrics_Goal_1A_to_1F.log'
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        filemode='w',
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__file__)
    logger.info("Script execution started")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Process zero-vehicle and car-light households (needed for the job access metrics)
    household_autos_df = process_households()
    
    # Compute the job access metrics (accessible jobs)
    logger.info("Computing job access metrics for walkToTransit access <= 45 minutes")
    metrics_walkToTransit_df = tally_access_to_jobs_v3(household_autos_df, access_type='walkToTransit')
    metrics_walkToTransit_df.rename(columns={'trn_45_acc_jobs_weighted': 'walkToTransit_45_acc_jobs_weighted',
                                            'total_jobs_weighted': 'walkToTransit_total_jobs_weighted',
                                            'trn_45_acc_accessible_job_share': 'walkToTransit_45_acc_accessible_job_share',
                                            'acc_jobs_to_all_jobs_ratio': 'walkToTransit_acc_jobs_to_all_jobs_ratio'}, inplace=True)
    
    logger.info("Computing job access metrics for walkToTransit or driveToTransit access <= 45 minutes")
    metrics_walkDriveToTransit_df = tally_access_to_jobs_v3(household_autos_df, access_type='walkDriveToTransit')
    metrics_walkDriveToTransit_df.rename(columns={'trn_45_acc_jobs_weighted': 'walkDriveToTransit_45_acc_jobs_weighted',
                                                  'total_jobs_weighted': 'walkDriveToTransit_total_jobs_weighted',
                                                  'trn_45_acc_accessible_job_share': 'walkDriveToTransit_45_acc_accessible_job_share',
                                                  'acc_jobs_to_all_jobs_ratio': 'walkDriveToTransit_acc_jobs_to_all_jobs_ratio'}, inplace=True)
    metrics_df = pd.merge(
        metrics_walkToTransit_df,
        metrics_walkDriveToTransit_df,
        on=['county', 'epc_category', 'auto_hh_category'],
        how='outer', validate='one_to_one'
    )
    output_file = pathlib.Path("metrics", "NPA_metrics_Goal_1A_to_1F.csv")
    metrics_df.to_csv(output_file, index=True)
    logger.info(f"Wrote {output_file}")
