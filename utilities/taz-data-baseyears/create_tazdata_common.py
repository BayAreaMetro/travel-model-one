"""
Common methods and constants for TAZ data preparation.

This is a Python port of the helper functions in common.R, used by
create_tazdata_2020_and_after.py.  It is kept separate from common.py (which
holds only simple data dictionaries shared with other scripts) because this
module has import-time side effects (reading the Census API key and the
2020 block-to-TAZ equivalency file).

Note on random sampling: several functions here use weighted random sampling
to distribute county-level control-total differences among TAZs.  This mirrors
R's slice_sample(replace=TRUE, weight_by=...).  Because R and NumPy use
different random number generators, the per-TAZ allocations produced here will
NOT be identical to the R script, even with the same seed.  However, the county
and regional control totals are matched by construction, so the results are
functionally equivalent.
"""

import logging
import pathlib

import numpy
import pandas
import requests

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Module constants (ported from common.R)
# ----------------------------------------------------------------------------

BAY_AREA_COUNTIES = [
    "Alameda",
    "Contra Costa",
    "Marin",
    "Napa",
    "San Francisco",
    "San Mateo",
    "Santa Clara",
    "Solano",
    "Sonoma",
]

# https://github.com/BayAreaMetro/modeling-website/wiki/InflationAssumptions
# Used by map_ACS5year_household_income_to_TM1_categories()
DOLLARS_2000_TO_202X = {
    2021: 1.72,
    2022: 1.81,
    2023: 1.88,
    2024: 1.93,
}

# Census geography codes
STATE_CODE = "06"
# 2-digit county FIPS codes for the nine Bay Area counties
BAY_COUNTIES_FIPS = ["001", "013", "041", "055", "075", "081", "085", "095", "097"]

CENSUS_API_KEY_FILE = "M:/Data/Census/API/api-key.txt"

BLOCK2020_TO_TAZ1454_FILE = "M:/Data/GIS layers/TM1_taz_census2020/2020block_to_TAZ1454.csv"


def read_census_api_key(key_file=CENSUS_API_KEY_FILE):
    """Read the Census API key from the given file."""
    with open(key_file, "r") as f:
        return f.read().strip()


# ----------------------------------------------------------------------------
# Census data fetching (tidycensus equivalents)
#
# tidycensus has no direct Python equivalent, and the `census` PyPI package
# hard-codes a list of supported years that excludes recent ACS vintages.  To
# avoid that limitation these helpers call the Census API directly with
# `requests`.  All return "wide" DataFrames with a GEOID column and friendly
# variable names, matching the output="wide" behavior used in the R script.
# ----------------------------------------------------------------------------

CENSUS_API_BASE = "https://api.census.gov/data"

# The Census API caps the number of variables in a single `get=` request at 50,
# so field lists are requested in chunks and merged on the geography keys.
_CENSUS_MAX_FIELDS = 45


def _census_api_request(url, params):
    """Make a Census API request and return the response as a DataFrame."""
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    return pandas.DataFrame(data[1:], columns=data[0])


def _fetch_wide_chunked(url, est_fields, geo_keys, for_clause, in_clause, api_key, extra_fields=None):
    """Fetch Census data, chunking the variable list (50-var API limit) and merging.

    url:          full endpoint URL including the year
    est_fields:   list of estimate variable codes to request (e.g. "B19001_001E")
    geo_keys:     geography key columns returned by the API to merge on
    for_clause:   the `for=` predicate (e.g. "tract:*")
    in_clause:    the `in=` predicate (e.g. "state:06 county:001") or None
    api_key:      Census API key
    extra_fields: optional additional fields (e.g. ["NAME"]) requested in the
        first chunk only
    """
    merged = None
    first = True
    for i in range(0, len(est_fields), _CENSUS_MAX_FIELDS):
        chunk = list(est_fields[i:i + _CENSUS_MAX_FIELDS])
        get_fields = (list(extra_fields) if (first and extra_fields) else []) + chunk
        params = {"get": ",".join(get_fields), "for": for_clause, "key": api_key}
        if in_clause:
            params["in"] = in_clause
        chunk_df = _census_api_request(url, params)

        keep = [k for k in geo_keys if k in chunk_df.columns]
        if first and extra_fields:
            keep = keep + [f for f in extra_fields if f in chunk_df.columns]
        keep = keep + [c for c in chunk if c in chunk_df.columns]
        chunk_df = chunk_df[keep]

        if merged is None:
            merged = chunk_df
        else:
            merged = merged.merge(
                chunk_df, on=[k for k in geo_keys if k in merged.columns], how="outer"
            )
        first = False
    return merged


def _finalize_acs_wide(df, variables, geoid_parts):
    """Build GEOID from geography parts and rename estimate columns to friendly names."""
    df = df.copy()
    df["GEOID"] = df[geoid_parts[0]].astype(str)
    for part in geoid_parts[1:]:
        df["GEOID"] = df["GEOID"] + df[part].astype(str)

    rename = {}
    for friendly, code in variables.items():
        est_col = code + "E"
        rename[est_col] = friendly
        df[est_col] = pandas.to_numeric(df[est_col], errors="coerce")
    df = df.rename(columns=rename)
    return df


