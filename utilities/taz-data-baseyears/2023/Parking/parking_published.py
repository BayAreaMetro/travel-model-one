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
    
    Applies area-weighted parking costs to TAZ zones from four cities:
    - Oakland meters (buffered 75m) 
    - San Jose meters (buffered 75m)
    - San Francisco meter districts (polygons)
    - Berkeley meter districts (polygons)
    
    All sources use area-weighting with 5% minimum coverage threshold.
    
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

    # Load Berkeley meter districts
    print("  Loading Berkeley districts...")
    berk_meter_areas = gpd.read_file(PARKING_RAW_DATA_DIR / "goBerkeley_Areas.shp").to_crs(ANALYSIS_CRS)
    berk_meter_areas["Hourly_rat"] = berk_meter_areas["Hourly_rat"].apply(extract_hourly_cost)
    berk_meter_areas['OPRKCST'] = berk_meter_areas['Hourly_rat']
    berk_meter_areas = berk_meter_areas[["OPRKCST", "geometry"]]
    print(f"    Loaded {len(berk_meter_areas):,} Berkeley meter districts")
    
    # Ensure CRS consistency
    print(f"  Converting all datasets to {ANALYSIS_CRS}...")
    oak_meters = oak_meters.to_crs(ANALYSIS_CRS)
    sj_meters = sj_meters.to_crs(ANALYSIS_CRS)
    sf_meter_areas = sf_meter_areas.to_crs(ANALYSIS_CRS)
    berk_meter_areas = berk_meter_areas.to_crs(ANALYSIS_CRS)
    
    # Buffer point meters to create metered zones (75m = typical block face)
    print("  Buffering point meters (75m radius)...")
    oak_meters_buffered = oak_meters.copy()
    oak_meters_buffered.geometry = oak_meters.buffer(75)
    sj_meters_buffered = sj_meters.copy()
    sj_meters_buffered.geometry = sj_meters.buffer(75)
    
    # Dissolve overlapping buffers to avoid double-counting, averaging costs in overlap areas
    print("  Dissolving overlapping meter buffers (average cost in overlaps)...")
    oak_meter_areas = oak_meters_buffered.dissolve(by=None, aggfunc='mean')[['OPRKCST', 'geometry']].explode(index_parts=False).reset_index(drop=True)
    sj_meter_areas = sj_meters_buffered.dissolve(by=None, aggfunc='mean')[['OPRKCST', 'geometry']].explode(index_parts=False).reset_index(drop=True)

    # Store original count for validation
    original_count = len(taz)
    
    # Calculate TAZ areas once for all area-weighting operations
    taz_areas = taz.copy()
    taz_areas['taz_area'] = taz_areas.geometry.area
    
    # Spatial join: Oakland dissolved meter areas to TAZ (area-weighted with 5% minimum)
    print("  Spatial join: Oakland meter areas to TAZ (area-weighted)...")
    oak_overlay = gpd.overlay(taz, oak_meter_areas, how="intersection")
    oak_overlay['intersection_area'] = oak_overlay.geometry.area
    oak_overlay = oak_overlay.merge(taz_areas[['TAZ1454', 'taz_area']], on='TAZ1454', how='left')
    oak_overlay['pct_of_taz'] = oak_overlay['intersection_area'] / oak_overlay['taz_area']
    
    # Filter out areas covering <5% of TAZ, then apply area-weighting
    oak_significant = oak_overlay[oak_overlay['pct_of_taz'] >= 0.05].copy()
    oak_significant['weighted_cost'] = oak_significant['OPRKCST'] * oak_significant['pct_of_taz']
    oak_by_taz = oak_significant.groupby('TAZ1454')['weighted_cost'].sum().reset_index()
    oak_by_taz.columns = ['TAZ1454', 'OPRKCST_oak']
    print(f"    Oakland: {len(oak_by_taz):,} TAZs with parking meter costs")
    
    # Spatial join: San Jose dissolved meter areas to TAZ (area-weighted with 5% minimum)
    print("  Spatial join: San Jose meter areas to TAZ (area-weighted)...")
    sj_overlay = gpd.overlay(taz, sj_meter_areas, how="intersection")
    sj_overlay['intersection_area'] = sj_overlay.geometry.area
    sj_overlay = sj_overlay.merge(taz_areas[['TAZ1454', 'taz_area']], on='TAZ1454', how='left')
    sj_overlay['pct_of_taz'] = sj_overlay['intersection_area'] / sj_overlay['taz_area']
    
    # Filter out areas covering <5% of TAZ, then apply area-weighting
    sj_significant = sj_overlay[sj_overlay['pct_of_taz'] >= 0.05].copy()
    sj_significant['weighted_cost'] = sj_significant['OPRKCST'] * sj_significant['pct_of_taz']
    sj_by_taz = sj_significant.groupby('TAZ1454')['weighted_cost'].sum().reset_index()
    sj_by_taz.columns = ['TAZ1454', 'OPRKCST_sj']
    print(f"    San Jose: {len(sj_by_taz):,} TAZs with parking meter costs")
    
    # Spatial join: SF polygon meter areas to TAZ (area-weighted with 5% minimum)
    print("  Spatial join: San Francisco meter districts to TAZ (area-weighted)...")
    sf_overlay = gpd.overlay(taz, sf_meter_areas, how="intersection")
    sf_overlay['intersection_area'] = sf_overlay.geometry.area
    sf_overlay = sf_overlay.merge(taz_areas[['TAZ1454', 'taz_area']], on='TAZ1454', how='left')
    sf_overlay['pct_of_taz'] = sf_overlay['intersection_area'] / sf_overlay['taz_area']
    
    # Filter out districts covering <5% of TAZ, then apply area-weighting
    sf_significant = sf_overlay[sf_overlay['pct_of_taz'] >= 0.05].copy()
    sf_significant['weighted_cost'] = sf_significant['OPRKCST'] * sf_significant['pct_of_taz']
    sf_by_taz = sf_significant.groupby('TAZ1454')['weighted_cost'].sum().reset_index()
    sf_by_taz.columns = ['TAZ1454', 'OPRKCST_sf']
    print(f"    San Francisco: {len(sf_by_taz):,} TAZs with parking meter costs")
    
    # Spatial join: Berkeley polygon meter areas to TAZ (area-weighted with 5% minimum)
    print("  Spatial join: Berkeley meter districts to TAZ (area-weighted)...")
    berk_overlay = gpd.overlay(taz, berk_meter_areas, how="intersection")
    berk_overlay['intersection_area'] = berk_overlay.geometry.area
    berk_overlay = berk_overlay.merge(taz_areas[['TAZ1454', 'taz_area']], on='TAZ1454', how='left')
    berk_overlay['pct_of_taz'] = berk_overlay['intersection_area'] / berk_overlay['taz_area']
    
    # Filter out districts covering <5% of TAZ, then apply area-weighting
    berk_significant = berk_overlay[berk_overlay['pct_of_taz'] >= 0.05].copy()
    berk_significant['weighted_cost'] = berk_significant['OPRKCST'] * berk_significant['pct_of_taz']
    berk_by_taz = berk_significant.groupby('TAZ1454')['weighted_cost'].sum().reset_index()
    berk_by_taz.columns = ['TAZ1454', 'OPRKCST_berk']
    print(f"    Berkeley: {len(berk_by_taz):,} TAZs with parking meter costs")
    
    # Merge all sources back to complete TAZ set
    print("  Merging all sources to TAZ...")
    taz = taz.merge(oak_by_taz, on='TAZ1454', how='left')
    taz = taz.merge(sj_by_taz, on='TAZ1454', how='left')
    taz = taz.merge(sf_by_taz, on='TAZ1454', how='left')
    taz = taz.merge(berk_by_taz, on='TAZ1454', how='left')
    
    # Combine into single OPRKCST column (coalesce across sources)
    # Since SF/SJ/OAK/Berkeley are geographically distinct, only one should have a value per TAZ
    taz['OPRKCST'] = taz[['OPRKCST_oak', 'OPRKCST_sj', 'OPRKCST_sf', 'OPRKCST_berk']].bfill(axis=1).iloc[:, 0]
    
    # Drop intermediate columns
    taz = taz.drop(columns=['OPRKCST_oak', 'OPRKCST_sj', 'OPRKCST_sf', 'OPRKCST_berk'])
    
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
    result["OPRKCST"] = result["OPRKCST"].round(2)

    return result
