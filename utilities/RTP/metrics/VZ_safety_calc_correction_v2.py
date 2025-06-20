#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Calculate Safe1 metrics -- fatalities and injuries -- from MTC model outputs

Pass three arguments to the script:
1) Project (one of NGF, PBA50 or PBA50+)
2) MODEL_RUN_ID_NO_PROJECT
3) MODEL_RUN_ID_SCENARIO

For no project only, you can pass MODEL_RUN_ID_SCENARIO == MODEL_RUN_ID_NO_PROJECT.

This script implements two corrections to the fatalities and injuries as they were 
originally calculated:
1) General correction: this is based on the difference between the modeled fatalites/injuries
   (which is itself based on VMT by facilty type and area type) to determine factors to make 
   the 2015 modeled fatalies and injuries match the observed.

2) The second correction is to account for reduced speeds, and it applies a correction 
   based on literature to decrease fatality and injury rates. This correction is based upon:
   
   The Power Model of the relationship between speed and road safety
   a report from the Institute of Transport Economics (TOI) by Run Elvik from October 2009
   https://www.toi.no/getfile.php?mmfileid=13206

   This report is also discussed in the US Federal Highway Administration Report:
   Self-Enforcing Roadways: A Guidance Report (Publication Number: FHWA-HRT-17-098, Date: January 2018)
   Chapter 2. Relationship between Speed and Safety
   https://www.fhwa.dot.gov/publications/research/safety/17098/003.cfm

   Documentation on how this speed correction factor was applied for Plan Bay Area 2050 
   can be found on page 49 of the Plan Bay Area 2050 Performance Report (October 2021)
   https://www.planbayarea.org/sites/default/files/documents/Plan_Bay_Area_2050_Performance_Report_October_2021.pdf
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
import logging
from pandas.core.dtypes.common import is_numeric_dtype

# Set up logging
logger = logging.getLogger(__name__)

# Constants
N_DAYS_PER_YEAR = 300  # assume 300 days per year (outputs are for one day)
ONE_HUNDRED_THOUSAND = 100000
ONE_MILLION = 1000000
ONE_HUNDRED_MILLION = 100000000

