#!/usr/bin/env python3
"""
This script is used for computing accessibility benefits (logsum). 
The function calculateConsumerSurplus() is adopted unchanged from mapAccessibilityDiffs.py.
The final output is a single CSV file named "NPA_metrics_Goal_1G_1H.csv".

The script reads the following input files:
- ../supporting_data/TAZ1454_tract2010_crosswalk.csv (crosswalk file)
- ../supporting_data/COCs_ACS2018_tbl_TEMP.csv (EPC_18 data)
- {SCEN_DIR}/INPUT/metrics/taz1454_epcPBA50plus_2024_02_23.csv (EPC_22 data)
- {SCEN_DIR}/INPUT/metrics/taz1454_epcPBA50plus_18.csv (EPC_18 data)
- {BASE_DIR}&{SCEN_DIR}/logsums/mandatoryAccessibilities.csv (mandatory accessibilities)
- {BASE_DIR}&{SCEN_DIR}/logsums/nonMandatoryAccessibilities.csv (nonmandatory accessibilities)
- {BASE_DIR}&{SCEN_DIR}/core_summaries/AccessibilityMarkets.csv (accessibility markets)

The script writes the following output files:
- {SCEN_DIR}/INPUT/metrics/taz1454_epcPBA50plus_18.csv (EPC_18 data), also used for input
- {OUTPUT_Dir}/mandatoryAccess_epc_22.csv (mandatory accessibilities for epc_22) (debug file)
- {OUTPUT_Dir}/nonmandatoryAccess_epc_22.csv (nonmandatory accessibilities for epc_22) (debug file)
- {OUTPUT_Dir}/mandatoryAccess_epc_18.csv (mandatory accessibilities for epc_18) (debug file)
- {OUTPUT_Dir}/nonmandatoryAccess_epc_18.csv (nonmandatory accessibilities for epc_18) (debug file)
- {OUTPUT_Dir}/NPA_Metrics_Goal_1G_1H.csv (combined metrics)
- {OUTPUT_Dir}/NPA_Metrics_Goal_1G_1H_reordered.csv (combined metrics reordered)
- {OUTPUT_Dir_Tableau}/NPA_Metrics_Goal_1G_1H_{WORK_DIR.name}.xlsx (excel file for Tableau)
"""

import os
import pathlib
from pathlib import Path
import numpy as np
import pandas as pd
from collections import OrderedDict
import re  

# ---------------------------
# Set working directory & options
# ---------------------------
BASE_DIR = pathlib.Path("../2035_TM161_FBP_NoProject_06")  # Baseline
SCEN_DIR = pathlib.Path("../2035_TM161_FBP_Plan_06")      # Another scenario
print("Base directory:", BASE_DIR)
print("Scenario directory:", SCEN_DIR)

OUTPUT_Dir = Path(f"../data_output/base_{BASE_DIR.name}_vs_scen_{SCEN_DIR.name}/NPA_Metrics_Goal_1")
OUTPUT_Dir.mkdir(parents=True, exist_ok=True)

os.makedirs(f"../data_output/Tableau_NPA_Metrics_Goal_1", exist_ok=True)
OUTPUT_Dir_Tableau = pathlib.Path(f"../data_output/Tableau_NPA_Metrics_Goal_1")

pd.set_option('display.width', 500)
pd.set_option('display.precision', 10)

