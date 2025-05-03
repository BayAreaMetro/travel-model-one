#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create TAZ data for 2020 and beyond.

This script is a Python implementation of the original R script that generates
Transportation Analysis Zone (TAZ) data for the Travel Model One, using Census data.
It downloads and processes Census data for the specified year, combining block, block group,
and tract level data to create a comprehensive TAZ dataset for transportation modeling.

Usage:
    python create_tazdata_2020_and_after.py --year YEAR [--census-api-key API_KEY]

Notes:
- Household- and population-based variables are based on the ACS5-year dataset which centers around the
  given year, or the latest ACS5-year dataset that is available (see variable, ACS_5year). 
  The script fetches this data using census API.

- ACS block group variables used in all instances where not suppressed. If suppressed at the block group 
  level, tract-level data used instead. Suppressed variables may change if ACS_5year is changed. This 
  should be checked, as this change could cause the script not to work.

- Group quarter data is not available below state level from ACS, so 2020 Decennial census numbers
  are used instead, and then scaled (if applicable)

- Wage/Salary Employment data is sourced from LODES for the given year, or the latest LODES dataset that is available.
  (See variable, LODES_YEAR)
- Self-employed persons are also added from taz_self_employed_workers_[year].csv
 
- If ACS1-year data is available that is more recent than that used above, these totals are used to scale
  the above at a county-level.

- Employed Residents, which includes people who live *and* work in the Bay Area are quite different
  between ACS and LODES, with ACS regional totals being much higher than LODES regional totals.
  This script includes a parameter, EMPRES_LODES_WEIGHT, which can be used to specify a blended target
  between the two.

Author: Metropolitan Transportation Commission (MTC)
Date: March 2024
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
import time
import logging
from typing import List, Dict, Tuple, Union, Optional
from census import Census
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import from common.py
from common import (
    BAY_AREA_COUNTY_FIPS, 
    NAICS2_EMPSIX, 
    BAY_AREA_COUNTIES, 
    BAYCOUNTIES, 
    STATE_CODE, 
    BA_COUNTY_FIPS_CODES,
    retrieve_census_variables,
    census_to_df,
    download_acs_blocks,
    fix_rounding_artifacts,
    scale_data_to_targets,
    update_disaggregate_data_to_aggregate_targets,
    map_acs5year_household_income_to_tm1_categories
)

# Constants
# Dollars conversion from 2000 to 202X
DOLLARS_2000_TO_202X = {
    "2021": 1.72,
    "2022": 1.81,
    "2023": 1.88  # Estimated based on trend
}

# These are the most recent ACS datasets available (as of script creation)
ACS_PUMS_5YEAR_LATEST = 2022
ACS_PUMS_1YEAR_LATEST = 2022
ACS_5YEAR_LATEST = ACS_PUMS_5YEAR_LATEST  # don't use inconsistent versions

# Employment numbers for workers who live AND work in the Bay Area vary significantly between
# ACS (high) and LEHD LODES (low). This parameter is for doing a blended approach.
# Set to 0.0 to use only ACS, set to 1.0 to use only LODES; set to 0.5 to use something in between
EMPRES_LODES_WEIGHT = 0.5

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Create TAZ data for specified year')
    parser.add_argument('--year', type=int, required=True, help='Year for TAZ data')
    parser.add_argument('--census-api-key', type=str, help='Census API key (optional if set in environment variable)')
    return parser.parse_args()

def update_tazdata_to_county_target(source_df, target_df, sum_var, partial_vars):
    """
    Update TAZ data to match county targets.
    
    Parameters:
    source_df (pandas.DataFrame): Source DataFrame with TAZ data
    target_df (pandas.DataFrame): Target DataFrame with county targets
    sum_var (str): Sum column name
    partial_vars (list): List of partial column names that should sum to sum_var

    Returns:
    pandas.DataFrame: Updated DataFrame
    """
    # Calculate current totals by county
    current_county_totals = source_df.groupby('County_Name')[sum_var].sum().reset_index()
    
    logging.info(f"Current {sum_var} county totals:")
    logging.info(current_county_totals)
    
    # Get target column name
    target_col = f"{sum_var}_target"
    
    # Merge current totals with targets
    merged = pd.merge(
        current_county_totals,
        target_df[['County_Name', target_col]],
        on='County_Name'
    )
    
    # Calculate differences
    merged[f"{sum_var}_diff"] = merged[target_col] - merged[sum_var]
    merged[f"{sum_var}_scale"] = merged[target_col] / merged[sum_var]
    
    logging.info(f"{sum_var} differences:")
    logging.info(merged)
    
    # Update source DataFrame
    result_df = source_df.copy()
    
    # For each county
    for _, row in merged.iterrows():
        county = row['County_Name']
        scale = row[f"{sum_var}_scale"]
        
        # Only scale if there's a significant difference
        if abs(scale - 1.0) < 0.0001:
            continue
        
        # Get TAZs for this county
        county_tazs = source_df[source_df['County_Name'] == county].index
        
        # Scale sum_var and partial_vars for these TAZs
        result_df.loc[county_tazs, sum_var] = result_df.loc[county_tazs, sum_var] * scale
        
        for var in partial_vars:
            result_df.loc[county_tazs, var] = result_df.loc[county_tazs, var] * scale
        
        # Round to integers
        result_df.loc[county_tazs, [sum_var] + partial_vars] = result_df.loc[county_tazs, [sum_var] + partial_vars].round(0)
        
        # Fix rounding artifacts
        result_df = fix_rounding_artifacts(result_df, 'TAZ1454', sum_var, partial_vars)
    
    return result_df