class FatalitiesInjuries:
    """
    Class to hold fatalities and injuries data with the variables:
    - year
    - model_run_id
    - population
    - annual_VMT
    - network_summary_df (DataFrame with columns):
        - N_fatalities_motorist
        - N_fatalities_ped
        - N_fatalities_bike
        - N_serious_injuries
        - N_fatalities_total
        - per 100k capita and per 100M VMT versions of the above
    """
    
    def __init__(self, attributes=None):
        """Constructor for the FatalitiesInjuries class"""
        if attributes is None:
            attributes = {}
        for key, value in attributes.items():
            setattr(self, key, value)
    
    def __str__(self):
        """String representation"""
        result = []
        result.append(f"fatalities_injuries for {self.year} -- {self.model_run_id}")
        result.append("=================================================================")
        result.append(f"annual_VMT: {self.annual_VMT:,}")
        result.append(f"population: {self.population:,}")
        
        # Convert wide table to long for display
        if getattr(self, 'network_group_by_col', None) is None:
            # This is a one-row table so just melt to long format
            network_summary_long = pd.melt(self.network_summary_df)
            result.append(str(network_summary_long))
        else:
            # This has one row per value of network_group_by_col
            id_vars = [self.network_group_by_col]
            network_summary_long = pd.melt(self.network_summary_df, 
                                           id_vars=id_vars, 
                                           var_name='metric')
            network_summary_wide = network_summary_long.pivot(index='metric', 
                                                              columns=self.network_group_by_col, 
                                                              values='value')
            result.append(str(network_summary_wide))
        
        # Add model_network_df info if available
        if hasattr(self, 'model_network_df'):
            result.append(f"-- model_network_df has {len(self.model_network_df)} rows")
        
        # Add correction factors if available
        if hasattr(self, 'correct_N_fatalities_motorist'):
            result.append("-- Correction (to observed) factors:")
            result.append(f"  correct_N_fatalities_motorist = {self.correct_N_fatalities_motorist:.5f}")
            result.append(f"  correct_N_fatalities_ped      = {self.correct_N_fatalities_ped:.5f}")
            result.append(f"  correct_N_fatalities_bike     = {self.correct_N_fatalities_bike:.5f}")
            result.append(f"  correct_N_serious_injuries    = {self.correct_N_serious_injuries:.5f}")
        
        return "\n".join(result)
    
    def calculate_per_capita(self):
        """
        Calculates per 100M VMT fatalities and injuries as well as
        per 100K population fatalities and injuries
        """
        # Add annual_VMT_100M if it's not there already
        if 'annual_VMT_100M' not in self.network_summary_df.columns:
            self.network_summary_df['annual_VMT_100M'] = self.annual_VMT / ONE_HUNDRED_MILLION
        
        # Calculate per 100M VMT
        self.network_summary_df['N_fatalities_per_100M_VMT_motorist'] = \
            self.network_summary_df['N_fatalities_motorist'] / self.network_summary_df['annual_VMT_100M']
        
        self.network_summary_df['N_fatalities_per_100M_VMT_ped'] = \
            self.network_summary_df['N_fatalities_ped'] / self.network_summary_df['annual_VMT_100M']
        
        self.network_summary_df['N_fatalities_per_100M_VMT_bike'] = \
            self.network_summary_df['N_fatalities_bike'] / self.network_summary_df['annual_VMT_100M']
        
        self.network_summary_df['N_fatalities_per_100M_VMT_total'] = \
            self.network_summary_df['N_fatalities_total'] / self.network_summary_df['annual_VMT_100M']
        
        self.network_summary_df['N_serious_injuries_per_100M_VMT'] = \
            self.network_summary_df['N_serious_injuries'] / self.network_summary_df['annual_VMT_100M']
        
        # Calculate per 100K population
        pop_100k = self.population / ONE_HUNDRED_THOUSAND
        
        self.network_summary_df['N_fatalities_per_100K_pop_motorist'] = \
            self.network_summary_df['N_fatalities_motorist'] / pop_100k
        
        self.network_summary_df['N_fatalities_per_100K_pop_ped'] = \
            self.network_summary_df['N_fatalities_ped'] / pop_100k
        
        self.network_summary_df['N_fatalities_per_100K_pop_bike'] = \
            self.network_summary_df['N_fatalities_bike'] / pop_100k
        
        self.network_summary_df['N_fatalities_per_100K_pop_total'] = \
            self.network_summary_df['N_fatalities_total'] / pop_100k
        
        self.network_summary_df['N_serious_injuries_per_100K_pop'] = \
            self.network_summary_df['N_serious_injuries'] / pop_100k
        
        return self
    
    def create_correction_factors_for_observed(self, obs_fatal_inj):
        """
        Updates the modeled fatalities and injuries to match that of the observed
        by determining and storing correction factors
        """
        # Check years match
        assert self.year == obs_fatal_inj.year, "Years must match"
        
        # Check network summaries have single row
        assert len(self.network_summary_df) == 1, "Model summary should have a single row"
        assert len(obs_fatal_inj.network_summary_df) == 1, "Observed summary should have a single row"
        
        logger.info(f"create_correction_factors_for_observed() fatalities and injuries for year {self.year}")
        
        # Determine correction factors
        self.correct_N_fatalities_motorist = obs_fatal_inj.network_summary_df.iloc[0]['N_fatalities_motorist'] / \
                                             self.network_summary_df.iloc[0]['N_fatalities_motorist']
        
        self.correct_N_fatalities_ped = obs_fatal_inj.network_summary_df.iloc[0]['N_fatalities_ped'] / \
                                        self.network_summary_df.iloc[0]['N_fatalities_ped']
        
        self.correct_N_fatalities_bike = obs_fatal_inj.network_summary_df.iloc[0]['N_fatalities_bike'] / \
                                         self.network_summary_df.iloc[0]['N_fatalities_bike']
        
        self.correct_N_serious_injuries = obs_fatal_inj.network_summary_df.iloc[0]['N_serious_injuries'] / \
                                          self.network_summary_df.iloc[0]['N_serious_injuries']
        
        return self
    
    def correct_using_observed_factors(self, corrective_fatal_inj):
        """
        Applies the correction factors from comparing modeling vs observed
        """
        logger.info("correct_using_observed_factors(): correcting fatalities/injuries")
        logger.info(f"  for {self.year} -- {self.model_run_id}")
        logger.info(f"  using {corrective_fatal_inj.year} -- {corrective_fatal_inj.model_run_id}")
        
        # Apply correction factors
        self.network_summary_df['N_fatalities_motorist'] = \
            self.network_summary_df['N_fatalities_motorist'] * corrective_fatal_inj.correct_N_fatalities_motorist
        
        self.network_summary_df['N_fatalities_ped'] = \
            self.network_summary_df['N_fatalities_ped'] * corrective_fatal_inj.correct_N_fatalities_ped
        
        self.network_summary_df['N_fatalities_bike'] = \
            self.network_summary_df['N_fatalities_bike'] * corrective_fatal_inj.correct_N_fatalities_bike
        
        self.network_summary_df['N_serious_injuries'] = \
            self.network_summary_df['N_serious_injuries'] * corrective_fatal_inj.correct_N_serious_injuries
        
        # Recalculate total fatalities
        self.network_summary_df['N_fatalities_total'] = \
            self.network_summary_df['N_fatalities_motorist'] + \
            self.network_summary_df['N_fatalities_ped'] + \
            self.network_summary_df['N_fatalities_bike']
        
        # Recalculate per capita
        return self.calculate_per_capita()

def observed_fatalities_injuries(observed_year, annual_VMT_arg, population_arg):
    """Helper for creating instance of observed fatalities and injuries"""
    if observed_year != 2015:
        raise ValueError("observed_fatalities_injuries() not implemented for observed_year != 2015")

    if observed_year == 2015:
        # 2015 Observed values
        # TODO: Please document source for these numbers
        network_summary_df = pd.DataFrame({
            'N_fatalities_motorist': [301],
            'N_fatalities_ped': [127],
            'N_fatalities_bike': [27],
            'N_serious_injuries': [1968]
        })
        
        # Calculate total fatalities
        network_summary_df['N_fatalities_total'] = \
            network_summary_df['N_fatalities_motorist'] + \
            network_summary_df['N_fatalities_ped'] + \
            network_summary_df['N_fatalities_bike']

        observed = {
            'model_run_id': "observed",
            'year': 2015,
            'population': population_arg,
            'annual_VMT': annual_VMT_arg,  # full network-level
            'network_summary_df': network_summary_df
        }

        # Create and return instance with per capita calculations
        return FatalitiesInjuries(observed).calculate_per_capita()

