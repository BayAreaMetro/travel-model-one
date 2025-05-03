#
# common.py - Common utilities and functions for Travel Model One scripts
#
# This file contains common mappings, constants, and utility functions that are 
# used across multiple scripts in the Travel Model One codebase. By centralizing
# these functions, we ensure consistency and reduce code duplication.
#
# Key components:
# - Geography mappings (counties, FIPS codes)
# - Census API functions for data retrieval
# - Data manipulation utilities (rounding, scaling)
# - Input/output helpers
#
# Usage:
# Import specific functions or constants from this file as needed:
#
# from common import BAY_AREA_COUNTY_FIPS, census_to_df, fix_rounding_artifacts
#
# Author: Metropolitan Transportation Commission (MTC)
# Date: March 2024
#

import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Union, Optional

BAY_AREA_COUNTY_FIPS = {
    "06001": "Alameda",
    "06013": "Contra Costa",
    "06041": "Marin",
    "06055": "Napa",
    "06075": "San Francisco",
    "06081": "San Mateo",
    "06085": "Santa Clara",
    "06095": "Solano",
    "06097": "Sonoma"
}

# from petrale\applications\travel_model_lu_inputs\2015\Employment\NAICS_to_EMPSIX.xlsx, abag-6 worksheet
# column names are from https://github.com/BayAreaMetro/modeling-website/wiki/TazData
NAICS2_EMPSIX = {
    'NAICS 11':     'AGREMPN',
    'NAICS 21':     'AGREMPN',
    'NAICS 22':     'MWTEMPN',
    'NAICS 23':     'OTHEMPN',
    'NAICS 31-33':  'MWTEMPN',
    'NAICS 42':     'MWTEMPN',
    'NAICS 44-45':  'RETEMPN',
    'NAICS 48-49':  'MWTEMPN',
    'NAICS 51':     'OTHEMPN',
    'NAICS 52':     'FPSEMPN',
    'NAICS 53':     'FPSEMPN',
    'NAICS 54':     'FPSEMPN',
    'NAICS 55':     'FPSEMPN',
    'NAICS 56':     'FPSEMPN',
    'NAICS 61':     'HEREMPN',
    'NAICS 62':     'HEREMPN',
    'NAICS 71':     'HEREMPN',
    'NAICS 72':     'HEREMPN',
    'NAICS 81':     'HEREMPN',
    'NAICS 92':     'OTHEMPN',
}

# Bay Area counties
BAY_AREA_COUNTIES = [
    "Alameda",
    "Contra Costa", 
    "Marin",
    "Napa",
    "San Francisco",
    "San Mateo",
    "Santa Clara",
    "Solano",
    "Sonoma"
]

# Bay Area county FIPS codes
BAYCOUNTIES = ["001", "013", "041", "055", "075", "081", "085", "095", "097"]
STATE_CODE = "06"

# Bay Area county FIPS codes with state code
BA_COUNTY_FIPS_CODES = {
    '001': '06',  # Alameda County
    '013': '06',  # Contra Costa County
    '041': '06',  # Marin County
    '055': '06',  # Napa County
    '075': '06',  # San Francisco County
    '081': '06',  # San Mateo County
    '085': '06',  # Santa Clara County
    '095': '06',  # Solano County
    '097': '06'   # Sonoma County
}

def retrieve_census_variables(c, year, dataset, variables, for_geo='block', in_geo=None, for_geo_id=None, state=None, county=None):
    """
    Retrieve data from Census API.
    
    Parameters:
    c (Census): Census API client
    year (str): Year for which to retrieve data
    dataset (str): Census dataset to query (e.g., 'acs5', 'dec/pl')
    variables (list): List of variables to retrieve
    for_geo (str): Geography level to retrieve data for (e.g., 'block', 'block group', 'tract')
    in_geo (str): Geography level to filter by (e.g., 'state', 'county')
    for_geo_id (str): ID for the for_geo level
    state (str): State FIPS code
    county (str): County FIPS code
    
    Returns:
    list: List of dictionaries containing the requested data
    """
    # Construct geo dictionary
    geo = {}
    
    if for_geo:
        geo['for'] = f"{for_geo}:*"
    
    if for_geo_id:
        geo['for'] = f"{for_geo}:{for_geo_id}"
    
    if in_geo:
        geo['in'] = f"{in_geo}:*"
    
    if state:
        geo['in'] = f"state:{state}"
    
    if county:
        if 'in' in geo:
            geo['in'] += f" county:{county}"
        else:
            geo['in'] = f"county:{county}"
    
    # Make API call
    try:
        logging.info(f"Retrieving Census data for {year} {dataset} with variables {variables} and geo {geo}")
        response = c.get(dataset, year, variables, geo=geo)
        logging.info(f"Retrieved {len(response)} records")
        return response
    except Exception as e:
        logging.error(f"Error retrieving Census data: {e}")
        return []

