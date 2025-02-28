#!/usr/bin/env python3
"""
This script includes two parts, which are used for computing accessible jobs and accessibility benefits (logsum). 
The final output is a single CSV file named "NPA_metrics_Goal_1.csv" that includes both metric sets.
Function tally_access_to_jobs_v3() is modified based on scenarioMetrics.py function tally_access_to_jobs_v2.
Function calculateConsumerSurplus_v2() is modified based on RunResults.py function calculateConsumerSurplus.
The script reads the following input files:
- popsyn/hhFile.csv (household file)
- INPUT/metrics/zero_car_hh.csv (zero-vehicle households)
- INPUT/metrics/car_light_hh.csv (car-light households)
- INPUT/metrics/taz1454_epcPBA50plus_2024_02_23.csv (EPC data)
- database/TimeSkimsDatabaseAM.csv (time-skim data)
- landuse/tazData.csv (TAZ employment/socioeconomic data)
- logsums/mandatoryAccessibilities.csv (mandatory accessibilities)
- logsums/nonMandatoryAccessibilities.csv (nonmandatory accessibilities)
- core_summaries/AccessibilityMarkets.csv (accessibility markets)
The script writes the following output files:
- INPUT/metrics/zero_car_hh.csv (zero-vehicle households), also used for input
- INPUT/metrics/car_light_hh.csv (car-light households), also used for input
- {OUTPUT_Dir}/accessed_jobs_by_origin_zone.csv (debug file)
- {OUTPUT_Dir}/mandatoryAccess_epc1.csv (mandatory accessibilities for EPC1) (debug file)
- {OUTPUT_Dir}/nonmandatoryAccess_epc1.csv (nonmandatory accessibilities for EPC1) (debug file)
- {OUTPUT_Dir}/mandatoryAccess_epc2.csv (mandatory accessibilities for EPC2) (debug file)
- {OUTPUT_Dir}/nonmandatoryAccess_epc2.csv (nonmandatory accessibilities for EPC2) (debug file)
- {OUTPUT_Dir}/NPA_metrics_Goal_1.csv (combined metrics)
The script is run from the working directory where the input files are located.
"""

import os
import pathlib
import numpy as np
import pandas as pd
from collections import OrderedDict

# ---------------------------
# Set working directory & options
# ---------------------------
WORK_DIR = pathlib.Path("../2050_TM160_DBP_Plan_08b")
os.chdir(WORK_DIR)
print("Current working directory:", os.getcwd())
os.makedirs("../data_output", exist_ok=True)
OUTPUT_Dir = pathlib.Path("../data_output")

pd.set_option('display.width', 500)
pd.set_option('display.precision', 10)

# ---------------------------
# Part 1: Household Processing & Accessible Jobs Metrics
# ---------------------------
def process_households():
    """
    Process the household file to count “zero‐car” and “car‐light” households by TAZ and write the results to CSV files (which are used later).
    """
    input_file = pathlib.Path("popsyn/hhFile.csv")
    print(f"Reading household file: {input_file}")
    df = pd.read_csv(input_file, usecols=['HHID', 'TAZ', 'hworkers', 'VEHICL'])
    df.replace(-9, 0, inplace=True)
    df = df[df['VEHICL'].notna()]
    
    zero_car = df[df['VEHICL'] == 0]
    car_light = df[df['VEHICL'] < df['hworkers']]
    
    zero_car_hh_df = zero_car.groupby("TAZ")["HHID"].count().reset_index(name="zero_car_hh")
    car_light_hh_df = car_light.groupby("TAZ")["HHID"].count().reset_index(name="car_light_hh")
    
    # These files are read later in the accessible jobs function.
    zero_car_hh_df.to_csv(pathlib.Path("INPUT/metrics/zero_car_hh.csv"), index=False)
    car_light_hh_df.to_csv(pathlib.Path("INPUT/metrics/car_light_hh.csv"), index=False)
    print("Household processing completed.")

def read_epc_data():
    """
    Read the Equity Priority Communities (EPC) file and return the DataFrame.
    """
    epc_file = pathlib.Path("INPUT/metrics/taz1454_epcPBA50plus_2024_02_23.csv")
    print(f"Reading EPC data from: {epc_file}")
    epc_df = pd.read_csv(epc_file)
    return epc_df