def add_speed_correction_columns(model_network_df, network_no_project_df, project):
    """
    Adds four columns to the model_network_df and returns it:
    - [fatality|injury]_speed_correction_[tp,avg]:
        - fatality or injury speed correction based on comparing congested speed to no project
        - for suffix tp, the congested speed is time period specific
        - for suffix avg, the congested speed is average (unweighted) across all 5 timeperiods
    """
    # Left join model network to no project
    n_row_before = len(model_network_df)
    
    # Select required columns from no_project and add _no_project suffix
    no_project_cols = network_no_project_df[['a', 'b', 'timeperiod', 'cspd', 'avg_speed']]
    no_project_cols = no_project_cols.rename(columns={'cspd': 'cspd_no_project', 
                                                     'avg_speed': 'avg_speed_no_project'})
    
    # Merge
    model_network_df = pd.merge(
        model_network_df,
        no_project_cols,
        on=['a', 'b', 'timeperiod'],
        how='left'
    )
    
    # Verify rows are unchanged
    assert len(model_network_df) == n_row_before, "Row count changed after merge"
    
    # Calculate speed correction factors
    model_network_df['fatality_speed_correction_tp'] = \
        (model_network_df['cspd'] / model_network_df['cspd_no_project']) ** model_network_df['fatality_exponent']
    
    model_network_df['fatality_speed_correction_avg'] = \
        (model_network_df['avg_speed'] / model_network_df['avg_speed_no_project']) ** model_network_df['fatality_exponent']
    
    model_network_df['injury_speed_correction_tp'] = \
        (model_network_df['cspd'] / model_network_df['cspd_no_project']) ** model_network_df['injury_exponent']
    
    model_network_df['injury_speed_correction_avg'] = \
        (model_network_df['avg_speed'] / model_network_df['avg_speed_no_project']) ** model_network_df['injury_exponent']
    
    # Handle NaN values - these are multiplicative so default to 1.0 in place of NaN
    # Keeping PBA50 bug for compatibility
    if project != "PBA50":
        model_network_df['fatality_speed_correction_tp'] = \
            model_network_df['fatality_speed_correction_tp'].fillna(1.0)
        
        model_network_df['fatality_speed_correction_avg'] = \
            model_network_df['fatality_speed_correction_avg'].fillna(1.0)
        
        model_network_df['injury_speed_correction_tp'] = \
            model_network_df['injury_speed_correction_tp'].fillna(1.0)
        
        model_network_df['injury_speed_correction_avg'] = \
            model_network_df['injury_speed_correction_avg'].fillna(1.0)
    
    # Cap values at 1.0 (don't allow increases in fatalities/injuries due to speed increases)
    if project in ["PBA50", "PBA50+", "NGF"]:
        model_network_df['fatality_speed_correction_tp'] = \
            model_network_df['fatality_speed_correction_tp'].apply(lambda x: min(x, 1.0) if not pd.isna(x) else x)
        
        model_network_df['fatality_speed_correction_avg'] = \
            model_network_df['fatality_speed_correction_avg'].apply(lambda x: min(x, 1.0) if not pd.isna(x) else x)
        
        model_network_df['injury_speed_correction_tp'] = \
            model_network_df['injury_speed_correction_tp'].apply(lambda x: min(x, 1.0) if not pd.isna(x) else x)
        
        model_network_df['injury_speed_correction_avg'] = \
            model_network_df['injury_speed_correction_avg'].apply(lambda x: min(x, 1.0) if not pd.isna(x) else x)
    else:
        # Set all to 1.0 (no correction)
        model_network_df['fatality_speed_correction_tp'] = 1.0
        model_network_df['fatality_speed_correction_avg'] = 1.0
        model_network_df['injury_speed_correction_tp'] = 1.0
        model_network_df['injury_speed_correction_avg'] = 1.0
    
    return model_network_df

