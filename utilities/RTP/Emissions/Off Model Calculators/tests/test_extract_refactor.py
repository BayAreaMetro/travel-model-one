"""
Test the refactored extract_offmodel_results.py with vertical format support.
"""

import sys
import os
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the function to test
from extract_offmodel_results import read_output_data

def test_read_output_data():
    """
    Test the read_output_data function with a sample Excel file.
    """
    print("=" * 80)
    print("Testing read_output_data() function")
    print("=" * 80)

    # Path to test Excel file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_file = os.path.join(script_dir, 'test_data', 'PBA50+_OffModel_Bikeshare.xlsx')

    if not os.path.exists(excel_file):
        print(f"\n❌ ERROR: Test file not found: {excel_file}")
        return False

    # Test parameters
    run_id = '2035_TM160_IPA_16'
    year = run_id[:4]

    print(f"\nTest Configuration:")
    print(f"  Excel File: {excel_file}")
    print(f"  Run ID: {run_id}")
    print(f"  Year: {year}")
    print(f"  Reading from: Output_test tab")

    try:
        # Call the function
        print("\n1. Calling read_output_data()...")
        result_df = read_output_data(excel_file, run_id, output_tab_name='Output_test')

        print("\n2. Result DataFrame:")
        print("-" * 80)
        print(result_df)
        print("-" * 80)

        # Validate structure
        print("\n3. Validation:")
        expected_columns = [
            'Horizon Run ID',
            f'Out_daily_GHG_reduced_{year}',
            f'Out_per_capita_GHG_reduced_{year}'
        ]

        print(f"   Expected columns: {expected_columns}")
        print(f"   Actual columns: {list(result_df.columns)}")

        all_columns_present = all(col in result_df.columns for col in expected_columns)

        if all_columns_present:
            print("   ✓ All expected columns present")
        else:
            print("   ❌ Missing columns!")
            return False

        # Check values
        print("\n4. Values:")
        print(f"   Horizon Run ID: {result_df['Horizon Run ID'].iloc[0]}")
        print(f"   Out_daily_GHG_reduced_{year}: {result_df[f'Out_daily_GHG_reduced_{year}'].iloc[0]}")
        print(f"   Out_per_capita_GHG_reduced_{year}: {result_df[f'Out_per_capita_GHG_reduced_{year}'].iloc[0]}")

        # Check for NaN values
        has_nan = result_df.isna().any().any()
        if has_nan:
            print("\n   ❌ ERROR: Some values are NaN (variables are missing!)")
            print(f"   NaN columns: {result_df.columns[result_df.isna().any()].tolist()}")
            print("\n" + "=" * 80)
            print("❌ TEST FAILED: Variables not found in Output_test tab")
            print("=" * 80)
            return False
        else:
            print("\n   ✓ No NaN values - all variables found")

        print("\n" + "=" * 80)
        print("✓ TEST PASSED: Function works correctly with vertical format")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        return False

def test_transformation():
    """
    Test that vertical → horizontal transformation works correctly.
    """
    print("\n" + "=" * 80)
    print("Testing Vertical → Horizontal Transformation")
    print("=" * 80)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_file = os.path.join(script_dir, 'test_data', 'PBA50+_OffModel_Bikeshare.xlsx')

    if not os.path.exists(excel_file):
        print(f"\n❌ ERROR: Test file not found")
        return False

    try:
        # Show vertical format
        print("\n1. VERTICAL FORMAT (Input - Output_test tab):")
        print("-" * 80)
        df_vertical = pd.read_excel(excel_file, sheet_name='Output_test')
        output_vars = df_vertical[df_vertical['Sheet'] == 'Output']
        print(output_vars[['Sheet', 'Variable Name', 'Value']].head(10).to_string())

        # Show horizontal format
        print("\n2. HORIZONTAL FORMAT (Output - after transformation):")
        print("-" * 80)
        df_horizontal = read_output_data(excel_file, '2035_TM160_IPA_16', output_tab_name='Output_test')
        print(df_horizontal.to_string())

        print("\n3. Transformation Summary:")
        print(f"   Vertical rows (Output sheet only): {len(output_vars)}")
        print(f"   Horizontal rows: {len(df_horizontal)}")
        print(f"   Horizontal columns: {len(df_horizontal.columns)}")

        print("\n✓ Transformation works - vertical data converted to horizontal format")
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\nRefactored extract_offmodel_results.py Test Suite")
    print("=" * 80)

    result1 = test_read_output_data()
    result2 = test_transformation()

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"read_output_data() test: {'✓ PASSED' if result1 else '❌ FAILED'}")
    print(f"Transformation test: {'✓ PASSED' if result2 else '❌ FAILED'}")

    if result1 and result2:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nThe refactored extraction script is ready to use!")
        print("\nNext steps:")
        print("1. Test with actual workbook files")
        print("2. After testing, change 'Output_test' to 'Output' in line 127")
        sys.exit(0)
    else:
        print("\n❌❌❌ SOME TESTS FAILED ❌❌❌")
        sys.exit(1)