def census_to_df(response, geo_col='GEOID'):
    """
    Convert Census API response to pandas DataFrame.
    
    Parameters:
    response (list): List of dictionaries from Census API
    geo_col (str): Name of the column to use for geography ID
    
    Returns:
    pandas.DataFrame: DataFrame with Census data
    """
    if not response:
        return pd.DataFrame()
    
    df = pd.DataFrame(response)
    
    # Remove the 'E' suffix from column names (indicates estimate)
    rename_cols = {}
    for col in df.columns:
        if col.endswith('E'):
            rename_cols[col] = col[:-1]
    
    df = df.rename(columns=rename_cols)
    
    # Convert numeric columns to numeric
    for col in df.columns:
        if col not in ['NAME', 'state', 'county', 'tract', 'block', 'block group']:
            try:
                df[col] = pd.to_numeric(df[col])
            except:
                pass
    
    return df

def download_acs_blocks(c, year, dataset, states=None, counties=None):
    """
    Download block data from ACS. We're only interested in population.
    
    Parameters:
    c (Census): Census API client
    year (str): Year for which to retrieve data
    dataset (str): Census dataset to query (e.g., 'acs5', 'dec/pl')
    states (list): List of state FIPS codes
    counties (list): List of county FIPS codes
    
    Returns:
    pandas.DataFrame: DataFrame with block data
    """
    if states is None:
        states = list(set(BA_COUNTY_FIPS_CODES.values()))
    
    all_blocks = []
    
    for state in states:
        if counties is None:
            # Use counties from BA_COUNTY_FIPS_CODES if state matches
            state_counties = [county for county, state_county in BA_COUNTY_FIPS_CODES.items() if state_county == state]
        else:
            state_counties = counties
        
        for county in state_counties:
            blocks = retrieve_census_variables(
                c, 
                year, 
                dataset, 
                ['P1_001N'],  # Total population
                for_geo='block',
                state=state,
                county=county
            )
            all_blocks.extend(blocks)
    
    blocks_df = pd.DataFrame(all_blocks)
    
    # Return early if no data
    if len(blocks_df) == 0:
        logging.warning("No block data retrieved")
        return pd.DataFrame()
    
    return blocks_df