def modeled_fatalities_injuries(model_run_id, model_year, model_network_df, population,
                               network_group_by_col=None, network_no_project_df=None, 
                               collision_rates_df=None, collision_ft=None, collision_at=None,
                               project_scenarios_dir=None, model_run_id_scenario=None,
                               project=None):
    """
    Creates and returns an instance of modeled fatalities and injuries
    
    Args:
        model_run_id: string, the model run ID for legibility
        model_year: the year the model is representing
        model_network_df: DataFrame from avgload5period.csv
        population: total regional population for per 100k residents calculations
        network_group_by_col: pass a column in model_network_df to perform a group_by operation
        network_no_project_df: pass this to do speed corrections based on no project link speeds
        collision_rates_df: DataFrame with collision rates
        collision_ft: DataFrame with facility type mapping
        collision_at: DataFrame with area type mapping
        project_scenarios_dir: project scenarios directory
        model_run_id_scenario: model run ID for scenario
        project: project type (NGF, PBA50, or PBA50+)
    """
    # Create a copy for use
    model_network_df = model_network_df.copy()
    
    # Drop ctim, vc cols
    time_cols = ['ctimEA', 'ctimAM', 'ctimMD', 'ctimPM', 'ctimEV', 
                'vcEA', 'vcAM', 'vcMD', 'vcPM', 'vcEV']
    
    for col in time_cols:
        if col in model_network_df.columns:
            model_network_df = model_network_df.drop(col, axis=1)
    
    # Add avg_speed column
    model_network_df['avg_speed'] = (model_network_df['cspdEA'] + 
                                     model_network_df['cspdAM'] + 
                                     model_network_df['cspdMD'] + 
                                     model_network_df['cspdPM'] + 
                                     model_network_df['cspdEV']) / 5.0
    
    # Move time period to column for volume and cspd
    n_row_before = len(model_network_df)
    
    # For volume
    vol_df = pd.melt(
        model_network_df[['a', 'b', 'volEA_tot', 'volAM_tot', 'volMD_tot', 'volPM_tot', 'volEV_tot']],
        id_vars=['a', 'b'],
        value_vars=['volEA_tot', 'volAM_tot', 'volMD_tot', 'volPM_tot', 'volEV_tot'],
        var_name='vol_timeperiod',
        value_name='vol'
    )
    vol_df['timeperiod'] = vol_df['vol_timeperiod'].str.extract(r'vol(.*)_tot')
    vol_df = vol_df.drop('vol_timeperiod', axis=1)
    
    # For cspd
    cspd_df = pd.melt(
        model_network_df[['a', 'b', 'cspdEA', 'cspdAM', 'cspdMD', 'cspdPM', 'cspdEV']],
        id_vars=['a', 'b'],
        value_vars=['cspdEA', 'cspdAM', 'cspdMD', 'cspdPM', 'cspdEV'],
        var_name='cspd_timeperiod',
        value_name='cspd'
    )
    cspd_df['timeperiod'] = cspd_df['cspd_timeperiod'].str.extract(r'cspd(.*)')
    cspd_df = cspd_df.drop('cspd_timeperiod', axis=1)
    
    # Combine vol and cspd
    vol_cspd_df = pd.merge(vol_df, cspd_df, on=['a', 'b', 'timeperiod'])
    assert len(vol_cspd_df) == 5 * n_row_before, "Row count issue after reshaping"
    
    # Combine with non-timeperiod based columns
    # First, drop time period columns from the original dataframe
    non_time_df = model_network_df.drop([
        'volEA_tot', 'volAM_tot', 'volMD_tot', 'volPM_tot', 'volEV_tot',
        'cspdEA', 'cspdAM', 'cspdMD', 'cspdPM', 'cspdEV'
    ], axis=1)
    
    # Merge with time period data
    model_network_df = pd.merge(vol_cspd_df, non_time_df, on=['a', 'b'])
    assert len(model_network_df) == 5 * n_row_before, "Row count issue after merging"
    
    # Recode ft and at by joining with COLLISION_FT and COLLISION_AT
    model_network_df = pd.merge(model_network_df, collision_ft, on=['ft'], how='left')
    model_network_df = pd.merge(model_network_df, collision_at, on=['at'], how='left')
    
    # Add annual_VMT column (timeperiod-based)
    model_network_df['annual_VMT'] = N_DAYS_PER_YEAR * model_network_df['vol'] * model_network_df['distance']
    
    # Add speed correction columns if no_project data is provided
    if network_no_project_df is not None:
        logger.info("Adding speed correction columns from no project")
        model_network_df = add_speed_correction_columns(
            model_network_df, 
            network_no_project_df, 
            project
        )
    else:
        # Default values (no correction)
        model_network_df['fatality_speed_correction_tp'] = 1.0
        model_network_df['fatality_speed_correction_avg'] = 1.0
        model_network_df['injury_speed_correction_tp'] = 1.0
        model_network_df['injury_speed_correction_avg'] = 1.0
    
    # Join to collision rates and calculate fatalities, injuries by link
    model_network_df = pd.merge(
        model_network_df, 
        collision_rates_df, 
        on=['ft_collision', 'at_collision'],
        how='left'
    )
    
    # Calculate fatalities and injuries
    model_network_df['N_fatalities_motorist'] = model_network_df['fatality_speed_correction_avg'] * \
                                              (model_network_df['annual_VMT'] / ONE_MILLION) * \
                                              model_network_df['fatality_rate_motorist']
    
    model_network_df['N_fatalities_ped'] = model_network_df['fatality_speed_correction_avg'] * \
                                         (model_network_df['annual_VMT'] / ONE_MILLION) * \
                                         model_network_df['fatality_rate_ped']
    
    model_network_df['N_fatalities_bike'] = model_network_df['fatality_speed_correction_avg'] * \
                                          (model_network_df['annual_VMT'] / ONE_MILLION) * \
                                          model_network_df['fatality_rate_bike']
    
    model_network_df['N_fatalities_total'] = model_network_df['N_fatalities_motorist'] + \
                                           model_network_df['N_fatalities_ped'] + \
                                           model_network_df['N_fatalities_bike']
    
    model_network_df['N_serious_injuries'] = model_network_df['injury_speed_correction_avg'] * \
                                           (model_network_df['annual_VMT'] / ONE_MILLION) * \
                                           model_network_df['serious_injury_rate']
    
    # Save for debugging
    if project_scenarios_dir and model_run_id_scenario:
        debug_file = os.path.join(
            project_scenarios_dir, 
            model_run_id_scenario, 
            "OUTPUT", 
            "metrics", 
            f"fatalities_injuries_debug_{model_run_id}.csv"
        )
        model_network_df.to_csv(debug_file, index=False)
        logger.info(f"Wrote debug file: {debug_file}")
    
    # Group by network_group_by_col if provided
    if network_group_by_col:
        grouped = model_network_df.groupby(network_group_by_col)
    else:
        # Create a dummy groupby with a single group
        model_network_df['_dummy_group'] = 1
        grouped = model_network_df.groupby('_dummy_group')
    
    # Aggregate
    model_summary_df = grouped.agg({
        'annual_VMT': lambda x: sum(x) / ONE_HUNDRED_MILLION,
        'N_fatalities_motorist': 'sum',
        'N_fatalities_ped': 'sum',
        'N_fatalities_bike': 'sum',
        'N_serious_injuries': 'sum'
    }).reset_index()
    
    # Rename annual_VMT column
    model_summary_df = model_summary_df.rename(columns={'annual_VMT': 'annual_VMT_100M'})
    
    # Calculate total fatalities
    model_summary_df['N_fatalities_total'] = model_summary_df['N_fatalities_motorist'] + \
                                          model_summary_df['N_fatalities_ped'] + \
                                          model_summary_df['N_fatalities_bike']
    
    # Create and return FatalitiesInjuries object
    modeled = {
        'model_run_id': model_run_id,
        'year': model_year,
        'population': population,
        'annual_VMT': model_network_df['annual_VMT'].sum(),  # entire network
        'model_network_df': model_network_df,
        'network_summary_df': model_summary_df,
        'network_group_by_col': network_group_by_col if network_group_by_col else None
    }
    
    # Remove the dummy group column if we created one
    if network_group_by_col is None and '_dummy_group' in model_summary_df.columns:
        model_summary_df = model_summary_df.drop('_dummy_group', axis=1)
        modeled['network_summary_df'] = model_summary_df
    
    return FatalitiesInjuries(modeled).calculate_per_capita()

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Calculate Safe1 metrics -- fatalities and injuries -- from MTC model outputs")
    parser.add_argument("project", choices=["NGF", "PBA50", "PBA50+"], 
                        help="Project (one of NGF, PBA50 or PBA50+)")
    parser.add_argument("model_run_id_no_project", 
                        help="MODEL_RUN_ID_NO_PROJECT")
    parser.add_argument("model_run_id_scenario", 
                        help="MODEL_RUN_ID_SCENARIO")
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_args()
    
    PROJECT = args.project
    MODEL_RUN_ID_NO_PROJECT = args.model_run_id_no_project
    MODEL_RUN_ID_SCENARIO = args.model_run_id_scenario
    FORECAST_YEAR = int(MODEL_RUN_ID_SCENARIO[0:4])
    
    # Set up project-specific paths and settings
    if PROJECT == "NGF":
        TAZ_EPC_FILE = "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/metrics/metrics_01/taz1454_epcPBA50plus_2024_02_23.csv"
        PROJECT_SCENARIOS_DIR = "L:/Application/Model_One/NextGenFwys_Round2/Scenarios"
        BASE_YEAR = 2015
        MODEL_RUN_ID_BASE_YEAR = "2015_TM152_NGF_05"
        MODEL_FULL_DIR_BASE_YEAR = os.path.join(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_BASE_YEAR)
    
    elif PROJECT == "PBA50":
        TAZ_EPC_FILE = "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/metrics/metrics_FinalBlueprint/CommunitiesOfConcern.csv"
        PROJECT_SCENARIOS_DIR = "M:/Application/Model One/RTP2021/Blueprint"
        BASE_YEAR = 2015
        MODEL_RUN_ID_BASE_YEAR = "2015_TM152_IPA_17"
        
        # IPA runs
        if "IPA" in MODEL_RUN_ID_SCENARIO:
            PROJECT_SCENARIOS_DIR = PROJECT_SCENARIOS_DIR.replace("Blueprint", "IncrementalProgress")
            MODEL_FULL_DIR_BASE_YEAR = os.path.join(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_BASE_YEAR)
        else:
            # for other runs, the base year is still in IncrementalProgress
            MODEL_FULL_DIR_BASE_YEAR = os.path.join(
                PROJECT_SCENARIOS_DIR.replace("Blueprint", "IncrementalProgress"),
                MODEL_RUN_ID_BASE_YEAR
            )
    
    elif PROJECT == "PBA50+":
        TAZ_EPC_FILE = "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/metrics/metrics_01/taz1454_epcPBA50plus_2024_02_23.csv"
        PROJECT_SCENARIOS_DIR = "M:/Application/Model One/RTP2025/Blueprint"
        BASE_YEAR = 2015
        MODEL_RUN_ID_BASE_YEAR = "2015_TM161_IPA_08"
        
        # IPA runs
        if "IPA" in MODEL_RUN_ID_SCENARIO:
            PROJECT_SCENARIOS_DIR = PROJECT_SCENARIOS_DIR.replace("Blueprint", "IncrementalProgress")
            MODEL_FULL_DIR_BASE_YEAR = os.path.join(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_BASE_YEAR)
        else:
            # for other runs, the base year is still in IncrementalProgress
            MODEL_FULL_DIR_BASE_YEAR = os.path.join(
                PROJECT_SCENARIOS_DIR.replace("Blueprint", "IncrementalProgress"),
                MODEL_RUN_ID_BASE_YEAR
            )
    
    COLLISION_RATES_EXCEL = "X:/travel-model-one-master/utilities/RTP/metrics/CollisionLookupFINAL.xlsx"
    OUTPUT_FILE = os.path.join(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_SCENARIO, "OUTPUT", "metrics", "fatalities_injuries.csv")
    LOG_FILE = os.path.join(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_SCENARIO, "OUTPUT", "metrics", "fatalities_injuries.log")
    
    # Configure logging
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    
    logger.info(f"This file is written by travel-model-one/utilities/RTP/metrics/VZ_safety_calc_correction_v2.py")
    logger.info(f"                  PROJECT: {PROJECT}")
    logger.info(f"             TAZ_EPC_FILE: {TAZ_EPC_FILE}")
    logger.info(f"    PROJECT_SCENARIOS_DIR: {PROJECT_SCENARIOS_DIR}")
    logger.info(f"                BASE_YEAR: {BASE_YEAR}")
    logger.info(f"   MODEL_RUN_ID_BASE_YEAR: {MODEL_RUN_ID_BASE_YEAR}")
    logger.info(f" MODEL_FULL_DIR_BASE_YEAR: {MODEL_FULL_DIR_BASE_YEAR}")
    logger.info(f"            FORECAST_YEAR: {FORECAST_YEAR}")
    logger.info(f"  MODEL_RUN_ID_NO_PROJECT: {MODEL_RUN_ID_NO_PROJECT}")
    logger.info(f"    MODEL_RUN_ID_SCENARIO: {MODEL_RUN_ID_SCENARIO}")
    
    logger.info(f"     ONE_HUNDRED_THOUSAND: {ONE_HUNDRED_THOUSAND:,}")
    logger.info(f"              ONE_MILLION: {ONE_MILLION:,}")
    logger.info(f"      ONE_HUNDRED_MILLION: {ONE_HUNDRED_MILLION:,}")

    # Read collision lookup table
    collision_rates_df = pd.read_excel(COLLISION_RATES_EXCEL, sheet_name="Lookup Table")
    collision_rates_df = collision_rates_df.rename(columns={
        'ft': 'ft_collision',                # Aggregated: 2 = freeway, 3 = expressway, 4 = collector / arterial
        'at': 'at_collision',                # Aggregated: 3 = urban, 4 = suburban and rural
        'a': 'serious_injury_rate',          # Count per 1 million vehicle miles traveled
        'k': 'fatality_rate',                # Count per 1 million vehicle miles traveled
        'k_ped': 'fatality_rate_ped',        # Count per 1 million vehicle miles traveled
        'k_motor': 'fatality_rate_motorist', # Count per 1 million vehicle miles traveled
        'k_bike': 'fatality_rate_bike'       # Count per 1 million vehicle miles traveled
    })
    collision_rates_df = collision_rates_df[['ft_collision', 'at_collision', 'fatality_rate', 
                                            'serious_injury_rate', 'fatality_rate_motorist', 
                                            'fatality_rate_ped', 'fatality_rate_bike']]
    logger.info("head(collision_rates_df):")
    logger.info(collision_rates_df.head())
    
    # Create COLLISION_FT dataframe
    # Maps facility type (ft) to aggregate version used for collision lookup (ft_collision)
    # https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#facility-type-ft
    # 
    # Also maps to fwy or non_fwy for segmentation
    # And fatality / injury exponents for speed corrections
    #                   ft |fatality| injury | fwy_non  | ft_collision
    #                      |exponent|exponent|          | (2 = freeway, 3 = expressway, 4 = collector / arterial)
    collision_ft_data = {
        'ft': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'fatality_exponent': [4.6, 4.6, 4.6, 3.0, 4.6, 0, 3.0, 4.6, 0, 0],
        'injury_exponent': [3.5, 3.5, 3.5, 2.0, 3.5, 0, 2.0, 3.5, 0, 0],
        'fwy_non': ['fwy', 'fwy', 'non_fwy', 'non_fwy', 'fwy', 'non_fwy', 'non_fwy', 'fwy', 'non_fwy', 'fwy'],
        'ft_collision': [2, 2, 3, 4, 2, -1, 4, 2, -1, 2],
    }
    COLLISION_FT = pd.DataFrame(collision_ft_data)
    
    # Apply PBA50 specific changes if needed
    if PROJECT == "PBA50":
        COLLISION_FT.loc[COLLISION_FT['ft'] == 5, 'ft_collision'] = 4  # freeway ramp
        COLLISION_FT.loc[COLLISION_FT['ft'] == 9, 'ft_collision'] = 4  # special facility
        COLLISION_FT.loc[COLLISION_FT['ft'] == 10, 'ft_collision'] = 4  # toll plaza
        
        # PBA50 assigns exponent *after* renaming ft=ft_collision
        COLLISION_FT['fatality_exponent'] = 0.0
        COLLISION_FT.loc[COLLISION_FT['ft_collision'].isin([1, 2, 3, 5, 6, 8]), 'fatality_exponent'] = 4.6
        COLLISION_FT.loc[COLLISION_FT['ft_collision'].isin([4, 7]), 'fatality_exponent'] = 3.0
        
        COLLISION_FT['injury_exponent'] = 0.0
        COLLISION_FT.loc[COLLISION_FT['ft_collision'].isin([1, 2, 3, 5, 6, 8]), 'injury_exponent'] = 3.5
        COLLISION_FT.loc[COLLISION_FT['ft_collision'].isin([4, 7]), 'injury_exponent'] = 2.0
    
    logger.info("COLLISION_FT")
    logger.info(COLLISION_FT)
    
    # Create COLLISION_AT dataframe
    # Maps area type (at) to aggregate version used for collision lookup (at_collision)
    # https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#facility-type-at
    #                at, at_collision: 3 = urban, 4 = suburban and rural
    collision_at_data = {
        'at': [0, 1, 2, 3, 4, 5],
        'at_collision': [3, 3, 3, 3, 4, 4]
    }
    COLLISION_AT = pd.DataFrame(collision_at_data)
    logger.info("COLLISION_AT:")
    logger.info(COLLISION_AT)
    
    # Read TAZ_EPC_LOOKUP
    TAZ_EPC_LOOKUP_DF = pd.read_csv(TAZ_EPC_FILE)
    logger.info(f"Read {len(TAZ_EPC_LOOKUP_DF)} lines of TAZ_EPC_LOOKUP from {TAZ_EPC_FILE}")
    
    # Make PBA50 version compatible
    if PROJECT == "PBA50":
        TAZ_EPC_LOOKUP_DF = TAZ_EPC_LOOKUP_DF.rename(columns={'taz': 'TAZ1454', 'in_set': 'taz_epc'})
        
    logger.info("head(TAZ_EPC_LOOKUP_DF):")
    logger.info(TAZ_EPC_LOOKUP_DF.head())

    ####### Calculate for the base year to determine correction factors #######
    tazdata_base_year_df = pd.read_csv(os.path.join(MODEL_FULL_DIR_BASE_YEAR, "INPUT", "landuse", "tazData.csv"))
    network_base_year_df = pd.read_csv(os.path.join(MODEL_FULL_DIR_BASE_YEAR, "OUTPUT", "avgload5period.csv"))
    
    # Calculate population and VMT for base year
    population_base_year = tazdata_base_year_df['TOTPOP'].sum()
    
    # Calculate daily VMT and annualize
    network_base_year_df['daily_VMT'] = network_base_year_df['distance'] * (
        network_base_year_df['volEA_tot'] + 
        network_base_year_df['volAM_tot'] + 
        network_base_year_df['volMD_tot'] + 
        network_base_year_df['volPM_tot'] + 
        network_base_year_df['volEV_tot']
    )
    annual_VMT_base_year = network_base_year_df['daily_VMT'].sum() * N_DAYS_PER_YEAR
    
    # Create observed and modeled fatalities/injuries objects for base year
    OBSERVED_FATALITIES_INJURIES_BASE_YEAR = observed_fatalities_injuries(
        BASE_YEAR, 
        annual_VMT_base_year, 
        population_base_year
    )
    logger.info(OBSERVED_FATALITIES_INJURIES_BASE_YEAR)
    
    model_fatal_inj_base_year = modeled_fatalities_injuries(
        MODEL_RUN_ID_BASE_YEAR,
        BASE_YEAR,
        network_base_year_df,
        population_base_year,
        network_group_by_col=None,
        network_no_project_df=None,
        collision_rates_df=collision_rates_df,
        collision_ft=COLLISION_FT,
        collision_at=COLLISION_AT,
        project_scenarios_dir=PROJECT_SCENARIOS_DIR,
        model_run_id_scenario=MODEL_RUN_ID_SCENARIO,
        project=PROJECT
    )
    logger.info(model_fatal_inj_base_year)
    
    # Create correction factors based on observed data
    model_fatal_inj_base_year.create_correction_factors_for_observed(OBSERVED_FATALITIES_INJURIES_BASE_YEAR)
    model_fatal_inj_base_year.correct_using_observed_factors(model_fatal_inj_base_year)
    
    logger.info("--------------------------------------")
    logger.info("AFTER CORRECTION to BASE YEAR OBSERVED")
    logger.info(model_fatal_inj_base_year)
    
    ####### Calculate for no project forecast year and scenario #######
    MODEL_RUN_IDS = {
        "NO_PROJECT": MODEL_RUN_ID_NO_PROJECT,
        "SCENARIO": MODEL_RUN_ID_SCENARIO
    }
    
    # We'll save this for SCENARIO
    network_no_project_df = None
    model_fatal_no_project = None  # debug
    results_df = pd.DataFrame()
    
    for model_run_type in ["NO_PROJECT", "SCENARIO"]:
        model_run_id = MODEL_RUN_IDS[model_run_type]
        model_full_dir = os.path.join(PROJECT_SCENARIOS_DIR, model_run_id)
        
        # Read input data
        tazdata_df = pd.read_csv(os.path.join(model_full_dir, "INPUT", "landuse", "tazData.csv"))
        network_df = pd.read_csv(os.path.join(model_full_dir, "OUTPUT", "avgload5period.csv"))
        link_to_taz_df = pd.read_csv(os.path.join(model_full_dir, "OUTPUT", "shapefile", "network_links_TAZ.csv"))
        link_to_taz_df = link_to_taz_df.rename(columns={'A': 'a', 'B': 'b'})
        
        # Calculate annual VMT and average speed
        network_df['annual_VMT'] = N_DAYS_PER_YEAR * (
            network_df['volEA_tot'] + 
            network_df['volAM_tot'] + 
            network_df['volMD_tot'] + 
            network_df['volPM_tot'] + 
            network_df['volEV_tot']
        ) * network_df['distance']
        
        network_df['avg_speed'] = (
            network_df['cspdEA'] + 
            network_df['cspdAM'] + 
            network_df['cspdMD'] + 
            network_df['cspdPM'] + 
            network_df['cspdEV']
        ) / 5.0
        
        # Associate each link to EPC vs non-EPC
        # Note: This is assuming a link is in an EPC taz if ANY part of it is within (even a small fraction)
        link_to_taz_df = pd.merge(link_to_taz_df, TAZ_EPC_LOOKUP_DF, on='TAZ1454', how='left')
        
        # Aggregate to link level
        link_to_epc_df = link_to_taz_df.groupby(['a', 'b']).agg({'taz_epc': 'max'}).reset_index()
        
        # Merge to network and create indicators
        network_df = pd.merge(network_df, link_to_epc_df, on=['a', 'b'], how='left')
        
        # Convert EPC values to categories
        network_df['taz_epc'] = np.where(network_df['taz_epc'] == 1, "EPC", "Non-EPC")
        network_df['taz_epc'] = network_df['taz_epc'].fillna("Non-EPC")
        
        # Create local street indicators based on facility types
        local_street_ft = [3, 4, 6, 7, 9]  # expressway, collector, dummy link, major arterial, special facility
        
        network_df['taz_epc_local'] = np.where(
            (network_df['taz_epc'] == "EPC") & (network_df['ft'].isin(local_street_ft)),
            "taz_epc_local", 
            "pass"
        )
        network_df['taz_epc_local'] = network_df['taz_epc_local'].fillna("pass")
        
        network_df['Non_EPC_local'] = np.where(
            (network_df['taz_epc'] == "Non-EPC") & (network_df['ft'].isin(local_street_ft)),
            "non_epc_local", 
            "pass"
        )
        network_df['Non_EPC_local'] = network_df['Non_EPC_local'].fillna("pass")
        
        # Get total population for forecast year
        population_forecast = tazdata_df['TOTPOP'].sum()
        
        # Calculate fatalities and injuries for all links
        model_fatal_inj = modeled_fatalities_injuries(
            model_run_id, 
            FORECAST_YEAR, 
            network_df, 
            population_forecast,
            network_group_by_col=None, 
            network_no_project_df=network_no_project_df,
            collision_rates_df=collision_rates_df,
            collision_ft=COLLISION_FT,
            collision_at=COLLISION_AT,
            project_scenarios_dir=PROJECT_SCENARIOS_DIR,
            model_run_id_scenario=MODEL_RUN_ID_SCENARIO,
            project=PROJECT
        )
        model_fatal_inj.correct_using_observed_factors(model_fatal_inj_base_year)
        
        if model_run_type == "NO_PROJECT":
            model_fatal_no_project = model_fatal_inj
        
        logger.info("--------------------------------------")
        logger.info(model_fatal_inj)
        
        # Calculate fatalities and injuries by freeway/non-freeway
        model_fatal_inj_fwy_non = modeled_fatalities_injuries(
            model_run_id, 
            FORECAST_YEAR, 
            network_df, 
            population_forecast,
            network_group_by_col="fwy_non", 
            network_no_project_df=network_no_project_df,
            collision_rates_df=collision_rates_df,
            collision_ft=COLLISION_FT,
            collision_at=COLLISION_AT,
            project_scenarios_dir=PROJECT_SCENARIOS_DIR,
            model_run_id_scenario=MODEL_RUN_ID_SCENARIO,
            project=PROJECT
        )
        model_fatal_inj_fwy_non.correct_using_observed_factors(model_fatal_inj_base_year)
        
        logger.info("--------------------------------------")
        logger.info(model_fatal_inj_fwy_non)
        
        # Calculate fatalities and injuries by EPC/non-EPC
        model_fatal_inj_epc_non = modeled_fatalities_injuries(
            model_run_id, 
            FORECAST_YEAR, 
            network_df, 
            population_forecast,
            network_group_by_col="taz_epc", 
            network_no_project_df=network_no_project_df,
            collision_rates_df=collision_rates_df,
            collision_ft=COLLISION_FT,
            collision_at=COLLISION_AT,
            project_scenarios_dir=PROJECT_SCENARIOS_DIR,
            model_run_id_scenario=MODEL_RUN_ID_SCENARIO,
            project=PROJECT
        )
        model_fatal_inj_epc_non.correct_using_observed_factors(model_fatal_inj_base_year)
        
        logger.info("--------------------------------------")
        logger.info(model_fatal_inj_epc_non)
        
        # Calculate fatalities and injuries for local streets in EPCs
        model_fatal_inj_epc_local = modeled_fatalities_injuries(
            model_run_id, 
            FORECAST_YEAR, 
            network_df, 
            population_forecast,
            network_group_by_col="taz_epc_local", 
            network_no_project_df=network_no_project_df,
            collision_rates_df=collision_rates_df,
            collision_ft=COLLISION_FT,
            collision_at=COLLISION_AT,
            project_scenarios_dir=PROJECT_SCENARIOS_DIR,
            model_run_id_scenario=MODEL_RUN_ID_SCENARIO,
            project=PROJECT
        )
        model_fatal_inj_epc_local.correct_using_observed_factors(model_fatal_inj_base_year)
        
        logger.info("--------------------------------------")
        logger.info(model_fatal_inj_epc_local)
        
        # Calculate fatalities and injuries for local streets in non-EPCs
        model_fatal_inj_non_epc_local = modeled_fatalities_injuries(
            model_run_id, 
            FORECAST_YEAR, 
            network_df, 
            population_forecast,
            network_group_by_col="Non_EPC_local", 
            network_no_project_df=network_no_project_df,
            collision_rates_df=collision_rates_df,
            collision_ft=COLLISION_FT,
            collision_at=COLLISION_AT,
            project_scenarios_dir=PROJECT_SCENARIOS_DIR,
            model_run_id_scenario=MODEL_RUN_ID_SCENARIO,
            project=PROJECT
        )
        model_fatal_inj_non_epc_local.correct_using_observed_factors(model_fatal_inj_base_year)
        
        logger.info("--------------------------------------")
        logger.info(model_fatal_inj_non_epc_local)
        
        # Combine results into a single DataFrame
        # Add all links results
        df_all = model_fatal_inj.network_summary_df.copy()
        df_all['key'] = 'all'
        df_all['model_run_type'] = model_run_type
        df_all['model_run_id'] = model_run_id
        results_df = pd.concat([results_df, df_all], ignore_index=True)
        
        # Add freeway/non-freeway results
        df_fwy = model_fatal_inj_fwy_non.network_summary_df.copy()
        df_fwy = df_fwy.rename(columns={model_fatal_inj_fwy_non.network_group_by_col: 'key'})
        df_fwy['model_run_type'] = model_run_type
        df_fwy['model_run_id'] = model_run_id
        results_df = pd.concat([results_df, df_fwy], ignore_index=True)
        
        # Add EPC/non-EPC results
        df_epc = model_fatal_inj_epc_non.network_summary_df.copy()
        df_epc = df_epc.rename(columns={model_fatal_inj_epc_non.network_group_by_col: 'key'})
        df_epc['model_run_type'] = model_run_type
        df_epc['model_run_id'] = model_run_id
        results_df = pd.concat([results_df, df_epc], ignore_index=True)
        
        # Add local streets in EPC results
        df_epc_local = model_fatal_inj_epc_local.network_summary_df.copy()
        df_epc_local = df_epc_local.rename(columns={model_fatal_inj_epc_local.network_group_by_col: 'key'})
        df_epc_local['model_run_type'] = model_run_type
        df_epc_local['model_run_id'] = model_run_id
        results_df = pd.concat([results_df, df_epc_local], ignore_index=True)
        
        # Add local streets in non-EPC results
        df_non_epc_local = model_fatal_inj_non_epc_local.network_summary_df.copy()
        df_non_epc_local = df_non_epc_local.rename(columns={model_fatal_inj_non_epc_local.network_group_by_col: 'key'})
        df_non_epc_local['model_run_type'] = model_run_type
        df_non_epc_local['model_run_id'] = model_run_id
        results_df = pd.concat([results_df, df_non_epc_local], ignore_index=True)
        
        # If there's no scenario, we're done
        if MODEL_RUN_IDS["NO_PROJECT"] == MODEL_RUN_IDS["SCENARIO"]:
            break
            
        # Save no project for SCENARIO if this is the NO_PROJECT run
        if model_run_type == "NO_PROJECT":
            network_no_project_df = model_fatal_inj.model_network_df.copy()
    
    # Write results to CSV
    results_df.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Wrote {len(results_df)} rows to {OUTPUT_FILE}")
    logger.info(f"Wrote log to {LOG_FILE}")
    
    # Print results to console
    print(f"Wrote {len(results_df)} rows to {OUTPUT_FILE}")
    print(f"Wrote log to {LOG_FILE}")

if __name__ == "__main__":
    main() 