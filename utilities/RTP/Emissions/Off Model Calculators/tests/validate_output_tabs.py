"""
Validation script to compare Output tab (old horizontal format) vs Output_test tab (new vertical format).
Ensures no variables are lost in the transition.
"""

import pandas as pd
import os
import sys

def get_variables_from_output_tab(excel_file, year):
    """
    Extract variable names from old Output tab (horizontal format).
    Returns set of variable names.
    """
    try:
        # Read Output tab (skip first row which is usually headers)
        df = pd.read_excel(excel_file, sheet_name='Output', skiprows=1)

        # Get column names (these are the variables in horizontal format)
        variables = set(df.columns)

        # Filter for year-specific variables
        year_variables = {col for col in variables if str(year) in str(col)}

        return variables, year_variables
    except Exception as e:
        print(f"Error reading Output tab: {e}")
        return set(), set()

def get_variables_from_output_test_tab(excel_file, year):
    """
    Extract variable names from new Output_test tab (vertical format).
    Returns set of variable names.
    """
    try:
        # Read Output_test tab
        df = pd.read_excel(excel_file, sheet_name='Output_test')

        # Filter for Output sheet
        output_vars = df[df['Sheet'] == 'Output'].copy()

        # Get all variable names
        all_variables = set(output_vars['Variable Name'].dropna())

        # Get year-specific variables (ending with _YYYY)
        year_suffix = f'_{year}'
        year_variables = {var for var in all_variables if var.endswith(year_suffix)}

        # Get year-agnostic variables (not ending with _YYYY)
        agnostic_variables = {var for var in all_variables if not var[-5:].startswith('_') or not var[-4:].isdigit()}

        return all_variables, year_variables, agnostic_variables
    except Exception as e:
        print(f"Error reading Output_test tab: {e}")
        return set(), set(), set()

def compare_output_tabs(excel_file, year):
    """
    Compare Output and Output_test tabs to ensure no variables are lost.
    """
    print("=" * 80)
    print(f"Validating Output Tabs for Year {year}")
    print("=" * 80)
    print(f"File: {excel_file}\n")

    # Get variables from old Output tab
    print("1. Reading Output tab (horizontal format)...")
    output_all, output_year = get_variables_from_output_tab(excel_file, year)
    print(f"   Total columns: {len(output_all)}")
    print(f"   Year-specific variables ({year}): {len(output_year)}")

    # Get variables from new Output_test tab
    print("\n2. Reading Output_test tab (vertical format)...")
    test_all, test_year, test_agnostic = get_variables_from_output_test_tab(excel_file, year)
    print(f"   Total variables: {len(test_all)}")
    print(f"   Year-specific variables ({year}): {len(test_year)}")
    print(f"   Year-agnostic variables: {len(test_agnostic)}")

    # Remove year suffix from Output_test variables for comparison
    test_year_normalized = {var.replace(f'_{year}', '') for var in test_year}

    # Compare
    print("\n3. COMPARISON:")
    print("-" * 80)

    # Show Output tab variables
    print(f"\nOutput tab variables (year {year}):")
    for var in sorted(output_year):
        print(f"  - {var}")

    # Show Output_test tab year-specific variables (before normalization)
    print(f"\nOutput_test tab year-specific variables (year {year}):")
    for var in sorted(test_year):
        print(f"  - {var}")

    # Show Output_test tab year-agnostic variables
    if test_agnostic:
        print(f"\nOutput_test tab year-agnostic variables:")
        for var in sorted(test_agnostic):
            print(f"  - {var}")

    # Check for missing variables
    print("\n4. VALIDATION:")
    print("-" * 80)

    # Normalize Output tab variable names (remove year suffix if present)
    output_year_normalized = {var.replace(f'_{year}', '') for var in output_year if f'_{year}' in var}

    # Variables in Output but not in Output_test
    missing_in_test = output_year_normalized - test_year_normalized - test_agnostic

    # Variables in Output_test but not in Output
    new_in_test = test_year_normalized - output_year_normalized

    if missing_in_test:
        print(f"\n❌ MISSING VARIABLES in Output_test (present in Output):")
        for var in sorted(missing_in_test):
            print(f"  - {var}")
    else:
        print(f"\n✓ All Output tab variables are present in Output_test")

    if new_in_test:
        print(f"\n✓ NEW VARIABLES in Output_test (not in Output):")
        for var in sorted(new_in_test):
            print(f"  - {var}")

    # Summary
    print("\n5. SUMMARY:")
    print("=" * 80)
    print(f"Output tab variables:             {len(output_year_normalized)}")
    print(f"Output_test year-specific:        {len(test_year_normalized)}")
    print(f"Output_test year-agnostic:        {len(test_agnostic)}")
    print(f"Output_test total (normalized):   {len(test_year_normalized) + len(test_agnostic)}")
    print(f"Missing variables:                {len(missing_in_test)}")
    print(f"New variables:                    {len(new_in_test)}")

    if missing_in_test:
        print("\n❌ VALIDATION FAILED: Some variables are missing!")
        return False
    else:
        print("\n✓ VALIDATION PASSED: All variables accounted for!")
        return True

def validate_specific_extraction_variables(excel_file, year):
    """
    Validate that the specific variables needed by extract_offmodel_results.py are present.
    """
    print("\n" + "=" * 80)
    print("Validating Required Extraction Variables")
    print("=" * 80)

    required_vars = [
        f'Out_daily_GHG_reduced_{year}',
        f'Out_per_capita_GHG_reduced_{year}'
    ]

    try:
        df = pd.read_excel(excel_file, sheet_name='Output_test')
        output_vars = df[df['Sheet'] == 'Output']
        available_vars = set(output_vars['Variable Name'].dropna())

        print("\nRequired variables for extraction:")
        all_present = True
        for var in required_vars:
            if var in available_vars:
                print(f"  ✓ {var}")
            else:
                print(f"  ❌ {var} - MISSING!")
                all_present = False

        if all_present:
            print("\n✓ All required variables are present")
            return True
        else:
            print("\n❌ Some required variables are missing!")
            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == '__main__':
    # Path to test file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_file = os.path.join(script_dir, 'test_data', 'PBA50+_OffModel_Bikeshare.xlsx')

    if not os.path.exists(excel_file):
        print(f"ERROR: Excel file not found: {excel_file}")
        sys.exit(1)

    # Test for year 2035 (adjust as needed)
    year = '2035'

    # Run comparisons
    result1 = compare_output_tabs(excel_file, year)
    result2 = validate_specific_extraction_variables(excel_file, year)

    if result1 and result2:
        print("\n" + "=" * 80)
        print("✓✓✓ ALL VALIDATIONS PASSED ✓✓✓")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print("❌❌❌ VALIDATION FAILED ❌❌❌")
        print("=" * 80)
        sys.exit(1)
