"""
Create 202X TAZ data from ACS 5-year data.

The year for which to generate the tazdata is passed as an argument to this script.

This is a Python port of create_tazdata_2020_and_after.R and is intended to be
functionally equivalent.  Helper functions live in create_tazdata_common.py.

Processing steps
 1. Resolve data-source years from the requested YEAR: the ACS 5-year vintage
    (ACS_5year, centered on YEAR but capped at the latest available), the ACS
    1-year and 5-year PUMS vintages, and the LODES year (LODES_YEAR).
 2. Build TAZ employment.  Wage/salary jobs come from the LODES WAC file; self-
    employed workers come from taz_self_employed_workers_[YEAR].csv.  The two are
    combined into six employment sectors (AGREMPN, FPSEMPN, HEREMPN, MWTEMPN,
    RETEMPN, OTHEMPN) plus TOTEMP per TAZ.
 3. Build a county-to-county worker table (lehd_lodes) from LODES: add estimated
    USPS jobs (USPS_PER_THOUSAND_JOBS) and self-employment, summarized to county.
    This is used later to form the employed-residents (EMPRES) target.
 4. Compute block-level population shares from the 2020 block-to-TAZ equivalency:
    each block's share of its block group (sharebg) and of its tract (sharetract).
 5. Download census data directly from the Census API: ACS 5-year block group and
    tract tables (year=ACS_5year) and the 2020 Decennial DHC tract table.  Group
    quarters are only published below the state level in the Decennial data, so
    DHC is used for group quarters (and later scaled if applicable).
 6. Allocate census data to TAZs by population share and derive the model
    variables: block group variables are apportioned by sharebg, tract variables
    (workers, kids, group quarters) by sharetract.  This yields age, race/
    ethnicity, dwelling-unit type, tenure, household size, household workers,
    households with/without kids, persons by occupation, and group quarters.
 7. Split households into model income quartiles (HHINCQ1-4) by mapping the ACS
    16-category household-income distribution through PUMS-derived shares.
 8. Aggregate everything to the TAZ level (tazdata_census) and attach income,
    superdistrict/county geography, and employment.
 9. Round to integers and fix rounding artifacts so each set of component parts
    (age, group quarters, tenure, size, income, occupation) sums exactly to its
    control total (TOTPOP, gqpop, TOTHH, EMPRES).
10. Build county control targets.  Start from the ACS 5-year-based totals; if a
    newer ACS 1-year vintage is available, scale TOTHH/TOTPOP/HHPOP/EMPRES/GQPOP
    to those county totals (removing institutionalized group quarters, assumed
    unchanged from 2020).  The EMPRES target is a blend of the ACS and LODES
    values controlled by EMPRES_LODES_WEIGHT (ACS tends high, LODES tends low).
11. Implement the county targets by reallocating whole units across TAZs within
    each county (weighted random sampling) for group quarters, employed residents,
    age, ethnicity, dwelling units, tenure, kids, income, and household size; then
    reconcile household sizes with HHPOP, do household workers, and reconcile those
    with EMPRES.  Finally set TOTHH = sum of sizes and TOTPOP = HHPOP + gqpop.
12. Apply patchwork fields carried from the 2015 land use file (area type,
    topology, terminal, zero, superdistrict) plus 2023 updates for parking,
    school enrollment, and developable acres.
13. Write the outputs (see "Output files" below): the ethnicity file, the full
    intermediate table, the land use file, district summaries, popsim control
    files, and the Tableau long-format file.

Random sampling note: step 11 uses NumPy's random number generator (seeded with
the year), which differs from R's.  Per-TAZ allocations therefore differ from the R
script, but county and regional control totals match by construction.

Input files (YEAR, LODES_YEAR, ACS_5year, ACS_PUMS_1year are resolved from the year
argument; the script is run from this directory, taz-data-baseyears):
- Census API (requires an API key at M:/Data/Census/API/api-key.txt):
    - ACS 5-year block group + tract tables (year=ACS_5year)
    - ACS 1-year county tables (year=ACS_PUMS_1year), when scaling is applicable
    - 2020 Decennial DHC tract table (group quarters)
- ./[LODES_YEAR]/lodes_wac_employment_[LODES_YEAR].csv: wage/salary employment
- ./[YEAR]/taz_self_employed_workers_[YEAR].csv: self-employed workers
- M:/Data/Census/LEHD/Origin-Destination Employment Statistics (LODES)/
    LODES_Bay_Area_county_[LODES_YEAR].csv: county-to-county workers
- ../geographies/taz-superdistrict-county.csv: TAZ / superdistrict / county
- M:/Data/GIS layers/TM1_taz_census2020/2020block_to_TAZ1454.csv: 2020 block-to-TAZ
- M:/Data/Census/PUMS/PUMS [ACS_5year-4]-[ACS_5year]/hbayarea[..].feather: PUMS
    households, used to map ACS income categories to model income quartiles
- M:/Data/Census/PUMS/PUMS [ACS_PUMS_1year]/summaries/noninst_gq_summary.csv: group
    quarters worker/age/type distributions
- M:/Data/Census/PUMS/PUMS 2017-21/summaries/county_hh_size_summary_wide.csv and
    county_hh_worker_summary_wide.csv: avg persons/workers in the largest category
- E:/Box/Modeling and Surveys/Share Data/plan-bay-area-2050/tazdata/
    PBA50_FinalBlueprintLandUse_TAZdata.xlsx (sheet census2015) .. 2015 land use +
    county equivalencies, area type, topology, terminal, zero fields
- ./2023/Parking/parking_costs_taz.csv: parking costs (PRKCST, OPRKCST)
- ./2023/School Enrollment/enrollment_taz.csv: enrollment (HSENROLL, COLL*)
- M:/urban_modeling/baus/PBA50Plus/PBA50Plus_NoProject/PBA50Plus_NoProject_v38/
    travel_model_summaries/PBA50Plus_NoProject_v38_taz1_summary_2025.csv: dev acres
    (RESACRE, CIACRE, TOTACRE)

Output files (written to ./[YEAR]/ unless noted):
- create_tazdata_[YEAR].log: run log
- TAZ1454_Ethnicity.csv: ethnicity by TAZ
- TAZ Land Use File [YEAR].feather: full intermediate table
- TAZ1454 [YEAR] Land Use.csv: travel model land use file
- TAZ1454 [YEAR] District Summary.csv: superdistrict summary
- ./2015/TAZ1454 2015 District Summary.csv: 2015 superdistrict summary
- TAZ1454 [YEAR] Popsim Vars.csv: population synthesis controls
- TAZ1454 [YEAR] Popsim Vars Region.csv: region-level popsim controls
- TAZ1454 [YEAR] Popsim Vars County.csv: county-level popsim controls
- TAZ1454_[YEAR]_long.csv: tidy/long format (Tableau)
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy
import pandas

# bring in common modules
sys.path.append(str(Path(__file__).resolve().parent))
import create_tazdata_common as ctc  # noqa: E402

# ----------------------------------------------------------------------------
# Parse arguments and set up logging
# ----------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="Create 202X TAZ data from ACS 5-year data.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("year", type=int, choices=[2020, 2021, 2023], help="Year for TAZ data")
args = parser.parse_args()

YEAR = args.year
numpy.random.seed(YEAR)

YEAR_DIR = Path(str(YEAR))
YEAR_DIR.mkdir(exist_ok=True)
RUN_LOG = YEAR_DIR / f"create_tazdata_{YEAR}.log"

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
_fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(_fmt)
logger.addHandler(_ch)
_fh = logging.FileHandler(RUN_LOG, mode="w")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_fmt)
logger.addHandler(_fh)

logger.info("Writing log to %s", RUN_LOG)

# make pandas print wide
pandas.set_option("display.width", 500)
pandas.set_option("display.max_columns", 100)

# ----------------------------------------------------------------------------
# Determine data source years
# ----------------------------------------------------------------------------
ACS_PUMS_5YEAR_LATEST = 2022
ACS_PUMS_1YEAR_LATEST = 2023
ACS_5YEAR_LATEST = ACS_PUMS_5YEAR_LATEST  # don't use inconsistent versions

# figure out our primary datasource - which ACS5-year
ACS_5year = min(YEAR + 2, ACS_5YEAR_LATEST)
logger.info("ACS_5year: %d", ACS_5year)

# Used for avg workers per 3+ person households
ACS_PUMS_1year = min(ACS_PUMS_1YEAR_LATEST, YEAR)
ACS_PUMS_5year = min(ACS_PUMS_5YEAR_LATEST, YEAR + 2)

# lodes year
LODES_YEAR_LATEST = 2022
LODES_YEAR = min(YEAR, LODES_YEAR_LATEST)

# Blended ACS/LODES employed residents weight (0.0=ACS only, 1.0=LODES only)
EMPRES_LODES_WEIGHT = 0.5

# USPS jobs per thousand, consistent with lodes_wac_to_TAZ.py
USPS_PER_THOUSAND_JOBS = 1.83

# ----------------------------------------------------------------------------
# Setup paths and read employment
# ----------------------------------------------------------------------------
BOX_TM = Path("E:/Box/Modeling and Surveys")
PBA_TAZ_2015 = (
    BOX_TM / "Share Data" / "plan-bay-area-2050" / "tazdata"
    / "PBA50_FinalBlueprintLandUse_TAZdata.xlsx"
)
TM1 = Path(".")

emp_wage_salary = pandas.read_csv(
    TM1 / str(LODES_YEAR) / f"lodes_wac_employment_{LODES_YEAR}.csv"
)
emp_self_employed = pandas.read_csv(
    TM1 / str(YEAR) / f"taz_self_employed_workers_{YEAR}.csv"
)
lehd_lodes = pandas.read_csv(
    Path("M:/Data/Census/LEHD/Origin-Destination Employment Statistics (LODES)")
    / f"LODES_Bay_Area_county_{LODES_YEAR}.csv"
)
TAZ_SD_COUNTY = pandas.read_csv(
    Path("..") / "geographies" / "taz-superdistrict-county.csv"
).rename(columns={"COUNTY_NAME": "County_Name", "SD": "DISTRICT", "SD_NAME": "DISTRICT_NAME"})
TAZ_SD_COUNTY = TAZ_SD_COUNTY.drop(columns=["SD_NUM_NAME", "COUNTY_NUM_NAME"])
# TAZ_SD_COUNTY columns: ZONE, DISTRICT, COUNTY, DISTRICT_NAME, County_Name

# Restructure employment frame to wide format
# drop unnamed index column ("X" in R)
emp_self_employed = emp_self_employed.loc[
    :, ~emp_self_employed.columns.str.startswith("Unnamed")
]
emp_self_employed_w = emp_self_employed.pivot_table(
    index="zone_id", columns="industry", values="value", fill_value=0
).reset_index()
emp_self_employed_w.columns.name = None
# TOTEMP = sum of industry columns (all except zone_id)
industry_cols = [c for c in emp_self_employed_w.columns if c != "zone_id"]
emp_self_employed_w["TOTEMP"] = emp_self_employed_w[industry_cols].sum(axis=1)
emp_self_employed_w = emp_self_employed_w.sort_values("zone_id")
emp_self_employed_w = emp_self_employed_w.rename(columns={"zone_id": "TAZ1454"})
emp_self_employed_w.columns = [c.upper() for c in emp_self_employed_w.columns]
logger.info("emp_self_employed_w:\n%s", emp_self_employed_w)

lehd_lodes = lehd_lodes.drop(columns=["w_state", "h_state"]).rename(
    columns={"Total_Workers": "TOTEMP"}
)
lehd_lodes = lehd_lodes.groupby(["w_county", "h_county"], as_index=False)["TOTEMP"].sum()

# get self employment ready to add: summarize to county and set h_county = w_county
emp_self_employed_county = emp_self_employed_w.merge(
    TAZ_SD_COUNTY[["ZONE", "County_Name"]], left_on="TAZ1454", right_on="ZONE", how="left"
)
emp_self_employed_county = (
    emp_self_employed_county.groupby("County_Name", as_index=False)["TOTEMP"]
    .sum()
    .rename(columns={"County_Name": "h_county", "TOTEMP": "TOTEMP_self"})
)
emp_self_employed_county["w_county"] = emp_self_employed_county["h_county"]
logger.info(
    "emp_self_employed_county total: %s",
    f"{int(emp_self_employed_county['TOTEMP_self'].sum()):,}",
)

# add estimated USPS jobs, consistent with lodes_wac_to_TAZ.py
lehd_lodes["TOTEMP"] = (
    (lehd_lodes["TOTEMP"] * (1.0 + USPS_PER_THOUSAND_JOBS / 1000.0)).round().astype(int)
)
# add self-employment to lehd lodes
lehd_lodes = lehd_lodes.merge(
    emp_self_employed_county, on=["h_county", "w_county"], how="left"
)
lehd_lodes["TOTEMP_self"] = lehd_lodes["TOTEMP_self"].fillna(0)
lehd_lodes["TOTEMP"] = lehd_lodes["TOTEMP"] + lehd_lodes["TOTEMP_self"]
lehd_lodes = lehd_lodes.drop(columns=["TOTEMP_self"])
logger.info("LEHD LODES from %d (after adding self-employment):\n%s", LODES_YEAR, lehd_lodes)

# Combine the two employment frames - wage/salary and self-employment
emp_cols = ["TAZ1454", "AGREMPN", "FPSEMPN", "HEREMPN", "MWTEMPN", "RETEMPN", "OTHEMPN", "TOTEMP"]
employment = pandas.concat(
    [emp_wage_salary[emp_cols], emp_self_employed_w[emp_cols]], ignore_index=True
)
employment = employment.groupby("TAZ1454", as_index=False).sum()
logger.info("employment:\n%s", employment)
logger.info("TOTEMP: %s", f"{int(employment['TOTEMP'].sum()):,}")

# ----------------------------------------------------------------------------
# ACS / DHC variable definitions
#
# Friendly names are given WITHOUT the trailing underscore used in the R script.
# In R, get_acs(output="wide") appends "_E" to each name and the script strips
# "_E", so e.g. R's "tothh_" -> "tothh_E" -> "tothh".  We name them "tothh"
# directly to match the names referenced downstream.
# ----------------------------------------------------------------------------
ACS_BG_variables = {
    # total households
    "tothh": "B19001_001",
    "hhpop": "B28005_001",
    # Sex by Age; Universe = Total Population (male)
    "male0_4": "B01001_003", "male5_9": "B01001_004", "male10_14": "B01001_005",
    "male15_17": "B01001_006", "male18_19": "B01001_007", "male20": "B01001_008",
    "male21": "B01001_009", "male22_24": "B01001_010", "male25_29": "B01001_011",
    "male30_34": "B01001_012", "male35_39": "B01001_013", "male40_44": "B01001_014",
    "male45_49": "B01001_015", "male50_54": "B01001_016", "male55_59": "B01001_017",
    "male60_61": "B01001_018", "male62_64": "B01001_019", "male65_66": "B01001_020",
    "male67_69": "B01001_021", "male70_74": "B01001_022", "male75_79": "B01001_023",
    "male80_84": "B01001_024", "male85p": "B01001_025",
    # female
    "female0_4": "B01001_027", "female5_9": "B01001_028", "female10_14": "B01001_029",
    "female15_17": "B01001_030", "female18_19": "B01001_031", "female20": "B01001_032",
    "female21": "B01001_033", "female22_24": "B01001_034", "female25_29": "B01001_035",
    "female30_34": "B01001_036", "female35_39": "B01001_037", "female40_44": "B01001_038",
    "female45_49": "B01001_039", "female50_54": "B01001_040", "female55_59": "B01001_041",
    "female60_61": "B01001_042", "female62_64": "B01001_043", "female65_66": "B01001_044",
    "female67_69": "B01001_045", "female70_74": "B01001_046", "female75_79": "B01001_047",
    "female80_84": "B01001_048", "female85p": "B01001_049",
    # Household size by tenure; B25009 Tenure by Household Size
    "own1": "B25009_003", "own2": "B25009_004", "own3": "B25009_005", "own4": "B25009_006",
    "own5": "B25009_007", "own6": "B25009_008", "own7p": "B25009_009",
    "rent1": "B25009_011", "rent2": "B25009_012", "rent3": "B25009_013", "rent4": "B25009_014",
    "rent5": "B25009_015", "rent6": "B25009_016", "rent7p": "B25009_017",
    # Race/Ethnicity; B03002 Hispanic or Latino Origin by Race
    "white_nonh": "B03002_003", "black_nonh": "B03002_004", "asian_nonh": "B03002_006",
    "total_nonh": "B03002_002", "total_hisp": "B03002_012",
    # Units; B25024
    "unit1d": "B25024_002", "unit1a": "B25024_003", "unit2": "B25024_004",
    "unit3_4": "B25024_005", "unit5_9": "B25024_006", "unit10_19": "B25024_007",
    "unit20_49": "B25024_008", "unit50p": "B25024_009", "mobile": "B25024_010",
    "boat_RV_Van": "B25024_011",
    # Employment; B23025
    "employed": "B23025_004", "armedforces": "B23025_006",
    # Household income; B19001
    "hhinc000_010": "B19001_002", "hhinc010_015": "B19001_003", "hhinc015_020": "B19001_004",
    "hhinc020_025": "B19001_005", "hhinc025_030": "B19001_006", "hhinc030_035": "B19001_007",
    "hhinc035_040": "B19001_008", "hhinc040_045": "B19001_009", "hhinc045_050": "B19001_010",
    "hhinc050_060": "B19001_011", "hhinc060_075": "B19001_012", "hhinc075_100": "B19001_013",
    "hhinc100_125": "B19001_014", "hhinc125_150": "B19001_015", "hhinc150_200": "B19001_016",
    "hhinc200p": "B19001_017",
    # C24010 Sex by Occupation (male)
    "occ_m_manage": "C24010_005", "occ_m_prof_biz": "C24010_006", "occ_m_prof_comp": "C24010_007",
    "occ_m_svc_comm": "C24010_012", "occ_m_prof_leg": "C24010_013", "occ_m_prof_edu": "C24010_014",
    "occ_m_svc_ent": "C24010_015", "occ_m_prof_heal": "C24010_016", "occ_m_svc_heal": "C24010_020",
    "occ_m_svc_fire": "C24010_022", "occ_m_svc_law": "C24010_023", "occ_m_ret_eat": "C24010_024",
    "occ_m_man_build": "C24010_025", "occ_m_svc_pers": "C24010_026", "occ_m_ret_sales": "C24010_028",
    "occ_m_svc_off": "C24010_029", "occ_m_man_nat": "C24010_030", "occ_m_man_prod": "C24010_034",
    # C24010 Sex by Occupation (female)
    "occ_f_manage": "C24010_041", "occ_f_prof_biz": "C24010_042", "occ_f_prof_comp": "C24010_043",
    "occ_f_svc_comm": "C24010_048", "occ_f_prof_leg": "C24010_049", "occ_f_prof_edu": "C24010_050",
    "occ_f_svc_ent": "C24010_051", "occ_f_prof_heal": "C24010_052", "occ_f_svc_heal": "C24010_056",
    "occ_f_svc_fire": "C24010_058", "occ_f_svc_law": "C24010_059", "occ_f_ret_eat": "C24010_060",
    "occ_f_man_build": "C24010_061", "occ_f_svc_pers": "C24010_062", "occ_f_ret_sales": "C24010_064",
    "occ_f_svc_off": "C24010_065", "occ_f_man_nat": "C24010_066", "occ_f_man_prod": "C24010_070",
}

ACS_tract_variables = {
    # Households by number of workers; B08202
    "hhwrks0": "B08202_002", "hhwrks1": "B08202_003", "hhwrks2": "B08202_004", "hhwrks3p": "B08202_005",
    # Households by number of kids; B25012
    "ownkidsyes": "B25012_003", "rentkidsyes": "B25012_011",
    "ownkidsno": "B25012_009", "rentkidsno": "B25012_017",
}

# Group quarters from Decennial census (DHC) - ACS only has these at state level
DHC_tract_variables = {
    "gq_inst_m_0017": "PCT19_004N", "gq_noninst_m_0017_univ": "PCT19_024N",
    "gq_noninst_m_0017_mil": "PCT19_025N", "gq_noninst_m_0017_oth": "PCT19_028N",
    "gq_inst_m_1864": "PCT19_036N", "gq_noninst_m_1864_univ": "PCT19_056N",
    "gq_noninst_m_1864_mil": "PCT19_057N", "gq_noninst_m_1864_oth": "PCT19_060N",
    "gq_inst_m_65p": "PCT19_068N", "gq_noninst_m_65p_univ": "PCT19_088N",
    "gq_noninst_m_65p_mil": "PCT19_089N", "gq_noninst_m_65p_oth": "PCT19_092N",
    "gq_inst_f_0017": "PCT19_101N", "gq_noninst_f_0017_univ": "PCT19_121N",
    "gq_noninst_f_0017_mil": "PCT19_122N", "gq_noninst_f_0017_oth": "PCT19_125N",
    "gq_inst_f_1864": "PCT19_133N", "gq_noninst_f_1864_univ": "PCT19_153N",
    "gq_noninst_f_1864_mil": "PCT19_154N", "gq_noninst_f_1864_oth": "PCT19_157N",
    "gq_inst_f_65p": "PCT19_165N", "gq_noninst_f_65p_univ": "PCT19_185N",
    "gq_noninst_f_65p_mil": "PCT19_186N", "gq_noninst_f_65p_oth": "PCT19_189N",
}

# ----------------------------------------------------------------------------
# Block/blockgroup/tract population shares
# ----------------------------------------------------------------------------
BLOCK2020_TAZ1454 = ctc.load_block2020_taz1454()

blockTAZBG = BLOCK2020_TAZ1454.groupby("blockgroup", as_index=False)["block_POPULATION"].sum()
blockTAZBG = blockTAZBG.rename(columns={"block_POPULATION": "BGTotal"})
logger.info("blockTAZBG has %d rows:\n%s", len(blockTAZBG), blockTAZBG.head())

blockTAZTract = BLOCK2020_TAZ1454.groupby("tract", as_index=False)["block_POPULATION"].sum()
blockTAZTract = blockTAZTract.rename(columns={"block_POPULATION": "TractTotal"})
logger.info("blockTAZTract has %d rows:\n%s", len(blockTAZTract), blockTAZTract.head())

combined_block = BLOCK2020_TAZ1454.merge(blockTAZBG, on="blockgroup", how="left")
combined_block["sharebg"] = numpy.where(
    combined_block["block_POPULATION"] == 0, 0,
    combined_block["block_POPULATION"] / combined_block["BGTotal"],
)
combined_block = combined_block.merge(blockTAZTract, on="tract", how="left")
combined_block["sharetract"] = numpy.where(
    combined_block["block_POPULATION"] == 0, 0,
    combined_block["block_POPULATION"] / combined_block["TractTotal"],
)
logger.info("combined_block has %d rows", len(combined_block))

# ----------------------------------------------------------------------------
# Download ACS data (and DHC data for group quarters)
# ----------------------------------------------------------------------------
census_key = ctc.read_census_api_key()

ACS_tract_raw = ctc.get_acs5_tract_wide(census_key, ACS_tract_variables, ACS_5year)
ACS_BG_raw = ctc.get_acs5_blockgroup_wide(census_key, ACS_BG_variables, ACS_5year)
DHC_tract_raw = ctc.get_decennial_dhc_tract_wide(census_key, DHC_tract_variables, year=2020)

logger.info("DHC_tract_raw (%d rows)", len(DHC_tract_raw))
logger.info("ACS_tract_raw (%d rows):\n%s", len(ACS_tract_raw), ACS_tract_raw)
logger.info("ACS_BG_raw (%d rows):\n%s", len(ACS_BG_raw), ACS_BG_raw)

# ----------------------------------------------------------------------------
# Join ACS/DHC to blocks and allocate by population share
# ----------------------------------------------------------------------------
interim = combined_block.merge(
    ACS_BG_raw, left_on="blockgroup", right_on="GEOID", how="left", suffixes=("", "_bg")
)
interim = interim.merge(
    ACS_tract_raw, left_on="tract", right_on="GEOID", how="left", suffixes=("", "_tract")
)
interim = interim.merge(
    DHC_tract_raw, left_on="tract", right_on="GEOID", how="left", suffixes=("", "_dhc")
)
logger.info("interim (%d rows)", len(interim))

wd = interim.copy()
sb = wd["sharebg"]
st = wd["sharetract"]

wd["TOTHH"] = wd["tothh"] * sb
wd["HHPOP"] = wd["hhpop"] * sb
wd["EMPRES"] = (wd["employed"] + wd["armedforces"]) * sb
wd["AGE0004"] = (wd["male0_4"] + wd["female0_4"]) * sb
wd["AGE0519"] = (
    wd["male5_9"] + wd["male10_14"] + wd["male15_17"] + wd["male18_19"]
    + wd["female5_9"] + wd["female10_14"] + wd["female15_17"] + wd["female18_19"]
) * sb
wd["AGE2044"] = (
    wd["male20"] + wd["male21"] + wd["male22_24"] + wd["male25_29"] + wd["male30_34"]
    + wd["male35_39"] + wd["male40_44"]
    + wd["female20"] + wd["female21"] + wd["female22_24"] + wd["female25_29"]
    + wd["female30_34"] + wd["female35_39"] + wd["female40_44"]
) * sb
wd["AGE4564"] = (
    wd["male45_49"] + wd["male50_54"] + wd["male55_59"] + wd["male60_61"] + wd["male62_64"]
    + wd["female45_49"] + wd["female50_54"] + wd["female55_59"] + wd["female60_61"] + wd["female62_64"]
) * sb
wd["AGE65P"] = (
    wd["male65_66"] + wd["male67_69"] + wd["male70_74"] + wd["male75_79"] + wd["male80_84"] + wd["male85p"]
    + wd["female65_66"] + wd["female67_69"] + wd["female70_74"] + wd["female75_79"] + wd["female80_84"] + wd["female85p"]
) * sb
wd["AGE62P"] = (
    wd["male62_64"] + wd["male65_66"] + wd["male67_69"] + wd["male70_74"] + wd["male75_79"] + wd["male80_84"] + wd["male85p"]
    + wd["female62_64"] + wd["female65_66"] + wd["female67_69"] + wd["female70_74"] + wd["female75_79"] + wd["female80_84"] + wd["female85p"]
) * sb
# race/ethnicity (note: dplyr mutate is sequential; other_nonh uses scaled values)
wd["white_nonh"] = wd["white_nonh"] * sb
wd["black_nonh"] = wd["black_nonh"] * sb
wd["asian_nonh"] = wd["asian_nonh"] * sb
wd["other_nonh"] = (wd["total_nonh"] - (wd["white_nonh"] + wd["black_nonh"] + wd["asian_nonh"])) * sb
wd["hispanic"] = wd["total_hisp"] * sb
# single family versus multi-family
wd["SFDU"] = (wd["unit1d"] + wd["unit1a"] + wd["mobile"] + wd["boat_RV_Van"]) * sb
wd["MFDU"] = (wd["unit2"] + wd["unit3_4"] + wd["unit5_9"] + wd["unit10_19"] + wd["unit20_49"] + wd["unit50p"]) * sb
# tenure
wd["hh_own"] = (wd["own1"] + wd["own2"] + wd["own3"] + wd["own4"] + wd["own5"] + wd["own6"] + wd["own7p"]) * sb
wd["hh_rent"] = (wd["rent1"] + wd["rent2"] + wd["rent3"] + wd["rent4"] + wd["rent5"] + wd["rent6"] + wd["rent7p"]) * sb
# households by size
wd["hh_size_1"] = (wd["own1"] + wd["rent1"]) * sb
wd["hh_size_2"] = (wd["own2"] + wd["rent2"]) * sb
wd["hh_size_3"] = (wd["own3"] + wd["rent3"]) * sb
wd["hh_size_4_plus"] = (wd["own4"] + wd["own5"] + wd["own6"] + wd["own7p"] + wd["rent4"] + wd["rent5"] + wd["rent6"] + wd["rent7p"]) * sb
# households by number of workers
wd["hh_wrks_0"] = wd["hhwrks0"] * st
wd["hh_wrks_1"] = wd["hhwrks1"] * st
wd["hh_wrks_2"] = wd["hhwrks2"] * st
wd["hh_wrks_3_plus"] = wd["hhwrks3p"] * st
# households with children or not
wd["hh_kids_yes"] = (wd["ownkidsyes"] + wd["rentkidsyes"]) * st
wd["hh_kids_no"] = (wd["ownkidsno"] + wd["rentkidsno"]) * st
# persons by occupation
wd["pers_occ_management"] = (wd["occ_m_manage"] + wd["occ_f_manage"]) * sb
wd["pers_occ_professional"] = (
    wd["occ_m_prof_biz"] + wd["occ_f_prof_biz"]
    + wd["occ_m_prof_comp"] + wd["occ_f_prof_comp"]
    + wd["occ_m_prof_leg"] + wd["occ_f_prof_leg"]
    + wd["occ_m_prof_edu"] + wd["occ_f_prof_edu"]
    + wd["occ_m_prof_heal"] + wd["occ_f_prof_heal"]
) * sb
wd["pers_occ_services"] = (
    wd["occ_m_svc_comm"] + wd["occ_f_svc_comm"]
    + wd["occ_m_svc_ent"] + wd["occ_f_svc_ent"]
    + wd["occ_m_svc_heal"] + wd["occ_f_svc_heal"]
    + wd["occ_m_svc_fire"] + wd["occ_f_svc_fire"]
    + wd["occ_m_svc_law"] + wd["occ_f_svc_law"]
    + wd["occ_m_svc_pers"] + wd["occ_f_svc_pers"]
    + wd["occ_m_svc_off"] + wd["occ_f_svc_off"]
) * sb
wd["pers_occ_retail"] = (
    wd["occ_m_ret_eat"] + wd["occ_f_ret_eat"]
    + wd["occ_m_ret_sales"] + wd["occ_f_ret_sales"]
) * sb
wd["pers_occ_manual"] = (
    wd["occ_m_man_build"] + wd["occ_f_man_build"]
    + wd["occ_m_man_nat"] + wd["occ_f_man_nat"]
    + wd["occ_m_man_prod"] + wd["occ_f_man_prod"]
) * sb
wd["pers_occ_military"] = wd["armedforces"] * sb
# group quarters
wd["gq_inst"] = (
    wd["gq_inst_m_0017"] + wd["gq_inst_m_1864"] + wd["gq_inst_m_65p"]
    + wd["gq_inst_f_0017"] + wd["gq_inst_f_1864"] + wd["gq_inst_f_65p"]
) * st
wd["gq_type_univ"] = (
    wd["gq_noninst_m_0017_univ"] + wd["gq_noninst_m_1864_univ"] + wd["gq_noninst_m_65p_univ"]
    + wd["gq_noninst_f_0017_univ"] + wd["gq_noninst_f_1864_univ"] + wd["gq_noninst_f_65p_univ"]
) * st
wd["gq_type_mil"] = (
    wd["gq_noninst_m_0017_mil"] + wd["gq_noninst_m_1864_mil"] + wd["gq_noninst_m_65p_mil"]
    + wd["gq_noninst_f_0017_mil"] + wd["gq_noninst_f_1864_mil"] + wd["gq_noninst_f_65p_mil"]
) * st
wd["gq_type_othnon"] = (
    wd["gq_noninst_m_0017_oth"] + wd["gq_noninst_m_1864_oth"] + wd["gq_noninst_m_65p_oth"]
    + wd["gq_noninst_f_0017_oth"] + wd["gq_noninst_f_1864_oth"] + wd["gq_noninst_f_65p_oth"]
) * st

workingdata = wd
logger.info("workingdata (%d rows)", len(workingdata))

# ----------------------------------------------------------------------------
# Household income - handled separately using PUMS mapping
# ----------------------------------------------------------------------------
hhinc_cols = [c for c in ACS_BG_variables.keys() if c.startswith("hhinc")]
workingdata_hhinc = workingdata[
    ["GEOID", "blockgroup", "tract", "TAZ1454", "sharebg"] + hhinc_cols
].copy()

workingdata_hhinc = workingdata_hhinc.melt(
    id_vars=["GEOID", "blockgroup", "tract", "TAZ1454", "sharebg"],
    value_vars=hhinc_cols,
    var_name="householdinc_acs_cat",
    value_name="num_households",
)
workingdata_hhinc = workingdata_hhinc[workingdata_hhinc["num_households"].notna()].copy()

PUMS_hhinc_cat = ctc.map_ACS5year_household_income_to_TM1_categories(ACS_5year)

workingdata_hhinc["num_households"] = workingdata_hhinc["num_households"] * workingdata_hhinc["sharebg"]
workingdata_hhinc = workingdata_hhinc.merge(
    PUMS_hhinc_cat, on="householdinc_acs_cat", how="left"
)
workingdata_hhinc["num_households"] = (
    workingdata_hhinc["num_households"] * workingdata_hhinc["acs_to_hhincq_share"]
)

TAZ_hhinc = (
    workingdata_hhinc.groupby(["TAZ1454", "HHINCQ"], as_index=False)["num_households"].sum()
)
TAZ_hhinc = TAZ_hhinc.pivot_table(
    index="TAZ1454", columns="HHINCQ", values="num_households"
).reset_index()
TAZ_hhinc.columns.name = None
logger.info("Resulting TAZ_hhinc (%d rows):\n%s", len(TAZ_hhinc), TAZ_hhinc)

# ----------------------------------------------------------------------------
# Aggregate workingdata to TAZ
# ----------------------------------------------------------------------------
sum_cols = [
    "TOTHH", "HHPOP", "EMPRES", "AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P",
    "SFDU", "MFDU", "hh_own", "hh_rent",
    "hh_size_1", "hh_size_2", "hh_size_3", "hh_size_4_plus",
    "hh_wrks_0", "hh_wrks_1", "hh_wrks_2", "hh_wrks_3_plus",
    "hh_kids_yes", "hh_kids_no", "AGE62P",
    "gq_inst", "gq_type_univ", "gq_type_mil", "gq_type_othnon",
    "pers_occ_management", "pers_occ_professional", "pers_occ_services",
    "pers_occ_retail", "pers_occ_manual", "pers_occ_military",
    "white_nonh", "black_nonh", "asian_nonh", "other_nonh", "hispanic",
]
tazdata_census = workingdata.groupby("TAZ1454", as_index=False)[sum_cols].sum()
tazdata_census["sum_age"] = tazdata_census[["AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P"]].sum(axis=1)
tazdata_census["gqpop"] = tazdata_census[["gq_type_univ", "gq_type_mil", "gq_type_othnon"]].sum(axis=1)

tazdata_census = tazdata_census.merge(TAZ_hhinc, on="TAZ1454", how="left")
# add county, County_Name, DISTRICT, DISTRICT_NAME, etc.
tazdata_census = tazdata_census.merge(
    TAZ_SD_COUNTY, left_on="TAZ1454", right_on="ZONE", how="left"
).drop(columns=["ZONE"])
# add employment
tazdata_census = tazdata_census.merge(employment, on="TAZ1454", how="left")
logger.info("tazdata_census (%d rows)", len(tazdata_census))

# GQ population by county (does NOT include institutionalized; used later)
DHC_gqpop = tazdata_census[
    ["TAZ1454", "gq_inst", "gq_type_univ", "gq_type_mil", "gq_type_othnon", "gqpop", "County_Name"]
]
DHC_gqpop = DHC_gqpop.groupby("County_Name", as_index=False)[
    ["gq_inst", "gq_type_univ", "gq_type_mil", "gq_type_othnon", "gqpop"]
].sum()
logger.info("DHC GQ population:\n%s", DHC_gqpop)

# ----------------------------------------------------------------------------
# Sum constituent parts to compare with marginal totals
# ----------------------------------------------------------------------------
tazdata_census["sum_age"] = tazdata_census[["AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P"]].sum(axis=1)
tazdata_census["sum_groupquarters"] = tazdata_census[["gq_type_univ", "gq_type_mil", "gq_type_othnon"]].sum(axis=1)
tazdata_census["sum_DU"] = tazdata_census["MFDU"] + tazdata_census["SFDU"]
tazdata_census["sum_tenure"] = tazdata_census["hh_own"] + tazdata_census["hh_rent"]
tazdata_census["sum_size"] = tazdata_census[["hh_size_1", "hh_size_2", "hh_size_3", "hh_size_4_plus"]].sum(axis=1)
tazdata_census["sum_hhworkers"] = tazdata_census[["hh_wrks_0", "hh_wrks_1", "hh_wrks_2", "hh_wrks_3_plus"]].sum(axis=1)
tazdata_census["sum_kids"] = tazdata_census["hh_kids_yes"] + tazdata_census["hh_kids_no"]
tazdata_census["sum_income"] = tazdata_census[["HHINCQ1", "HHINCQ2", "HHINCQ3", "HHINCQ4"]].sum(axis=1)
tazdata_census["sum_empres"] = tazdata_census[
    ["pers_occ_management", "pers_occ_professional", "pers_occ_services",
     "pers_occ_retail", "pers_occ_manual", "pers_occ_military"]
].sum(axis=1)
tazdata_census["TOTPOP"] = tazdata_census["sum_age"]
tazdata_census["gqpop"] = tazdata_census["gqpop"].round()
tazdata_census["sum_ethnicity"] = tazdata_census[
    ["white_nonh", "black_nonh", "asian_nonh", "other_nonh", "hispanic"]
].sum(axis=1)

# ----------------------------------------------------------------------------
# Round data and fix rounding artifacts
# ----------------------------------------------------------------------------
numeric_cols = tazdata_census.select_dtypes(include=[numpy.number]).columns
tazdata_census[numeric_cols] = tazdata_census[numeric_cols].round(0)

tazdata_census = ctc.fix_rounding_artifacts(
    tazdata_census, "TAZ1454", "TOTPOP", ["AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P"]
)
tazdata_census = ctc.fix_rounding_artifacts(
    tazdata_census, "TAZ1454", "gqpop", ["gq_type_univ", "gq_type_mil", "gq_type_othnon"]
)
tazdata_census = ctc.fix_rounding_artifacts(
    tazdata_census, "TAZ1454", "TOTHH", ["hh_own", "hh_rent"]
)
tazdata_census = ctc.fix_rounding_artifacts(
    tazdata_census, "TAZ1454", "TOTHH", ["hh_size_1", "hh_size_2", "hh_size_3", "hh_size_4_plus"]
)
tazdata_census = ctc.fix_rounding_artifacts(
    tazdata_census, "TAZ1454", "TOTHH", ["HHINCQ1", "HHINCQ2", "HHINCQ3", "HHINCQ4"]
)
tazdata_census = ctc.fix_rounding_artifacts(
    tazdata_census, "TAZ1454", "EMPRES",
    ["pers_occ_management", "pers_occ_professional", "pers_occ_services",
     "pers_occ_retail", "pers_occ_manual", "pers_occ_military"],
)

# Population over age 62 share (not rounded, added at the end)
tazdata_census["SHPOP62P"] = numpy.where(
    tazdata_census["TOTPOP"] == 0, 0, tazdata_census["AGE62P"] / tazdata_census["TOTPOP"]
)

# ----------------------------------------------------------------------------
# Create county-based targets
# ----------------------------------------------------------------------------
current_county_totals = tazdata_census.groupby("County_Name", as_index=False).agg(
    TOTHH=("TOTHH", "sum"),
    TOTPOP=("TOTPOP", "sum"),
    GQPOP=("gqpop", "sum"),
    HHPOP=("HHPOP", "sum"),
    EMPRES=("EMPRES", "sum"),
    TOTEMP=("TOTEMP", "sum"),
)
logger.info("current_county_totals:\n%s", current_county_totals)

county_targets = current_county_totals.copy()
county_targets["TOTHH_target"] = county_targets["TOTHH"]
county_targets["TOTPOP_target"] = county_targets["TOTPOP"]
county_targets["GQPOP_target"] = county_targets["GQPOP"]
county_targets["HHPOP_target"] = county_targets["HHPOP"]
county_targets["EMPRES_target"] = county_targets["EMPRES"]
county_targets["TOTEMP_target"] = county_targets["TOTEMP"]

# ACS_5year should be ACS_PUMS_1year + 2; if not, scale up using ACS1-year totals
if ACS_5year < ACS_PUMS_1year + 2:
    logger.info("#" * 90)
    logger.info(
        "Scaling to ACS 1Year Totals: ACS_5year %d < ACS_PUMS_1year + 2 = %d",
        ACS_5year, ACS_PUMS_1year + 2,
    )
    ACS_target_vars = {
        "tothh": "B19001_001",
        "totpop": "B01001_001",
        "hhpop": "B28005_001",
        "employed": "B23025_004",
        "armedforces": "B23025_006",
    }
    ACS_1year_target = ctc.get_acs1_county_wide(census_key, ACS_target_vars, ACS_PUMS_1year)
    ACS_1year_target["empres"] = ACS_1year_target["employed"] + ACS_1year_target["armedforces"]
    ACS_1year_target = ACS_1year_target.drop(columns=["GEOID", "employed", "armedforces"]).rename(
        columns={
            "tothh": "TOTHH_target",
            "totpop": "TOTPOP_target",
            "hhpop": "HHPOP_target",
            "empres": "EMPRES_target",
        }
    )
    ACS_1year_target["GQPOP_target"] = ACS_1year_target["TOTPOP_target"] - ACS_1year_target["HHPOP_target"]

    # this includes institutionalized GQ, so remove them (assuming unchanged from 2020)
    ACS_1year_target = ACS_1year_target.merge(
        DHC_gqpop[["County_Name", "gq_inst"]], on="County_Name", how="left"
    )
    logger.info("ACS_1year_target before removing institutionalized GQ:\n%s", ACS_1year_target)
    ACS_1year_target["TOTPOP_target"] = ACS_1year_target["TOTPOP_target"] - ACS_1year_target["gq_inst"]
    ACS_1year_target["GQPOP_target"] = ACS_1year_target["GQPOP_target"] - ACS_1year_target["gq_inst"]
    logger.info("ACS_1year_target after removing institutionalized GQ:\n%s", ACS_1year_target)

    # replace in county_targets
    county_targets = county_targets.drop(
        columns=["TOTHH_target", "TOTPOP_target", "HHPOP_target", "EMPRES_target", "GQPOP_target"]
    )
    county_targets = county_targets.merge(
        ACS_1year_target[
            ["County_Name", "TOTHH_target", "TOTPOP_target", "HHPOP_target", "EMPRES_target", "GQPOP_target"]
        ],
        on="County_Name", how="left",
    )

# factor EMPRES by LODES
in_bay = ctc.BAY_AREA_COUNTIES
logger.info(
    "  Workers with h_county in BayArea: %s",
    f"{int(lehd_lodes.loc[lehd_lodes['h_county'].isin(in_bay), 'TOTEMP'].sum()):,}",
)
logger.info(
    "  Workers with w_county in BayArea: %s",
    f"{int(lehd_lodes.loc[lehd_lodes['w_county'].isin(in_bay), 'TOTEMP'].sum()):,}",
)
logger.info(
    "  Workers with h_county AND w_county in BayArea: %s",
    f"{int(lehd_lodes.loc[lehd_lodes['w_county'].isin(in_bay) & lehd_lodes['h_county'].isin(in_bay), 'TOTEMP'].sum()):,}",
)

lehd_lodes_h_county = lehd_lodes[
    lehd_lodes["w_county"].isin(in_bay) & lehd_lodes["h_county"].isin(in_bay)
]
lehd_lodes_h_county = (
    lehd_lodes_h_county.groupby("h_county", as_index=False)["TOTEMP"]
    .sum()
    .rename(columns={"h_county": "County_Name", "TOTEMP": "EMPRES_LEHD_target"})
)
logger.info("lehd_lodes_h_county:\n%s", lehd_lodes_h_county)

county_targets = county_targets.merge(lehd_lodes_h_county, on="County_Name", how="left")
county_targets["EMPRES_target"] = (
    EMPRES_LODES_WEIGHT * county_targets["EMPRES_LEHD_target"]
    + (1.0 - EMPRES_LODES_WEIGHT) * county_targets["EMPRES_target"]
)
county_targets = county_targets.drop(columns=["EMPRES_LEHD_target"])
logger.info("county_targets after adjustment:\n%s", county_targets)

# ----------------------------------------------------------------------------
# Implement county_targets
# ----------------------------------------------------------------------------
logger.info("Implementing County Targets:")
county_targets["TOTHH_diff"] = county_targets["TOTHH_target"] - county_targets["TOTHH"]
county_targets["TOTPOP_diff"] = county_targets["TOTPOP_target"] - county_targets["TOTPOP"]
county_targets["HHPOP_diff"] = county_targets["HHPOP_target"] - county_targets["HHPOP"]
county_targets["GQPOP_diff"] = county_targets["GQPOP_target"] - county_targets["GQPOP"]
county_targets["EMPRES_diff"] = county_targets["EMPRES_target"] - county_targets["EMPRES"]
county_targets["TOTEMP_diff"] = county_targets["TOTEMP_target"] - county_targets["TOTEMP"]
logger.info("county_targets:\n%s", county_targets)

# 1. group quarters population (includes employed residents and persons by age)
tazdata_census = ctc.update_gqpop_to_county_totals(tazdata_census, county_targets, ACS_PUMS_1year)

# 2. employed residents (not including households by workers)
tazdata_census = ctc.update_tazdata_to_county_target(
    source_df=tazdata_census, target_df=county_targets, sum_var="EMPRES",
    partial_vars=["pers_occ_management", "pers_occ_professional", "pers_occ_services",
                  "pers_occ_retail", "pers_occ_manual", "pers_occ_military"],
)

# 3. total households and population
tazdata_census = ctc.update_tazdata_to_county_target(
    source_df=tazdata_census,
    target_df=county_targets.rename(columns={"TOTPOP_target": "sum_age_target"}),
    sum_var="sum_age", partial_vars=["AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P"],
)
tazdata_census = ctc.update_tazdata_to_county_target(
    source_df=tazdata_census,
    target_df=county_targets.rename(columns={"TOTPOP_target": "sum_ethnicity_target"}),
    sum_var="sum_ethnicity", partial_vars=["white_nonh", "black_nonh", "asian_nonh", "other_nonh", "hispanic"],
)
tazdata_census = ctc.update_tazdata_to_county_target(
    source_df=tazdata_census,
    target_df=county_targets.rename(columns={"TOTHH_target": "sum_DU_target"}),
    sum_var="sum_DU", partial_vars=["SFDU", "MFDU"],
)
tazdata_census = ctc.update_tazdata_to_county_target(
    source_df=tazdata_census,
    target_df=county_targets.rename(columns={"TOTHH_target": "sum_tenure_target"}),
    sum_var="sum_tenure", partial_vars=["hh_own", "hh_rent"],
)
tazdata_census = ctc.update_tazdata_to_county_target(
    source_df=tazdata_census,
    target_df=county_targets.rename(columns={"TOTHH_target": "sum_kids_target"}),
    sum_var="sum_kids", partial_vars=["hh_kids_yes", "hh_kids_no"],
)
tazdata_census = ctc.update_tazdata_to_county_target(
    source_df=tazdata_census,
    target_df=county_targets.rename(columns={"TOTHH_target": "sum_income_target"}),
    sum_var="sum_income", partial_vars=["HHINCQ1", "HHINCQ2", "HHINCQ3", "HHINCQ4"],
)
tazdata_census = ctc.update_tazdata_to_county_target(
    source_df=tazdata_census,
    target_df=county_targets.rename(columns={"TOTHH_target": "sum_size_target"}),
    sum_var="sum_size", partial_vars=["hh_size_1", "hh_size_2", "hh_size_3", "hh_size_4_plus"],
)
# Now make adjustment for HHPOP
tazdata_census = ctc.make_hhsizes_consistent_with_population(
    source_df=tazdata_census, target_df=county_targets,
    size_or_workers="hh_size", popsyn_acs_pums_5year=2021,
)
# Households by workers
tazdata_census = ctc.update_tazdata_to_county_target(
    source_df=tazdata_census,
    target_df=county_targets.rename(columns={"TOTHH_target": "sum_hhworkers_target"}),
    sum_var="sum_hhworkers", partial_vars=["hh_wrks_0", "hh_wrks_1", "hh_wrks_2", "hh_wrks_3_plus"],
)
# Now make adjustment for EMPRES
tazdata_census = ctc.make_hhsizes_consistent_with_population(
    source_df=tazdata_census, target_df=county_targets,
    size_or_workers="hh_wrks", popsyn_acs_pums_5year=2021,
)
# TOTHH = sum_size = sum_hh_wrks
tazdata_census["TOTHH"] = tazdata_census["sum_size"]
tazdata_census["TOTPOP"] = tazdata_census["HHPOP"] + tazdata_census["gqpop"]

logger.info("FINAL tazdata_census (%d rows)", len(tazdata_census))
regional_summary = tazdata_census.select_dtypes(include=[numpy.number]).sum()
logger.info("FINAL tazdata_census sums:\n%s", regional_summary)

# Remove sum variables
tazdata_census = tazdata_census.drop(columns=[
    "sum_age", "sum_groupquarters", "sum_tenure", "sum_size", "sum_hhworkers",
    "sum_kids", "sum_income", "sum_empres", "sum_ethnicity",
])

# Convert integer-valued count columns to integer dtype.  These were kept as
# floats through rounding and the county-target reallocation (which only shift
# whole units), so cast them now to make the integer values explicit in the
# outputs.  Genuine floats (SHPOP62P, and the acres/cost/enrollment fields
# joined in below) are intentionally left as floats.
INTEGER_COLUMNS = [
    "TOTHH", "HHPOP", "TOTPOP", "EMPRES",
    "AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P", "AGE62P",
    "SFDU", "MFDU", "hh_own", "hh_rent",
    "hh_size_1", "hh_size_2", "hh_size_3", "hh_size_4_plus",
    "hh_wrks_0", "hh_wrks_1", "hh_wrks_2", "hh_wrks_3_plus",
    "hh_kids_yes", "hh_kids_no",
    "gq_inst", "gq_type_univ", "gq_type_mil", "gq_type_othnon", "gqpop",
    "pers_occ_management", "pers_occ_professional", "pers_occ_services",
    "pers_occ_retail", "pers_occ_manual", "pers_occ_military",
    "white_nonh", "black_nonh", "asian_nonh", "other_nonh", "hispanic",
    "HHINCQ1", "HHINCQ2", "HHINCQ3", "HHINCQ4",
    "TOTEMP", "AGREMPN", "FPSEMPN", "HEREMPN", "MWTEMPN", "RETEMPN", "OTHEMPN",
]
int_cols_present = [c for c in INTEGER_COLUMNS if c in tazdata_census.columns]
tazdata_census[int_cols_present] = tazdata_census[int_cols_present].round().astype("int64")

# ----------------------------------------------------------------------------
# Write out ethnic variables
# ----------------------------------------------------------------------------
ethnic = tazdata_census[
    ["TAZ1454", "hispanic", "white_nonh", "black_nonh", "asian_nonh", "other_nonh",
     "TOTPOP", "COUNTY", "County_Name"]
]
ethnic_file = YEAR_DIR / "TAZ1454_Ethnicity.csv"
ethnic.to_csv(ethnic_file, index=False)
logger.info("Wrote %s", ethnic_file)

# ----------------------------------------------------------------------------
# Patchwork updates - a few carried from 2015 file + select 2023 updates
# ----------------------------------------------------------------------------
PBA2015 = pandas.read_excel(PBA_TAZ_2015, sheet_name="census2015")
PBA2015_joiner = PBA2015[["ZONE", "SD", "AREATYPE", "TOPOLOGY", "TERMINAL", "ZERO"]]

parking_2023 = pandas.read_csv(Path("2023") / "Parking" / "parking_costs_taz.csv")
enrollment_2023 = pandas.read_csv(Path("2023") / "School Enrollment" / "enrollment_taz.csv")

dev_acres_2025_file = (
    Path("M:/urban_modeling/baus/PBA50Plus/PBA50Plus_NoProject")
    / "PBA50Plus_NoProject_v38" / "travel_model_summaries"
    / "PBA50Plus_NoProject_v38_taz1_summary_2025.csv"
)
dev_acres_2025 = pandas.read_csv(dev_acres_2025_file)[["ZONE", "RESACRE", "CIACRE", "TOTACRE"]]

tazdata_census = tazdata_census.merge(parking_2023, on="TAZ1454", how="left")
tazdata_census = tazdata_census.merge(enrollment_2023, on="TAZ1454", how="left")
tazdata_census = tazdata_census.merge(
    dev_acres_2025, left_on="TAZ1454", right_on="ZONE", how="left"
).drop(columns=["ZONE"])

# PBA2015_joiner on left intentionally renames TAZ1454 key to ZONE for downstream output
tazdata_census = PBA2015_joiner.merge(
    tazdata_census, left_on="ZONE", right_on="TAZ1454", how="left"
).drop(columns=["TAZ1454"])

# Save intermediate version of data (feather instead of R .rdata)
output_file = YEAR_DIR / f"TAZ Land Use File {YEAR}.feather"
tazdata_census.reset_index(drop=True).to_feather(output_file)
logger.info("Wrote %s", output_file)

# ----------------------------------------------------------------------------
# Write out subsets of final data
# ----------------------------------------------------------------------------
tazdata_landuse = tazdata_census.copy()
tazdata_landuse["hhlds"] = tazdata_landuse["TOTHH"]
tazdata_landuse = tazdata_landuse[[
    "ZONE", "DISTRICT", "SD", "COUNTY", "TOTHH", "HHPOP", "TOTPOP", "EMPRES", "SFDU", "MFDU",
    "HHINCQ1", "HHINCQ2", "HHINCQ3", "HHINCQ4", "TOTACRE", "RESACRE", "CIACRE", "SHPOP62P",
    "TOTEMP", "AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P", "RETEMPN", "FPSEMPN",
    "HEREMPN", "AGREMPN", "MWTEMPN", "OTHEMPN", "PRKCST", "OPRKCST", "AREATYPE", "HSENROLL",
    "COLLFTE", "COLLPTE", "TERMINAL", "TOPOLOGY", "ZERO", "hhlds", "gqpop",
]]
output_file = YEAR_DIR / f"TAZ1454 {YEAR} Land Use.csv"
tazdata_landuse.to_csv(output_file, index=False)
logger.info("Wrote %s", output_file)

# District summaries for 2015 and the given year
district_summary_cols = [
    "TOTHH", "HHPOP", "TOTPOP", "EMPRES", "SFDU", "MFDU", "HHINCQ1", "HHINCQ2", "HHINCQ3",
    "HHINCQ4", "TOTEMP", "AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P", "RETEMPN",
    "FPSEMPN", "HEREMPN", "AGREMPN", "MWTEMPN", "OTHEMPN", "HSENROLL", "COLLFTE", "COLLPTE",
]
district_summary_2015 = PBA2015.groupby("DISTRICT", as_index=False)[district_summary_cols].sum()
district_summary_2015["gqpop"] = district_summary_2015["TOTPOP"] - district_summary_2015["HHPOP"]
DIR_2015 = Path("2015")
DIR_2015.mkdir(exist_ok=True)
output_file = DIR_2015 / "TAZ1454 2015 District Summary.csv"
district_summary_2015.to_csv(output_file, index=False)
logger.info("Wrote %s", output_file)

district_summary = tazdata_census.groupby("DISTRICT", as_index=False)[district_summary_cols + ["gqpop"]].sum()
output_file = YEAR_DIR / f"TAZ1454 {YEAR} District Summary.csv"
district_summary.to_csv(output_file, index=False)
logger.info("Wrote %s", output_file)

# PopSim variables
popsim_vars = tazdata_census.rename(columns={"ZONE": "TAZ", "gqpop": "gq_tot_pop"})[[
    "TAZ", "TOTHH", "TOTPOP", "hh_own", "hh_rent", "hh_size_1", "hh_size_2", "hh_size_3",
    "hh_size_4_plus", "hh_wrks_0", "hh_wrks_1", "hh_wrks_2", "hh_wrks_3_plus", "hh_kids_no",
    "hh_kids_yes", "HHINCQ1", "HHINCQ2", "HHINCQ3", "HHINCQ4", "AGE0004", "AGE0519",
    "AGE2044", "AGE4564", "AGE65P", "gq_tot_pop", "gq_type_univ", "gq_type_mil", "gq_type_othnon",
]]
output_file = YEAR_DIR / f"TAZ1454 {YEAR} Popsim Vars.csv"
popsim_vars.to_csv(output_file, index=False)
logger.info("Wrote %s", output_file)

# region popsim vars
popsim_vars_region = pandas.DataFrame(
    {"REGION": [1], "gq_num_hh_region": [popsim_vars["gq_tot_pop"].sum()]}
)
output_file = YEAR_DIR / f"TAZ1454 {YEAR} Popsim Vars Region.csv"
popsim_vars_region.to_csv(output_file, index=False)
logger.info("Wrote %s", output_file)

# county popsim vars
popsim_vars_county = tazdata_census.groupby("COUNTY", as_index=False)[[
    "pers_occ_management", "pers_occ_professional", "pers_occ_services",
    "pers_occ_retail", "pers_occ_manual", "pers_occ_military",
]].sum()
output_file = YEAR_DIR / f"TAZ1454 {YEAR} Popsim Vars County.csv"
popsim_vars_county.to_csv(output_file, index=False)
logger.info("Wrote %s", output_file)

# ----------------------------------------------------------------------------
# Tableau-friendly (long) format
# ----------------------------------------------------------------------------
long_value_cols = [
    "TOTHH", "HHPOP", "TOTPOP", "EMPRES", "SFDU", "MFDU", "HHINCQ1", "HHINCQ2", "HHINCQ3",
    "HHINCQ4", "SHPOP62P", "TOTEMP", "AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P",
    "RETEMPN", "FPSEMPN", "HEREMPN", "AGREMPN", "MWTEMPN", "OTHEMPN", "PRKCST", "OPRKCST",
    "HSENROLL", "COLLFTE", "COLLPTE", "gqpop",
]
long_id_cols = ["ZONE", "DISTRICT", "DISTRICT_NAME", "COUNTY", "County_Name", "Year"]

tazdata_census_long = tazdata_census.copy()
tazdata_census_long["Year"] = YEAR
tazdata_census_long = tazdata_census_long[long_id_cols + long_value_cols].copy()
# Cast value columns to object before melting so integer variables stay integers
# and float variables (SHPOP62P, PRKCST, ...) keep their decimals in the single
# Value column.  Otherwise melt upcasts the mixed int/float columns to float and
# every integer would be written as e.g. 1234.0.
tazdata_census_long[long_value_cols] = tazdata_census_long[long_value_cols].astype(object)
tazdata_census_long = tazdata_census_long.melt(
    id_vars=long_id_cols, value_vars=long_value_cols, var_name="Variable", value_name="Value"
)
output_file = YEAR_DIR / f"TAZ1454_{YEAR}_long.csv"
tazdata_census_long.to_csv(output_file, index=False)
logger.info("Wrote %s", output_file)

logger.info("Done.")