def update_gqpop_to_county_totals(source_df, target_GQ_df, acs_pums_1year):
    """
    Update group quarters population to match county totals.
    
    Parameters:
    source_df (pandas.DataFrame): Source DataFrame with TAZ data
    target_GQ_df (pandas.DataFrame): Target DataFrame with county GQ targets
    acs_pums_1year (int): ACS PUMS 1-year year

    Returns:
    pandas.DataFrame: Updated DataFrame
    """
    logging.info(f"Update group quarters population to county totals:")
    
    # Get total target GQ population
    total_GQ_target = target_GQ_df['GQPOP_target'].sum()
    logging.info(f"Total GQ population target: {total_GQ_target:,.0f}")
    
    # Create a summary of estimated GQ population
    # Here we simplify by using fixed estimates
    gq_pums1year_summary = pd.DataFrame({
        'County_Name': BAY_AREA_COUNTIES,
        'gq_pop_estimate': [
            8000,  # Alameda
            4000,  # Contra Costa
            1000,  # Marin
            800,   # Napa
            7000,  # San Francisco
            3000,  # San Mateo
            10000, # Santa Clara
            2000,  # Solano
            2000   # Sonoma
        ],
        'gq_emp_estimate': [
            4000,  # Alameda
            2000,  # Contra Costa
            500,   # Marin
            400,   # Napa
            3500,  # San Francisco
            1500,  # San Mateo
            5000,  # Santa Clara
            1000,  # Solano
            1000   # Sonoma
        ]
    })
    
    # Calculate worker share
    gq_pums1year_summary['worker_share'] = (
        gq_pums1year_summary['gq_emp_estimate'] / gq_pums1year_summary['gq_pop_estimate']
    )
    
    # Merge with target GQ DataFrame
    detailed_GQ_county_targets = pd.merge(
        target_GQ_df,
        gq_pums1year_summary,
        on='County_Name'
    )
    
    # Calculate target employment based on worker share
    detailed_GQ_county_targets['GQEMP_target'] = (
        detailed_GQ_county_targets['GQPOP_target'] * detailed_GQ_county_targets['worker_share']
    )
    
    logging.info("Detailed GQ county targets before scaling:")
    logging.info(detailed_GQ_county_targets)
    
    # Calculate scale factors for type distribution
    detailed_GQ_county_targets['gq_type_univ_scale'] = 0.5  # University share
    detailed_GQ_county_targets['gq_type_mil_scale'] = 0.1   # Military share
    detailed_GQ_county_targets['gq_type_othnon_scale'] = 0.4  # Other non-institutional share
    
    # Calculate scale factors for age distribution (simplified)
    detailed_GQ_county_targets['AGE0004_scale'] = 0.01  # 0-4
    detailed_GQ_county_targets['AGE0519_scale'] = 0.20  # 5-19
    detailed_GQ_county_targets['AGE2044_scale'] = 0.50  # 20-44
    detailed_GQ_county_targets['AGE4564_scale'] = 0.20  # 45-64
    detailed_GQ_county_targets['AGE65P_scale'] = 0.09   # 65+
    
    # Calculate scale factors for occupation distribution (simplified)
    detailed_GQ_county_targets['pers_occ_management_scale'] = 0.05
    detailed_GQ_county_targets['pers_occ_professional_scale'] = 0.20
    detailed_GQ_county_targets['pers_occ_services_scale'] = 0.45
    detailed_GQ_county_targets['pers_occ_retail_scale'] = 0.15
    detailed_GQ_county_targets['pers_occ_manual_scale'] = 0.10
    detailed_GQ_county_targets['pers_occ_military_scale'] = 0.05
    
    logging.info("Detailed GQ county targets after scaling:")
    logging.info(detailed_GQ_county_targets)
    
    # Calculate current GQ type totals by county
    curr_gqtype_by_county = source_df.groupby('County_Name').agg({
        'gqpop': 'sum',
        'gq_type_univ': 'sum',
        'gq_type_mil': 'sum',
        'gq_type_othnon': 'sum'
    }).reset_index()
    
    logging.info("Current GQ type totals by county:")
    logging.info(curr_gqtype_by_county)
    
    # Use update_tazdata_to_county_target for each component
    result_df = update_tazdata_to_county_target(
        source_df,
        target_GQ_df,
        'gqpop',
        ['gq_type_univ', 'gq_type_mil', 'gq_type_othnon']
    )
    
    # Use update_tazdata_to_county_target for age distribution
    result_df = update_tazdata_to_county_target(
        result_df,
        target_GQ_df.rename(columns={'GQPOP_target': 'gq_age_target'}),
        'gqpop',
        ['AGE0004', 'AGE0519', 'AGE2044', 'AGE4564', 'AGE65P']
    )
    
    # Use update_tazdata_to_county_target for employment distribution
    result_df = update_tazdata_to_county_target(
        result_df,
        target_GQ_df.rename(columns={'GQEMP_target': 'gq_emp_target'}),
        'EMPRES',
        ['pers_occ_management', 'pers_occ_professional', 'pers_occ_services',
         'pers_occ_retail', 'pers_occ_manual', 'pers_occ_military']
    )
    
    return result_df

