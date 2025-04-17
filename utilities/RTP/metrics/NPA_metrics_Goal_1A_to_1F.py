#!/usr/bin/env python3
"""
This script is used for computing accessible jobs. 
The final output is a single CSV file named "NPA_Metrics_Goal_1A_to_1F.csv".
Function tally_access_to_jobs_v3() is modified based on scenarioMetrics.py function tally_access_to_jobs_v2.

The script reads the following input files:
- main/householdData_*.csv (household file), * is the highest numbered file in the main folder
- ../supporting_data/TAZ1454_tract2010_crosswalk.csv (crosswalk file)
- ../supporting_data/COCs_ACS2018_tbl_TEMP.csv (EPC_18 data)
- INPUT/metrics/zero_car_hh.csv (zero-vehicle households)
- INPUT/metrics/car_light_hh.csv (car-light households)
- INPUT/metrics/taz1454_epcPBA50plus_2024_02_23.csv (EPC_22 data)
- INPUT/metrics/taz1454_epcPBA50plus_18.csv (EPC_18 data)
- database/TimeSkimsDatabaseAM.csv (time-skim data)
- landuse/tazData.csv (TAZ employment/socioeconomic data)

The script writes the following output files:
- INPUT/metrics/zero_car_hh.csv (zero-vehicle households), also used for input
- INPUT/metrics/car_light_hh.csv (car-light households), also used for input
- INPUT/metrics/taz1454_epcPBA50plus_18.csv (EPC_18 data), also used for input
- {OUTPUT_Dir}/accessed_jobs_by_origin_zone.csv (debug file)
- {OUTPUT_Dir}/NPA_Metrics_Goal_1A_to_1F.csv (combined metrics)
- {OUTPUT_Dir}/NPA_Metrics_Goal_1A_to_1F_reordered.csv (reordered metrics)
- {OUTPUT_Dir_Tableau}/NPA_Metrics_Goal_1A_to_1F_{WORK_DIR.name}.xlsx (excel file for Tableau)
"""

import os
import pathlib
from pathlib import Path
import numpy as np
import pandas as pd

# ---------------------------
# Set working directory & options
# ---------------------------
WORK_DIR = pathlib.Path("../2050_TM160_DBP_Plan_08b")
os.chdir(WORK_DIR)
print("Current working directory:", os.getcwd())

OUTPUT_Dir = Path(f"../data_output/{WORK_DIR.name}/NPA_Metrics_Goal_1")
OUTPUT_Dir.mkdir(parents=True, exist_ok=True)

os.makedirs(f"../data_output/Tableau_NPA_Metrics_Goal_1", exist_ok=True)
OUTPUT_Dir_Tableau = pathlib.Path(f"../data_output/Tableau_NPA_Metrics_Goal_1")

pd.set_option('display.width', 500)
pd.set_option('display.precision', 10)


def process_households():
    """
    Process the household file to count "zero‐car" and "car‐light" households by TAZ and write the results to CSV files (which are used later).
    """
    # Find the highest numbered householdData file in the main folder
    household_files = list(pathlib.Path("main").glob("householdData_*.csv"))

    # Extract numbers from filenames and find the highest
    file_numbers = [int(f.stem.split('_')[-1]) for f in household_files if f.stem.split('_')[-1].isdigit()]
    input_file = pathlib.Path(f"main/householdData_{max(file_numbers)}.csv")
    print(f"Reading household file: {input_file}")
    df = pd.read_csv(input_file, usecols=['hh_id', 'taz', 'autos', 'workers'])
    
    zero_car = df[df['autos'] == 0]
    car_light = df[df['autos'] < df['workers']]
    
    zero_car_hh_df = zero_car.groupby("taz")["hh_id"].count().reset_index(name="zero_car_hh")
    car_light_hh_df = car_light.groupby("taz")["hh_id"].count().reset_index(name="car_light_hh")
    
    # These files are read later in the accessible jobs function.
    zero_car_hh_df.to_csv(pathlib.Path("INPUT/metrics/zero_car_hh.csv"), index=False)
    car_light_hh_df.to_csv(pathlib.Path("INPUT/metrics/car_light_hh.csv"), index=False)
    print("Household processing completed.")