def get_acs5_blockgroup_wide(api_key, variables, year):
    """Fetch ACS 5-year block group data for the Bay Area counties, wide format."""
    url = "{}/{}/acs/acs5".format(CENSUS_API_BASE, year)
    geo_keys = ["state", "county", "tract", "block group"]
    est_fields = [code + "E" for code in variables.values()]
    frames = []
    for county in BAY_COUNTIES_FIPS:
        frames.append(_fetch_wide_chunked(
            url, est_fields, geo_keys, "block group:*",
            "state:{} county:{}".format(STATE_CODE, county), api_key,
        ))
    df = pandas.concat(frames, ignore_index=True)
    logger.info("Fetched %d ACS5 block group rows for year %d", len(df), year)
    df = _finalize_acs_wide(df, variables, geo_keys)
    return df[["GEOID"] + list(variables.keys())]


def get_acs5_tract_wide(api_key, variables, year):
    """Fetch ACS 5-year tract data for the Bay Area counties, wide format."""
    url = "{}/{}/acs/acs5".format(CENSUS_API_BASE, year)
    geo_keys = ["state", "county", "tract"]
    est_fields = [code + "E" for code in variables.values()]
    frames = []
    for county in BAY_COUNTIES_FIPS:
        frames.append(_fetch_wide_chunked(
            url, est_fields, geo_keys, "tract:*",
            "state:{} county:{}".format(STATE_CODE, county), api_key,
        ))
    df = pandas.concat(frames, ignore_index=True)
    logger.info("Fetched %d ACS5 tract rows for year %d", len(df), year)
    df = _finalize_acs_wide(df, variables, geo_keys)
    return df[["GEOID"] + list(variables.keys())]


def get_acs1_county_wide(api_key, variables, year):
    """Fetch ACS 1-year county data for the Bay Area counties, wide format.

    Also returns a County_Name column (NAME with " County, California" removed).
    """
    url = "{}/{}/acs/acs1".format(CENSUS_API_BASE, year)
    geo_keys = ["state", "county"]
    est_fields = [code + "E" for code in variables.values()]
    counties = ",".join(BAY_COUNTIES_FIPS)
    df = _fetch_wide_chunked(
        url, est_fields, geo_keys, "county:{}".format(counties),
        "state:{}".format(STATE_CODE), api_key, extra_fields=["NAME"],
    )
    logger.info("Fetched %d ACS1 county rows for year %d", len(df), year)
    df = _finalize_acs_wide(df, variables, geo_keys)
    df["County_Name"] = df["NAME"].str.replace(" County, California", "", regex=False)
    return df[["GEOID", "County_Name"] + list(variables.keys())]


def get_decennial_dhc_tract_wide(api_key, variables, year=2020):
    """Fetch 2020 Decennial DHC tract data for the Bay Area counties, wide format.

    variables is {friendly_name: dhc_code} (e.g. {"gq_inst_m_0017": "PCT19_004N"}).
    """
    url = "{}/{}/dec/dhc".format(CENSUS_API_BASE, year)
    geo_keys = ["state", "county", "tract"]
    codes = list(variables.values())
    friendly_by_code = {code: friendly for friendly, code in variables.items()}

    frames = []
    for county in BAY_COUNTIES_FIPS:
        frames.append(_fetch_wide_chunked(
            url, codes, geo_keys, "tract:*",
            "state:{} county:{}".format(STATE_CODE, county), api_key,
        ))
    df = pandas.concat(frames, ignore_index=True)
    df["GEOID"] = df["state"].astype(str) + df["county"].astype(str) + df["tract"].astype(str)
    for code in codes:
        df[code] = pandas.to_numeric(df[code], errors="coerce")
    df = df.rename(columns=friendly_by_code)
    logger.info("Fetched %d DHC tract rows for year %d", len(df), year)
    return df[["GEOID"] + list(variables.keys())]


def load_block2020_taz1454(block_file=BLOCK2020_TO_TAZ1454_FILE):
    """Load the 2020 block/TAZ equivalency file.

    Creates block group ID and tract ID string fields for later joining to
    ACS data.  Removes the San Quentin block and moves other blocks with
    population in TAZ 1439 to adjacent TAZ 1438.

    Returns a DataFrame with columns:
      GEOID, NAME, variable, blockgroup, tract, TAZ1454, SUPERD, block_POPULATION
    """
    block_df = pandas.read_csv(
        block_file,
        dtype={"GEOID": str, "blockgroup": str, "tract": str},
    )
    # remove San Quentin block
    san_quentin = "Block 1007, Block Group 1, Census Tract 1220, Marin County, California"
    block_df = block_df.loc[block_df["NAME"] != san_quentin].copy()

    # move other blocks with population in TAZ 1439 to adjacent 1438
    move_to_1438 = [
        "Block 1006, Block Group 1, Census Tract 1220, Marin County, California",
        "Block 1002, Block Group 1, Census Tract 1220, Marin County, California",
    ]
    block_df.loc[block_df["NAME"].isin(move_to_1438), "TAZ1454"] = 1438

    logger.info("BLOCK2020_TAZ1454:\n%s", block_df.head())
    return block_df


