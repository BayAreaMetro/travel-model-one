'''
Enrollment Counts by TAZ
This script processes public school, private school, and college enrollment data
for the Bay Area. It spatially joins enrollment locations to TAZ and aggregates counts by zone.
The output includes:
- HSENROLL: Total high school enrollment (public + private)
- COLLFTE: Full-time equivalent college enrollment (4-year institutions)
- COLLPTE: Part-time equivalent college enrollment (2-year/certificate programs)
Data sources:
- Public schools: California Department of Education School Sites
- Private schools: California Private School Registry
- Colleges: IPEDS (Integrated Postsecondary Education Data System)
    --write: Save spatial output to GeoPackage format
'''

import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
sys.path.insert(0, str(Path(__file__).parent.parent))
from setup import *
from utils import *


def load_public_schools():
    """
    Loads public school data, filters to active schools in Bay Area counties, and derives enrollment vars.
    Returns:
        GeoDataFrame: Public schools with enrollment vars and geometry.
    """
    pubschls = gpd.read_file(RAW_DATA_DIR / "enrollment" / "SchoolSites2425.gpkg").to_crs(ANALYSIS_CRS)
    pubschls = pubschls[pubschls["Status"]=="Active"]

    # Filter to Bay Area
    pubschls = pubschls[pubschls["CountyName"].isin(BAY_AREA_COUNTIES)]

    pubschls["HSENROLL_PUB"] = pubschls.apply(
        lambda row: row[["Grade9", "Grad10", "Grade11", "Grade12"]].sum() if row["SchoolLevel"] != "Adult Education" else 0,
        axis=1
    )

    pubschls = pubschls[[#"CDSCode", 
                        "HSENROLL_PUB", "geometry"]]

    return pubschls


def load_private_schools():
    """
    Loads private school data, filters to Bay Area counties, and derives enrollment vars.
    Returns:
        GeoDataFrame: Private schools with enrollment vars and geometry.
    """
    prvschls = gpd.read_file(ENROLLMENT_RAW_DATA_DIR / "cprs_2324.gpkg").to_crs(ANALYSIS_CRS)

    # Filter to Bay Area
    prvschls = prvschls[prvschls["County"].isin(BAY_AREA_COUNTIES)]

    prvschls["HSENROLL_PRIV"] = prvschls[["Enroll09", "Enroll10", "Enroll11", "Enroll12"]].sum(axis=1)

    # Reduce to necessary cols
    prvschls = prvschls[["HSENROLL_PRIV", "geometry"]]
    
    return prvschls


def load_colleges():
    """
    Loads college location and separate enrollment data, merges them, and returns COLLFTE/COLLPTE directly from IPEDS FT/PT headcounts.
    Returns:
        GeoDataFrame: Colleges with COLLFTE, COLLPTE enrollment vars and geometry.
    """
    # Location and enrollment are seperate - start with locations
    colleges = gpd.read_file(ENROLLMENT_RAW_DATA_DIR / "bayarea_postsec_2324.shp").to_crs(ANALYSIS_CRS)
    colleges["UNITID"] = colleges["UNITID"].astype(int)

    # Now enrollment
    college_enroll = pd.read_csv(ENROLLMENT_RAW_DATA_DIR / "postsec_enroll_2324.csv")
    college_enroll = college_enroll.rename(columns={
        "Full-time 12-month unduplicated headcount (DRVEF122024)": "COLLFTE",
        "Part-time 12-month unduplicated headcount (DRVEF122024)": "COLLPTE",
        "Total 12-month unduplicated headcount (DRVEF122024)": "enrollment",
    })
    # Merge and make sure we keep only institutions with enrollment (a few administrative office locations make there way in otherwise)
    colleges = colleges.merge(college_enroll, left_on="UNITID", right_on="UnitID", how="inner", validate="1:1")
    colleges = colleges[colleges["enrollment"] > 0]

    # Reduce to necessary cols
    colleges = gpd.GeoDataFrame(colleges[["geometry", "COLLFTE", "COLLPTE"]], geometry="geometry", crs=ANALYSIS_CRS)

    print("Sum of COLLFTE:", colleges["COLLFTE"].sum())
    print("Sum of COLLPTE:", colleges["COLLPTE"].sum())

    return colleges

