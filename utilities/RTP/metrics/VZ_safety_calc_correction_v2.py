#!/usr/bin/env python3
"""
Calculate Safe1 metrics -- fatalities and injuries -- from MTC model outputs

Pass three arguments to the script:
1) Project (one of NGF, PBA50 or PBA50+)
2) MODEL_RUN_ID_NO_PROJECT
3) MODEL_RUN_ID_SCENARIO

For no project only, you can pass MODEL_RUN_ID_SCENARIO == MODEL_RUN_ID_NO_PROJECT.

This script implements two corrections to the fatalities and injuries as they were originally calculated:
1) General correction: based on the difference between modeled fatalities/injuries vs observed
2) Speed correction: based on literature to decrease fatality and injury rates for reduced speeds

Script converted from R to Python. The original R script contains more background documentation:
https://github.com/BayAreaMetro/travel-model-one/blob/147678bcf549b3af9803db5b0547899206dd5304/utilities/RTP/metrics/VZ_safety_calc_correction_v2.R
"""

import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
import logging

# Configuration
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 150)
pd.set_option('display.max_rows', 50)

def main():
    if len(sys.argv) != 4:
        print("Three arguments are required: PROJECT (NGF, PBA50 or PBA50+), MODEL_RUN_ID_NO_PROJECT and MODEL_RUN_ID_SCENARIO")
        sys.exit(1)

    PROJECT = sys.argv[1]
    MODEL_RUN_ID_NO_PROJECT = sys.argv[2] 
    MODEL_RUN_ID_SCENARIO = sys.argv[3]
    FORECAST_YEAR = int(MODEL_RUN_ID_SCENARIO[:4])

    # Validate project
    if PROJECT not in ["NGF", "PBA50", "PBA50+"]:
        raise ValueError("PROJECT must be one of NGF, PBA50 or PBA50+")

    # Project-specific settings
    if PROJECT == "NGF":
        # NextGen Fwy settings
        TAZ_EPC_FILE = "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/metrics/metrics_01/taz1454_epcPBA50plus_2024_02_23.csv"
        PROJECT_SCENARIOS_DIR = "L:/Application/Model_One/NextGenFwys_Round2/Scenarios"
        BASE_YEAR = 2015
        MODEL_RUN_ID_BASE_YEAR = "2015_TM152_NGF_05"
        MODEL_FULL_DIR_BASE_YEAR = os.path.join(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_BASE_YEAR)
        
    elif PROJECT == "PBA50":
        # PBA50 settings
        TAZ_EPC_FILE = "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/metrics/metrics_FinalBlueprint/CommunitiesOfConcern.csv"
        PROJECT_SCENARIOS_DIR = "M:/Application/Model One/RTP2021/Blueprint"
        BASE_YEAR = 2015
        MODEL_RUN_ID_BASE_YEAR = "2015_TM152_IPA_17"
        
        # IPA runs
        if "IPA" in MODEL_RUN_ID_SCENARIO:
            PROJECT_SCENARIOS_DIR = PROJECT_SCENARIOS_DIR.replace("Blueprint", "IncrementalProgress")
            MODEL_FULL_DIR_BASE_YEAR = os.path.join(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_BASE_YEAR)
        else:
            MODEL_FULL_DIR_BASE_YEAR = os.path.join(
                PROJECT_SCENARIOS_DIR.replace("Blueprint", "IncrementalProgress"),
                MODEL_RUN_ID_BASE_YEAR
            )
            
    elif PROJECT == "PBA50+":
        # PBA50+ settings
        TAZ_EPC_FILE_18 = "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/metrics/metrics_02/taz_coc_crosswalk.csv"
        TAZ_EPC_FILE = "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/metrics/metrics_02/taz1454_epcPBA50plus_2024_02_29.csv"
        TAZ_HRA_FILE = "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/metrics/metrics_02/taz1454_hraPBA50plus_2025_02_22.csv"
        PROJECT_SCENARIOS_DIR = "M:/Application/Model One/RTP2025/Blueprint"
        BASE_YEAR = 2015
        MODEL_RUN_ID_BASE_YEAR = "2015_TM161_IPA_08"
        
        # IPA runs
        if "IPA" in MODEL_RUN_ID_SCENARIO:
            PROJECT_SCENARIOS_DIR = PROJECT_SCENARIOS_DIR.replace("Blueprint", "IncrementalProgress")
            MODEL_FULL_DIR_BASE_YEAR = os.path.join(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_BASE_YEAR)
        else:
            MODEL_FULL_DIR_BASE_YEAR = os.path.join(
                PROJECT_SCENARIOS_DIR.replace("Blueprint", "IncrementalProgress"),
                MODEL_RUN_ID_BASE_YEAR
            )

    COLLISION_RATES_EXCEL = "X:/travel-model-one-master/utilities/RTP/metrics/CollisionLookupFINAL.xlsx"
    OUTPUT_FILE = os.path.join(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_SCENARIO, "OUTPUT", "metrics", "fatalities_injuries_test.csv")
    LOG_FILE = os.path.join(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_SCENARIO, "OUTPUT", "metrics", "fatalities_injuries_test.log")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

    logging.info(f"This file is written by VZ_safety_calc_correction_v2.py (converted from R)")
    logging.info(f"                  PROJECT: {PROJECT}")
    if PROJECT == "PBA50+":
        logging.info(f"         TAZ_EPC_FILE_18: {TAZ_EPC_FILE_18}")
        logging.info(f"             TAZ_HRA_FILE: {TAZ_HRA_FILE}")
    logging.info(f"             TAZ_EPC_FILE: {TAZ_EPC_FILE}")
    logging.info(f"    PROJECT_SCENARIOS_DIR: {PROJECT_SCENARIOS_DIR}")
    logging.info(f"                BASE_YEAR: {BASE_YEAR}")
    logging.info(f"   MODEL_RUN_ID_BASE_YEAR: {MODEL_RUN_ID_BASE_YEAR}")
    logging.info(f" MODEL_FULL_DIR_BASE_YEAR: {MODEL_FULL_DIR_BASE_YEAR}")
    logging.info(f"            FORECAST_YEAR: {FORECAST_YEAR}")
    logging.info(f"  MODEL_RUN_ID_NO_PROJECT: {MODEL_RUN_ID_NO_PROJECT}")
    logging.info(f"    MODEL_RUN_ID_SCENARIO: {MODEL_RUN_ID_SCENARIO}")

    # Constants
    N_DAYS_PER_YEAR = 300
    ONE_HUNDRED_THOUSAND = 100000
    ONE_MILLION = 1000000
    ONE_HUNDRED_MILLION = 100000000

    logging.info(f"     ONE_HUNDRED_THOUSAND: {ONE_HUNDRED_THOUSAND:,}")
    logging.info(f"              ONE_MILLION: {ONE_MILLION:,}")
    logging.info(f"      ONE_HUNDRED_MILLION: {ONE_HUNDRED_MILLION:,}")

    # Load collision rates
    collision_rates_df = pd.read_excel(COLLISION_RATES_EXCEL, sheet_name='Lookup Table')
    collision_rates_df = collision_rates_df.rename(columns={
        'ft': 'ft_collision',
        'at': 'at_collision', 
        'a': 'serious_injury_rate',
        'k': 'fatality_rate',
        'k_ped': 'fatality_rate_ped',
        'k_motor': 'fatality_rate_motorist',
        'k_bike': 'fatality_rate_bike'
    })
    collision_rates_df = collision_rates_df[[
        'ft_collision', 'at_collision', 'fatality_rate', 'serious_injury_rate',
        'fatality_rate_motorist', 'fatality_rate_ped', 'fatality_rate_bike'
    ]]
    
    logging.info("collision_rates_df head:")
    logging.info(collision_rates_df.head().to_string())

    # Define facility type mapping
    collision_ft_data = [
        [1, 4.6, 3.5, "fwy", 2],      # freeway-to-freeway connector
        [2, 4.6, 3.5, "fwy", 2],      # freeway  
        [3, 4.6, 3.5, "non_fwy", 3],  # expressway
        [4, 3.0, 2.0, "non_fwy", 4],  # collector
        [5, 4.6, 3.5, "fwy", 2],      # freeway ramp
        [6, 0.0, 0.0, "non_fwy", -1], # dummy link
        [7, 3.0, 2.0, "non_fwy", 4],  # major arterial
        [8, 4.6, 3.5, "fwy", 2],      # managed freeway
        [9, 0.0, 0.0, "non_fwy", -1], # special facility
        [10, 0.0, 0.0, "fwy", 2]      # toll plaza
    ]
    
    collision_ft_df = pd.DataFrame(collision_ft_data, columns=[
        'ft', 'fatality_exponent', 'injury_exponent', 'fwy_non', 'ft_collision'
    ])

    # PBA50 specific corrections (replicating original errors)
    if PROJECT == "PBA50":
        collision_ft_df.loc[collision_ft_df['ft'] == 5, 'ft_collision'] = 4   # freeway ramp
        collision_ft_df.loc[collision_ft_df['ft'] == 9, 'ft_collision'] = 4   # special facility  
        collision_ft_df.loc[collision_ft_df['ft'] == 10, 'ft_collision'] = 4  # toll plaza
        
        # Reset exponents based on ft_collision
        collision_ft_df['fatality_exponent'] = 0.0
        collision_ft_df.loc[collision_ft_df['ft_collision'].isin([1,2,3,5,6,8]), 'fatality_exponent'] = 4.6
        collision_ft_df.loc[collision_ft_df['ft_collision'].isin([4,7]), 'fatality_exponent'] = 3.0
        
        collision_ft_df['injury_exponent'] = 0.0
        collision_ft_df.loc[collision_ft_df['ft_collision'].isin([1,2,3,5,6,8]), 'injury_exponent'] = 3.5
        collision_ft_df.loc[collision_ft_df['ft_collision'].isin([4,7]), 'injury_exponent'] = 2.0

    logging.info("COLLISION_FT:")
    logging.info(collision_ft_df.to_string())

    # Define area type mapping
    collision_at_data = [
        [0, 3],  # Regional Core
        [1, 3],  # Central business district
        [2, 3],  # Urban business
        [3, 3],  # Urban
        [4, 4],  # Suburban
        [5, 4]   # Rural
    ]
    collision_at_df = pd.DataFrame(collision_at_data, columns=['at', 'at_collision'])
    logging.info("COLLISION_AT:")
    logging.info(collision_at_df.to_string())

    # Load TAZ EPC lookup
    taz_epc_lookup_df = pd.read_csv(TAZ_EPC_FILE)
    logging.info(f"Read {len(taz_epc_lookup_df)} lines of TAZ_EPC_LOOKUP from {TAZ_EPC_FILE}")
    
    # Make PBA50 version compatible
    if PROJECT == "PBA50":
        taz_epc_lookup_df = taz_epc_lookup_df.rename(columns={'taz': 'TAZ1454', 'in_set': 'taz_epc'})

    # For PBA50+, merge additional lookups
    if PROJECT == "PBA50+":
        taz_epc_lookup_18_df = pd.read_csv(TAZ_EPC_FILE_18)
        taz_epc_lookup_df = taz_epc_lookup_df.merge(taz_epc_lookup_18_df, on='TAZ1454')      
        taz_hra_lookup_df = pd.read_csv(TAZ_HRA_FILE) 
        taz_epc_lookup_df = taz_epc_lookup_df.merge(taz_hra_lookup_df, on='TAZ1454')

    logging.info("taz_epc_lookup_df head:")
    logging.info(taz_epc_lookup_df.head().to_string())

    # Initialize classes and functions
    safety_calc = SafetyCalculator(
        PROJECT, collision_rates_df, collision_ft_df, collision_at_df,
        N_DAYS_PER_YEAR, ONE_HUNDRED_THOUSAND, ONE_MILLION, ONE_HUNDRED_MILLION
    )
    # Calculate base year correction factors
    logging.info("Calculating base year correction factors...")
    base_year_results = safety_calc.calculate_base_year_corrections(
        MODEL_FULL_DIR_BASE_YEAR, MODEL_RUN_ID_BASE_YEAR, BASE_YEAR
    )
    # Process scenarios
    logging.info("Processing scenarios...")
    results_df = safety_calc.process_scenarios(
        PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_NO_PROJECT, MODEL_RUN_ID_SCENARIO,
        FORECAST_YEAR, taz_epc_lookup_df, base_year_results, PROJECT
    )
    # Save results
    results_df.to_csv(OUTPUT_FILE, index=False)
    logging.info(f"Wrote {len(results_df)} rows to {OUTPUT_FILE}")