def fix_rounding_artifacts(df, id_var, sum_var, partial_vars, logging_on=True):
    """
    Fix rounding artifacts by adjusting partial variable values to match the sum variable.
    
    Parameters:
    df (pandas.DataFrame): DataFrame to fix
    id_var (str): ID column name
    sum_var (str): Sum column name
    partial_vars (list): List of partial column names that should sum to sum_var
    logging_on (bool): Whether to log the process

    Returns:
    pandas.DataFrame: DataFrame with fixed rounding artifacts
    """
    # Make a copy to avoid modifying the original DataFrame
    df_copy = df.copy()
    
    # For each row in the DataFrame
    for idx, row in df_copy.iterrows():
        # Calculate the sum of partial variables
        partial_sum = sum(row[var] for var in partial_vars)
        
        # Get the target sum
        target_sum = row[sum_var]
        
        # Check if there's a discrepancy
        discrepancy = target_sum - partial_sum
        
        if discrepancy != 0:
            if logging_on:
                logging.info(f"Fixing rounding artifact for {id_var}={row[id_var]}: " +
                           f"{sum_var}={target_sum} but partial sum={partial_sum} " +
                           f"(discrepancy={discrepancy})")
            
            # Handle the discrepancy
            if abs(discrepancy) <= len(partial_vars):
                # Small discrepancy, distribute one unit to each partial variable
                adjust_vars = []
                
                # For positive discrepancy, add to largest values
                if discrepancy > 0:
                    # Sort partial variables by value, largest first
                    sorted_vars = sorted(partial_vars, key=lambda x: row[x], reverse=True)
                    adjust_vars = sorted_vars[:int(discrepancy)]
                    
                    # Add one to each variable
                    for var in adjust_vars:
                        df_copy.at[idx, var] += 1
                        
                # For negative discrepancy, subtract from smallest values
                else:
                    # Sort partial variables by value, smallest first
                    sorted_vars = sorted(partial_vars, key=lambda x: row[x])
                    # Ignore variables that are already 0
                    positive_vars = [var for var in sorted_vars if row[var] > 0]
                    # Take abs(discrepancy) variables from the smallest
                    adjust_vars = positive_vars[:abs(int(discrepancy))]
                    
                    # Subtract one from each variable
                    for var in adjust_vars:
                        df_copy.at[idx, var] -= 1
            else:
                # Large discrepancy, distribute proportionally
                # Calculate proportions
                if partial_sum > 0:
                    proportions = {var: row[var] / partial_sum for var in partial_vars}
                else:
                    # If partial_sum is 0, distribute equally
                    proportions = {var: 1.0 / len(partial_vars) for var in partial_vars}
                
                # Distribute the discrepancy proportionally
                remaining = discrepancy
                for var in partial_vars:
                    if var == partial_vars[-1]:
                        # Last variable gets the remainder
                        adjustment = remaining
                    else:
                        # Calculate proportional adjustment
                        adjustment = int(discrepancy * proportions[var])
                        remaining -= adjustment
                    
                    # Apply the adjustment
                    df_copy.at[idx, var] += adjustment
    
    return df_copy

def scale_data_to_targets(source_df, target_df, id_var, sum_var, partial_vars, logging_on=False):
    """
    Scale data in source_df to match targets in target_df.
    
    Parameters:
    source_df (pandas.DataFrame): Source DataFrame to scale
    target_df (pandas.DataFrame): Target DataFrame with target values
    id_var (str): ID column name
    sum_var (str): Sum column name
    partial_vars (list): List of partial column names that should sum to sum_var
    logging_on (bool): Whether to log the process

    Returns:
    pandas.DataFrame: DataFrame with scaled values
    """
    # Make a copy to avoid modifying the original DataFrame
    result_df = source_df.copy()
    
    # Get target column name
    target_col = f"{sum_var}_target"
    
    # Merge target values
    merged = pd.merge(source_df[[id_var, sum_var] + partial_vars], 
                     target_df[[id_var, target_col]], 
                     on=id_var)
    
    # For each row in the merged DataFrame
    for idx, row in merged.iterrows():
        # Get source row index
        source_idx = source_df[source_df[id_var] == row[id_var]].index[0]
        
        # Calculate scaling factor
        source_sum = row[sum_var]
        target_sum = row[target_col]
        
        if source_sum > 0:
            scale_factor = target_sum / source_sum
        else:
            # If source sum is 0, no scaling needed or possible
            continue
        
        if logging_on:
            logging.info(f"Scaling {id_var}={row[id_var]}: {sum_var}={source_sum} " +
                       f"to {target_col}={target_sum} (factor={scale_factor:.4f})")
        
        # Update the sum variable
        result_df.at[source_idx, sum_var] = target_sum
        
        # Update partial variables
        for var in partial_vars:
            result_df.at[source_idx, var] = round(row[var] * scale_factor)
    
    # Fix any rounding artifacts
    result_df = fix_rounding_artifacts(result_df, id_var, sum_var, partial_vars, logging_on)
    
    return result_df