def prepare_epc18_data():
    """
    Prepare EPC 2018 data by reading the crosswalk and EPC files,
    merging them, and saving the merged result to the metrics folder.
    """
    epc18_merged = (
        pd.read_csv(
            pathlib.Path(SCEN_DIR).parent.joinpath("supporting_data/TAZ1454_tract2010_crosswalk.csv"),
            usecols=['TAZ1454', 'GEOID10_tract2010']
        )
        .merge(
            pd.read_csv(
                pathlib.Path(SCEN_DIR).parent.joinpath("supporting_data/COCs_ACS2018_tbl_TEMP.csv"),
                usecols=['geoid', 'coc_flag_pba2050']
            ),
            left_on="GEOID10_tract2010",
            right_on="geoid",
            how="left"
        )
        .rename(columns={"coc_flag_pba2050": "taz_epc"})
    )
    output_path = pathlib.Path(SCEN_DIR, "INPUT/metrics/taz1454_epcPBA50plus_18.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    epc18_merged.to_csv(output_path, index=False)
    print(f"EPC 2018 data prepared and saved to {output_path}")

def read_epc_data(epc_18=False):
    """
    Read the Equity Priority Communities (EPC) file and return the DataFrame.
    Args:
        epc_18: If True, read the 2018 EPC file, otherwise read the 2022 file
    """
    if epc_18:
        epc_file = pathlib.Path(SCEN_DIR, "INPUT/metrics/taz1454_epcPBA50plus_18.csv")
    else:
        epc_file = pathlib.Path(SCEN_DIR, "INPUT/metrics/taz1454_epcPBA50plus_2024_02_23.csv")
    print(f"Reading EPC data from: {epc_file}")
    epc_df = pd.read_csv(epc_file)
    return epc_df

class RunResults:
    CEM_THRESHOLD = 0.1
    CEM_SHALLOW   = 0.05
    
    @staticmethod
    def parseNumList(numlist_str):
        """
        Parses a number list of the format 1,4,6,10-14,23 into a list of numbers.

        Used for Zero Logsum TAZs parsing
        """
        if numlist_str in ["","nan"]: return []

        # Parse the taz list.
        taz_list_strs = numlist_str.split(",")
        # these should be either 123 or 1-123
        taz_list = []
        for taz_list_str in taz_list_strs:
            taz_list_regex = re.compile(r"[ ]*(\d+)(-(\d+))?")
            match_obj = re.match(taz_list_regex, taz_list_str)
            if match_obj.group(3) == None:
                taz_list.append(int(match_obj.group(1)))
            else:
                taz = int(match_obj.group(1))
                while taz <= int(match_obj.group(3)):
                    taz_list.append(taz)
                    taz += 1
        return taz_list
        
    @staticmethod
    def calculateConsumerSurplus(config, daily_results,
                             mandatoryAccessibilities, base_mandatoryAccessibilities,
                             nonmandatoryAccessibilities, base_nonmandatoryAccessibilities,
                             accessibilityMarkets, base_accessibilityMarkets,
                             debug_dir):
        """
        Static method for calculating consumer surplus.
        Done as a static method so it can be used by this script as well as by other scripts (e.g. mapAccessibilitydiffs.py)

        config is used for 'Zero Logsum TAZs' -- and if it's configured, 'Project Run Dir'

        If debug_dir is specified, this also writes a debug file, consumer_surplus.csv, to debug_dir
        And copies the tableau workbook, consumer_surplus_RUNID.twb to debug_dir, where RUNID = config['Foldername - Future'].twb
        Specify include_output_dir=False to drop OUTPUT from the directory


        Returns:
            - mandatoryAccessibilities    with new columns: diff_dclogsum, logsum_diff_minutes, ldm_ratio, ldm_mult, ldm_cem
            - nonMandatoryAccessibilities with new columns: diff_dclogsum, logsum_diff_minutes, ldm_ratio, ldm_mult, ldm_cem
            - mandatoryAccess
            - nonmandatoryAccess
        """
        # print("mandatoryAccessibilities length {}, head():\n{}".format(len(mandatoryAccessibilities), mandatoryAccessibilities.head()))
        # print("base_mandatoryAccessibilities length {}, head():\n{}".format(len(base_mandatoryAccessibilities), base_mandatoryAccessibilities.head()))
        # print("nonmandatoryAccessibilities length {}, head():\n{}".format(len(nonmandatoryAccessibilities), nonmandatoryAccessibilities.head()))
        # print("base_nonmandatoryAccessibilities length {}, head():\n{}".format(len(base_nonmandatoryAccessibilities), base_nonmandatoryAccessibilities.head()))
        # print("accessibilityMarkets length {}, head():\n{}".format(len(accessibilityMarkets), accessibilityMarkets.head()))
        # print("base_accessibilityMarkets length {}, head():\n{}".format(len(base_accessibilityMarkets), base_accessibilityMarkets.head()))

        zero_neg_taz_list = []
        zero_taz_list     = []
        if ("Zero Logsum TAZs" in config) or ("Zero Negative Logsum TAZs" in config):

            if "Zero Negative Logsum TAZs" in config:
                zero_neg_taz_list = RunResults.parseNumList(str(config["Zero Negative Logsum TAZs"]))
                print("Zeroing out negative diffs for tazs {}".format(zero_neg_taz_list))

            if "Zero Logsum TAZs" in config:
                zero_taz_list = RunResults.parseNumList(str(config["Zero Logsum TAZs"]))
                print("Zeroing out diffs for tazs {}".format(zero_taz_list))

        # Take the difference and convert utils to minutes (k_ivt = 0.0134 k_mc_ls = 1.0 in access calcs);
        # TODO: is k_mc_ls = 1.0?  DestinationChoice.cls has different values
        mandatoryAccessibilities = pd.merge(mandatoryAccessibilities,
                                            base_mandatoryAccessibilities,
                                            how='left')
        mandatoryAccessibilities['diff_dclogsum'] = mandatoryAccessibilities['scen_dclogsum'] - mandatoryAccessibilities['base_dclogsum']

        # zero out negative diffs if directed
        if len(zero_neg_taz_list) > 0:
            mandatoryAccessibilities.loc[(mandatoryAccessibilities.taz.isin(zero_neg_taz_list)) & (mandatoryAccessibilities.diff_dclogsum<0), 'diff_dclogsum'] = 0.0

        # zero out diffs if directed
        if len(zero_taz_list) > 0:
            mandatoryAccessibilities.loc[mandatoryAccessibilities.taz.isin(zero_taz_list), 'diff_dclogsum'] = 0.0

        mandatoryAccessibilities['logsum_diff_minutes'] = mandatoryAccessibilities.diff_dclogsum / 0.0134

        # Cliff Effect Mitigation
        mand_ldm_max = mandatoryAccessibilities.logsum_diff_minutes.abs().max()
        if mand_ldm_max < 0.00001:
            mandatoryAccessibilities['ldm_ratio'] = 1.0
            mandatoryAccessibilities['ldm_mult' ] = 1.0
        else:
            mandatoryAccessibilities['ldm_ratio'] = mandatoryAccessibilities['logsum_diff_minutes'].abs()/mand_ldm_max    # how big is the magnitude compared to max magnitude?
            mandatoryAccessibilities['ldm_mult' ] = 1.0/(1.0+np.exp(-(mandatoryAccessibilities['ldm_ratio']-RunResults.CEM_THRESHOLD)/RunResults.CEM_SHALLOW))
            mandatoryAccessibilities['ldm_cem']   = mandatoryAccessibilities['logsum_diff_minutes']*mandatoryAccessibilities['ldm_mult']

        # This too
        nonmandatoryAccessibilities = pd.merge(nonmandatoryAccessibilities,
                                               base_nonmandatoryAccessibilities,
                                               how='left')
        nonmandatoryAccessibilities['diff_dclogsum'] = \
                nonmandatoryAccessibilities['scen_dclogsum'] - nonmandatoryAccessibilities['base_dclogsum']

        # zero out negative diffs if directed
        if len(zero_neg_taz_list) > 0:
            nonmandatoryAccessibilities.loc[(nonmandatoryAccessibilities.taz.isin(zero_neg_taz_list)) & (nonmandatoryAccessibilities.diff_dclogsum<0), 'diff_dclogsum'] = 0.0

        # zero out diffs if directed
        if len(zero_taz_list) > 0:
            nonmandatoryAccessibilities.loc[nonmandatoryAccessibilities.taz.isin(zero_taz_list), 'diff_dclogsum'] = 0.0

        nonmandatoryAccessibilities['logsum_diff_minutes'] = nonmandatoryAccessibilities['diff_dclogsum'] / 0.0175

        # Cliff Effect Mitigation
        nonmm_ldm_max = nonmandatoryAccessibilities['logsum_diff_minutes'].abs().max()
        nonmandatoryAccessibilities['ldm_ratio'] = nonmandatoryAccessibilities['logsum_diff_minutes'].abs()/nonmm_ldm_max    # how big is the magnitude compared to max magnitude?
        nonmandatoryAccessibilities['ldm_mult' ] = 1.0/(1.0+np.exp(-(nonmandatoryAccessibilities['ldm_ratio']-RunResults.CEM_THRESHOLD)/RunResults.CEM_SHALLOW))
        nonmandatoryAccessibilities['ldm_cem']   = nonmandatoryAccessibilities['logsum_diff_minutes']*nonmandatoryAccessibilities['ldm_mult']

        # merge scenario + base accessbiity markets data
        accessibilityMarkets = pd.merge(accessibilityMarkets, base_accessibilityMarkets, how='left')

        mandatoryAccess = pd.merge(mandatoryAccessibilities, accessibilityMarkets, how='left')
        mandatoryAccess.fillna(0, inplace=True)

        nonmandatoryAccess = pd.merge(nonmandatoryAccessibilities, accessibilityMarkets, how='left')
        nonmandatoryAccess.fillna(0, inplace=True)

        # Cliff Effect Mitigated - rule of one-half
        cat1 = 'Accessibility Benefits (household-based) (with CEM)'
        cat2 = 'Logsum Hours - Mandatory Tours - Workers & Students'
        mandatoryAccess['CS diff work/school'] = \
            (0.5*mandatoryAccess.base_num_workers_students + 0.5*mandatoryAccess.scen_num_workers_students) *mandatoryAccess.ldm_cem
        for inclabel in ['lowInc','medInc','highInc','veryHighInc']:
            daily_results[(cat1,cat2,inclabel)] = mandatoryAccess.loc[mandatoryAccess.incQ_label==inclabel, 'CS diff work/school'].sum()/60.0;

        cat2 = 'Logsum Hours - NonMandatory Tours - All people'
        nonmandatoryAccess['CS diff all'] = \
            (0.5*nonmandatoryAccess.base_num_persons + 0.5*nonmandatoryAccess.scen_num_persons)*nonmandatoryAccess.ldm_cem
        for inclabel in ['lowInc','medInc','highInc','veryHighInc']:
            daily_results[(cat1,cat2,inclabel)] = nonmandatoryAccess.loc[nonmandatoryAccess.incQ_label==inclabel, 'CS diff all'].sum()/60.0;

        # create dataframe for debugging -- with mandatory and nonmandatory logsums and CS
        mandatoryAccess["mandatory"] = True
        nonmandatoryAccess["mandatory"] = False
        debug_cem_df = pd.concat(objs=[mandatoryAccess.rename(columns={'CS diff work/school':'CS diff min'}), 
                                    nonmandatoryAccess.rename(columns={'CS diff all':'CS diff min'})], axis="index", sort=True)
        debug_cem_df["cem"] = True

        # No Cliff Effect Mitigation - rule of one-half
        '''
        cat1 = 'Accessibility Benefits (household-based) (no CEM)'
        cat2 = 'Logsum Hours - Mandatory Tours - Workers & Students'
        mandatoryAccess['CS diff work/school'] = \
            (0.5*mandatoryAccess.base_num_workers_students + 0.5*mandatoryAccess.scen_num_workers_students)*mandatoryAccess.logsum_diff_minutes
        for inclabel in ['lowInc','medInc','highInc','veryHighInc']:
            daily_results[(cat1,cat2,inclabel)] = mandatoryAccess.loc[mandatoryAccess.incQ_label==inclabel, 'CS diff work/school'].sum()/60.0;

        cat2 = 'Logsum Hours - NonMandatory Tours - All people'
        nonmandatoryAccess['CS diff all'] = \
            (0.5*nonmandatoryAccess.base_num_persons + 0.5*nonmandatoryAccess.scen_num_persons)*nonmandatoryAccess.logsum_diff_minutes
        for inclabel in ['lowInc','medInc','highInc','veryHighInc']:
            daily_results[(cat1,cat2,inclabel)] = nonmandatoryAccess.loc[nonmandatoryAccess.incQ_label==inclabel, 'CS diff all'].sum()/60.0;

        # create dataframe for debugging -- with mandatory and nonmandatory logsums and CS
        debug_nocem_df = pd.concat(objs=[mandatoryAccess.rename(columns={'CS diff work/school':'CS diff min'}), 
                                        nonmandatoryAccess.rename(columns={'CS diff all':'CS diff min'})], axis="index", sort=True)
        debug_nocem_df["cem"] = False
        '''
        # note that this is misleading in that the cem column here pertains to the CEM status of the CS columns
        # but the logsum diffs themselves have CEM enabled in the ldm_cem column and not in the logsum_diff_minutes column

        if debug_dir:
            # prepare the debug info
            debug_df = pd.concat(objs=[debug_cem_df, debug_nocem_df], axis="index", sort=True)
            debug_df['CS diff hours'] = debug_df['CS diff min']/60.0

            # drop columns that are redundant (but missing data) -- incQ_label and walk_subzone should be used
            debug_df.drop(columns=['incQ','walk_subzone_label'], inplace=True)

            # write it
            debug_filename = os.path.join(debug_dir, "consumer_surplus.csv")
            debug_df.to_csv(debug_filename, index=False)
            print("Wrote {}".format(debug_filename))

            # copy Tableau template into the project folder for mapping
            try:
                from shutil import copyfile
                cs_tableau_filename = os.path.join(debug_dir, "consumer_surplus_{}.twb".format(config['Foldername - Future']))
                cs_tableau_template="\\\\mainmodel\\MainModelShare\\travel-model-one-master\\utilities\\PBA40\\metrics\\consumer_surplus.twb"
                copyfile(cs_tableau_template, cs_tableau_filename)
                print("Copied file to {}".format(cs_tableau_filename))
            except Exception as e:
                print(f"Could not copy tableau template: {e}")

        return (mandatoryAccessibilities, nonmandatoryAccessibilities,
                mandatoryAccess,          nonmandatoryAccess)

def read_accessibilities(filename, col_prefix, directory):
    """
    Read an accessibility CSV (logsums) from the specified directory
    Args:
        filename: Name of the file without .csv extension
        col_prefix: Prefix for column renaming (base or scen)
        directory: Path to the directory containing the file
    """
    filepath = os.path.join(directory, "logsums", f"{filename}.csv")
    df = pd.read_csv(filepath, sep=",")
    df.drop(columns='destChoiceAlt', inplace=True)
    df.set_index(['taz', 'subzone'], inplace=True)
    df = pd.DataFrame(df.stack()).reset_index()
    # Extract labels from the stacked column name
    df['incQ_label'] = df['level_2'].str.split('_', n=1).str.get(0)
    df['autoSuff_label'] = df['level_2'].str.split('_', n=1).str.get(1).str.rsplit('_', n=1).str.get(0)
    df['hasAV'] = df['level_2'].apply(lambda x: 0 if "noAV" in x else 1)
    df.drop(columns='level_2', inplace=True)
    df.rename(columns={0: f'{col_prefix}_dclogsum', 'subzone': 'walk_subzone'}, inplace=True)
    return df

def read_accessibility_markets(col_prefix, directory):
    """
    Read the AccessibilityMarkets CSV from the specified directory
    """
    filepath = os.path.join(directory, "core_summaries", "AccessibilityMarkets.csv")
    df = pd.read_csv(filepath, sep=",")
    df.rename(columns={'num_persons': f'{col_prefix}_num_persons',
                      'num_workers': f'{col_prefix}_num_workers',
                      'num_workers_students': f'{col_prefix}_num_workers_students'}, inplace=True)
    return df

def compute_access_benefits_metrics():
    """
    Compute final access metrics from the daily accessibility processing, merge with EPC data, and return a DataFrame.
    """
    # Read base files from BASE_DIR
    base_mandatory = read_accessibilities("mandatoryAccessibilities", "base", BASE_DIR)
    base_nonmandatory = read_accessibilities("nonMandatoryAccessibilities", "base", BASE_DIR)
    base_markets = read_accessibility_markets("base", BASE_DIR)

    # Read scenario files from SCEN_DIR
    scen_mandatory = read_accessibilities("mandatoryAccessibilities", "scen", SCEN_DIR)
    scen_nonmandatory = read_accessibilities("nonMandatoryAccessibilities", "scen", SCEN_DIR)
    scen_markets = read_accessibility_markets("scen", SCEN_DIR)
    
    # Create an empty dictionary for daily results
    daily_results = OrderedDict()
    
    # Create minimal config
    config = {}
    
    # Use the static method to calculate consumer surplus
    _, _, mandatoryAccess, nonmandatoryAccess = RunResults.calculateConsumerSurplus(
        config=config,
        daily_results=daily_results,
        mandatoryAccessibilities=scen_mandatory,
        base_mandatoryAccessibilities=base_mandatory,
        nonmandatoryAccessibilities=scen_nonmandatory,
        base_nonmandatoryAccessibilities=base_nonmandatory,
        accessibilityMarkets=scen_markets,
        base_accessibilityMarkets=base_markets,
        debug_dir=None  
    )
    
    # Process EPC data for both EPC types and compute metrics in a streamlined loop
    epc_metrics = {}
    for key, use_epc18 in (("epc_22", False), ("epc_18", True)):
        # Read and rename EPC data
        epc_df = read_epc_data(epc_18=use_epc18).rename(columns={"taz_epc": f"taz_{key}"})
        # Merge with mandatory and nonmandatory accessibility data
        mand_merge = pd.merge(mandatoryAccess, epc_df, left_on="taz", right_on="TAZ1454")
        nonmand_merge = pd.merge(nonmandatoryAccess, epc_df, left_on="taz", right_on="TAZ1454")
        # Export debug files (optional)
        mand_merge.to_csv(pathlib.Path(OUTPUT_Dir, f"mandatoryAccess_{key}_(intermediate_file).csv"), index=False)
        nonmand_merge.to_csv(pathlib.Path(OUTPUT_Dir, f"nonmandatoryAccess_{key}_(intermediate_file).csv"), index=False)
        # Compute EPC-specific metrics using the renamed EPC flag column
        col = f"taz_{key}"
        mand_val = mand_merge.loc[mand_merge[col] == 1, 'CS diff work/school'].sum()
        nonmand_val = nonmand_merge.loc[nonmand_merge[col] == 1, 'CS diff all'].sum()
        workers_students = 0.5 * mand_merge.loc[mand_merge[col] == 1, 'base_num_workers_students'].sum() + \
             0.5 * mand_merge.loc[mand_merge[col] == 1, 'scen_num_workers_students'].sum()
        persons = 0.5 * nonmand_merge.loc[nonmand_merge[col] == 1, 'base_num_persons'].sum() + \
                  0.5 * nonmand_merge.loc[nonmand_merge[col] == 1, 'scen_num_persons'].sum()
        epc_metrics[key] = {
            "mandatory_value": mand_val,
            "nonmandatory_value": nonmand_val,
            "per_capita_benefits": (mand_val + nonmand_val) / (workers_students + persons),
            "num_workers_students": workers_students,
            "num_persons": persons
        }
    
    # Overall accessibility metrics
    mandatoryAccess_value = mandatoryAccess['CS diff work/school'].sum()
    nonmandatoryAccess_value = nonmandatoryAccess['CS diff all'].sum()

    all_workers_students = 0.5 * mandatoryAccess['base_num_workers_students'].sum() + \
                            0.5 * mandatoryAccess['scen_num_workers_students'].sum()
    all_persons = 0.5 * nonmandatoryAccess['base_num_persons'].sum() + \
                   0.5 * nonmandatoryAccess['scen_num_persons'].sum()

    per_capita_access_benefits = (mandatoryAccess_value + nonmandatoryAccess_value) / (all_workers_students + all_persons)

    per_capita_access_benefits_epc_22 = epc_metrics["epc_22"]["per_capita_benefits"]
    per_capita_access_benefits_epc_18 = epc_metrics["epc_18"]["per_capita_benefits"]
    per_capita_access_benefits_epc_22_to_total_ratio = per_capita_access_benefits_epc_22 / per_capita_access_benefits
    per_capita_access_benefits_epc_18_to_total_ratio = per_capita_access_benefits_epc_18 / per_capita_access_benefits
    
    # Create separate metrics lists for each group
    metrics_list_1g = [
        # 1G - Overall access benefits
        ('mandatory_access_benefits', mandatoryAccess_value),
        ('nonmandatory_access_benefits', nonmandatoryAccess_value),
        ('num_workers_students', all_workers_students),
        ('num_persons', all_persons),
        ('total_access_benefits', mandatoryAccess_value + nonmandatoryAccess_value),
        ('total_num_workers_students', all_workers_students),
        ('total_num_persons', all_persons),
        ('per_capita_access_benefits', per_capita_access_benefits)
    ]

    metrics_list_1ha = [
        # 1Ha - epc_22 metrics
        ('mandatory_access_epc_22_benefits', epc_metrics["epc_22"]["mandatory_value"]),
        ('nonmandatory_access_epc_22_benefits', epc_metrics["epc_22"]["nonmandatory_value"]),
        ('num_workers_students_epc_22', epc_metrics["epc_22"]["num_workers_students"]),
        ('num_persons_epc_22', epc_metrics["epc_22"]["num_persons"]),
        ('total_access_benefits_epc_22', epc_metrics["epc_22"]["mandatory_value"] + epc_metrics["epc_22"]["nonmandatory_value"]),
        ('total_num_workers_students_epc_22', epc_metrics["epc_22"]["num_workers_students"]),
        ('total_num_persons_epc_22', epc_metrics["epc_22"]["num_persons"]),
        ('per_capita_access_benefits_epc_22', epc_metrics["epc_22"]["per_capita_benefits"]),
        ('per_capita_access_benefits_epc_22_to_total_ratio', per_capita_access_benefits_epc_22_to_total_ratio)

    ]

    metrics_list_1hb = [
        # 1Hb - epc_18 metrics
        ('mandatory_access_epc_18_benefits', epc_metrics["epc_18"]["mandatory_value"]),   
        ('nonmandatory_access_epc_18_benefits', epc_metrics["epc_18"]["nonmandatory_value"]),
        ('num_workers_students_epc_18', epc_metrics["epc_18"]["num_workers_students"]),
        ('num_persons_epc_18', epc_metrics["epc_18"]["num_persons"]),
        ('total_access_benefits_epc_18', epc_metrics["epc_18"]["mandatory_value"] + epc_metrics["epc_18"]["nonmandatory_value"]),
        ('total_num_workers_students_epc_18', epc_metrics["epc_18"]["num_workers_students"]),
        ('total_num_persons_epc_18', epc_metrics["epc_18"]["num_persons"]),
        ('per_capita_access_benefits_epc_18', epc_metrics["epc_18"]["per_capita_benefits"]),
        ('per_capita_access_benefits_epc_18_to_total_ratio', per_capita_access_benefits_epc_18_to_total_ratio)

    ]

    # Create separate DataFrames for each group
    run_name = os.path.split(os.getcwd())[1]
    
    df_1g = pd.DataFrame(metrics_list_1g, columns=['variable_desc', 'value'])
    df_1g.insert(0, 'run_name', run_name)
    df_1g['group_code'] = '1G'

    df_1ha = pd.DataFrame(metrics_list_1ha, columns=['variable_desc', 'value'])
    df_1ha.insert(0, 'run_name', run_name)
    df_1ha['group_code'] = '1Ha'

    df_1hb = pd.DataFrame(metrics_list_1hb, columns=['variable_desc', 'value'])
    df_1hb.insert(0, 'run_name', run_name)
    df_1hb['group_code'] = '1Hb'

    # Combine all DataFrames
    out_frame = pd.concat([df_1g, df_1ha, df_1hb], ignore_index=True)
    
    print("Access metrics computed.")
    return out_frame

# ---------------------------
# Main routine
# ---------------------------
if __name__ == '__main__':
    print("Current working directory:", os.getcwd())
    
    # First prepare the EPC 2018 data so that later functions can read it
    prepare_epc18_data()
    
    # Compute the access benefits (logsum) metrics
    access_benefit_df = compute_access_benefits_metrics()
    
    # Rename the original 'value' column and group_code column
    access_benefit_df = access_benefit_df.rename(columns={
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
    access_benefit_df = access_benefit_df[column_order]
    
    # Drop run_name column before writing to CSV
    access_benefit_df = access_benefit_df.drop('run_name', axis=1)
    
    # Write the combined metrics to a single CSV file
    output_filename = pathlib.Path(OUTPUT_Dir, "NPA_Metrics_Goal_1G_1H.csv")
    access_benefit_df.to_csv(output_filename, header=True, float_format='%.5f', index=False)
    print("Combined metrics written to", output_filename)
    
    # Print a summary of the computed metrics
    print("\nCombined Metrics:")
    print(access_benefit_df)

# ---------------------------
# Reorder the output
# ---------------------------
def reorder_metrics(row):
    desc = row['variable_desc']
    metric_name = (
        'access_benefits' if 'benefits' in desc and 'per_capita' not in desc else
        'per_capita_access_benefits' if 'per_capita' in desc and '_to_total_ratio' not in desc else
        'per_capita_access_benefits_to_total_ratio' if '_to_total_ratio' in desc else
        'num_workers_students' if 'num_workers_students' in desc else
        'num_persons' if 'num_persons' in desc else None
    )
    epc_population = 'epc_22' if 'epc_22' in desc else 'epc_18' if 'epc_18' in desc else 'all'
    tour_classification = (
        'nonmandatory' if 'nonmandatory' in desc or ('persons' in desc and 'total' not in desc) else
        'mandatory' if (desc.startswith('mandatory') or ('workers_students' in desc and 'total' not in desc))
        else 'total'
    )
    return pd.Series({
        'metric_name': metric_name,
        'epc_population': epc_population,
        'tour_classification': tour_classification,
    })

access_benefit_df[['metric_name', 'epc_population', 'tour_classification']] = access_benefit_df.apply(reorder_metrics, axis=1)

access_benefit_df_new = access_benefit_df.pivot(
    index=['measure_names', 'epc_population', 'tour_classification'],
    columns='metric_name',
    values='current_value'
)
access_benefit_df_new['access_benefits'] = access_benefit_df_new['access_benefits'].round(0)
for col in ['per_capita_access_benefits', 'per_capita_access_benefits_to_total_ratio']:
    if col in access_benefit_df_new.columns:
        access_benefit_df_new[col] = access_benefit_df_new[col].round(2)

access_benefit_df_new = access_benefit_df_new.reset_index()
access_benefit_df_new.insert(0, 'base', BASE_DIR.name)
access_benefit_df_new.insert(1, 'alt', SCEN_DIR.name)

access_benefit_df_new.to_csv(pathlib.Path(OUTPUT_Dir, "NPA_Metrics_Goal_1G_1H_reordered.csv"), index=False)
access_benefit_df_new.to_excel(pathlib.Path(OUTPUT_Dir_Tableau, f"NPA_metrics_Goal_1G_1H_base_{BASE_DIR.name}_vs_scen_{SCEN_DIR.name}.xlsx"), index=False)