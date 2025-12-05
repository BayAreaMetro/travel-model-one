"""
Quick script to verify Excel file has the Output_test tab with expected structure.
"""

import pandas as pd
import os

# Path to Excel file (relative to this script's location)
script_dir = os.path.dirname(os.path.abspath(__file__))
excel_file = os.path.join(script_dir, 'test_data', 'PBA50+_OffModel_Bikeshare.xlsx')

if not os.path.exists(excel_file):
    print(f"ERROR: File not found: {excel_file}")
else:
    print(f"Checking Excel file: {excel_file}\n")

    # Read Excel file to get sheet names
    xl = pd.ExcelFile(excel_file)
    print(f"Available sheets:")
    for i, sheet in enumerate(xl.sheet_names, 1):
        print(f"  {i}. {sheet}")

    # Check if Output_test exists
    if 'Output_test' in xl.sheet_names:
        print(f"\n✓ Output_test sheet found!")

        # Read Output_test tab
        df = pd.read_excel(excel_file, sheet_name='Output_test')

        print(f"\nOutput_test structure:")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {list(df.columns)}")

        print(f"\nFirst 15 rows:")
        print(df.head(15).to_string())

        # Check for year suffixes
        print(f"\nVariable names with year suffixes:")
        year_vars = df[df['Variable Name'].str.contains('_20', na=False)]
        if len(year_vars) > 0:
            unique_vars = year_vars['Variable Name'].unique()[:10]
            for var in unique_vars:
                print(f"  - {var}")
            print(f"  ... (showing first 10 of {len(year_vars)} variables)")
        else:
            print("  No variables with year suffixes found")

    else:
        print(f"\n✗ Output_test sheet NOT found!")
        print(f"Please add Output_test sheet to the Excel file.")