def tally_access_to_jobs_v3(metrics_dict):
    """
    Tally accessible jobs by reading time‐skim data, TAZ employment/socioeconomic data, and the household counts. 
    The function updates metrics_dict with person‐and household–weighted accessible jobs.
    This function is modified based on scenarioMetrics.py function tally_access_to_jobs_v2.
    """
    print("\nTallying accessible jobs (v3)...")
    # Read travel‐time (time‐skim) data
    tt_file = pathlib.Path("database/TimeSkimsDatabaseAM.csv")
    print(f"Reading travel‐time data from: {tt_file}")
    traveltime_df = pd.read_csv(tt_file)[['orig', 'dest', 'da', 'daToll', 'wTrnW', 'bike', 'walk']]
    traveltime_df.replace(-999.0, np.nan, inplace=True)
    traveltime_df['wtrn_45'] = (traveltime_df['wTrnW'] <= 45).astype(int)

    # Read TAZ employment and socioeconomic data
    taz_file = pathlib.Path("landuse/tazData.csv")
    print(f"Reading TAZ data from: {taz_file}")
    taz_df = pd.read_csv(taz_file)[['ZONE', 'TOTHH', 'TOTPOP', 'EMPRES', 'TOTEMP']]
    total_emp = taz_df['TOTEMP'].sum()
    total_pop = taz_df['TOTPOP'].sum()
    total_hh  = taz_df['TOTHH'].sum()
    metrics_dict.update({"total_jobs": total_emp, "total_pop": total_pop, "total_hh": total_hh})

    # Merge employment counts to time-skims (matching destination TAZ)
    traveltime_df = traveltime_df.merge(taz_df[['ZONE', 'TOTEMP']], left_on="dest", right_on="ZONE", how="left")
    traveltime_df.drop(columns="ZONE", inplace=True)
    traveltime_df['wtrn_45'] *= traveltime_df['TOTEMP']
    traveltime_df['wTrnW'] = pd.to_numeric(traveltime_df['wTrnW'])

    # Aggregate accessible jobs to origins
    accessiblejobs_df = traveltime_df.groupby('orig').agg({'wTrnW': np.mean,
                                          'TOTEMP': np.sum,
                                          'wtrn_45': np.sum}).reset_index()

    # --------------------------- Merge concerned socioeconomic data ---------------------------
    # Read Equity Priority Communities (EPC) file
    epc1_df = read_epc_data()
    epc2_df = read_epc_data()
    taz_df = taz_df.merge(epc1_df, left_on="ZONE", right_on="TAZ1454", validate="one_to_one").rename(columns={"taz_epc": "taz_epc1"})
    taz_df = taz_df.merge(epc2_df, left_on="ZONE", right_on="TAZ1454", validate="one_to_one").rename(columns={"taz_epc": "taz_epc2"})
    print(f"Found {taz_df['taz_epc1'].sum()} TAZs in EPC1s")
    print(f"Found {taz_df['taz_epc2'].sum()} TAZs in EPC2s")

    # Read Zero-Vehicle & Car-Light Households
    for metric_file, col_name in [("INPUT/metrics/zero_car_hh.csv", "zero_car_hh"),
                                  ("INPUT/metrics/car_light_hh.csv", "car_light_hh")]:
        print(f"Reading {metric_file}")
        temp_df = pd.read_csv(pathlib.Path(metric_file))
        taz_df = taz_df.merge(temp_df, left_on="ZONE", right_on="TAZ", how="left")
        taz_df[col_name] = taz_df[col_name].fillna(0)

    # Merge concerned socioeconomic info into aggregated accessible jobs (match origin TAZ)
    accessiblejobs_df = accessiblejobs_df.merge(taz_df[['ZONE', 'TOTPOP', 'TOTHH', 'taz_epc1', 'taz_epc2', 'zero_car_hh', 'car_light_hh']],
                          left_on='orig', right_on='ZONE', how='left', validate="one_to_one")
    
    # Save a debug file (optional)
    debug_out = pathlib.Path(OUTPUT_Dir, "accessed_jobs_by_origin_zone_(intermediate_file).csv")
    accessiblejobs_df.to_csv(debug_out, index=False)
    print(f"Debug file written to {debug_out}")
    
    # --------------------------- Compute population‐weighted accessible jobs ---------------------------
    accessiblejobs_df['TOTEMP_weighted']  = accessiblejobs_df['TOTEMP'] * accessiblejobs_df['TOTPOP']
    accessiblejobs_df['wtrn_45_weighted'] = accessiblejobs_df['wtrn_45'] * accessiblejobs_df['TOTPOP']

    for suffix in ["", "_epc1", "_epc2"]:
        if suffix == "_epc1":
            sub_df = accessiblejobs_df[accessiblejobs_df["taz_epc1"] == 1]
            totalpop_subset = taz_df.loc[taz_df["taz_epc1"] == 1, "TOTPOP"].sum()
        elif suffix == "_epc2":
            sub_df = accessiblejobs_df[accessiblejobs_df["taz_epc2"] == 1]
            totalpop_subset = taz_df.loc[taz_df["taz_epc2"] == 1, "TOTPOP"].sum()
        else:
            sub_df = accessiblejobs_df
            totalpop_subset = total_pop

        # metrics_dict[f"wtrn_45_acc_jobs{suffix}"] = sub_df['wtrn_45'].sum()
        metrics_dict[f"wtrn_45_acc_jobs_weighted_persons{suffix}"] = sub_df['wtrn_45_weighted'].sum()
        metrics_dict[f"total_jobs_weighted_persons{suffix}"] = total_emp * totalpop_subset
        metrics_dict[f"wtrn_45_acc_accessible_job_share{suffix}"] = (
            metrics_dict[f"wtrn_45_acc_jobs_weighted_persons{suffix}"] /
            (total_emp * totalpop_subset)
        )

    # --------------------------- Compute household‐weighted accessible jobs ---------------------------
    accessiblejobs_df['TOTEMP_weightedhh'] = accessiblejobs_df['TOTEMP'] * accessiblejobs_df['TOTHH']
    accessiblejobs_df['wtrn_45_weightedhh'] = accessiblejobs_df['wtrn_45'] * accessiblejobs_df['TOTHH']
    for suffix in ["_zerocar", "_carlight"]:
        if suffix == "":
            accessiblejobs_df[f"TOTEMP_weightedhh{suffix}"] = accessiblejobs_df['TOTEMP'] * accessiblejobs_df['TOTHH']
            accessiblejobs_df[f"wtrn_45_weightedhh{suffix}"] = accessiblejobs_df['wtrn_45'] * accessiblejobs_df['TOTHH']
        elif suffix == "_zerocar":
            accessiblejobs_df[f"TOTEMP_weightedhh{suffix}"] = accessiblejobs_df['TOTEMP'] * accessiblejobs_df['zero_car_hh']
            accessiblejobs_df[f"wtrn_45_weightedhh{suffix}"] = accessiblejobs_df['wtrn_45'] * accessiblejobs_df['zero_car_hh']
        elif suffix == "_carlight":
            accessiblejobs_df[f"TOTEMP_weightedhh{suffix}"] = accessiblejobs_df['TOTEMP'] * accessiblejobs_df['car_light_hh']
            accessiblejobs_df[f"wtrn_45_weightedhh{suffix}"] = accessiblejobs_df['wtrn_45'] * accessiblejobs_df['car_light_hh']
            
        metrics_dict[f"wtrn_45_acc_jobs_weighted_hh{suffix}"] = accessiblejobs_df[f"wtrn_45_weightedhh{suffix}"].sum()
        metrics_dict[f"total_jobs_weighted_hh{suffix}"] = accessiblejobs_df[f"TOTEMP_weightedhh{suffix}"].sum()
        metrics_dict[f"wtrn_45_acc_accessible_job_share_hh{suffix}"] = (
            metrics_dict[f"wtrn_45_acc_jobs_weighted_hh{suffix}"] /
            metrics_dict[f"total_jobs_weighted_hh{suffix}"]
        )
    print("Tallying accessible jobs completed.")

