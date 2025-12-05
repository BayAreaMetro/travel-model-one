"""
Test script to understand how get_variable_locations() works.
This script isolates and tests the get_variable_locations() function
without needing access to all production paths.
"""

import sys
import os
import pandas as pd

# Add parent directory to path to import helper modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import test_config

def test_get_variable_locations():
    """
    Mock version of get_variable_locations() from calcs.py
    This demonstrates how the function reads and processes Variable_locations.csv
    """

    print("=" * 80)
    print("Testing get_variable_locations() function")
    print("=" * 80)

    # Check if Variable_locations.csv exists
    if not os.path.exists(test_config.VARIABLE_LOCATIONS_CSV):
        print(f"\nERROR: Variable_locations.csv not found at:")
        print(f"  {test_config.VARIABLE_LOCATIONS_CSV}")
        print("\nPlease create a test_data folder and add your Variable_locations.csv file.")
        print(f"Expected location: {test_config.TEST_DATA_DIR}")
        return None

    print(f"\n1. Reading Variable_locations.csv from:")
    print(f"   {test_config.VARIABLE_LOCATIONS_CSV}")

    # Read the CSV file
    allVars = pd.read_csv(test_config.VARIABLE_LOCATIONS_CSV)

    print(f"\n2. Total variables in CSV: {len(allVars)}")
    print(f"   Columns: {list(allVars.columns)}")

    # Show sample of all data
    print(f"\n3. Sample of all variables (first 10 rows):")
    print(allVars.head(10).to_string())

    # Filter by workbook name
    masterWbName = test_config.TEST_WORKBOOK_NAME
    runs = test_config.TEST_MODEL_RUN_ID
    year = runs[:4]  # Extract year from run ID (e.g., "2035" from "2035_TM160_IPA_16")

    print(f"\n4. Filtering for workbook: '{masterWbName}'")
    print(f"   Model run: {runs}")
    print(f"   Year: {year}")

    calcVars = allVars.loc[allVars['Workbook'].isin([masterWbName])]

    print(f"\n5. Variables found for this workbook: {len(calcVars)}")

    if len(calcVars) == 0:
        print(f"\n   WARNING: No variables found for workbook '{masterWbName}'")
        print(f"   Available workbooks in CSV:")
        if 'Workbook' in allVars.columns:
            for wb in allVars['Workbook'].unique():
                print(f"     - {wb}")
        return None

    # Select relevant columns
    location_col = f'Location_{year}'

    print(f"\n6. Looking for location column: '{location_col}'")

    if location_col not in calcVars.columns:
        print(f"\n   WARNING: Column '{location_col}' not found!")
        print(f"   Available location columns:")
        location_cols = [col for col in calcVars.columns if col.startswith('Location_')]
        for col in location_cols:
            print(f"     - {col}")

        if location_cols:
            location_col = location_cols[0]
            print(f"\n   Using first available column: '{location_col}'")
        else:
            print("\n   No location columns found!")
            return None

    # Select and rename columns
    calcVars = calcVars[['Sheet', 'Variable Name', location_col]].copy()
    calcVars.rename(columns={location_col: 'Location'}, inplace=True)

    print(f"\n7. Processed variables (all rows):")
    print(calcVars.to_string())

    # Group by sheet
    groups = set(calcVars['Sheet'])
    print(f"\n8. Sheets found: {groups}")

    # Create dictionary structure
    v = {}
    for group in groups:
        v.setdefault(group, dict())
        group_vars = calcVars[calcVars['Sheet'] == group]
        v[group] = dict(zip(group_vars['Variable Name'], group_vars['Location']))

    print(f"\n9. Final dictionary structure (v):")
    print("-" * 80)
    for sheet, variables in v.items():
        print(f"\nSheet: '{sheet}'")
        for var_name, location in variables.items():
            print(f"  {var_name:30s} -> {location}")

    print("\n" + "=" * 80)
    print("Test completed successfully!")
    print("=" * 80)

    return v


def create_sample_csv():
    """
    Create a sample Variable_locations.csv file for testing.
    This shows the expected structure of the file.
    """
    sample_data = {
        'Workbook': [
            'PBA50+_OffModel_Bikeshare',
            'PBA50+_OffModel_Bikeshare',
            'PBA50+_OffModel_Bikeshare',
            'PBA50+_OffModel_Carshare',
            'PBA50+_OffModel_Carshare',
        ],
        'Sheet': [
            'Main Sheet',
            'Main Sheet',
            'Calculations',
            'Main Sheet',
            'Main Sheet',
        ],
        'Variable Name': [
            'Run_directory',
            'year',
            'total_trips',
            'Run_directory',
            'year',
        ],
        'Location_2035': [
            'B5',
            'B6',
            'C10',
            'B5',
            'B6',
        ],
        'Location_2050': [
            'B5',
            'B6',
            'C10',
            'B5',
            'B6',
        ]
    }

    df = pd.DataFrame(sample_data)
    sample_path = os.path.join(test_config.TEST_DATA_DIR, 'Variable_locations_SAMPLE.csv')
    df.to_csv(sample_path, index=False)

    print(f"\nSample Variable_locations.csv created at:")
    print(f"  {sample_path}")
    print("\nSample structure:")
    print(df.to_string())
    print(f"\nRename this file to 'Variable_locations.csv' to use it for testing.")


if __name__ == '__main__':
    print("\nOff-Model Calculator Variable Locations Test")
    print("=" * 80)
    print(f"Test configuration:")
    print(f"  Workbook: {test_config.TEST_WORKBOOK_NAME}")
    print(f"  Model Run: {test_config.TEST_MODEL_RUN_ID}")
    print(f"  CSV Path: {test_config.VARIABLE_LOCATIONS_CSV}")
    print("=" * 80)

    # Check if Variable_locations.csv exists
    if not os.path.exists(test_config.VARIABLE_LOCATIONS_CSV):
        print("\n[INFO] Variable_locations.csv not found. Creating sample file...")
        create_sample_csv()
        print("\n[ACTION REQUIRED]")
        print("1. Check the test_data folder")
        print("2. Either:")
        print("   a) Copy your actual Variable_locations.csv to test_data/, OR")
        print("   b) Rename Variable_locations_SAMPLE.csv to Variable_locations.csv")
        print("3. Update test_config.py with correct workbook name and run ID")
        print("4. Run this script again")
    else:
        # Run the test
        result = test_get_variable_locations()

        if result:
            print("\n[SUCCESS] Variable locations loaded successfully!")
            print("\nYou can now understand how the data flows:")
            print("1. CSV file contains mappings for all calculators")
            print("2. Filtered by workbook name (calculator type)")
            print("3. Organized by sheet name")
            print("4. Each variable maps to an Excel cell location")
            print("5. Used by write_runid_to_mainsheet() to write data to Excel")