# ----------------------------------------------------------------------------
# Rounding / scaling helpers
# ----------------------------------------------------------------------------

def fix_rounding_artifacts(df, id_var, sum_var, partial_vars, logging_on=True):
    """Fix rounding artifacts for columns which should sum to a total column.

    For example, if col_a = 2.3 => 2, col_b = 3.4 => 3, col_c = 4.3 => 4, but
    tot_col = 10 while the sum of the rounded cols is only 9. This allocates the
    additional 1 to the largest col (col_c).

    Ties on the max value go to the first partial variable listed (matching R's
    which.max).
    """
    logger.info(
        "fix_rounding_artifacts(id_var=%s, sum_var=%s, partial_vars=%s)",
        id_var, sum_var, partial_vars,
    )
    original_order = list(df.columns)

    my_df = df[[id_var, sum_var] + list(partial_vars)].copy()
    # column name with the max value out of partial_vars (first on ties)
    my_df["max_col"] = my_df[partial_vars].idxmax(axis=1)
    # discrepancy between partial vars and sum_var to be resolved
    my_df["diff_col"] = my_df[sum_var] - my_df[partial_vars].sum(axis=1)

    if logging_on:
        logger.info(
            "fix_rounding_artifacts(): Rows needing updating:\n%s",
            my_df.loc[my_df["diff_col"] != 0],
        )

    # for each partial var, update the value by diff if max_col matches
    for partial_name in partial_vars:
        my_df[partial_name] = my_df[partial_name] + numpy.where(
            my_df["max_col"] == partial_name, my_df["diff_col"], 0
        )

    # verify by recalculating diff_col
    recomputed_diff = my_df[sum_var] - my_df[partial_vars].sum(axis=1)
    assert (recomputed_diff == 0).all(), "fix_rounding_artifacts failed to reconcile"

    # select to just id_var, partial_vars
    my_df = my_df[[id_var] + list(partial_vars)]

    # replace the partial_vars in the original df
    df = df.drop(columns=list(partial_vars)).merge(my_df, on=id_var, how="left")

    # keep columns in same order
    return df[original_order]


def scale_data_to_targets(source_df, target_df, id_var, sum_var, partial_vars, logging_on=False):
    """Scale a column in source_df to match target_df, including component columns.

    source_df: DataFrame with columns id_var, sum_var, partial_vars where
        partial_vars sum to sum_var
    target_df: DataFrame with columns id_var, sum_var + "_target"
    Returns: source_df with sum_var == sum_var_target and partial_vars keeping
        their distribution but still adding to sum_var.
    """
    logger.info(
        "scale_data_to_targets(id_var=%s, sum_var=%s, partial_vars=%s)",
        id_var, sum_var, partial_vars,
    )
    sum_var_target = sum_var + "_target"
    source_df = source_df.merge(
        target_df[[id_var, sum_var_target]], on=id_var, how="left"
    )
    if logging_on:
        logger.info(
            "scale_data_to_targets(): source_df before:\n%s",
            source_df[[id_var, sum_var, sum_var_target] + list(partial_vars)],
        )

    # scale the sum_var
    target_scale = source_df[sum_var_target] / source_df[sum_var]
    source_df[sum_var] = (source_df[sum_var] * target_scale).round().astype(int)
    # and the partial vars, rounded
    for partial_name in partial_vars:
        source_df[partial_name] = (source_df[partial_name] * target_scale).round().astype(int)

    # fix rounding artifacts
    source_df = fix_rounding_artifacts(source_df, id_var, sum_var, partial_vars, logging_on)

    if logging_on:
        logger.info(
            "scale_data_to_targets(): source_df after:\n%s",
            source_df[[id_var, sum_var, sum_var_target] + list(partial_vars)],
        )
    # remove target column from source
    return source_df.drop(columns=[sum_var_target])


def update_disaggregate_data_to_aggregate_targets(
    source_df, target_df, disagg_id_var, agg_id_var, col_name
):
    """Update disaggregate (TAZ) data to match aggregate (county) targets.

    * source_df must have columns: disagg_id_var (unique), agg_id_var (not
      unique), col_name
    * target_df must have columns: agg_id_var (unique), col_name + "_diff"

    Increases or decreases component source_df rows by col_name_diff, keeping the
    distribution the same across rows (TAZs) via weighted random sampling.
    """
    logger.info(
        "update_disaggregate_data_to_aggregate_targets(disagg_id_var=%s, agg_id_var=%s, col_name=%s)",
        disagg_id_var, agg_id_var, col_name,
    )
    diff_col_name = col_name + "_diff"

    for agg_id_value in target_df[agg_id_var].tolist():
        diff_value = int(
            target_df.loc[target_df[agg_id_var] == agg_id_value, diff_col_name].iloc[0]
        )
        if diff_value == 0:
            continue

        # rows for this agg_id_value from which to sample (positive col only)
        filtered_source_df = source_df[[disagg_id_var, agg_id_var, col_name]]
        filtered_source_df = filtered_source_df[
            (filtered_source_df[agg_id_var] == agg_id_value)
            & (filtered_source_df[col_name] > 0)
        ]

        logger.info(
            "  Processing agg_id_value=%20s with diff=%8d; filtered_source_df has %4d rows",
            agg_id_value, diff_value, len(filtered_source_df),
        )
        if len(filtered_source_df) == 0:
            continue

        # sample the rows (TAZs) to modify, weighted by col_name
        modify_sample = filtered_source_df.sample(
            n=abs(diff_value),
            replace=True,
            weights=filtered_source_df[col_name],
        )
        # aggregate to TAZ
        modify_sample = (
            modify_sample.groupby(disagg_id_var).size().reset_index(name="TO_MODIFY")
        )

        # join to source, which now has column TO_MODIFY
        source_df = source_df.merge(modify_sample, on=disagg_id_var, how="left")
        source_df["TO_MODIFY"] = source_df["TO_MODIFY"].fillna(0).astype(int)

        # make the modification
        if diff_value > 0:
            source_df[col_name] = source_df[col_name] + source_df["TO_MODIFY"]
        else:
            source_df[col_name] = source_df[col_name] - source_df["TO_MODIFY"]
            source_df[col_name] = source_df[col_name].clip(lower=0)
        source_df = source_df.drop(columns=["TO_MODIFY"])

    return source_df


