"""
Setup for TAZ 2023 enrollment, parking, res dev acre update
"""

from pathlib import Path


ANALYSIS_CRS = "EPSG:26910"  # NAD83 / UTM Zone 10N (Bay Area)
WGS84_CRS = "EPSG:4326"

# ================================
# Directories
# ================================

# Local repository directories
REPO_BASE = Path(__file__).parent.parent.parent.parent.parent  # travel-model-one root

# ================================
# Input Data Directories
# ================================
# Raw data directories
RAW_DATA_DIR = Path(r"E:\Box\Modeling and Surveys\Development\raw_base_data\2023")
ENROLLMENT_RAW_DATA_DIR = RAW_DATA_DIR / "enrollment"
PARKING_RAW_DATA_DIR = RAW_DATA_DIR / "parking"

# MAZ/TAZ shapefiles
TAZ_FILE = REPO_BASE / "utilities" / "geographies" / "bayarea_rtaz1454_rev1_WGS84.shp"


# Output file - insert updated attributes
LU_FILE_2023 = REPO_BASE / "utilities" / "taz-data-baseyears" / "2023" / "TAZ1454 2023 Land Use.csv"

# ================================
# Constants
# ================================

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