def prepare_epc18_data():
    """
    Prepare EPC 2018 data by reading the crosswalk and EPC files,
    merging them, and saving the merged result to the metrics folder.
    """
    epc18_merged = (
        pd.read_csv(
            pathlib.Path("..").joinpath("supporting_data/TAZ1454_tract2010_crosswalk.csv"),
            usecols=['TAZ1454', 'GEOID10_tract2010']
        )
        .merge(
            pd.read_csv(
                pathlib.Path("..").joinpath("supporting_data/COCs_ACS2018_tbl_TEMP.csv"),
                usecols=['geoid', 'coc_flag_pba2050']
            ),
            left_on="GEOID10_tract2010",
            right_on="geoid",
            how="left"
        )
        .rename(columns={"coc_flag_pba2050": "taz_epc"})
    )
    output_path = pathlib.Path("INPUT/metrics/taz1454_epcPBA50plus_18.csv")
    epc18_merged.to_csv(output_path, index=False)
    print(f"EPC 2018 data prepared and saved to {output_path}")

def read_epc_data(epc_18=False):
    """
    Read the Equity Priority Communities (EPC) file and return the DataFrame.
    Args:
        epc_18: If True, read the 2018 EPC file, otherwise read the 2022 file
    """
    if epc_18:
        epc_file = pathlib.Path("INPUT/metrics/taz1454_epcPBA50plus_18.csv")
    else:
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
    # metrics_dict.update({"total_jobs": total_emp, "total_pop": total_pop, "total_hh": total_hh})

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
    epc_22_df = read_epc_data(epc_18=False)
    epc_18_df = read_epc_data(epc_18=True)
    taz_df = taz_df.merge(epc_22_df, left_on="ZONE", right_on="TAZ1454", validate="one_to_one").rename(columns={"taz_epc": "taz_epc_22"})
    taz_df = taz_df.merge(epc_18_df, left_on="ZONE", right_on="TAZ1454", validate="one_to_one").rename(columns={"taz_epc": "taz_epc_18"})
    print(f"Found {taz_df['taz_epc_22'].sum()} TAZs in epc_22s")
    print(f"Found {taz_df['taz_epc_18'].sum()} TAZs in epc_18s")

    # Read Zero-Vehicle & Car-Light Households
    for metric_file, col_name in [("INPUT/metrics/zero_car_hh.csv", "zero_car_hh"),
                                  ("INPUT/metrics/car_light_hh.csv", "car_light_hh")]:
        print(f"Reading {metric_file}")
        temp_df = pd.read_csv(pathlib.Path(metric_file))
        taz_df = taz_df.merge(temp_df, left_on="ZONE", right_on="taz", how="left")
        taz_df[col_name] = taz_df[col_name].fillna(0)

    # Merge concerned socioeconomic info into aggregated accessible jobs (match origin TAZ)
    accessiblejobs_df = accessiblejobs_df.merge(taz_df[['ZONE', 'TOTPOP', 'TOTHH', 'taz_epc_22', 'taz_epc_18', 'zero_car_hh', 'car_light_hh']],
                          left_on='orig', right_on='ZONE', how='left', validate="one_to_one")
    
    # Save a debug file (optional)
    debug_out = pathlib.Path(OUTPUT_Dir, "accessed_jobs_by_origin_zone_(intermediate_file).csv")
    accessiblejobs_df.to_csv(debug_out, index=False)
    print(f"Debug file written to {debug_out}")
    
    # --------------------------- Compute population‐weighted accessible jobs ---------------------------
    accessiblejobs_df['TOTEMP_weighted']  = accessiblejobs_df['TOTEMP'] * accessiblejobs_df['TOTPOP']
    accessiblejobs_df['wtrn_45_weighted'] = accessiblejobs_df['wtrn_45'] * accessiblejobs_df['TOTPOP']

    for suffix in ["", "_epc_22", "_epc_18"]:
        if suffix == "_epc_22":
            sub_df = accessiblejobs_df[accessiblejobs_df["taz_epc_22"] == 1]
            totalpop_subset = taz_df.loc[taz_df["taz_epc_22"] == 1, "TOTPOP"].sum()
        elif suffix == "_epc_18":
            sub_df = accessiblejobs_df[accessiblejobs_df["taz_epc_18"] == 1]
            totalpop_subset = taz_df.loc[taz_df["taz_epc_18"] == 1, "TOTPOP"].sum()
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
    (Also computes additional ratio metrics for epc_22, epc_18, and zero-car households)
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
        'total_jobs_weighted_persons': '1A',
        'wtrn_45_acc_accessible_job_share': '1A',

        'wtrn_45_acc_jobs_weighted_persons_epc_22': '1Ba',
        'total_jobs_weighted_persons_epc_22': '1Ba',
        'wtrn_45_acc_accessible_job_share_epc_22': '1Ba',

        'wtrn_45_acc_jobs_weighted_persons_epc_18': '1Bb',
        'total_jobs_weighted_persons_epc_18': '1Bb',
        'wtrn_45_acc_accessible_job_share_epc_18': '1Bb',

        'wtrn_45_acc_jobs_weighted_hh_zerocar': '1C',
        'total_jobs_weighted_hh_zerocar': '1C',
        'wtrn_45_acc_accessible_job_share_hh_zerocar': '1C',

        'wtrn_45_acc_jobs_weighted_hh_carlight': '1D',
        'total_jobs_weighted_hh_carlight': '1D',
        'wtrn_45_acc_accessible_job_share_hh_carlight': '1D'
    }


    out_frame['group_code'] = out_frame['variable_desc'].map(access_group)
    
    # Compute additional ratios
    base_val = out_frame.loc[out_frame['variable_desc'] == 'wtrn_45_acc_accessible_job_share', 'value']
    base_value = base_val.iloc[0] if not base_val.empty else None

    epc_22_val = out_frame.loc[out_frame['variable_desc'] == 'wtrn_45_acc_accessible_job_share_epc_22', 'value']
    epc_22_ratio = (epc_22_val.iloc[0] / base_value) if base_value and base_value != 0 and not epc_22_val.empty else None

    epc_18_val = out_frame.loc[out_frame['variable_desc'] == 'wtrn_45_acc_accessible_job_share_epc_18', 'value']
    epc_18_ratio = (epc_18_val.iloc[0] / base_value) if base_value and base_value != 0 and not epc_18_val.empty else None

    zerocar_val = out_frame.loc[out_frame['variable_desc'] == 'wtrn_45_acc_accessible_job_share_hh_zerocar', 'value']
    zerocar_ratio = (zerocar_val.iloc[0] / base_value) if base_value and base_value != 0 and not zerocar_val.empty else None


    # Create separate rows for each metric while maintaining their relationships
    new_rows = []
    metric_groups = [
        # epc_22 group (1Ea)
        {
            'metrics': [
                ('wtrn_45_acc_accessible_job_share_epc_22', epc_22_val.iloc[0]),
                ('wtrn_45_acc_accessible_job_share_base', base_value),
                ('epc_22_acc_jobs_to_all_jobs_ratio', epc_22_ratio)
            ],

            'group_code': '1Ea'
        },
        # epc_18 group (1Eb) 
        {
            'metrics': [
                ('wtrn_45_acc_accessible_job_share_epc_18', epc_18_val.iloc[0]),
                ('wtrn_45_acc_accessible_job_share_base', base_value),
                ('epc_18_acc_jobs_to_all_jobs_ratio', epc_18_ratio)
            ],
            'group_code': '1Eb'
        },

        # Zero-car group (1F)
        {
            'metrics': [
                ('wtrn_45_acc_accessible_job_share_hh_zerocar', zerocar_val.iloc[0]),
                ('wtrn_45_acc_accessible_job_share_base', base_value),
                ('zerocar_acc_jobs_to_all_jobs_ratio', zerocar_ratio)
            ],

            'group_code': '1F'
        }
    ]
    for group in metric_groups:
        for variable_desc, value in group['metrics']:
            new_rows.append({
                'run_name': run_name,
                'variable_desc': variable_desc,
                'value': value,
                'group_code': group['group_code']
            })

    new_rows_df = pd.DataFrame(new_rows)
    out_frame = pd.concat([out_frame, new_rows_df], ignore_index=True)
    print("Accessed Jobs metrics computed.")
    return out_frame