def update_tazdata_to_county_target(source_df, target_df, sum_var, partial_vars):
    """Generic county-target implementation.

    source_df: a TAZ-based DataFrame including id variables County_Name, TAZ1454
        and sum_var comprised of partial_vars.
    target_df: a county-based DataFrame including columns County_Name,
        sum_var + "_target".
    """
    logger.info(
        "########## update_tazdata_to_county_target(sum_var=%s, partial_vars=%s) ##########",
        sum_var, partial_vars,
    )
    sum_var_target = sum_var + "_target"
    target_df = target_df[["County_Name", sum_var_target]].copy()
    logger.info(
        "target_df %s total=%d", sum_var_target, int(target_df[sum_var_target].sum())
    )

    # summarize current totals for sum_var and partial_vars
    source_county_summary = (
        source_df.groupby("County_Name")[[sum_var] + list(partial_vars)]
        .sum()
        .reset_index()
    )
    logger.info(
        "source_county_summary from source_df (regional total=%d):\n%s",
        int(source_county_summary[sum_var].sum()), source_county_summary,
    )

    # figure out target partial_vars by county
    target_partials_county = scale_data_to_targets(
        source_df=source_county_summary,
        target_df=target_df,
        id_var="County_Name",
        sum_var=sum_var,
        partial_vars=partial_vars,
    )
    # rename scaled columns to *_target
    rename_to_target = {c: c + "_target" for c in [sum_var] + list(partial_vars)}
    target_partials_county = target_partials_county.rename(columns=rename_to_target)

    # join with original to calculate diffs
    target_partials_county = target_partials_county.merge(
        source_county_summary, on="County_Name", how="left"
    )
    for col in [sum_var] + list(partial_vars):
        target_partials_county[col + "_diff"] = (
            target_partials_county[col + "_target"] - target_partials_county[col]
        )

    logger.info("target_partials_county:\n%s", target_partials_county)

    # apply to TAZs for each partial_var
    for partial_var in partial_vars:
        source_df = update_disaggregate_data_to_aggregate_targets(
            source_df, target_partials_county, "TAZ1454", "County_Name", partial_var
        )
    source_df[sum_var] = source_df[list(partial_vars)].sum(axis=1)

    logger.info(
        "Resulting %s and %s by county:\n%s",
        sum_var, partial_vars,
        source_df.groupby("County_Name")[[sum_var] + list(partial_vars)].sum().reset_index(),
    )
    return source_df


# ----------------------------------------------------------------------------
# Household income mapping (reads PUMS)
# ----------------------------------------------------------------------------

def _pums_paths(acs_year):
    """Return (feather_path, dataframe_var_hint) for the 5-year PUMS ending in acs_year."""
    pums_dir = "PUMS {}-{:02d}".format(acs_year - 4, acs_year % 100)
    pums_file = "hbayarea{:02d}{:02d}.feather".format((acs_year - 4) % 100, acs_year % 100)
    return pathlib.Path("M:/Data/Census/PUMS") / pums_dir / pums_file