def compute_job_access_metrics():
    """
    Compute metrics for accessible jobs and return a DataFrame.
    (Also computes additional ratio metrics for EPC1, EPC2, and zero-car households)
    """
    metrics_dict = {}
    tally_access_to_jobs_v3(metrics_dict)
    
    # Convert the metrics dictionary to a DataFrame.
    out_frame = pd.DataFrame(list(metrics_dict.items()), columns=['variable_desc', 'value'])
    run_name = os.path.split(os.getcwd())[1]
    out_frame.insert(0, 'run_name', run_name)
    
    # Map certain metric names to group codes
    access_group = {
        'wtrn_45_acc_jobs_weighted_persons': '1A',
        'wtrn_45_acc_jobs_weighted_persons_epc1': '1Ba',
        'wtrn_45_acc_jobs_weighted_persons_epc2': '1Bb',
        'wtrn_45_acc_jobs_weighted_hh_zerocar': '1C',
        'wtrn_45_acc_jobs_weighted_hh_carlight': '1D'
    }

    out_frame['group_code'] = out_frame['variable_desc'].map(access_group)
    
    # Compute additional ratios
    base_val = out_frame.loc[out_frame['variable_desc'] == 'wtrn_45_acc_accessible_job_share', 'value']
    base_value = base_val.iloc[0] if not base_val.empty else None

    epc1_val = out_frame.loc[out_frame['variable_desc'] == 'wtrn_45_acc_accessible_job_share_epc1', 'value']
    epc1_ratio = (epc1_val.iloc[0] / base_value) if base_value and base_value != 0 and not epc1_val.empty else None

    epc2_val = out_frame.loc[out_frame['variable_desc'] == 'wtrn_45_acc_accessible_job_share_epc2', 'value']
    epc2_ratio = (epc2_val.iloc[0] / base_value) if base_value and base_value != 0 and not epc2_val.empty else None

    zerocar_val = out_frame.loc[out_frame['variable_desc'] == 'wtrn_45_acc_accessible_job_share_hh_zerocar', 'value']
    zerocar_ratio = (zerocar_val.iloc[0] / base_value) if base_value and base_value != 0 and not zerocar_val.empty else None

    access_group_2 = {
        'wtrn_45_acc_accessible_job_share_epc1': '1Ea',
        'wtrn_45_acc_accessible_job_share_epc2': '1Eb',
        'wtrn_45_acc_accessible_job_share_hh_zerocar': '1F'
    }
    new_rows = pd.DataFrame({
        'run_name': [run_name] * 9,
        'variable_desc': ['wtrn_45_acc_accessible_job_share_epc1', 'wtrn_45_acc_accessible_job_share', 'epc1_acc_jobs_to_all_jobs_ratio', 'wtrn_45_acc_accessible_job_share_epc2', 'wtrn_45_acc_accessible_job_share', 'epc2_acc_jobs_to_all_jobs_ratio', 'wtrn_45_acc_accessible_job_share_hh_zerocar', 'wtrn_45_acc_accessible_job_share','zerocar_acc_jobs_to_all_jobs_ratio'],
        'value': [epc1_val.iloc[0], base_value, epc1_ratio, epc2_val.iloc[0], base_value, epc2_ratio, zerocar_val.iloc[0], base_value,zerocar_ratio]
    })
    new_rows['group_code'] = new_rows['variable_desc'].map(access_group_2)
    out_frame = pd.concat([out_frame, new_rows], ignore_index=True)
    # Instead of writing to file here, we return the DataFrame.
    print("Accessed Jobs metrics computed.")
    return out_frame

