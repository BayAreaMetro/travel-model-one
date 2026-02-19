"""
Setup for TAZ 2023 enrollment, parking, res dev acre update
"""

from pathlib import Path


ANALYSIS_CRS = "EPSG:26910"  # NAD83 / UTM Zone 10N (Bay Area)
WGS84_CRS = "EPSG:4326"

# Census API key (for parking prep - pytidycensus)
CENSUS_API_KEY = "a3928abdddafbb9bbd88399816c55c82337c3ca6"

# ================================
# Directories
# ================================

# Local repository directories
REPO_BASE = Path(__file__).parent.parent.parent.parent  # travel-model-one root

# ================================
# Input Data Directories
# ================================
# Raw data directories
RAW_DATA_DIR = Path(r"E:\Box\Modeling and Surveys\Development\raw_base_data\2023")
ENROLLMENT_RAW_DATA_DIR = RAW_DATA_DIR / "enrollment"
PARKING_RAW_DATA_DIR = RAW_DATA_DIR / "parking"

# Box directory for TM2 dev (we share some interim outputs for the TAZ parking cost generation)
BOX_LANDUSE_TM2 = Path(r"E:\Box\Modeling and Surveys\Development\Travel Model Two Conversion\Model Inputs\2023-tm22-dev-version-05\landuse")
INTERIM_CACHE_DIR = BOX_LANDUSE_TM2 / "interim_cache"

# MAZ/TAZ shapefiles
TAZ_FILE = REPO_BASE / "utilities" / "geographies" / "bayarea_rtaz1454_rev1_WGS84.shp"


# Output file - insert updated attributes
LU_FILE_2023 = REPO_BASE / "utilities" / "taz-data-baseyears" / "2023" / "TAZ1454 2023 Land Use.csv"

# ================================
# Constants
# ================================

SQUARE_METERS_PER_ACRE = 4046.86

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