# ---------------------------
# Main routine
# ---------------------------

if __name__ == '__main__':
    # First prepare the EPC 2018 data so that later functions can read it
    prepare_epc18_data()
    
    # Process zero-vehicle and car-light households (needed for the job access metrics)
    process_households()
    
    # Compute the job access metrics (accessible jobs)
    job_access_df = compute_job_access_metrics()
    
    # Rename the original 'value' column and group_code column
    job_access_df = job_access_df.rename(columns={
        'value': 'current_value',
        'group_code': 'measure_names'
    })
    
    # Reorder the columns to ensure desired order
    column_order = [
        'run_name',
        'variable_desc',
        'current_value',
        'measure_names'
    ]
    job_access_df = job_access_df[column_order]
    
    # Drop run_name column before writing to CSV
    job_access_df = job_access_df.drop('run_name', axis=1)
    
    # Write the metrics to a CSV file
    output_filename = pathlib.Path(OUTPUT_Dir, "NPA_Metrics_Goal_1A_to_1F.csv")
    job_access_df.to_csv(output_filename, header=True, float_format='%.5f', index=False)
    print("Metrics written to", output_filename)
    
    # Print a summary of the computed metrics
    print("\nMetrics:")
    print(job_access_df)

# --------------------------
# Reorder the output
# --------------------------