# ---------------------------
# Part 2: Accessibility Benefits (Logsum) Metrics
# ---------------------------
class RunResults:
    CEM_THRESHOLD = 0.1
    CEM_SHALLOW   = 0.05

def read_accessibilities(filename, col_prefix, adjust=False):
    """
    Read an accessibility CSV (logsums), optionally adjust the values, then “stack” the wide DataFrame so that the income/auto‐sufficiency level (embedded in the column names) becomes a variable.
    """
    filepath = os.path.join("logsums", f"{filename}.csv")
    df = pd.read_csv(filepath, sep=",")
    if adjust:
        exclude = ['destChoiceAlt', 'taz', 'subzone']
        df.loc[:, ~df.columns.isin(exclude)] += 1
    df.drop(columns='destChoiceAlt', inplace=True)
    df.set_index(['taz', 'subzone'], inplace=True)
    df = pd.DataFrame(df.stack()).reset_index()
    # Extract labels from the stacked column name (e.g., "lowInc_0_autos")
    df['incQ_label'] = df['level_2'].str.split('_', n=1).str.get(0)
    df['autoSuff_label'] = df['level_2'].str.split('_', n=1).str.get(1).str.rsplit('_', n=1).str.get(0)
    df['hasAV'] = df['level_2'].apply(lambda x: 0 if "noAV" in x else 1)
    df.drop(columns='level_2', inplace=True)
    df.rename(columns={0: f'{col_prefix}_dclogsum', 'subzone': 'walk_subzone'}, inplace=True)
    return df

