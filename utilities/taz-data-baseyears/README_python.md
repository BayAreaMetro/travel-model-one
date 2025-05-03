# TAZ Data Generation for Travel Model One

This repository contains scripts to generate Transportation Analysis Zone (TAZ) data for the Travel Model One, using Census data and other sources.

## Python Implementation

The `create_tazdata_2020_and_after.py` script is a Python implementation of the original R script (`create_tazdata_2020_and_after.R`). It processes Census data to generate TAZ-level demographic and employment data for transportation modeling.

### Code Organization

The implementation is organized into two main files:

1. **common.py** - Contains common utility functions, constants, and mappings that can be reused across multiple scripts. This includes:
   - Census data retrieval and processing functions
   - Data transformation functions
   - Bay Area county mappings and constants
   - Utility functions for data handling

2. **create_tazdata_2020_and_after.py** - The main script that implements the TAZ data generation workflow. It imports common functions from `common.py` and implements the specific logic for TAZ data generation.

This structure enables better code reuse and makes the codebase more maintainable.

### Prerequisites

- Python 3.8+
- Required Python packages:
  - pandas
  - numpy
  - requests
  - census
  - argparse
  - logging

You can install the required packages using:

```bash
pip install pandas numpy requests census argparse logging
```

### Usage

```bash
python create_tazdata_2020_and_after.py --year YEAR [--census-api-key API_KEY]
```

Where:
- `YEAR` is the target year for which to generate TAZ data (e.g., 2020, 2021, etc.)
- `API_KEY` is your Census API key (optional if you have it set in the CENSUS_API_KEY environment variable)

Example:
```bash
python create_tazdata_2020_and_after.py --year 2020 --census-api-key YOUR_API_KEY
```

### Script Features

The script performs the following operations:

1. Processes employment data:
   - Loads self-employment data from PUMS
   - Merges with LEHD LODES data
   - Adjusts and scales employment data

2. Loads Census data:
   - Downloads ACS block, block group, and tract data
   - Processes DHC data for group quarters
   - Joins datasets for comprehensive analysis

3. Creates a working dataset with:
   - Demographic variables (age, race/ethnicity, etc.)
   - Housing variables (units by type, tenure)
   - Household characteristics (size, workers, children)
   - Employment by occupation

4. Processes income data:
   - Maps ACS income categories to TM1 income quartiles
   - Calculates household distributions by income quartile

5. Summarizes data to TAZ level:
   - Aggregates data for modeling purposes
   - Fixes rounding artifacts
   - Adjusts to match county-level control totals

6. Outputs data files:
   - TAZ Land Use CSV file
   - Ethnicity data
   - District summaries
   - Population synthesis variables
   - Tableau-friendly long format files

### Output Files

The script generates multiple output files in the specified year directory:
- `TAZ1454_Ethnicity.csv` - TAZ-level ethnicity data
- `TAZ Land Use File YYYY.pkl` - Full dataset in pickle format
- `TAZ1454 YYYY Land Use.csv` - TAZ land use data CSV file
- `TAZ1454 YYYY District Summary.csv` - Summary by superdistrict
- `TAZ1454 YYYY Popsim Vars.csv` - Population synthesis variables
- `TAZ1454 YYYY Popsim Vars Region.csv` - Regional population synthesis variables
- `TAZ1454 YYYY Popsim Vars County.csv` - County-level population synthesis variables
- `TAZ1454_YYYY_long.csv` - Data in Tableau-friendly long format

### Testing

A unit test suite is provided in `test_create_tazdata_2020_and_after.py`. To run the tests:

```bash
python -m unittest test_create_tazdata_2020_and_after.py
```

### Differences from R Implementation

The Python implementation follows the same overall logic and methodology as the R script, with a few differences:
- Uses the `census` Python package for API access instead of the R `tidycensus` package
- Implements more explicit logging for better debugging
- Uses pandas for data processing instead of R data frames
- Adds additional error handling and validation
- Organizes code with common functions in a separate module for better reusability 