def update_disaggregate_data_to_aggregate_targets(source_df, target_df, disagg_id_var, agg_id_var, col_name):
    """
    Update disaggregate data to match aggregate targets.
    
    Parameters:
    source_df (pandas.DataFrame): Source DataFrame with disaggregate data
    target_df (pandas.DataFrame): Target DataFrame with aggregate targets
    disagg_id_var (str): ID column name for disaggregate data
    agg_id_var (str): ID column name for aggregate data
    col_name (str): Column name to update

    Returns:
    pandas.DataFrame: Updated DataFrame
    """
    # Make a copy to avoid modifying the original DataFrame
    result_df = source_df.copy()
    
    # Calculate current totals by aggregate ID
    current_totals = source_df.groupby(agg_id_var)[col_name].sum().reset_index()
    
    # Merge current totals with targets
    diff_df = pd.merge(
        current_totals,
        target_df[[agg_id_var, f"{col_name}_target"]],
        on=agg_id_var
    )
    
    # Calculate differences
    diff_df[f"{col_name}_diff"] = diff_df[f"{col_name}_target"] - diff_df[col_name]
    
    # For each aggregate unit with a non-zero difference
    for _, row in diff_df[diff_df[f"{col_name}_diff"] != 0].iterrows():
        agg_id = row[agg_id_var]
        difference = row[f"{col_name}_diff"]
        
        # Get disaggregate units for this aggregate ID
        disagg_units = source_df[source_df[agg_id_var] == agg_id]
        
        # If no disaggregate units, skip
        if len(disagg_units) == 0:
            continue
        
        # Distribute the difference proportionally
        current_total = row[col_name]
        
        if current_total > 0:
            # Distribute based on current proportions
            for idx, unit_row in disagg_units.iterrows():
                proportion = unit_row[col_name] / current_total
                adjustment = round(difference * proportion)
                result_df.at[idx, col_name] += adjustment
        else:
            # If current total is 0, distribute equally
            equal_adjustment = difference / len(disagg_units)
            for idx in disagg_units.index:
                result_df.at[idx, col_name] += equal_adjustment
    
    return result_df

def map_acs5year_household_income_to_tm1_categories(acs_year):
    """
    Map ACS 5-year household income ranges to TM1 income quartiles.
    
    Parameters:
    acs_year (int): ACS year
    
    Returns:
    pandas.DataFrame: DataFrame mapping ACS income ranges to TM1 quartiles
    """
    # These are based on percentiles in the ACS data
    # For simplicity we're using fixed mappings, but these could be derived from data
    logging.info(f"Mapping ACS {acs_year} household income to TM1 categories")
    
    # Mapping of ACS income ranges to TM1 quartiles with sharing percentages
    income_mapping = [
        # incrange, HHINCQ (1-4), share
        ("B19001_002", 1, 1.0),  # Less than $10,000
        ("B19001_003", 1, 1.0),  # $10,000 to $14,999
        ("B19001_004", 1, 1.0),  # $15,000 to $19,999
        ("B19001_005", 1, 1.0),  # $20,000 to $24,999
        ("B19001_006", 1, 0.7),  # $25,000 to $29,999
        ("B19001_007", 1, 0.3),  # $30,000 to $34,999
        ("B19001_007", 2, 0.7),  # $30,000 to $34,999
        ("B19001_008", 2, 1.0),  # $35,000 to $39,999
        ("B19001_009", 2, 1.0),  # $40,000 to $44,999
        ("B19001_010", 2, 1.0),  # $45,000 to $49,999
        ("B19001_011", 2, 0.8),  # $50,000 to $59,999
        ("B19001_011", 3, 0.2),  # $50,000 to $59,999
        ("B19001_012", 3, 1.0),  # $60,000 to $74,999
        ("B19001_013", 3, 1.0),  # $75,000 to $99,999
        ("B19001_014", 3, 0.2),  # $100,000 to $124,999
        ("B19001_014", 4, 0.8),  # $100,000 to $124,999
        ("B19001_015", 4, 1.0),  # $125,000 to $149,999
        ("B19001_016", 4, 1.0),  # $150,000 to $199,999
        ("B19001_017", 4, 1.0)   # $200,000 or more
    ]
    
    # Create DataFrame
    pums_hhinc_cat = pd.DataFrame(income_mapping, columns=['incrange', 'HHINCQ', 'share'])
    
    logging.info(f"Income mapping: {pums_hhinc_cat.groupby('HHINCQ')['share'].sum()}")
    
    return pums_hhinc_cat