def read_accessibility_markets(col_prefix):
    """
    Read the AccessibilityMarkets CSV and rename key columns using the given prefix.
    """
    filepath = os.path.join("core_summaries", "AccessibilityMarkets.csv")
    df = pd.read_csv(filepath, sep=",")
    df.rename(columns={'num_persons': f'{col_prefix}_num_persons',
                       'num_workers': f'{col_prefix}_num_workers',
                       'num_workers_students': f'{col_prefix}_num_workers_students'}, inplace=True)
    return df

def calculateConsumerSurplus_v2():
    """
    Read base and scenario accessibility logsums and markets data, merge them, and compute daily accessibility benefits (in “logsum hours”) using the
    “rule of one‐half.”
    Returns a tuple (daily_results, mandatoryAccess, nonmandatoryAccess).
    """
    # Read base files (no adjustment)
    base_mandatory = read_accessibilities("mandatoryAccessibilities", "base", adjust=False)
    base_nonmandatory = read_accessibilities("nonMandatoryAccessibilities", "base", adjust=False)
    base_markets = read_accessibility_markets("base")

    # Read scenario files (with adjustment)
    scen_mandatory = read_accessibilities("mandatoryAccessibilities", "scen", adjust=True)
    scen_nonmandatory = read_accessibilities("nonMandatoryAccessibilities", "scen", adjust=True)
    scen_markets = read_accessibility_markets("scen")

    # --------------------------- Mandatory Accessibilities ---------------------------
    # Merge base and scenario for mandatory accessibilities
    mandatoryAccess = pd.merge(scen_mandatory, base_mandatory, how='left')
    mandatoryAccess['diff_dclogsum'] = mandatoryAccess['scen_dclogsum'] - mandatoryAccess['base_dclogsum']
    mandatoryAccess['logsum_diff_minutes'] = mandatoryAccess['diff_dclogsum'] / 0.0134 # convert utils to minutes (k_ivt = 0.0134 k_mc_ls = 1.0 in access calcs)

    # Cliff Effect Mitigation
    mand_ldm_max = mandatoryAccess['logsum_diff_minutes'].abs().max()
    if mand_ldm_max < 1e-5:
        mandatoryAccess['ldm_ratio'] = 1.0
        mandatoryAccess['ldm_mult']  = 1.0
    else:
        mandatoryAccess['ldm_ratio'] = mandatoryAccess['logsum_diff_minutes'].abs() / mand_ldm_max
        mandatoryAccess['ldm_mult'] = 1.0 / (1.0 + np.exp(-(mandatoryAccess['ldm_ratio'] - RunResults.CEM_THRESHOLD) / RunResults.CEM_SHALLOW))
    mandatoryAccess['ldm_cem'] = mandatoryAccess['logsum_diff_minutes'] * mandatoryAccess['ldm_mult']

    # --------------------------- Nonmandatory Accessibilities ---------------------------
    # Merge base and scenario for nonmandatory accessibilities
    nonmandatoryAccess = pd.merge(scen_nonmandatory, base_nonmandatory, how='left')
    nonmandatoryAccess['diff_dclogsum'] = nonmandatoryAccess['scen_dclogsum'] - nonmandatoryAccess['base_dclogsum']
    nonmandatoryAccess['logsum_diff_minutes'] = nonmandatoryAccess['diff_dclogsum'] / 0.0175

    # Cliff Effect Mitigation
    nonmm_ldm_max = nonmandatoryAccess['logsum_diff_minutes'].abs().max()
    nonmandatoryAccess['ldm_ratio'] = nonmandatoryAccess['logsum_diff_minutes'].abs() / nonmm_ldm_max
    nonmandatoryAccess['ldm_mult'] = 1.0 / (1.0 + np.exp(-(nonmandatoryAccess['ldm_ratio'] - RunResults.CEM_THRESHOLD) / RunResults.CEM_SHALLOW))
    nonmandatoryAccess['ldm_cem'] = nonmandatoryAccess['logsum_diff_minutes'] * nonmandatoryAccess['ldm_mult']

    # Merge markets data 
    scen_markets = pd.merge(scen_markets, base_markets, how='left')
    mandatoryAccess = pd.merge(mandatoryAccess, scen_markets, how='left').fillna(0)
    nonmandatoryAccess = pd.merge(nonmandatoryAccess, scen_markets, how='left').fillna(0)

    daily_results = OrderedDict()

    # --------------------------- Compute benefits for Mandatory Tours (Workers & Students) ---------------------------
    cat1 = 'Accessibility Benefits (household-based) (with CEM)'
    cat2 = 'Logsum Hours - Mandatory Tours - Workers & Students'
    mandatoryAccess['CS diff work/school'] = (
        0.5 * mandatoryAccess['base_num_workers_students'] +
        0.5 * mandatoryAccess['scen_num_workers_students']
    ) * mandatoryAccess['ldm_cem']
    for inclabel in ['lowInc', 'medInc', 'highInc', 'veryHighInc']:
        daily_results[(cat1, cat2, inclabel)] = mandatoryAccess.loc[
            mandatoryAccess['incQ_label'] == inclabel, 'CS diff work/school'
        ].sum() / 60.0

    # --------------------------- Compute benefits for NonMandatory Tours (All people) ---------------------------
    cat2 = 'Logsum Hours - NonMandatory Tours - All people'
    nonmandatoryAccess['CS diff all'] = (
        0.5 * nonmandatoryAccess['base_num_persons'] +
        0.5 * nonmandatoryAccess['scen_num_persons']
    ) * nonmandatoryAccess['ldm_cem']
    for inclabel in ['lowInc', 'medInc', 'highInc', 'veryHighInc']:
        daily_results[(cat1, cat2, inclabel)] = nonmandatoryAccess.loc[
            nonmandatoryAccess['incQ_label'] == inclabel, 'CS diff all'
        ].sum() / 60.0

    print("Daily accessibility results computed.")
    return mandatoryAccess, nonmandatoryAccess

