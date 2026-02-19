"""Process published parking meter cost data from SF, San Jose, and Oakland.

Spatially joins hourly parking meter costs (OPRKCST) from city-published data to TAZ zones.
"""

import pandas as pd
import geopandas as gpd
import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import configuration
from setup import PARKING_RAW_DATA_DIR, ANALYSIS_CRS
from utils import load_taz_shp


def extract_hourly_cost(config_string):
    """Extract hourly cost using regex - finds first $X.XX pattern."""
    if pd.isna(config_string):
        return 2.0  # Default to 2.0 for missing values
    
    # Match pattern like $2.00 or $ 2.00 or $1.50 or $2
    match = re.search(r'\$\s*(\d+\.?\d*)', str(config_string))
    if match:
        return float(match.group(1))
    return 2.0  # Default to 2.0 if no $ found


def published_cost():
    """
    Load and process published parking meter costs by TAZ.
    
    Spatially joins hourly parking costs from Oakland meters (points), 
    San Jose meters (points), and San Francisco meter districts (polygons) to TAZ zones.
    
    Returns:
        DataFrame: TAZ1454 and OPRKCST columns
    """
    print("Loading published parking meter cost data...")
    
    # Load TAZ shapefile
    taz = load_taz_shp()
    
    # Load Oakland meters
    print("  Loading Oakland meters...")
    oak_meters = gpd.read_file(PARKING_RAW_DATA_DIR / "City_of_Oakland_Parking_Meters_20260107.geojson")
    oak_meters['OPRKCST'] = oak_meters['config__na'].apply(extract_hourly_cost)
    oak_meters = oak_meters[["OPRKCST", "geometry"]]
    print(f"    Loaded {len(oak_meters):,} Oakland meters")
    
    # Load San Jose meters
    print("  Loading San Jose meters...")
    sj_meters = gpd.read_file(PARKING_RAW_DATA_DIR / "Parking_Meters.geojson")
    sj_meters = sj_meters.rename(columns={"PARKINGRATE": "OPRKCST"})
    sj_meters["OPRKCST"] = sj_meters["OPRKCST"].fillna(2.0).replace(0, 2.0)
    sj_meters = sj_meters[["OPRKCST", "geometry"]]
    print(f"    Loaded {len(sj_meters):,} San Jose meters")
    
    # Load San Francisco meter districts
    print("  Loading San Francisco meter districts...")
    sf_rates = pd.read_csv(PARKING_RAW_DATA_DIR / "January 2026 Parking Meter Rate Change Data.csv")
    sf_park_distr = gpd.read_file(PARKING_RAW_DATA_DIR / "Parking_Management_Districts_20260203.geojson")
    
    # Average Final Rate by Parking Management District
    avg_rates = sf_rates.groupby('Parking Management District')['Final Rate'].mean().reset_index()
    avg_rates.columns = ['Parking Management District', 'OPRKCST']
    
    # Join to sf_park_distr
    sf_park_distr = sf_park_distr.merge(
        avg_rates, 
        left_on='pm_district_name', 
        right_on='Parking Management District', 
        how='left'
    )
    sf_park_distr = sf_park_distr.drop(columns=['Parking Management District'])
    
    sf_meter_areas = sf_park_distr[["OPRKCST", "geometry"]]
    sf_meter_areas = sf_meter_areas[~sf_meter_areas["OPRKCST"].isnull()]
    print(f"    Loaded {len(sf_meter_areas):,} San Francisco meter districts")
    
    # Ensure CRS consistency
    print(f"  Converting all datasets to {ANALYSIS_CRS}...")
    oak_meters = oak_meters.to_crs(ANALYSIS_CRS)
    sj_meters = sj_meters.to_crs(ANALYSIS_CRS)
    sf_meter_areas = sf_meter_areas.to_crs(ANALYSIS_CRS)
    
    # Store original count for validation
    original_count = len(taz)
    
    # Spatial join: Oakland point meters to TAZ
    print("  Spatial join: Oakland meters to TAZ...")
    oak_joined = gpd.sjoin(taz, oak_meters, how="inner", predicate="intersects")
    oak_by_taz = oak_joined.groupby('TAZ1454')['OPRKCST'].mean().reset_index()
    oak_by_taz.columns = ['TAZ1454', 'OPRKCST_oak']
    print(f"    Oakland: {len(oak_by_taz):,} TAZs with parking meter costs")
    
    # Spatial join: San Jose point meters to TAZ
    print("  Spatial join: San Jose meters to TAZ...")
    sj_joined = gpd.sjoin(taz, sj_meters, how="inner", predicate="intersects")
    sj_by_taz = sj_joined.groupby('TAZ1454')['OPRKCST'].mean().reset_index()
    sj_by_taz.columns = ['TAZ1454', 'OPRKCST_sj']
    print(f"    San Jose: {len(sj_by_taz):,} TAZs with parking meter costs")
    
    # Spatial join: SF polygon meter areas to TAZ (50% area threshold)
    print("  Spatial join: San Francisco meter districts to TAZ (50% threshold)...")
    sf_overlay = gpd.overlay(taz, sf_meter_areas, how="intersection")
    
    # Calculate original TAZ areas
    taz_areas = taz.copy()
    taz_areas['taz_area'] = taz_areas.geometry.area
    
    # Calculate intersection areas and percentage
    sf_overlay['intersection_area'] = sf_overlay.geometry.area
    sf_overlay = sf_overlay.merge(
        taz_areas[['TAZ1454', 'taz_area']], 
        on='TAZ1454', 
        how='left'
    )
    sf_overlay['pct_of_taz'] = sf_overlay['intersection_area'] / sf_overlay['taz_area']
    
    # Filter for TAZs where intersection >= 50% of TAZ area
    sf_filtered = sf_overlay[sf_overlay['pct_of_taz'] >= 0.5].copy()
    sf_by_taz = sf_filtered.groupby('TAZ1454')['OPRKCST'].mean().reset_index()
    sf_by_taz.columns = ['TAZ1454', 'OPRKCST_sf']
    print(f"    San Francisco: {len(sf_by_taz):,} TAZs with parking meter costs")
    
    # Merge all sources back to complete TAZ set
    print("  Merging all sources to TAZ...")
    taz = taz.merge(oak_by_taz, on='TAZ1454', how='left')
    taz = taz.merge(sj_by_taz, on='TAZ1454', how='left')
    taz = taz.merge(sf_by_taz, on='TAZ1454', how='left')
    
    # Combine into single OPRKCST column (coalesce across sources)
    # Since SF/SJ/OAK are geographically distinct, only one should have a value per TAZ
    taz['OPRKCST'] = taz[['OPRKCST_oak', 'OPRKCST_sj', 'OPRKCST_sf']].bfill(axis=1).iloc[:, 0]
    
    # Drop intermediate columns
    taz = taz.drop(columns=['OPRKCST_oak', 'OPRKCST_sj', 'OPRKCST_sf'])
    
    # Validate no records were lost
    if len(taz) != original_count:
        print(f"  WARNING: Record count changed from {original_count:,} to {len(taz):,}")
    else:
        print(f"  ✓ All {original_count:,} TAZ records retained")
    
    # Report statistics
    tazs_with_OPRKCST = taz['OPRKCST'].notna().sum()
    tazs_without_OPRKCST = taz['OPRKCST'].isna().sum()
    print(f"  TAZs with OPRKCST: {tazs_with_OPRKCST:,}/{len(taz):,}")
    print(f"  TAZs without OPRKCST: {tazs_without_OPRKCST:,}/{len(taz):,}")
    
    if tazs_with_OPRKCST > 0:
        print(f"  OPRKCST range: ${taz['OPRKCST'].min():.2f} - ${taz['OPRKCST'].max():.2f}")
        print(f"  OPRKCST mean: ${taz['OPRKCST'].mean():.2f}")
    
    # Return just TAZ1454 and OPRKCST columns as a regular DataFrame
    result = pd.DataFrame({'TAZ1454': taz['TAZ1454'], 'OPRKCST': taz['OPRKCST']})
    return result