def reorder_metrics(row):
    var_desc = row['variable_desc']
    
    for pattern, mapped in (
        ('wtrn_45_acc_jobs_weighted', 'wtrn_45_acc_jobs_weighted_persons/hhs'),
        ('total_jobs_weighted', 'total_jobs_weighted_persons/hhs'),
        ('wtrn_45_acc_accessible_job_share', 'wtrn_45_acc_accessible_job_share'),
        ('acc_jobs_to_all_jobs_ratio', 'acc_jobs_to_all_jobs_ratio')
    ):
        if pattern in var_desc:
            metric_name = mapped
            break
    else:
        metric_name = None

    epc_population = 'epc_22' if 'epc_22' in var_desc else ('epc_18' if 'epc_18' in var_desc else 'all')
    auto_ownership = 'zerocar' if 'zerocar' in var_desc else ('carlight' if 'carlight' in var_desc else 'all')
    
    return pd.Series({
        'metric_name': metric_name,
        'epc_population': epc_population,
        'auto_ownership': auto_ownership
    })

job_access_df[['metric_name', 'epc_population', 'auto_ownership']] = job_access_df.apply(reorder_metrics, axis=1)
# Pivot the DataFrame: index by orig_city and dest_city and use the metric_name as column headers.
job_access_df_new = job_access_df.pivot(index=['measure_names', 'epc_population', 'auto_ownership'], columns='metric_name', values='current_value')

job_access_df_new = job_access_df_new.round({
    'wtrn_45_acc_accessible_job_share': 3,
    'acc_jobs_to_all_jobs_ratio': 2
})

# Reorder the pivoted columns so that 'wtrn_45_acc_jobs_weighted_persons/hhs' is the first column and 'acc_jobs_to_all_jobs_ratio' is the last.
cols = list(job_access_df_new.columns)
if 'wtrn_45_acc_jobs_weighted_persons/hhs' in cols:
    cols.remove('wtrn_45_acc_jobs_weighted_persons/hhs')
    cols.insert(0, 'wtrn_45_acc_jobs_weighted_persons/hhs')
if 'acc_jobs_to_all_jobs_ratio' in cols:
    cols.remove('acc_jobs_to_all_jobs_ratio')
    cols.append('acc_jobs_to_all_jobs_ratio')
job_access_df_new = job_access_df_new[cols]

# Remove the rows where the measure_names is "1Ea", "1Eb", or "1F" and the epc_population and auto_ownership are "all".
target_rows = job_access_df_new.index.get_level_values("measure_names").isin(["1Ea", "1Eb", "1F"])

# Remove all values in the "wtrn_45_acc_accessible_job_share" column for these rows
job_access_df_new.loc[target_rows, "wtrn_45_acc_accessible_job_share"] = np.nan

# Define the condition to drop rows where, in addition, both epc_population and auto_ownership are "all"
condition = (
    target_rows &
    (job_access_df_new.index.get_level_values("epc_population") == "all") &
    (job_access_df_new.index.get_level_values("auto_ownership") == "all")
)
job_access_df_new = job_access_df_new[~condition]

job_access_df_new.to_csv(pathlib.Path(OUTPUT_Dir, "NPA_Metrics_Goal_1A_to_1F_reordered.csv"), index=True)
job_access_df_new.to_excel(pathlib.Path(OUTPUT_Dir_Tableau, f"NPA_metrics_Goal_1A_to_1F_{WORK_DIR.name}.xlsx"), index=True)