def compute_access_benefits_metrics():
    """
    Compute final access metrics from the daily accessibility processing, merge with EPC data, and return a DataFrame.
    """
    # Process the accessibility data
    mandatoryAccess, nonmandatoryAccess = calculateConsumerSurplus_v2()
    
    # Read EPC data (used for an additional split)
    epc1_df  = read_epc_data().rename(columns={"taz_epc": "taz_epc1"})
    epc2_df  = read_epc_data().rename(columns={"taz_epc": "taz_epc2"})
    mandatoryAccess_epc1 = pd.merge(mandatoryAccess, epc1_df, left_on="taz", right_on="TAZ1454")
    nonmandatoryAccess_epc1 = pd.merge(nonmandatoryAccess, epc1_df, left_on="taz", right_on="TAZ1454")
    mandatoryAccess_epc2 = pd.merge(mandatoryAccess, epc2_df, left_on="taz", right_on="TAZ1454")
    nonmandatoryAccess_epc2 = pd.merge(nonmandatoryAccess, epc2_df, left_on="taz", right_on="TAZ1454")

    # Export debug files (optional)
    mandatoryAccess_epc1.to_csv(pathlib.Path(OUTPUT_Dir, "mandatoryAccess_epc1_(intermediate_file).csv"), index=False)
    nonmandatoryAccess_epc1.to_csv(pathlib.Path(OUTPUT_Dir, "nonmandatoryAccess_epc1_(intermediate_file).csv"), index=False)
    mandatoryAccess_epc2.to_csv(pathlib.Path(OUTPUT_Dir, "mandatoryAccess_epc2_(intermediate_file).csv"), index=False)
    nonmandatoryAccess_epc2.to_csv(pathlib.Path(OUTPUT_Dir, "nonmandatoryAccess_epc2_(intermediate_file).csv"), index=False)
    
    # Compute metric values
    mandatoryAccess_value = mandatoryAccess['CS diff work/school'].sum()
    nonmandatoryAccess_value = nonmandatoryAccess['CS diff all'].sum()
    totalAccess_value = mandatoryAccess_value + nonmandatoryAccess_value

    # Compute EPC1 metrics
    mandatoryAccess_epc1_value = mandatoryAccess_epc1.loc[mandatoryAccess_epc1['taz_epc1'] == 1, 'CS diff work/school'].sum()
    nonmandatoryAccess_epc1_value = nonmandatoryAccess_epc1.loc[nonmandatoryAccess_epc1['taz_epc1'] == 1, 'CS diff all'].sum()
    num_workers_students_epc1 = 0.5 * mandatoryAccess.loc[mandatoryAccess_epc1['taz_epc1'] == 1, 'base_num_workers_students'].sum() + 0.5 * mandatoryAccess.loc[mandatoryAccess_epc1['taz_epc1'] == 1, 'scen_num_workers_students'].sum()
    num_persons_epc1 = 0.5 * nonmandatoryAccess.loc[nonmandatoryAccess_epc1['taz_epc1'] == 1, 'base_num_persons'].sum() + 0.5 * nonmandatoryAccess.loc[nonmandatoryAccess_epc1['taz_epc1'] == 1, 'scen_num_persons'].sum()
    per_capita_access_benefits_epc1 = (mandatoryAccess_epc1_value +  nonmandatoryAccess_epc1_value)/ (num_workers_students_epc1 + num_persons_epc1)

    # Compute EPC2 metrics
    mandatoryAccess_epc2_value = mandatoryAccess_epc2.loc[mandatoryAccess_epc2['taz_epc2'] == 1, 'CS diff work/school'].sum()
    nonmandatoryAccess_epc2_value = nonmandatoryAccess_epc2.loc[nonmandatoryAccess_epc2['taz_epc2'] == 1, 'CS diff all'].sum()
    num_workers_students_epc2 = 0.5 * mandatoryAccess.loc[mandatoryAccess_epc2['taz_epc2'] == 1, 'base_num_workers_students'].sum() + 0.5 * mandatoryAccess.loc[mandatoryAccess_epc2['taz_epc2'] == 1, 'scen_num_workers_students'].sum()
    num_persons_epc2 = 0.5 * nonmandatoryAccess.loc[nonmandatoryAccess_epc2['taz_epc2'] == 1, 'base_num_persons'].sum() + 0.5 * nonmandatoryAccess.loc[nonmandatoryAccess_epc2['taz_epc2'] == 1, 'scen_num_persons'].sum()
    per_capita_access_benefits_epc2 = (mandatoryAccess_epc2_value +  nonmandatoryAccess_epc2_value)/ (num_workers_students_epc2 + num_persons_epc2)

    # Compute total metrics
    num_workers_students_base = mandatoryAccess['base_num_workers_students'].sum()
    num_persons_base = nonmandatoryAccess['base_num_persons'].sum()
    num_workers_students_scen = mandatoryAccess['scen_num_workers_students'].sum()
    num_persons_scen = nonmandatoryAccess['scen_num_persons'].sum()
    per_capita_access_benefits = totalAccess_value / (0.5 * (num_workers_students_base + num_persons_base + num_workers_students_scen + num_persons_scen))
    per_capita_access_benefits_epc1_to_total_ratio = per_capita_access_benefits_epc1 / per_capita_access_benefits
    per_capita_access_benefits_epc2_to_total_ratio = per_capita_access_benefits_epc2 / per_capita_access_benefits
    
    metrics_list = [
        # 1G
        ('mandatory_access_benefits', mandatoryAccess_value),
        ('nonmandatory_access_benefits', nonmandatoryAccess_value),
        ('total_access_benefits', totalAccess_value),

        # 1Ha
        ('mandatory_access_epc1_benefits', mandatoryAccess_epc1_value),
        ('nonmandatory_access_epc1_benefits', nonmandatoryAccess_epc1_value),
        ('num_workers_students_epc1', num_workers_students_epc1),
        ('num_persons_epc1', num_persons_epc1),
        ('per_capita_access_benefits_epc1', per_capita_access_benefits_epc1),
        ('mandatory_access_benefits', mandatoryAccess_value),
        ('nonmandatory_access_benefits', nonmandatoryAccess_value),
        ('num_workers_students_base', num_workers_students_base), 
        ('num_persons_base', num_persons_base),
        ('num_workers_students_scen', num_workers_students_scen),
        ('num_persons_scen', num_persons_scen),
        ('per_capita_access_benefits', per_capita_access_benefits),
        ('per_capita_access_benefits_epc1_to_total_ratio', per_capita_access_benefits_epc1_to_total_ratio),
        
        # 1Hb
        ('mandatory_access_epc2_benefits', mandatoryAccess_epc2_value),   
        ('nonmandatory_access_epc2_benefits', nonmandatoryAccess_epc2_value),
        ('num_workers_students_epc2', num_workers_students_epc2),
        ('num_persons_epc2', num_persons_epc2),
        ('per_capita_access_benefits_epc2', per_capita_access_benefits_epc2),
        ('mandatory_access_benefits', mandatoryAccess_value),
        ('nonmandatory_access_benefits', nonmandatoryAccess_value),
        ('num_workers_students_base', num_workers_students_base),
        ('num_persons_base', num_persons_base),
        ('num_workers_students_scen', num_workers_students_scen),
        ('num_persons_scen', num_persons_scen),
        ('per_capita_access_benefits', per_capita_access_benefits),
        ('per_capita_access_benefits_epc2_to_total_ratio', per_capita_access_benefits_epc2_to_total_ratio)
    ]

    
    out_frame = pd.DataFrame(metrics_list, columns=['variable_desc', 'value'])
    run_name = os.path.split(os.getcwd())[1]
    out_frame.insert(0, 'run_name', run_name)
    
    # Map metric names to group codes.
    group_mapping = {
        'mandatory_access_benefits': '1G',
        'mandatory_access_epc1_benefits': '1Ha',
        'mandatory_access_epc2_benefits': '1Hb'
    }
    out_frame['group_code'] = out_frame['variable_desc'].map(group_mapping)

    # Then, for rows where 'variable_desc' is 'mandatory_access_benefits' and that row is a duplicate (i.e. not the first occurrence), remove the group code
    mask = (out_frame['variable_desc'] == 'mandatory_access_benefits') & (out_frame.duplicated('variable_desc', keep='first'))
    out_frame.loc[mask, 'group_code'] = None
    
    print("Access metrics computed.")
    return out_frame

# ---------------------------
# Main routine
# ---------------------------
def main():
    # Process zero-vehicle and car-light households (needed for the job access metrics)
    process_households()
    
    # Compute the job access metrics (accessible jobs)
    job_access_df = compute_job_access_metrics()
    
    # Compute the access benefits (logsum) metrics
    access_benefit_df = compute_access_benefits_metrics()
    
    # Combine the two DataFrames into one
    combined_df = pd.concat([job_access_df, access_benefit_df], ignore_index=True)
    
    # Write the combined metrics to a single CSV file
    output_filename = pathlib.Path(OUTPUT_Dir, "NPA_metrics_Goal_1.csv")
    combined_df.to_csv(output_filename, header=False, float_format='%.5f', index=False)
    print("Combined metrics written to", output_filename)
    
    # Print a summary of the computed metrics
    print("\nCombined Metrics:")
    print(combined_df)

if __name__ == '__main__':
    main()