class SafetyCalculator:
    def __init__(self, project, collision_rates_df, collision_ft_df, collision_at_df,
                 n_days_per_year, one_hundred_thousand, one_million, one_hundred_million):
        self.project = project
        self.collision_rates_df = collision_rates_df
        self.collision_ft_df = collision_ft_df
        self.collision_at_df = collision_at_df
        self.n_days_per_year = n_days_per_year
        self.one_hundred_thousand = one_hundred_thousand
        self.one_million = one_million
        self.one_hundred_million = one_hundred_million

    def observed_fatalities_injuries(self, observed_year, annual_vmt, population):
        """Create observed fatalities and injuries data"""
        if observed_year != 2015:
            raise ValueError("observed_fatalities_injuries() not implemented for observed_year != 2015")

        data = {
            'N_fatalities_motorist': [301],
            'N_fatalities_ped': [127], 
            'N_fatalities_bike': [27],
            'N_serious_injuries': [1968]
        }
        
        network_summary_df = pd.DataFrame(data)
        network_summary_df['N_fatalities_total'] = (
            network_summary_df['N_fatalities_motorist'] + 
            network_summary_df['N_fatalities_ped'] + 
            network_summary_df['N_fatalities_bike']
        )

        observed = {
            'model_run_id': 'observed',
            'year': 2015,
            'population': population,
            'annual_VMT': annual_vmt,
            'network_summary_df': network_summary_df
        }

        return self.calculate_per_capita(observed)

    def calculate_per_capita(self, fatal_inj):
        """Calculate per capita and per VMT rates"""
        df = fatal_inj['network_summary_df']
        
        if 'annual_VMT_100M' not in df.columns:
            df['annual_VMT_100M'] = fatal_inj['annual_VMT'] / self.one_hundred_million

        # Per 100M VMT
        df['N_fatalities_per_100M_VMT_motorist'] = df['N_fatalities_motorist'] / df['annual_VMT_100M']
        df['N_fatalities_per_100M_VMT_ped'] = df['N_fatalities_ped'] / df['annual_VMT_100M']
        df['N_fatalities_per_100M_VMT_bike'] = df['N_fatalities_bike'] / df['annual_VMT_100M']
        df['N_fatalities_per_100M_VMT_total'] = df['N_fatalities_total'] / df['annual_VMT_100M']
        df['N_serious_injuries_per_100M_VMT'] = df['N_serious_injuries'] / df['annual_VMT_100M']

        # Per 100K population
        pop_100k = fatal_inj['population'] / self.one_hundred_thousand
        df['N_fatalities_per_100K_pop_motorist'] = df['N_fatalities_motorist'] / pop_100k
        df['N_fatalities_per_100K_pop_ped'] = df['N_fatalities_ped'] / pop_100k
        df['N_fatalities_per_100K_pop_bike'] = df['N_fatalities_bike'] / pop_100k
        df['N_fatalities_per_100K_pop_total'] = df['N_fatalities_total'] / pop_100k
        df['N_serious_injuries_per_100K_pop'] = df['N_serious_injuries'] / pop_100k

        fatal_inj['network_summary_df'] = df
        return fatal_inj

    def modeled_fatalities_injuries(self, model_run_id, model_year, model_network_df, 
                                   population, network_group_by_col=None, network_no_project_df=None):
        """Calculate modeled fatalities and injuries"""
        
        # Create copy and clean data
        df = model_network_df.copy()
        
        # Drop time-specific columns
        time_cols = ['ctimEA', 'ctimAM', 'ctimMD', 'ctimPM', 'ctimEV',
                    'vcEA', 'vcAM', 'vcMD', 'vcPM', 'vcEV']
        df = df.drop(columns=[col for col in time_cols if col in df.columns])

        # Add average speed
        df['avg_speed'] = (df['cspdEA'] + df['cspdAM'] + df['cspdMD'] + df['cspdPM'] + df['cspdEV']) / 5.0

        # Reshape volume and speed data
        vol_cols = ['volEA_tot', 'volAM_tot', 'volMD_tot', 'volPM_tot', 'volEV_tot']
        speed_cols = ['cspdEA', 'cspdAM', 'cspdMD', 'cspdPM', 'cspdEV']
        
        vol_df = df[['a', 'b'] + vol_cols].melt(
            id_vars=['a', 'b'], 
            value_vars=vol_cols,
            var_name='timeperiod', 
            value_name='vol'
        )
        vol_df['timeperiod'] = vol_df['timeperiod'].str.replace('vol', '').str.replace('_tot', '')

        speed_df = df[['a', 'b'] + speed_cols].melt(
            id_vars=['a', 'b'],
            value_vars=speed_cols, 
            var_name='timeperiod',
            value_name='cspd'
        )
        speed_df['timeperiod'] = speed_df['timeperiod'].str.replace('cspd', '')

        # Merge volume and speed
        vol_speed_df = vol_df.merge(speed_df, on=['a', 'b', 'timeperiod'])

        # Merge back with other columns
        other_cols = [col for col in df.columns if col not in vol_cols + speed_cols]
        df_final = vol_speed_df.merge(df[other_cols], on=['a', 'b'])

        # Add mappings
        df_final = df_final.merge(self.collision_ft_df, on='ft', how='left')
        df_final = df_final.merge(self.collision_at_df, on='at', how='left')

        # Calculate annual VMT
        df_final['annual_VMT'] = self.n_days_per_year * df_final['vol'] * df_final['distance']

        # Add speed corrections
        if network_no_project_df is not None:
            logging.info("Adding speed correction columns from no project")
            df_final = self.add_speed_correction_columns(df_final, network_no_project_df)
        else:
            df_final['fatality_speed_correction_tp'] = 1.0
            df_final['fatality_speed_correction_avg'] = 1.0
            df_final['injury_speed_correction_tp'] = 1.0
            df_final['injury_speed_correction_avg'] = 1.0

        # Merge collision rates and calculate fatalities/injuries
        df_final = df_final.merge(self.collision_rates_df, on=['ft_collision', 'at_collision'], how='left')
        
        df_final['N_fatalities_motorist'] = (
            df_final['fatality_speed_correction_avg'] * 
            (df_final['annual_VMT'] / self.one_million) * 
            df_final['fatality_rate_motorist']
        )
        df_final['N_fatalities_ped'] = (
            df_final['fatality_speed_correction_avg'] * 
            (df_final['annual_VMT'] / self.one_million) * 
            df_final['fatality_rate_ped']
        )
        df_final['N_fatalities_bike'] = (
            df_final['fatality_speed_correction_avg'] * 
            (df_final['annual_VMT'] / self.one_million) * 
            df_final['fatality_rate_bike']
        )
        df_final['N_fatalities_total'] = (
            df_final['N_fatalities_motorist'] + 
            df_final['N_fatalities_ped'] + 
            df_final['N_fatalities_bike']
        )
        df_final['N_serious_injuries'] = (
            df_final['injury_speed_correction_avg'] * 
            (df_final['annual_VMT'] / self.one_million) * 
            df_final['serious_injury_rate']
        )

        # Group and summarize
        if network_group_by_col is not None:
            grouped = df_final.groupby(network_group_by_col)
        else:
            grouped = df_final.groupby(lambda x: 'all')

        summary_df = grouped.agg({
            'annual_VMT': 'sum',
            'N_fatalities_motorist': 'sum',
            'N_fatalities_ped': 'sum', 
            'N_fatalities_bike': 'sum',
            'N_serious_injuries': 'sum'
        }).reset_index()
        
        summary_df['annual_VMT_100M'] = summary_df['annual_VMT'] / self.one_hundred_million
        summary_df['N_fatalities_total'] = (
            summary_df['N_fatalities_motorist'] + 
            summary_df['N_fatalities_ped'] + 
            summary_df['N_fatalities_bike']
        )

        modeled = {
            'model_run_id': model_run_id,
            'year': model_year,
            'population': population,
            'annual_VMT': df_final['annual_VMT'].sum(),
            'model_network_df': df_final,
            'network_summary_df': summary_df,
            'network_group_by_col': network_group_by_col
        }

        return self.calculate_per_capita(modeled)

    def add_speed_correction_columns(self, model_network_df, network_no_project_df):
        """Add speed correction columns based on no project speeds"""
        
        # Merge with no project data
        merged = model_network_df.merge(
            network_no_project_df[['a', 'b', 'timeperiod', 'cspd', 'avg_speed']],
            on=['a', 'b', 'timeperiod'],
            suffixes=('', '_no_project'),
            how='left'
        )

        # Calculate corrections
        merged['fatality_speed_correction_tp'] = (
            (merged['cspd'] / merged['cspd_no_project']) ** merged['fatality_exponent']
        )
        merged['fatality_speed_correction_avg'] = (
            (merged['avg_speed'] / merged['avg_speed_no_project']) ** merged['fatality_exponent']
        )
        merged['injury_speed_correction_tp'] = (
            (merged['cspd'] / merged['cspd_no_project']) ** merged['injury_exponent']
        )
        merged['injury_speed_correction_avg'] = (
            (merged['avg_speed'] / merged['avg_speed_no_project']) ** merged['injury_exponent']
        )

        # Handle NAs (set to 1.0 for non-PBA50)
        if self.project != "PBA50":
            merged['fatality_speed_correction_tp'].fillna(1.0, inplace=True)
            merged['fatality_speed_correction_avg'].fillna(1.0, inplace=True)
            merged['injury_speed_correction_tp'].fillna(1.0, inplace=True)
            merged['injury_speed_correction_avg'].fillna(1.0, inplace=True)

        # Cap corrections at 1.0 (only credit for slowing down)
        if self.project in ["PBA50", "PBA50+", "NGF"]:
            merged['fatality_speed_correction_tp'] = np.minimum(merged['fatality_speed_correction_tp'], 1.0)
            merged['fatality_speed_correction_avg'] = np.minimum(merged['fatality_speed_correction_avg'], 1.0)
            merged['injury_speed_correction_tp'] = np.minimum(merged['injury_speed_correction_tp'], 1.0)
            merged['injury_speed_correction_avg'] = np.minimum(merged['injury_speed_correction_avg'], 1.0)

        return merged

    def create_correction_factors_for_observed(self, modeled_fatal_inj, obs_fatal_inj):
        """Create correction factors to match observed data"""
        
        if modeled_fatal_inj['year'] != obs_fatal_inj['year']:
            raise ValueError("Years must match")

        mod_summary = modeled_fatal_inj['network_summary_df']
        obs_summary = obs_fatal_inj['network_summary_df']

        corrections = {
            'correct_N_fatalities_motorist': obs_summary.iloc[0]['N_fatalities_motorist'] / mod_summary.iloc[0]['N_fatalities_motorist'],
            'correct_N_fatalities_ped': obs_summary.iloc[0]['N_fatalities_ped'] / mod_summary.iloc[0]['N_fatalities_ped'],
            'correct_N_fatalities_bike': obs_summary.iloc[0]['N_fatalities_bike'] / mod_summary.iloc[0]['N_fatalities_bike'],
            'correct_N_serious_injuries': obs_summary.iloc[0]['N_serious_injuries'] / mod_summary.iloc[0]['N_serious_injuries']
        }

        modeled_fatal_inj.update(corrections)
        return modeled_fatal_inj

    def correct_using_observed_factors(self, modeled_fatal_inj, corrective_fatal_inj):
        """Apply correction factors"""
        
        df = modeled_fatal_inj['network_summary_df'].copy()
        
        df['N_fatalities_motorist'] *= corrective_fatal_inj['correct_N_fatalities_motorist']
        df['N_fatalities_ped'] *= corrective_fatal_inj['correct_N_fatalities_ped']
        df['N_fatalities_bike'] *= corrective_fatal_inj['correct_N_fatalities_bike']
        df['N_serious_injuries'] *= corrective_fatal_inj['correct_N_serious_injuries']
        df['N_fatalities_total'] = df['N_fatalities_motorist'] + df['N_fatalities_ped'] + df['N_fatalities_bike']

        modeled_fatal_inj['network_summary_df'] = df
        return self.calculate_per_capita(modeled_fatal_inj)

    def calculate_base_year_corrections(self, model_full_dir_base_year, model_run_id_base_year, base_year):
        """Calculate base year correction factors"""
        
        # Load base year data
        tazdata_base_df = pd.read_csv(os.path.join(model_full_dir_base_year, "INPUT", "landuse", "tazData.csv"))
        network_base_df = pd.read_csv(os.path.join(model_full_dir_base_year, "OUTPUT", "avgload5period.csv"))

        population_base_year = tazdata_base_df['TOTPOP'].sum()
        
        print("network_base_df columns:")
        print(network_base_df.columns.tolist())
        network_base_df.columns = network_base_df.columns.str.strip()
        print("network_base_df columns:")
        print(network_base_df.columns.tolist())

        network_base_df['daily_VMT'] = network_base_df['distance'] * (
            network_base_df['volEA_tot'] + network_base_df['volAM_tot'] + 
            network_base_df['volMD_tot'] + network_base_df['volPM_tot'] + network_base_df['volEV_tot']
        )
        annual_vmt_base_year = network_base_df['daily_VMT'].sum() * self.n_days_per_year

        # Get observed data
        observed_fatal_inj = self.observed_fatalities_injuries(base_year, annual_vmt_base_year, population_base_year)
        logging.info("OBSERVED_FATALITIES_INJURIES_BASE_YEAR:")
        logging.info(observed_fatal_inj['network_summary_df'].to_string())

        # Calculate modeled base year
        model_fatal_inj_base_year = self.modeled_fatalities_injuries(
            model_run_id_base_year, base_year, network_base_df, population_base_year
        )
        logging.info("MODEL_FATALITIES_INJURIES_BASE_YEAR:")
        logging.info(model_fatal_inj_base_year['network_summary_df'].to_string())

        # Create and apply correction factors
        model_fatal_inj_base_year = self.create_correction_factors_for_observed(
            model_fatal_inj_base_year, observed_fatal_inj
        )
        model_fatal_inj_base_year = self.correct_using_observed_factors(
            model_fatal_inj_base_year, model_fatal_inj_base_year
        )
        
        logging.info("--------------------------------------")
        logging.info("AFTER CORRECTION to BASE YEAR OBSERVED")
        logging.info(model_fatal_inj_base_year['network_summary_df'].to_string())

        return model_fatal_inj_base_year

    def process_scenarios(self, project_scenarios_dir, model_run_id_no_project, model_run_id_scenario,
                         forecast_year, taz_epc_lookup_df, base_year_results, project):
        """Process both no project and scenario runs"""
        
        model_run_ids = {
            "NO_PROJECT": model_run_id_no_project,
            "SCENARIO": model_run_id_scenario
        }

        results_df = pd.DataFrame()
        network_no_project_df = None

        for model_run_type in ["NO_PROJECT", "SCENARIO"]:
            model_run_id = model_run_ids[model_run_type]
            model_full_dir = os.path.join(project_scenarios_dir, model_run_id)
            
            logging.info(f"Processing {model_run_type}: {model_run_id}")

            # Load data
            tazdata_df = pd.read_csv(os.path.join(model_full_dir, "INPUT", "landuse", "tazData.csv"))
            network_df = pd.read_csv(os.path.join(model_full_dir, "OUTPUT", "avgload5period.csv"))
            link_to_taz_df = pd.read_csv(os.path.join(model_full_dir, "OUTPUT", "shapefile", "network_links_TAZ.csv"))
            link_to_taz_df = link_to_taz_df.rename(columns={'A': 'a', 'B': 'b'})

            print("network_df columns:")
            print(network_df.columns.tolist())
            network_df.columns = network_df.columns.str.strip()
            print("network_df columns:")
            print(network_df.columns.tolist())
            
            # Calculate basic metrics
            network_df['annual_VMT'] = self.n_days_per_year * (
                network_df['volEA_tot'] + network_df['volAM_tot'] + 
                network_df['volMD_tot'] + network_df['volPM_tot'] + network_df['volEV_tot']
            ) * network_df['distance']
            network_df['avg_speed'] = (
                network_df['cspdEA'] + network_df['cspdAM'] + 
                network_df['cspdMD'] + network_df['cspdPM'] + network_df['cspdEV']
            ) / 5.0

            # Associate links to EPC geography
            if project == "PBA50+":
                # For PBA50+, merge both EPC definitions and HRA
                link_to_taz_df = link_to_taz_df.merge(taz_epc_lookup_df, on='TAZ1454', how='left')
                link_to_epc_df = link_to_taz_df.groupby(['a', 'b']).agg({
                    'taz_epc': 'max',
                    'taz_coc': 'max', 
                    'taz_hra': 'max'
                }).reset_index()
                
                network_df = network_df.merge(link_to_epc_df, on=['a', 'b'], how='left')
                
                # Create geography classifications
                network_df['taz_epc_22'] = network_df['taz_epc'].apply(lambda x: "EPC_22" if x == 1 else "Non-EPC_22")
                network_df['taz_epc_22'] = network_df['taz_epc_22'].fillna("Non-EPC_22")
                
                network_df['taz_epc_18'] = network_df['taz_coc'].apply(lambda x: "EPC_18" if x == 1 else "Non-EPC_18")
                network_df['taz_epc_18'] = network_df['taz_epc_18'].fillna("Non-EPC_18")
                
                network_df['taz_hra'] = network_df['taz_hra'].apply(lambda x: "HRA" if x == 1 else "Non-HRA")
                network_df['taz_hra'] = network_df['taz_hra'].fillna("Non-HRA")
                
                # Local street classifications
                local_ft = [3, 4, 6, 7, 9]
                network_df['taz_hra_local'] = network_df.apply(
                    lambda row: "taz_hra_local" if row['taz_hra'] == "HRA" and row['ft'] in local_ft else "pass", 
                    axis=1
                )
                
                # Union of both EPCs
                network_df['taz_epc'] = network_df.apply(
                    lambda row: "EPC" if row['taz_epc_22'] == "EPC_22" or row['taz_epc_18'] == "EPC_18" else "Non-EPC",
                    axis=1
                )
                network_df['taz_epc'] = network_df['taz_epc'].fillna("Non-EPC")
                
                network_df['taz_epc_local'] = network_df.apply(
                    lambda row: "taz_epc_local" if row['taz_epc'] == "EPC" and row['ft'] in local_ft else "pass",
                    axis=1
                )
                network_df['Non_EPC_local'] = network_df.apply(
                    lambda row: "non_epc_local" if row['taz_epc'] == "Non-EPC" and row['ft'] in local_ft else "pass",
                    axis=1
                )

            else:
                # For NGF and PBA50
                link_to_taz_df = link_to_taz_df.merge(taz_epc_lookup_df, on='TAZ1454', how='left')
                link_to_epc_df = link_to_taz_df.groupby(['a', 'b']).agg({'taz_epc': 'max'}).reset_index()
                network_df = network_df.merge(link_to_epc_df, on=['a', 'b'], how='left')
                
                network_df['taz_epc'] = network_df['taz_epc'].apply(lambda x: "EPC" if x == 1 else "Non-EPC")
                network_df['taz_epc'] = network_df['taz_epc'].fillna("Non-EPC")
                
                local_ft = [3, 4, 6, 7, 9]
                network_df['taz_epc_local'] = network_df.apply(
                    lambda row: "taz_epc_local" if row['taz_epc'] == "EPC" and row['ft'] in local_ft else "pass",
                    axis=1
                )
                network_df['Non_EPC_local'] = network_df.apply(
                    lambda row: "non_epc_local" if row['taz_epc'] == "Non-EPC" and row['ft'] in local_ft else "pass",
                    axis=1
                )

            population_forecast = tazdata_df['TOTPOP'].sum()

            # Calculate fatalities and injuries for different groupings
            groupings = self.get_groupings(project)
            
            for grouping_name, group_col in groupings:
                logging.info(f"Calculating {grouping_name} for {model_run_type}")
                
                model_fatal_inj = self.modeled_fatalities_injuries(
                    model_run_id, forecast_year, network_df, population_forecast,
                    network_group_by_col=group_col, network_no_project_df=network_no_project_df
                )
                model_fatal_inj = self.correct_using_observed_factors(model_fatal_inj, base_year_results)
                
                # Add to results
                summary_df = model_fatal_inj['network_summary_df'].copy()
                if group_col is None:
                    summary_df['key'] = 'all'
                else:
                    summary_df = summary_df.rename(columns={group_col: 'key'})
                
                summary_df['model_run_type'] = model_run_type
                summary_df['model_run_id'] = model_run_id
                
                results_df = pd.concat([results_df, summary_df], ignore_index=True)

            # Save no project network for scenario speed corrections
            if model_run_type == "NO_PROJECT" and model_run_id_no_project != model_run_id_scenario:
                # Need to reshape network_df for speed corrections
                network_no_project_df = self.prepare_network_for_speed_corrections(network_df)

            # Break if same run ID for both
            if model_run_id_no_project == model_run_id_scenario:
                break

        return results_df

    def get_groupings(self, project):
        """Get list of groupings to calculate based on project"""
        
        base_groupings = [
            ("all", None),
            ("fwy_non", "fwy_non"),
            ("epc", "taz_epc"),
            ("epc_local", "taz_epc_local"),
            ("non_epc_local", "Non_EPC_local")
        ]

        if project == "PBA50+":
            additional_groupings = [
                ("epc_18", "taz_epc_18"),
                ("epc_22", "taz_epc_22"),
                ("hra", "taz_hra"),
                ("hra_local", "taz_hra_local")
            ]
            return base_groupings + additional_groupings
        
        return base_groupings

    def prepare_network_for_speed_corrections(self, network_df):
        """Prepare network dataframe for speed corrections by reshaping to time period format"""
        
        # Add average speed if not present
        if 'avg_speed' not in network_df.columns:
            network_df['avg_speed'] = (
                network_df['cspdEA'] + network_df['cspdAM'] + 
                network_df['cspdMD'] + network_df['cspdPM'] + network_df['cspdEV']
            ) / 5.0

        # Reshape speed data to long format
        speed_cols = ['cspdEA', 'cspdAM', 'cspdMD', 'cspdPM', 'cspdEV']
        
        speed_df = network_df[['a', 'b', 'avg_speed'] + speed_cols].melt(
            id_vars=['a', 'b', 'avg_speed'],
            value_vars=speed_cols,
            var_name='timeperiod',
            value_name='cspd'
        )
        speed_df['timeperiod'] = speed_df['timeperiod'].str.replace('cspd', '')

        return speed_df

if __name__ == "__main__":
    main()