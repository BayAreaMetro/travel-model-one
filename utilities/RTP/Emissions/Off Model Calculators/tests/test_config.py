"""
Configuration file for testing off-model calculator functions locally.
Update these paths to point to your local test data files.
"""

import os

# Base directory for test data
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')

# Path to Variable_locations.csv file
# Update this to point to your local copy of the Variable_locations.csv file
VARIABLE_LOCATIONS_CSV = os.path.join(TEST_DATA_DIR, 'Variable_locations.csv')

# Example master workbook name (bike_share, car_share, etc.)
TEST_WORKBOOK_NAME = 'PBA50+_OffModel_Bikeshare'

# Example model run ID (format: YYYY_TMXXX_RunName)
TEST_MODEL_RUN_ID = '2035_TM160_IPA_16'

# Path to test Excel workbook
# For testing with actual file, you can also use the models directory:
# TEST_EXCEL_WORKBOOK = os.path.join(os.path.dirname(__file__), '..', 'models', f'{TEST_WORKBOOK_NAME}.xlsx')
TEST_EXCEL_WORKBOOK = os.path.join(TEST_DATA_DIR, f'{TEST_WORKBOOK_NAME}.xlsx')

# Create test_data directory if it doesn't exist
if not os.path.exists(TEST_DATA_DIR):
    os.makedirs(TEST_DATA_DIR)
    print(f"Created test data directory: {TEST_DATA_DIR}")