def get_enrollment_taz(write=False):
    """
    Loads public, private, and college data, spatially joins to TAZ, summarizes enrollment by TAZ, and merges results.
    Optionally writes output to GeoPackage.
    
    Parameters:
        write (bool, optional): If True, writes the resulting enrollment_taz GeoDataFrame to interim cache.
    
    Returns:
        DataFrame: Enrollment counts by TAZ for all school types.
    """
    
    # Load
    pubschls = load_public_schools()
    prvschls = load_private_schools()
    colleges = load_colleges()
    taz = load_taz_shp()

    # Spatial join schools to taz
    pubschls_taz = spatial_join_to_taz(pubschls, taz)
    privschls_taz = spatial_join_to_taz(prvschls, taz)
    colleges_taz = spatial_join_to_taz(colleges, taz)

    # Collapse enrollment by taz
    pub_enroll_taz = summarize_enrollment_by_taz(pubschls_taz, taz)
    priv_enroll_taz = summarize_enrollment_by_taz(privschls_taz, taz)
    college_enroll_taz = summarize_enrollment_by_taz(colleges_taz, taz)

    # Combine
    enroll_taz = pub_enroll_taz.merge(
        priv_enroll_taz, on="TAZ1454", how="left", validate="1:1"
    ).merge(
        college_enroll_taz, on="TAZ1454", how="left", validate="1:1"
    ).fillna(0)

    # Add public + private enroll cols
    enroll_taz["HSENROLL"] = enroll_taz["HSENROLL_PUB"] + enroll_taz["HSENROLL_PRIV"]
    enroll_taz = enroll_taz.drop(columns=["HSENROLL_PUB", "HSENROLL_PRIV"])
    
    # Sort by taz
    enroll_taz["TAZ1454"] = enroll_taz["TAZ1454"].sort_values()

    if write:
        # Select output columns
        output_cols = ['TAZ1454', 'HSENROLL', 'COLLFTE', 'COLLPTE']
        
        # Write CSV output (no geometry)
        csv_file = "enrollment_taz.csv"
        enroll_taz[output_cols].to_csv(csv_file, index=False)
        print(f"\nWrote CSV: {csv_file}")
        print(f"  Columns: {', '.join(output_cols)}")
        print(f"  Records: {len(enroll_taz):,}")
        
        # Write GeoPackage output (with geometry)
        enroll_taz_spatial = enroll_taz[output_cols].merge(
            taz[["TAZ1454", "geometry"]], 
            on="TAZ1454", 
            how="left"
        )
        enroll_taz_spatial = gpd.GeoDataFrame(enroll_taz_spatial, geometry="geometry", crs=ANALYSIS_CRS)
        
        gpkg_file = "enrollment_taz.gpkg"
        enroll_taz_spatial.to_file(gpkg_file, driver="GPKG")
        print(f"\nWrote GeoPackage: {gpkg_file}")
        print(f"  Columns: {', '.join(output_cols)} + geometry")
        print(f"  Records: {len(enroll_taz_spatial):,}")
    
    return enroll_taz


def summarize_enrollment_by_taz(schools_taz, taz):
    """
    Summarize enrollment counts by TAZ.
    Groups by TAZ1454 and sums all numeric columns.
    Returns a DataFrame with TAZ1454 and summed enrollment columns.
    """
    ENROLL_COLS = ['HSENROLL_PUB', 'HSENROLL_PRIV', 'COLLFTE', 'COLLPTE']

    # Only sum columns that are present in schools_taz and listed in ENROLL_COLS
    present_enroll_cols = [col for col in ENROLL_COLS if col in schools_taz.columns]
    enrollment_taz = schools_taz.groupby("TAZ1454", as_index=False)[present_enroll_cols].sum()

    # Concatenate taz with schools and taz w/o schools so we have a full set of taz
    taz["TAZ1454"] = taz["TAZ1454"].astype(int)
    schools_taz["TAZ1454"] = schools_taz["TAZ1454"].astype(int)

    print(f"taz dtypes: \n{taz.dtypes}")
    print(f"schools with taz dtypes: \n{schools_taz.dtypes}")

    taz_no_schools = taz[~taz["TAZ1454"].isin(schools_taz["TAZ1454"])].drop(columns="geometry")
    enrollment_taz = pd.concat([enrollment_taz, taz_no_schools], ignore_index=True)

    enrollment_taz["TAZ1454"] = enrollment_taz["TAZ1454"].astype(int)
    print(f"enrollment taz after concat dtypes: \n{enrollment_taz.dtypes}")

    # Ensure we have the same set of taz ids post process 
    taz_id_in = set(taz["TAZ1454"])
    enrollment_taz_ids = set(enrollment_taz["TAZ1454"])

    # Ensure enrollment_taz has the same set of TAZ1454 as taz_id_in
    if enrollment_taz_ids == taz_id_in:
        print("enrollment_taz has the same set of TAZ1454 ids as taz_id_in.")
    else:
        print("enrollment_taz does NOT have the same set of TAZ1454 ids as taz_id_in.")
        print("Missing in enrollment_taz:", taz_id_in - enrollment_taz_ids)
        print("Extra in enrollment_taz:", enrollment_taz_ids - taz_id_in)
    

    return enrollment_taz


def main():
    """
    Execute script directly with optional command-line flags.
    Usage:
        python enrollment_counts.py [--write]
    """
    write = "--write" in sys.argv
    
    enroll_taz = get_enrollment_taz(write=write)
    print(f"\nEnrollment counts processing complete.")
    print(f"Total TAZ records: {len(enroll_taz)}")
    print(f"Total high school enrollment: {enroll_taz['HSENROLL'].sum():,.0f}")
    print(f"Total college FTE enrollment: {enroll_taz['COLLFTE'].sum():,.0f}")
    print(f"Total college PTE enrollment: {enroll_taz['COLLPTE'].sum():,.0f}")

if __name__ == "__main__":
    main()