def map_ACS5year_household_income_to_TM1_categories(acs_year):
    """Map ACS 5-year household income categories to TM1 income quartiles.

    Uses the ACS 5-year PUMS data (household file) consistent with the given
    ACS 5-year to figure out how to split each ACS income category into travel
    model income categories (HHINCQ1-4), based on PUMS-weighted shares.

    Returns a DataFrame with columns:
      householdinc_acs_cat: ACS category (e.g. "hhinc000_010")
      HHINCQ:               travel model category (HHINCQ1-4)
      acs_to_hhincq_share:  share of the ACS category in that HHINCQ category
    """
    logger.info(
        "########## map_ACS5year_household_income_to_TM1_categories(%d) start ##########",
        acs_year,
    )
    pums_path = _pums_paths(acs_year)
    pums_hh = pandas.read_feather(pums_path)
    logger.info("Loaded %d rows from %s", len(pums_hh), pums_path)

    pums_hh = pums_hh[["NP", "HINCP", "ADJINC", "WGTP"]].copy()
    pums_hh = pums_hh[
        (pums_hh["NP"] > 0)  # filter out vacant units
        & (pums_hh["WGTP"] > 0)  # filter out group quarter placeholder records
        & (pums_hh["HINCP"] >= 0)  # filter out negative household income
    ].copy()

    # ADJINC/1e6 is the inflation adjustment factor to 202X dollars (X depends on acs_year)
    pums_hh["householdinc_202xdollars"] = (pums_hh["ADJINC"] / 1_000_000.0) * pums_hh["HINCP"]
    pums_hh["householdinc_2000dollars"] = (
        pums_hh["householdinc_202xdollars"] / DOLLARS_2000_TO_202X[acs_year]
    )

    # ACS categories from household income in 202X dollars
    inc = pums_hh["householdinc_202xdollars"]
    acs_bins = [
        (0, 10000, "hhinc000_010"),
        (10000, 15000, "hhinc010_015"),
        (15000, 20000, "hhinc015_020"),
        (20000, 25000, "hhinc020_025"),
        (25000, 30000, "hhinc025_030"),
        (30000, 35000, "hhinc030_035"),
        (35000, 40000, "hhinc035_040"),
        (40000, 45000, "hhinc040_045"),
        (45000, 50000, "hhinc045_050"),
        (50000, 60000, "hhinc050_060"),
        (60000, 75000, "hhinc060_075"),
        (75000, 100000, "hhinc075_100"),
        (100000, 125000, "hhinc100_125"),
        (125000, 150000, "hhinc125_150"),
        (150000, 200000, "hhinc150_200"),
    ]
    pums_hh["householdinc_acs_cat"] = numpy.nan
    for lower, upper, label in acs_bins:
        pums_hh.loc[(inc >= lower) & (inc < upper), "householdinc_acs_cat"] = label
    pums_hh.loc[inc >= 200000, "householdinc_acs_cat"] = "hhinc200p"

    # TM1 categories from household income in 2000 dollars
    inc2000 = pums_hh["householdinc_2000dollars"]
    pums_hh["householdinc_TM1_cat"] = numpy.nan
    pums_hh.loc[(inc2000 >= 0) & (inc2000 < 30000), "householdinc_TM1_cat"] = "HHINCQ1"
    pums_hh.loc[(inc2000 >= 30000) & (inc2000 < 60000), "householdinc_TM1_cat"] = "HHINCQ2"
    pums_hh.loc[(inc2000 >= 60000) & (inc2000 < 100000), "householdinc_TM1_cat"] = "HHINCQ3"
    pums_hh.loc[inc2000 >= 100000, "householdinc_TM1_cat"] = "HHINCQ4"

    # calculate weighted shares
    pums_hhinc_cat = (
        pums_hh.groupby(["householdinc_acs_cat", "householdinc_TM1_cat"])["WGTP"]
        .sum()
        .reset_index()
    )
    # move householdinc_TM1_cat values to columns
    pums_hhinc_cat = pums_hhinc_cat.pivot_table(
        index="householdinc_acs_cat",
        columns="householdinc_TM1_cat",
        values="WGTP",
        fill_value=0,
    ).reset_index()
    pums_hhinc_cat.columns.name = None

    hhincq_cols = ["HHINCQ1", "HHINCQ2", "HHINCQ3", "HHINCQ4"]
    for col in hhincq_cols:
        if col not in pums_hhinc_cat.columns:
            pums_hhinc_cat[col] = 0
    tot_wgtp = pums_hhinc_cat[hhincq_cols].sum(axis=1)
    for col in hhincq_cols:
        pums_hhinc_cat[col] = pums_hhinc_cat[col] / tot_wgtp

    # pivot longer for joining
    pums_hhinc_cat = pums_hhinc_cat.melt(
        id_vars="householdinc_acs_cat",
        value_vars=hhincq_cols,
        var_name="HHINCQ",
        value_name="acs_to_hhincq_share",
    )
    pums_hhinc_cat = pums_hhinc_cat[pums_hhinc_cat["acs_to_hhincq_share"] > 0].copy()

    logger.info("PUMS_hhinc_cat:\n%s", pums_hhinc_cat)
    logger.info(
        "########## map_ACS5year_household_income_to_TM1_categories(%d) end ##########",
        acs_year,
    )
    return pums_hhinc_cat


# ----------------------------------------------------------------------------
# Group quarters county targets (reads PUMS 1-year summary)
# ----------------------------------------------------------------------------

