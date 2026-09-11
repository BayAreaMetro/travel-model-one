"""
Utils for TAZ 2023 enrollment, parking, res dev acre update
"""

from pathlib import Path
import os
import sys
import pandas as pd
import geopandas as gpd
from setup import *
import pytidycensus

# Load taz shp
def load_taz_shp():
    taz = gpd.read_file(TAZ_FILE).to_crs(ANALYSIS_CRS)
    return taz


def spatial_join_to_taz(points_gdf, taz_gdf):
    """
    Spatially joins point features to TAZ polygons using a two-step approach:
    1. Join points within TAZ polygons (fast, catches majority)
    2. Join remaining points to nearest TAZ (catches edge cases)
    
    This ensures every point gets assigned to a TAZ, even if slightly outside polygon boundaries
    due to geocoding errors or topology issues.
    
    Args:
        points_gdf (GeoDataFrame): Point features to join to TAZ (e.g., firms, schools).
        taz_gdf (GeoDataFrame): TAZ polygons with TAZ1454 column.
    
    Returns:
        DataFrame: Input points with added TAZ1454 column (geometry dropped).
    """
    print(f"Spatially joining {len(points_gdf)} points to TAZ...")
    
    # Step 1: Spatial join using 'within' predicate (points inside TAZ polygons)
    joined = gpd.sjoin(points_gdf, taz_gdf, how="left", predicate="within")
    joined = joined.drop(columns=['index_right'], errors='ignore')
    
    matched_count = joined["TAZ1454"].notnull().sum()
    print(f"  Step 1 (within): {matched_count:,} / {len(points_gdf):,} points matched to TAZ")
    
    # Step 2: Nearest neighbor join for unmatched points
    unmatched = joined[joined["TAZ1454"].isnull()]
    if len(unmatched) > 0:
        print(f"  Step 2 (nearest): Assigning {len(unmatched):,} unmatched points to nearest TAZ...")
        
        # Prepare unmatched subset as GeoDataFrame, drop null TAZ column
        unmatched_gdf = gpd.GeoDataFrame(
            unmatched, 
            geometry="geometry", 
            crs=points_gdf.crs
        ).drop(columns=["TAZ1454"], errors='ignore')
        
        # Nearest neighbor spatial join
        nearest_joined = gpd.sjoin_nearest(unmatched_gdf, taz_gdf, how="left")
        nearest_joined = nearest_joined.drop(columns=['index_right'], errors='ignore')
        
        # Convert to DataFrame and concatenate with successfully matched points
        nearest_joined = pd.DataFrame(nearest_joined)
        matched = pd.DataFrame(joined[joined["TAZ1454"].notnull()])
        joined = pd.concat([matched, nearest_joined], ignore_index=True)
        
        still_unmatched = joined["TAZ1454"].isnull().sum()
        if still_unmatched > 0:
            print(f"  WARNING: {still_unmatched} points still unmatched after nearest join!")
        else:
            print(f"  Step 2 complete: All points now assigned to TAZ")
    
    total_matched = joined["TAZ1454"].notnull().sum()
    print(f"  Final: {total_matched:,} / {len(points_gdf):,} points assigned to TAZ")
    
    return joined

def load_bay_area_places():
    """Load Census place boundaries for Bay Area counties."""
    # Set Census API key
    pytidycensus.set_census_api_key(CENSUS_API_KEY)

    # Load census place geographies for California
    places = pytidycensus.get_acs(
        geography="place",
        variables=["B01001_001E"],  # Total population
        state="CA",
        year=2021,
        geometry=True
    ) 

    counties = pytidycensus.get_acs(
        geography="county",
        variables=["B01001_001E"],  # Total population
        state="CA",
        year=2021,
        geometry=True
    ) 

    COUNTY_FIPS = {
        "Alameda": "001",
        "Contra Costa": "013",
        "Marin": "041",
        "Napa": "055",
        "San Francisco": "075",
        "San Mateo": "081",
        "Santa Clara": "085",
        "Solano": "095",
        "Sonoma": "097"
    }
    
    # Filter to Bay Area counties
    bay_counties = counties[counties['GEOID'].str[2:].isin(COUNTY_FIPS.values())]
    
    # Add county names
    fips_to_name = {v: k for k, v in COUNTY_FIPS.items()}
    bay_counties['county_name'] = bay_counties['GEOID'].str[2:].map(fips_to_name)
    
    # Get place IDs that intersect Bay Area counties
    places_gdf = gpd.GeoDataFrame(places, geometry='geometry', crs=WGS84_CRS)
    counties_gdf = gpd.GeoDataFrame(bay_counties, geometry='geometry', crs=WGS84_CRS)
    
    # Spatial join to get places in Bay Area
    places_in_bay = gpd.sjoin(places_gdf, counties_gdf[['geometry', 'county_name']], how='inner', predicate='intersects')
    
    # Extract place info
    places_in_bay['place_id'] = places_in_bay['GEOID']
    places_in_bay['place_name'] = places_in_bay['NAME'].str.replace(' city, California', '').str.replace(' town, California', '').str.replace(', California', '')
    
    # Convert to analysis CRS
    places_in_bay = places_in_bay.to_crs(ANALYSIS_CRS)
    places_in_bay = places_in_bay[['place_id', 'place_name', 'county_name', 'geometry']]
    
    return places_in_bay


def spatial_join_taz_to_place(taz, places):
    """Spatially join TAZ to Census places by largest intersection area."""
    print(f"\n{'='*70}")
    print(f"Spatial Join: TAZ to Census Places")
    print(f"{'='*70}\n")
    
    # Ensure both are in same CRS
    print(f"  TAZ CRS: {taz.crs}")
    print(f"  Places CRS: {places.crs}")
    
    if taz.crs != places.crs:
        print(f"  WARNING: CRS mismatch! Converting places to {taz.crs}")
        places = places.to_crs(taz.crs)
    
    # Perform spatial overlay to get intersection areas
    print(f"  Performing spatial overlay...")
    overlay = gpd.overlay(taz, places, how='intersection')
    print(f"  Found {len(overlay):,} TAZ-place intersections")
    
    if len(overlay) == 0:
        print("  ERROR: No intersections found! Check geometries and CRS.")
        return taz
    
    # Calculate the area of each intersection
    overlay['intersection_area'] = overlay.geometry.area
    
    # For each TAZ, find the place with the largest intersection area
    idx_max_area = overlay.groupby('TAZ1454')['intersection_area'].idxmax()
    taz_place = overlay.loc[idx_max_area, ['TAZ1454', 'place_id', 'place_name', 'county_name']]
    
    # Merge place info back to taz
    taz = taz.merge(taz_place, on='TAZ1454', how='left')
    
    print(f"  Completed spatial join")
    print(f"  TAZs in cities: {taz['place_name'].notnull().sum():,}")
    print(f"  TAZs outside cities: {taz['place_name'].isnull().sum():,}")
    
    return taz