"""
Test script for the updated get_variable_locations() method.
This tests reading from Output_test tab in Excel instead of Variable_locations.csv.
"""

import sys
import os
import pandas as pd

# Add parent directory to path to import helper modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import test_config

def test_new_get_variable_locations():
    """
    Test the new get_variable_locations() logic that reads from Output_test tab.
    This simulates what the updated method does.
    """

    print("=" * 80)
    print("Testing NEW get_variable_locations() - Reading from Excel Output_test tab")
    print("=" * 80)

    excel_file = test_config.TEST_EXCEL_WORKBOOK
    runs = test_config.TEST_MODEL_RUN_ID

    # Check if Excel file exists
    if not os.path.exists(excel_file):
        print(f"\nERROR: Excel workbook not found at:")
        print(f"  {excel_file}")
        print("\nPlease update test_config.TEST_EXCEL_WORKBOOK with path to your Excel file.")
        return None

    print(f"\n1. Reading from Excel workbook:")
    print(f"   File: {excel_file}")
    print(f"   Sheet: Output_test")
    print(f"   Model Run: {runs}")

    # Get year from run ID (first 4 characters)
    year = runs[:4]
    print(f"   Year extracted: {year}")

    try:
        # Read Output_test tab from Excel
        allVars = pd.read_excel(excel_file, sheet_name='Output_test')
        print(f"\n2. Total rows in Output_test: {len(allVars)}")
        print(f"   Columns: {list(allVars.columns)}")

        # Show sample of all data
        print(f"\n3. Sample of Output_test (first 10 rows):")
        print(allVars.head(10).to_string())

        # Select relevant columns first
        allVars = allVars[['Sheet', 'Variable Name', 'Location']].copy()

        # Split variables into two groups:
        # 1. Variables with year suffix (e.g., variable_2035)
        # 2. Variables without year suffix (year-agnostic)

        year_suffix = f'_{year}'
        print(f"\n4. Processing variables:")
        print(f"   Year suffix to filter: '{year_suffix}'")

        # Get variables WITH year suffix for this specific year
        vars_with_year = allVars[allVars['Variable Name'].str.endswith(year_suffix)].copy()
        print(f"   Variables WITH year suffix ({year}): {len(vars_with_year)}")

        # Get variables WITHOUT any year suffix (year-agnostic)
        # A variable is year-agnostic if it doesn't end with _YYYY pattern
        vars_without_year = allVars[~allVars['Variable Name'].str.match(r'.*_\d{4}$')].copy()
        print(f"   Variables WITHOUT year suffix (year-agnostic): {len(vars_without_year)}")

        if len(vars_with_year) == 0 and len(vars_without_year) == 0:
            print(f"\n   WARNING: No variables found!")
            return None

        print(f"\n5. Variables WITH year suffix (before removing suffix):")
        print(vars_with_year.head(10).to_string())

        # Remove year suffix from year-specific variables
        vars_with_year['Variable Name'] = vars_with_year['Variable Name'].str.replace(year_suffix, '', regex=False)

        print(f"\n6. Variables WITHOUT year suffix (year-agnostic):")
        print(vars_without_year.to_string())

        # Combine both sets of variables
        calcVars = pd.concat([vars_with_year, vars_without_year], ignore_index=True)

        print(f"\n7. Combined variables (total: {len(calcVars)}):")
        print(calcVars.to_string())

        # Check for duplicates
        duplicates = calcVars[calcVars.duplicated(subset=['Sheet', 'Variable Name'], keep=False)]
        if len(duplicates) > 0:
            print(f"\n   ⚠ WARNING: Found {len(duplicates)} duplicate variable entries:")
            print(duplicates.sort_values(['Sheet', 'Variable Name']).to_string())
            print("\n   Removing duplicates (keeping first occurrence)...")
            calcVars = calcVars.drop_duplicates(subset=['Sheet', 'Variable Name'], keep='first')

        # Group by sheet
        groups = set(calcVars['Sheet'])
        print(f"\n8. Sheets found: {groups} (after deduplication)")

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
                print(f"  {var_name:40s} -> {location}")

        print("\n" + "=" * 80)
        print("Test completed successfully!")
        print("=" * 80)
        print("\nKey changes from CSV method:")
        print("  ✓ Reads from Excel Output_test tab (not external CSV)")
        print("  ✓ Filters by year suffix in variable name (not column name)")
        print("  ✓ Removes year suffix for clean variable names")
        print("  ✓ No dependency on external Variable_locations.csv file")

        return v

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def compare_csv_vs_excel():
    """
    Compare results from old CSV method vs new Excel method.
    """
    print("\n" + "=" * 80)
    print("COMPARISON: CSV method vs Excel method")
    print("=" * 80)

    # Test old method (CSV)
    csv_path = test_config.VARIABLE_LOCATIONS_CSV
    excel_path = test_config.TEST_EXCEL_WORKBOOK
    runs = test_config.TEST_MODEL_RUN_ID
    workbook_name = test_config.TEST_WORKBOOK_NAME
    year = runs[:4]

    csv_result = None
    excel_result = None

    # Try old CSV method
    if os.path.exists(csv_path):
        print("\n1. OLD METHOD (CSV):")
        print(f"   Reading from: {csv_path}")
        try:
            allVars = pd.read_csv(csv_path)
            calcVars = allVars.loc[allVars['Workbook'].isin([workbook_name])]
            location_col = f'Location_{year}'
            if location_col in calcVars.columns:
                calcVars = calcVars[['Sheet', 'Variable Name', location_col]].copy()
                calcVars.rename(columns={location_col: 'Location'}, inplace=True)

                csv_result = {}
                for sheet in set(calcVars['Sheet']):
                    sheet_vars = calcVars[calcVars['Sheet'] == sheet]
                    csv_result[sheet] = dict(zip(sheet_vars['Variable Name'], sheet_vars['Location']))

                print(f"   ✓ Found {len(calcVars)} variables")
            else:
                print(f"   ✗ Column '{location_col}' not found")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    else:
        print(f"\n1. OLD METHOD (CSV): Skipped (file not found)")

    # Try new Excel method
    if os.path.exists(excel_path):
        print("\n2. NEW METHOD (Excel):")
        print(f"   Reading from: {excel_path} -> Output_test")
        try:
            allVars = pd.read_excel(excel_path, sheet_name='Output_test')
            allVars = allVars[['Sheet', 'Variable Name', 'Location']].copy()

            year_suffix = f'_{year}'

            # Get variables WITH year suffix for this specific year
            vars_with_year = allVars[allVars['Variable Name'].str.endswith(year_suffix)].copy()
            vars_with_year['Variable Name'] = vars_with_year['Variable Name'].str.replace(year_suffix, '', regex=False)

            # Get variables WITHOUT any year suffix (year-agnostic)
            vars_without_year = allVars[~allVars['Variable Name'].str.match(r'.*_\d{4}$')].copy()

            # Combine both sets
            calcVars = pd.concat([vars_with_year, vars_without_year], ignore_index=True)

            # Remove duplicates (keep first occurrence)
            calcVars = calcVars.drop_duplicates(subset=['Sheet', 'Variable Name'], keep='first')

            excel_result = {}
            for sheet in set(calcVars['Sheet']):
                sheet_vars = calcVars[calcVars['Sheet'] == sheet]
                excel_result[sheet] = dict(zip(sheet_vars['Variable Name'], sheet_vars['Location']))

            print(f"   ✓ Found {len(calcVars)} unique variables ({len(vars_with_year)} with year, {len(vars_without_year)} year-agnostic)")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    else:
        print(f"\n2. NEW METHOD (Excel): Skipped (file not found)")

    # Compare
    if csv_result and excel_result:
        print("\n3. COMPARISON:")

        # Get all unique sheet names
        all_sheets = set(list(csv_result.keys()) + list(excel_result.keys()))

        for sheet_name in sorted(all_sheets):
            csv_vars = csv_result.get(sheet_name, {})
            excel_vars = excel_result.get(sheet_name, {})

            all_var_names = set(list(csv_vars.keys()) + list(excel_vars.keys()))

            print(f"\n   Sheet: '{sheet_name}'")
            print(f"   {'Variable Name':40s} {'CSV Location':15s} {'Excel Location':15s} {'Match':10s}")
            print(f"   {'-'*80}")

            for var_name in sorted(all_var_names):
                csv_loc = csv_vars.get(var_name, 'N/A')
                excel_loc = excel_vars.get(var_name, 'N/A')
                match = '✓' if csv_loc == excel_loc else '✗'
                print(f"   {var_name:40s} {csv_loc:15s} {excel_loc:15s} {match:10s}")

        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY:")
        total_matches = 0
        total_vars = 0
        for sheet_name in all_sheets:
            csv_vars = csv_result.get(sheet_name, {})
            excel_vars = excel_result.get(sheet_name, {})
            all_var_names = set(list(csv_vars.keys()) + list(excel_vars.keys()))

            for var_name in all_var_names:
                total_vars += 1
                if csv_vars.get(var_name) == excel_vars.get(var_name) and csv_vars.get(var_name) != None:
                    total_matches += 1

        print(f"Matching variables: {total_matches}/{total_vars}")
        print("=" * 80)


if __name__ == '__main__':
    print("\nUpdated get_variable_locations() Test")
    print("=" * 80)
    print(f"Test configuration:")
    print(f"  Workbook: {test_config.TEST_WORKBOOK_NAME}")
    print(f"  Model Run: {test_config.TEST_MODEL_RUN_ID}")
    print(f"  Excel Path: {test_config.TEST_EXCEL_WORKBOOK}")
    print("=" * 80)

    # Run main test
    result = test_new_get_variable_locations()

    # Run comparison if both files exist
    if os.path.exists(test_config.VARIABLE_LOCATIONS_CSV) and os.path.exists(test_config.TEST_EXCEL_WORKBOOK):
        print("\n")
        compare_csv_vs_excel()