def update_gqpop_to_county_totals(source_df, target_gq_df, acs_pums_1year):
    """Update GQ population in source_df to totals in target_gq_df.

    source_df: TAZ-based DataFrame including County_Name, TAZ1454,
        gq_type_[univ,mil,othnon], gqpop
    target_gq_df: DataFrame with columns County_Name, GQPOP_target
    acs_pums_1year: year for the target; uses ACS PUMS 1-year distributions for
        GQ workers to make these updates.
    """
    logger.info("########## update_gqpop_to_county_totals(%d) ##########", acs_pums_1year)
    target_df = target_gq_df[["County_Name", "GQPOP_target"]].copy()
    logger.info(
        "target_df with GQPOP_target total=%d:\n%s", int(target_df["GQPOP_target"].sum()), target_df
    )

    # this file is output by
    # census-tools-for-planning/analysis_by_topic/summarize_noninst_group_quarters.R
    gq_file = pathlib.Path("M:/Data/Census/PUMS") / "PUMS {}".format(acs_pums_1year) / "summaries" / "noninst_gq_summary.csv"
    gq_summary = pandas.read_csv(gq_file)
    logger.info("Read %d rows from %s", len(gq_summary), gq_file)

    # calculate gq worker share of total
    gq_summary["worker_share"] = gq_summary["EMPRES"] / gq_summary["gqpop"]

    # target_EMPRES will be target * worker_share
    target_df = target_df.merge(
        gq_summary[["County_Name", "worker_share"]], on="County_Name", how="left"
    )
    target_df["EMPRES_target"] = (target_df["GQPOP_target"] * target_df["worker_share"]).round().astype(int)
    logger.info("target_df with EMPRES_target:\n%s", target_df)

    # scale PUMS summary to the target total: gqtype distribution
    detailed = scale_data_to_targets(
        source_df=gq_summary,
        target_df=target_df.rename(columns={"GQPOP_target": "gqpop_target"}),
        id_var="County_Name",
        sum_var="gqpop",
        partial_vars=["gq_type_univ", "gq_type_mil", "gq_type_othnon"],
    )
    # scale PUMS summary to the target total: age distribution
    detailed["sum_age"] = detailed[["AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P"]].sum(axis=1)
    detailed = scale_data_to_targets(
        source_df=detailed,
        target_df=target_df.rename(columns={"GQPOP_target": "sum_age_target"}),
        id_var="County_Name",
        sum_var="sum_age",
        partial_vars=["AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P"],
    )
    # scale PUMS summary to the target total: occupation distribution
    detailed = scale_data_to_targets(
        source_df=detailed,
        target_df=target_df,
        id_var="County_Name",
        sum_var="EMPRES",
        partial_vars=[
            "pers_occ_management", "pers_occ_professional", "pers_occ_services",
            "pers_occ_retail", "pers_occ_manual", "pers_occ_military",
        ],
    )
    detailed = detailed.drop(columns=["worker_share"])
    logger.info("After adjusting to given target, detailed_GQ_county_targets:\n%s", detailed)

    # summarize source to county and join with targets and calculate diffs
    source_county_df = (
        source_df.groupby("County_Name")[["gq_type_univ", "gq_type_mil", "gq_type_othnon", "gqpop"]]
        .sum()
        .reset_index()
    )
    detailed_targets = detailed[["County_Name", "gq_type_univ", "gq_type_mil", "gq_type_othnon", "gqpop"]].rename(
        columns={
            "gq_type_univ": "gq_type_univ_target",
            "gq_type_mil": "gq_type_mil_target",
            "gq_type_othnon": "gq_type_othnon_target",
            "gqpop": "gqpop_target",
        }
    )
    source_county_df = source_county_df.merge(detailed_targets, on="County_Name", how="left")
    for col in ["gq_type_univ", "gq_type_mil", "gq_type_othnon", "gqpop"]:
        source_county_df[col + "_diff"] = source_county_df[col + "_target"] - source_county_df[col]
    logger.info("source_county_df:\n%s", source_county_df)

    # modify gq types based on diffs
    for col in ["gq_type_univ", "gq_type_mil", "gq_type_othnon"]:
        source_df = update_disaggregate_data_to_aggregate_targets(
            source_df, source_county_df, "TAZ1454", "County_Name", col
        )
    source_df["gqpop"] = source_df[["gq_type_univ", "gq_type_mil", "gq_type_othnon"]].sum(axis=1)

    logger.info(
        "Resulting group quarters by county:\n%s",
        source_df.groupby("County_Name")[["gq_type_univ", "gq_type_mil", "gq_type_othnon", "gqpop"]].sum().reset_index(),
    )
    return source_df


# ----------------------------------------------------------------------------
# Household size / worker consistency with population
# ----------------------------------------------------------------------------