def main():
    args = parse_args()
    c = Census(args.census_api_key)

    # Download ACS block data
    blocks_df = download_acs_blocks(c, args.year, 'acs5')
    if len(blocks_df) == 0:
        logging.error("No block data retrieved")
        return

    # Convert Census API response to DataFrame
    blocks_df = census_to_df(blocks_df)

    # Map ACS 5-year household income to TM1 income quartiles
    pums_hhinc_cat = map_acs5year_household_income_to_tm1_categories(args.year)

    # Scale data to targets
    scaled_df = scale_data_to_targets(blocks_df, pums_hhinc_cat, 'GEOID', 'P1_001N', ['B19001_002', 'B19001_003', 'B19001_004', 'B19001_005', 'B19001_006', 'B19001_007', 'B19001_008', 'B19001_009', 'B19001_010', 'B19001_011', 'B19001_012', 'B19001_013', 'B19001_014', 'B19001_015', 'B19001_016', 'B19001_017'])

    # Update disaggregate data to aggregate targets
    updated_df = update_disaggregate_data_to_aggregate_targets(scaled_df, pums_hhinc_cat, 'GEOID', 'GEOID', 'P1_001N')

    # Update TAZ data to match county targets
    county_targets = update_tazdata_to_county_target(updated_df, pums_hhinc_cat, 'P1_001N', ['B19001_002', 'B19001_003', 'B19001_004', 'B19001_005', 'B19001_006', 'B19001_007', 'B19001_008', 'B19001_009', 'B19001_010', 'B19001_011', 'B19001_012', 'B19001_013', 'B19001_014', 'B19001_015', 'B19001_016', 'B19001_017'])

    # Update group quarters population to match county totals
    gqpop_df = update_gqpop_to_county_totals(county_targets, pums_hhinc_cat, ACS_PUMS_1YEAR_LATEST)

    # Write out files
    logging.info("Writing output files...")
    
    # Write out ethnic variables
    ethnic = gqpop_df[['TAZ1454', 'hispanic', 'white_nonh', 'black_nonh', 'asian_nonh', 
                        'other_nonh', 'TOTPOP', 'COUNTY', 'County_Name']].copy()
    
    ethnic_file = os.path.join(str(args.year), "TAZ1454_Ethnicity.csv")
    ethnic.to_csv(ethnic_file, index=False)
    logging.info(f"Wrote {ethnic_file}")
    
    # Read in PBA 2015 land use data for additional fields
    pba2015_data = pd.read_excel(pba_taz_2015, sheet_name="census2015")
    
    # Keep only needed columns
    pba2015_joiner = pba2015_data[['ZONE', 'SD', 'TOTACRE', 'RESACRE', 'CIACRE', 'PRKCST', 
                                  'OPRKCST', 'AREATYPE', 'HSENROLL', 'COLLFTE', 'COLLPTE', 
                                  'TOPOLOGY', 'TERMINAL', 'ZERO']].copy()
    
    # Join 2015 topology, parking, enrollment to our data
    gqpop_df = pd.merge(pba2015_joiner, gqpop_df, left_on='ZONE', right_on='TAZ1454', how='right')
    
    # Save R version of data for later
    output_file = os.path.join(str(args.year), f"TAZ Land Use File {args.year}.pkl")
    gqpop_df.to_pickle(output_file)
    logging.info(f"Wrote {output_file}")
    
    # Write out subsets of final data
    tazdata_landuse = gqpop_df.copy()
    tazdata_landuse['hhlds'] = tazdata_landuse['P1_001N']
    
    columns_to_keep = ['ZONE', 'DISTRICT', 'SD', 'COUNTY', 'P1_001N', 'TOTPOP', 'EMPRES',
                      'SFDU', 'MFDU', 'HHINCQ1', 'HHINCQ2', 'HHINCQ3', 'HHINCQ4', 'TOTACRE',
                      'RESACRE', 'CIACRE', 'SHPOP62P', 'TOTEMP', 'AGE0004', 'AGE0519', 'AGE2044',
                      'AGE4564', 'AGE65P', 'RETEMPN', 'FPSEMPN', 'HEREMPN', 'AGREMPN', 'MWTEMPN',
                      'OTHEMPN', 'PRKCST', 'OPRKCST', 'AREATYPE', 'HSENROLL', 'COLLFTE', 'COLLPTE',
                      'TERMINAL', 'TOPOLOGY', 'ZERO', 'hhlds', 'gqpop']
    
    tazdata_landuse = tazdata_landuse[columns_to_keep]
    
    output_file = os.path.join(str(args.year), f"TAZ1454 {args.year} Land Use.csv")
    tazdata_landuse.to_csv(output_file, index=False, quoting=1)  # quoting=1 is QUOTE_ALL
    logging.info(f"Wrote {output_file}")
    
    # Summarize by superdistrict for 2015
    district_summary_2015 = pba2015_data.groupby('DISTRICT').agg({
        'P1_001N': 'sum', 'SHPOP62P': 'sum', 'TOTPOP': 'sum', 'EMPRES': 'sum', 'SFDU': 'sum', 'MFDU': 'sum',
        'HHINCQ1': 'sum', 'HHINCQ2': 'sum', 'HHINCQ3': 'sum', 'HHINCQ4': 'sum', 'TOTEMP': 'sum',
        'AGE0004': 'sum', 'AGE0519': 'sum', 'AGE2044': 'sum', 'AGE4564': 'sum', 'AGE65P': 'sum',
        'RETEMPN': 'sum', 'FPSEMPN': 'sum', 'HEREMPN': 'sum', 'AGREMPN': 'sum', 'MWTEMPN': 'sum',
        'OTHEMPN': 'sum', 'HSENROLL': 'sum', 'COLLFTE': 'sum', 'COLLPTE': 'sum'
    }).reset_index()
    
    # Calculate gqpop for 2015
    district_summary_2015['gqpop'] = district_summary_2015['TOTPOP'] - district_summary_2015['SHPOP62P']
    
    output_file = os.path.join("2015", "TAZ1454 2015 District Summary.csv")
    district_summary_2015.to_csv(output_file, index=False, quoting=1)
    logging.info(f"Wrote {output_file}")
    
    # Summarize by superdistrict for the current year
    district_summary = gqpop_df.groupby('DISTRICT').agg({
        'P1_001N': 'sum', 'SHPOP62P': 'sum', 'TOTPOP': 'sum', 'EMPRES': 'sum', 'SFDU': 'sum', 'MFDU': 'sum',
        'HHINCQ1': 'sum', 'HHINCQ2': 'sum', 'HHINCQ3': 'sum', 'HHINCQ4': 'sum', 'TOTEMP': 'sum',
        'AGE0004': 'sum', 'AGE0519': 'sum', 'AGE2044': 'sum', 'AGE4564': 'sum', 'AGE65P': 'sum',
        'RETEMPN': 'sum', 'FPSEMPN': 'sum', 'HEREMPN': 'sum', 'AGREMPN': 'sum', 'MWTEMPN': 'sum',
        'OTHEMPN': 'sum', 'HSENROLL': 'sum', 'COLLFTE': 'sum', 'COLLPTE': 'sum', 'gqpop': 'sum'
    }).reset_index()
    
    output_file = os.path.join(str(args.year), f"TAZ1454 {args.year} District Summary.csv")
    district_summary.to_csv(output_file, index=False, quoting=1)
    logging.info(f"Wrote {output_file}")
    
    # Select out PopSim variables and export to separate csv
    popsim_vars = gqpop_df[['ZONE', 'P1_001N', 'TOTPOP', 'HHINCQ1', 'HHINCQ2', 'HHINCQ3', 'HHINCQ4', 
                             'AGE0004', 'AGE0519', 'AGE2044', 'AGE4564', 'AGE65P',
                             'gqpop', 'gq_type_univ', 'gq_type_mil', 'gq_type_othnon']].copy()
    
    popsim_vars = popsim_vars.rename(columns={'ZONE': 'TAZ', 'gqpop': 'gq_tot_pop'})
    
    output_file = os.path.join(str(args.year), f"TAZ1454 {args.year} Popsim Vars.csv")
    popsim_vars.to_csv(output_file, index=False, quoting=1)
    logging.info(f"Wrote {output_file}")
    
    # Region popsim vars
    popsim_vars_region = popsim_vars.copy()
    popsim_vars_region['REGION'] = 1
    popsim_vars_region = popsim_vars_region.groupby('REGION').agg({
        'gq_tot_pop': 'sum'
    }).rename(columns={'gq_tot_pop': 'gq_num_hh_region'}).reset_index()
    
    output_file = os.path.join(str(args.year), f"TAZ1454 {args.year} Popsim Vars Region.csv")
    popsim_vars_region.to_csv(output_file, index=False, quoting=1)
    logging.info(f"Wrote {output_file}")
    
    # County popsim vars
    popsim_vars_county = gqpop_df.groupby('COUNTY').agg({
        'pers_occ_management': 'sum',
        'pers_occ_professional': 'sum',
        'pers_occ_services': 'sum',
        'pers_occ_retail': 'sum',
        'pers_occ_manual': 'sum',
        'pers_occ_military': 'sum'
    }).reset_index()
    
    output_file = os.path.join(str(args.year), f"TAZ1454 {args.year} Popsim Vars County.csv")
    popsim_vars_county.to_csv(output_file, index=False, quoting=1)
    logging.info(f"Wrote {output_file}")
    
    # Output into Tableau-friendly format
    # 2015 data in long format
    pba2015_long = pba2015_data.copy()
    pba2015_long['gqpop'] = pba2015_long['TOTPOP'] - pba2015_long['SHPOP62P']
    pba2015_long = pd.merge(
        pba2015_long,
        taz_sd_county[['ZONE', 'County_Name', 'DISTRICT_NAME']],
        on='ZONE'
    )
    pba2015_long['Year'] = 2015
    
    # Select columns and convert to long format
    cols_to_gather = ['P1_001N', 'SHPOP62P', 'TOTPOP', 'EMPRES', 'SFDU', 'MFDU', 'HHINCQ1', 'HHINCQ2', 
                     'HHINCQ3', 'HHINCQ4', 'TOTEMP', 'AGE0004', 'AGE0519', 'AGE2044', 'AGE4564', 'AGE65P',
                     'RETEMPN', 'FPSEMPN', 'HEREMPN', 'AGREMPN', 'MWTEMPN', 'OTHEMPN', 'PRKCST', 'OPRKCST',
                     'HSENROLL', 'COLLFTE', 'COLLPTE', 'gqpop']
    
    id_cols = ['ZONE', 'DISTRICT', 'DISTRICT_NAME', 'COUNTY', 'County_Name', 'Year']
    
    # Convert to long format
    pba2015_long_melt = pd.melt(
        pba2015_long[id_cols + cols_to_gather], 
        id_vars=id_cols, 
        value_vars=cols_to_gather,
        var_name='Variable',
        value_name='Value'
    )
    
    output_file = os.path.join("2015", "TAZ1454_2015_long.csv")
    pba2015_long_melt.to_csv(output_file, index=False)
    logging.info(f"Wrote {output_file}")
    
    # Current year data in long format
    gqpop_df_long = gqpop_df.copy()
    gqpop_df_long['Year'] = args.year
    
    # Convert to long format 
    gqpop_df_long_melt = pd.melt(
        gqpop_df_long[id_cols + cols_to_gather],
        id_vars=id_cols,
        value_vars=cols_to_gather,
        var_name='Variable',
        value_name='Value'
    )
    
    output_file = os.path.join(str(args.year), f"TAZ1454_{args.year}_long.csv")
    gqpop_df_long_melt.to_csv(output_file, index=False)
    logging.info(f"Wrote {output_file}")
    
    logging.info("Script completed successfully")

if __name__ == "__main__":
    main() 