"""Auto ownership calibration data helpers."""

import os
import requests
import pandas as pd
from dotenv import load_dotenv
from calib_report import tables

load_dotenv()

COUNTY_NAMES = {
    "001": "Alameda", "013": "Contra Costa", "041": "Marin",
    "055": "Napa", "075": "San Francisco", "081": "San Mateo",
    "085": "Santa Clara", "095": "Solano", "097": "Sonoma",
}

OWNERSHIP_COLS = {
    "B08201_001E": "total_households",
    "B08201_002E": "0_vehicles",
    "B08201_003E": "1_vehicle",
    "B08201_004E": "2_vehicles",
    "B08201_005E": "3_vehicles",
    "B08201_006E": "4plus_vehicles",
}

VALUE_COLS = [
    "0_vehicles", "1_vehicle", "2_vehicles",
    "3_vehicles", "4plus_vehicles", "total_households",
]

CATEGORY_LABELS = {
    "county_name": "County",
    "0_vehicles": "0 Vehicles",
    "1_vehicle": "1 Vehicle",
    "2_vehicles": "2 Vehicles",
    "3_vehicles": "3 Vehicles",
    "4plus_vehicles": "4+ Vehicles",
    "total_households": "Total Households",
}


def fetch_acs_ownership() -> pd.DataFrame:
    """Fetch ACS B08201 vehicle-availability data for Bay Area counties.

    Reads the Census API key from the ``CENSUS_KEY`` environment variable.

    Returns:
        pandas.DataFrame: Raw ACS 1-Year (2023) response for the nine Bay Area
        counties, with the API's header row used as column names.

    Raises:
        requests.HTTPError: If the Census API request fails.
    """
    api_key = os.environ.get("CENSUS_KEY")  # do NOT hardcode keys
    params = {
        "get": "group(B08201)",
        "for": "county:001,013,041,055,075,081,085,095,097",
        "in": "state:06",
        "key": api_key,
    }
    response = requests.get(
        "https://api.census.gov/data/2023/acs/acs1",
        params=params, timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return pd.DataFrame(data[1:], columns=data[0])


def build_county_ownership(acs_ownership: pd.DataFrame) -> pd.DataFrame:
    """Clean and label the ACS data and append a regional total row.

    Args:
        acs_ownership: Raw ACS response from :func:`fetch_acs_ownership`.

    Returns:
        pandas.DataFrame: One row per county with named vehicle-availability
        count columns, sorted by county FIPS, plus a final ``Total`` row.
    """
    df = (
        acs_ownership[["state", "county", *OWNERSHIP_COLS.keys()]]
        .rename(columns=OWNERSHIP_COLS)
        .assign(county_name=lambda d: d["county"].map(COUNTY_NAMES))
    )

    numeric_cols = list(OWNERSHIP_COLS.values())
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    df = df[
        ["county", "county_name", "0_vehicles", "1_vehicle", "2_vehicles",
         "3_vehicles", "4plus_vehicles", "total_households"]
    ].sort_values("county")

    subtotal = df[VALUE_COLS].sum()
    subtotal["county"] = "999"
    subtotal["county_name"] = "Total"
    return pd.concat([df, subtotal.to_frame().T], ignore_index=True)


def build_ownership_share(county_ownership: pd.DataFrame) -> pd.DataFrame:
    """Compute each county's share of households by vehicle-availability category.

    Args:
        county_ownership: Count table from :func:`build_county_ownership`.

    Returns:
        pandas.DataFrame: One row per county with each vehicle category expressed
        as a share of that county's total households; ``total_households`` is set
        to 1.0 as the row total.
    """
    long = county_ownership.melt(
        id_vars=["county", "county_name", "total_households"],
        value_vars=["0_vehicles", "1_vehicle", "2_vehicles",
                    "3_vehicles", "4plus_vehicles"],
        var_name="ownership_category",
        value_name="households",
    )
    share = long.assign(
        share=lambda d: d["households"] / d["total_households"]
    ).pivot(
        index=["county", "county_name"],
        columns="ownership_category", values="share",
    ).reset_index()
    share["total_households"] = 1.0
    return share


def format_auto_table(df: pd.DataFrame, num_fmt: str = ",.0f") -> pd.DataFrame:
    """Format an auto-ownership table for Markdown display.

    Args:
        df: A county count or share table from :func:`build_county_ownership`
            or :func:`build_ownership_share`.
        num_fmt: Python format spec applied to value columns (e.g. ``",.0f"`` for
            counts or ``".1%"`` for shares).

    Returns:
        pandas.DataFrame: A display-ready DataFrame with renamed columns,
        formatted values, a bold ``Total`` row, and bold headers.
    """
    tbl = df.drop(columns="county").rename(columns=CATEGORY_LABELS)
    tbl = tables.format_numeric(tbl, num_fmt, skip_cols = ["County"])   
    tbl.loc[tbl["County"] == "Total", "County"] = "**Total**"
    return tables.bold_headers(tbl)