def make_hhsizes_consistent_with_population(source_df, target_df, size_or_workers, popsyn_acs_pums_5year):
    """Shift households between size/worker categories to match target persons.

    After naively updating household size partials (hh_size_* or hh_wrks_*) to
    achieve target TOTHH, they may be inconsistent with persons (HHPOP or
    EMPRES). This keeps total households constant, but shifts households between
    categories to achieve target persons.

    size_or_workers: one of "hh_size" or "hh_wrks"
    source_df: TAZ-based DataFrame with County_Name, TAZ1454, the sum_var and
        partial_vars, and the pop_var to match (HHPOP or EMPRES).
    target_df: DataFrame with County_Name, pop_var + "_target".
    popsyn_acs_pums_5year: ACS5 year PUMS used for population synthesis, used to
        estimate persons/workers in the largest bucket by county.
    """
    logger.info(
        "########## make_hhsizes_consistent_with_population(%s, popsyn_acs_pums_5year=%d) ##########",
        size_or_workers, popsyn_acs_pums_5year,
    )
    popsyn_dir = pathlib.Path(
        "M:/Data/Census/PUMS/PUMS {}-{:02d}/summaries".format(
            popsyn_acs_pums_5year - 4, popsyn_acs_pums_5year % 100
        )
    )
    if size_or_workers == "hh_size":
        pop_var = "HHPOP"
        sum_var = "sum_size"
        partial_vars = ["hh_size_1", "hh_size_2", "hh_size_3", "hh_size_4_plus"]
        big_cat_file = popsyn_dir / "county_hh_size_summary_wide.csv"
        big_cat_col = "avg_persons.hh.hh_size_4plus"
    elif size_or_workers == "hh_wrks":
        pop_var = "EMPRES"
        sum_var = "sum_hhworkers"
        partial_vars = ["hh_wrks_0", "hh_wrks_1", "hh_wrks_2", "hh_wrks_3_plus"]
        big_cat_file = popsyn_dir / "county_hh_worker_summary_wide.csv"
        big_cat_col = "avg_workers.hh.hh_wrks14_3plus"
    else:
        raise NotImplementedError(size_or_workers)

    pop_var_target = pop_var + "_target"
    target_df = target_df[["County_Name", pop_var_target]].copy()
    logger.info("target_df (%s total=%d):\n%s", pop_var_target, int(target_df[pop_var_target].sum()), target_df)

    # read the big cat file to get the avg size of the biggest category
    big_cat_df = pandas.read_csv(big_cat_file)
    logger.info("Read %s", big_cat_file)
    big_cat_df = big_cat_df[["County_Name", big_cat_col]].rename(columns={big_cat_col: "big_cat_avg"})

    # join to source_df and use to estimate pop_var
    pop_var_est = pop_var + "_est"
    source_df = source_df.merge(big_cat_df, on="County_Name", how="left")
    if size_or_workers == "hh_size":
        source_df[pop_var_est] = (
            source_df["hh_size_1"] * 1
            + source_df["hh_size_2"] * 2
            + source_df["hh_size_3"] * 3
            + source_df["hh_size_4_plus"] * source_df["big_cat_avg"]
        )
    else:
        source_df[pop_var_est] = (
            source_df["hh_wrks_1"] * 1
            + source_df["hh_wrks_2"] * 2
            + source_df["hh_wrks_3_plus"] * source_df["big_cat_avg"]
        )

    # summarize current totals for sum_var and partial_vars, keeping big_cat_avg
    source_county_summary = (
        source_df.groupby(["County_Name", "big_cat_avg"])[[sum_var] + partial_vars + [pop_var_est]]
        .sum()
        .reset_index()
    )
    source_county_summary = source_county_summary.merge(target_df, on="County_Name", how="left")
    pop_var_diff = pop_var + "_diff"
    source_county_summary[pop_var_diff] = (
        source_county_summary[pop_var_target] - source_county_summary[pop_var_est]
    )
    # avg pop value of category change
    if size_or_workers == "hh_size":
        source_county_summary["avg_incr_value"] = (
            source_county_summary["hh_size_1"]
            + source_county_summary["hh_size_2"]
            + (source_county_summary["hh_size_3"] * (source_county_summary["big_cat_avg"] - 3))
        ) / (source_county_summary["hh_size_1"] + source_county_summary["hh_size_2"] + source_county_summary["hh_size_3"])
        source_county_summary["avg_decr_value"] = (
            source_county_summary["hh_size_2"]
            + source_county_summary["hh_size_3"]
            + (source_county_summary["hh_size_4_plus"] * (source_county_summary["big_cat_avg"] - 3))
        ) / (source_county_summary["hh_size_2"] + source_county_summary["hh_size_3"] + source_county_summary["hh_size_4_plus"])
    else:
        source_county_summary["avg_incr_value"] = (
            source_county_summary["hh_wrks_0"]
            + source_county_summary["hh_wrks_1"]
            + (source_county_summary["hh_wrks_2"] * (source_county_summary["big_cat_avg"] - 2))
        ) / (source_county_summary["hh_wrks_0"] + source_county_summary["hh_wrks_1"] + source_county_summary["hh_wrks_2"])
        source_county_summary["avg_decr_value"] = (
            source_county_summary["hh_wrks_1"]
            + source_county_summary["hh_wrks_2"]
            + (source_county_summary["hh_wrks_3_plus"] * (source_county_summary["big_cat_avg"] - 2))
        ) / (source_county_summary["hh_wrks_1"] + source_county_summary["hh_wrks_2"] + source_county_summary["hh_wrks_3_plus"])

    logger.info("source_county_summary:\n%s", source_county_summary)

    # loop through counties, building replacement TAZ rows
    new_taz_rows = []
    for county in source_county_summary["County_Name"].tolist():
        county_row = source_county_summary[source_county_summary["County_Name"] == county].iloc[0]
        diff_value = county_row[pop_var_diff]

        # rows for this county from which to sample
        filtered_source_df = source_df[["TAZ1454", "County_Name", sum_var] + partial_vars + [pop_var_est]]
        filtered_source_df = filtered_source_df[
            (filtered_source_df["County_Name"] == county) & (filtered_source_df[pop_var_est] > 0)
        ]

        if diff_value > 0:
            avg_change = county_row["avg_incr_value"]
        else:
            avg_change = county_row["avg_decr_value"]
        slice_size = int(abs(diff_value / avg_change)) if avg_change != 0 else 0

        logger.info(
            "  Processing county %13s (big_cat_avg=%.2f avg_change=%.2f) with diff=%6.0f slice_size=%6d; filtered_source_df has %4d rows",
            county, county_row["big_cat_avg"], avg_change, diff_value, slice_size, len(filtered_source_df),
        )
        if slice_size == 0 or len(filtered_source_df) == 0:
            continue

        modify_sample = filtered_source_df.sample(
            n=slice_size, replace=True, weights=filtered_source_df[pop_var_est]
        )
        # aggregate to TAZ
        modify_sample = modify_sample.groupby("TAZ1454").size().reset_index(name="TO_MODIFY")

        # for each TAZ, pick which category to move down/up from
        for taz in modify_sample["TAZ1454"].tolist():
            taz_long = filtered_source_df[filtered_source_df["TAZ1454"] == taz][partial_vars].iloc[0]
            taz_long = taz_long.reset_index()
            taz_long.columns = ["category", "num_hh"]

            taz_diff = int(modify_sample[modify_sample["TAZ1454"] == taz]["TO_MODIFY"].iloc[0])

            # if reducing, don't include smallest category; if adding, don't include largest
            taz_to_sample = taz_long.copy()
            if diff_value < 0:
                taz_diff = -1 * taz_diff
                taz_to_sample.loc[taz_to_sample["category"] == partial_vars[0], "num_hh"] = 0
            else:
                taz_to_sample.loc[taz_to_sample["category"] == partial_vars[-1], "num_hh"] = 0

            # nothing to sample from
            if taz_to_sample["num_hh"].sum() <= 0:
                continue

            # sample categories to move and aggregate to category
            category_sample = taz_to_sample.sample(
                n=abs(taz_diff), replace=True, weights=taz_to_sample["num_hh"]
            )
            category_sample = category_sample.groupby("category").size().reset_index(name="move_from")
            category_sample["move_from"] = -1 * category_sample["move_from"]

            taz_long = taz_long.merge(category_sample, on="category", how="left")

            # if moving down a category (taz_diff<0), lead; else lag
            if taz_diff < 0:
                taz_long["move_to"] = -1 * taz_long["move_from"].shift(-1)
            else:
                taz_long["move_to"] = -1 * taz_long["move_from"].shift(1)
            taz_long["move_from"] = taz_long["move_from"].fillna(0)
            taz_long["move_to"] = taz_long["move_to"].fillna(0)

            # apply it
            taz_long["num_hh"] = taz_long["num_hh"] + taz_long["move_from"] + taz_long["move_to"]
            if (taz_long["num_hh"] < 0).any():
                logger.warning("Negative resulting num_hh in TAZ %s:\n%s", taz, taz_long)
                taz_long["num_hh"] = taz_long["num_hh"].clip(lower=0)

            taz_wide = {"County_Name": county, "TAZ1454": taz}
            for _, r in taz_long.iterrows():
                taz_wide[r["category"]] = r["num_hh"]
            new_taz_rows.append(taz_wide)

    new_taz_tibble = pandas.DataFrame(new_taz_rows)
    logger.info("full new_taz_tibble (%d rows)", len(new_taz_tibble))

    # join to source_df and replace where the join succeeded and new value isn't na
    if len(new_taz_tibble) > 0:
        source_df = source_df.merge(
            new_taz_tibble, on=["County_Name", "TAZ1454"], how="left", suffixes=("", ".new")
        )
        for partial_var in partial_vars:
            new_col = partial_var + ".new"
            if new_col in source_df.columns:
                source_df[partial_var] = numpy.where(
                    source_df[new_col].notna(), source_df[new_col], source_df[partial_var]
                )
                source_df = source_df.drop(columns=[new_col])

    # recalculate sum_var and pop_var (now estimated)
    if size_or_workers == "hh_size":
        source_df[sum_var] = source_df[["hh_size_1", "hh_size_2", "hh_size_3", "hh_size_4_plus"]].sum(axis=1)
        source_df[pop_var] = (
            source_df["hh_size_1"] * 1
            + source_df["hh_size_2"] * 2
            + source_df["hh_size_3"] * 3
            + source_df["hh_size_4_plus"] * source_df["big_cat_avg"]
        ).round()
    else:
        source_df[sum_var] = source_df[["hh_wrks_0", "hh_wrks_1", "hh_wrks_2", "hh_wrks_3_plus"]].sum(axis=1)
        source_df[pop_var] = (
            source_df["hh_wrks_1"] * 1
            + source_df["hh_wrks_2"] * 2
            + source_df["hh_wrks_3_plus"] * source_df["big_cat_avg"]
        ).round()

    source_df = source_df.drop(columns=["big_cat_avg", pop_var_est])
    return source_df
