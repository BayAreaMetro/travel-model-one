from pathlib import Path
import pandas as pd
import geopandas as gpd
import numpy as np
import os
import sys

# Import configuration and utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from setup import (
    PARKING_RAW_DATA_DIR,
    ANALYSIS_CRS,
    SQUARE_METERS_PER_ACRE
)
from utils import load_taz_shp


def overlay_taz_blockgroups(taz, parking_capacity):
    """
    Spatially overlay TAZ and block group geometries to create TAZ-BlockGroup mapping.
    
    Parameters:
        taz (GeoDataFrame): TAZ polygons with geometry
        parking_capacity (GeoDataFrame): Block group parking data with geometry
        
    Returns:
        GeoDataFrame: TAZ-BlockGroup intersections with calculated areas
    """
    print(f"Performing spatial overlay of TAZ and block groups...")
    print(f"  Number of TAZs: {len(taz):,}")
    print(f"  Number of block groups: {len(parking_capacity):,}")
    
    # Spatial overlay to find intersections
    overlay = gpd.overlay(taz, parking_capacity, how='intersection')
    print(f"  Number of TAZ-BlockGroup intersections: {len(overlay):,}")
    
    # Calculate intersection area in acres
    overlay['taz_acres'] = overlay.geometry.area / SQUARE_METERS_PER_ACRE
    
    # Check for TAZs spanning multiple block groups
    tazs_multiple_bg = overlay.groupby('TAZ1454')['blkgrpid'].nunique()
    tazs_spanning = (tazs_multiple_bg > 1).sum()
    if tazs_spanning > 0:
        print(f"  ⚠ Warning: {tazs_spanning:,} TAZs span multiple block groups")
        print(f"    (This is handled by summing allocated parking across contributing block groups)")
    
    return overlay


def calculate_allocation_weights(overlay_df, employment_taz):
    """
    Calculate allocation weights for distributing block group parking to TAZs.
    Uses employment-based weights with area fallback for off-street non-residential,
    and pure area weights for on-street parking.
    
    Parameters:
        overlay_df (GeoDataFrame): TAZ-BlockGroup intersections with areas
        employment_taz (DataFrame): TAZ employment data with TOTEMP
        
    Returns:
        DataFrame: overlay_df with allocation weights added
    """
    print(f"Calculating allocation weights...")
    
    # Ensure consistent data types for merge
    overlay_df['TAZ1454'] = overlay_df['TAZ1454'].astype(int)
    
    # Merge employment data
    weights_df = overlay_df.merge(
        employment_taz[['TAZ1454', 'TOTEMP']], 
        on='TAZ1454', 
        how='left'
    )
    
    # Fill any missing employment with 0
    weights_df['TOTEMP'] = weights_df['TOTEMP'].fillna(0)
    
    # Calculate block group totals
    weights_df['bg_total_acres'] = weights_df.groupby('blkgrpid')['taz_acres'].transform('sum')
    weights_df['bg_total_emp'] = weights_df.groupby('blkgrpid')['TOTEMP'].transform('sum')
    
    # Calculate raw shares
    weights_df['area_share'] = np.where(
        weights_df['bg_total_acres'] > 0,
        weights_df['taz_acres'] / weights_df['bg_total_acres'],
        0
    )
    
    weights_df['emp_share'] = np.where(
        weights_df['bg_total_emp'] > 0,
        weights_df['TOTEMP'] / weights_df['bg_total_emp'],
        0
    )
    
    # Create hybrid weight for off-street non-residential:
    # Use employment share when available, area share as fallback
    weights_df['weight_offnres'] = np.where(
        weights_df['bg_total_emp'] > 0,
        weights_df['emp_share'],
        weights_df['area_share']
    )
    
    # Use pure area weight for on-street parking
    weights_df['weight_onall'] = weights_df['area_share']
    
    # Report on fallback usage
    zero_emp_bgs = (weights_df['bg_total_emp'] == 0).sum()
    if zero_emp_bgs > 0:
        unique_zero_emp_bgs = weights_df[weights_df['bg_total_emp'] == 0]['blkgrpid'].nunique()
        print(f"  {unique_zero_emp_bgs:,} block groups have zero employment - using area fallback")
    
    return weights_df


def allocate_parking_to_taz(weights_df, taz_gdf):
    """
    Normalize weights within each block group and allocate parking to TAZ level.
    
    Parameters:
        weights_df (DataFrame): TAZ-BlockGroup data with raw weights and parking values
        taz_gdf (GeoDataFrame): TAZ polygons with geometry
        
    Returns:
        GeoDataFrame: TAZ-level parking allocation with TAZ1454, TOTEMP, on_all, off_nres, geometry
    """
    print(f"Normalizing weights and allocating parking to TAZ level...")
    
    # Normalize weights to sum to 1.0 within each block group
    weights_df['weight_offnres_norm'] = (
        weights_df['weight_offnres'] / 
        weights_df.groupby('blkgrpid')['weight_offnres'].transform('sum')
    )
    
    weights_df['weight_onall_norm'] = (
        weights_df['weight_onall'] / 
        weights_df.groupby('blkgrpid')['weight_onall'].transform('sum')
    )
    
    # Apply weights to allocate parking
    weights_df['off_nres_allocated'] = weights_df['off_nres'] * weights_df['weight_offnres_norm']
    weights_df['on_all_allocated'] = weights_df['on_all'] * weights_df['weight_onall_norm']
    
    # Aggregate to TAZ level (summing across multiple block groups if TAZ spans them)
    parking_taz = weights_df.groupby(['TAZ1454'], as_index=False).agg({
        'off_nres_allocated': 'sum',
        'on_all_allocated': 'sum',
        'TOTEMP': 'first'  # Employment is constant per TAZ, take first value
    })
    
    # Rename to final column names
    parking_taz = parking_taz.rename(columns={
        'off_nres_allocated': 'off_nres',
        'on_all_allocated': 'on_all'
    })
    
    # Fill any NaN with 0
    parking_taz = parking_taz.fillna(0)
    
    # Clip any negative values to 0 (safety check)
    parking_taz['off_nres'] = parking_taz['off_nres'].clip(lower=0)
    parking_taz['on_all'] = parking_taz['on_all'].clip(lower=0)
    
    # Merge with TAZ geometry to create GeoDataFrame
    # Ensure TAZ1454 types match
    taz_gdf_copy = taz_gdf.copy()
    taz_gdf_copy['TAZ1454'] = taz_gdf_copy['TAZ1454'].astype(int)
    parking_taz = parking_taz.merge(
        taz_gdf_copy[['TAZ1454', 'geometry']], 
        on='TAZ1454', 
        how='left'
    )
    parking_taz = gpd.GeoDataFrame(parking_taz, geometry='geometry', crs=ANALYSIS_CRS)
    
    # Reorder columns for clarity
    column_order = ['TAZ1454', 'off_nres', 'on_all', 'geometry']
    parking_taz = parking_taz[column_order]
    
    print(f"  Total TAZs with allocated parking: {len(parking_taz):,}")
    
    return parking_taz


def get_parking_capacity(write=False):
    """
    Main function to allocate block group parking capacity to TAZ level.
    Uses hybrid allocation: employment-weighted for off-street non-residential,
    area-weighted for on-street parking.
    
    Parameters:
        write (bool): If True, writes output to GeoPackage in script directory
        
    Returns:
        DataFrame: TAZ-level parking with columns [TAZ1454, TOTEMP, off_nres, on_all]
    """
    print(f"\n{'='*60}")
    print(f"Allocating Block Group Parking Capacity to TAZ Level")
    print(f"{'='*60}\n")
    
    # Load data
    print(f"Loading input data...")
    parking_capacity = gpd.read_file(
        PARKING_RAW_DATA_DIR / "2123-Dataset" / "parking_density_Employee_Capita" / "parking_density_Employee_Capita.shp"
    ).to_crs(ANALYSIS_CRS)
    parking_capacity = parking_capacity[["blkgrpid", "on_all", "off_nres", "geometry"]]
    
    # Clean negative values (data quality issue in source)
    neg_on_all = (parking_capacity['on_all'] < 0).sum()
    neg_off_nres = (parking_capacity['off_nres'] < 0).sum()
    if neg_on_all > 0 or neg_off_nres > 0:
        print(f"  ⚠ Warning: Found negative parking values in source data:")
        if neg_on_all > 0:
            print(f"    on_all: {neg_on_all:,} block groups with negative values")
        if neg_off_nres > 0:
            print(f"    off_nres: {neg_off_nres:,} block groups with negative values")
        print(f"  Clipping negative values to 0...")
        parking_capacity['on_all'] = parking_capacity['on_all'].clip(lower=0)
        parking_capacity['off_nres'] = parking_capacity['off_nres'].clip(lower=0)
    
    print(f"  Loaded {len(parking_capacity):,} block groups with parking data")
    
    # Load TAZ shapefile
    taz = load_taz_shp().to_crs(ANALYSIS_CRS)
    print(f"  Loaded {len(taz):,} TAZ polygons")
    
    # Load employment data from land use CSV
    print(f"\nLoading TAZ employment data...")
    employment_taz = pd.read_csv("../TAZ1454 2023 Land Use.csv")[['ZONE', 'TOTEMP']].rename(columns={'ZONE': 'TAZ1454'})
    print(f"  Loaded employment for {len(employment_taz):,} TAZs")
    
    # Spatial overlay
    overlay_df = overlay_taz_blockgroups(taz, parking_capacity)
    
    # Calculate weights
    weights_df = calculate_allocation_weights(overlay_df, employment_taz)
    
    # Allocate parking
    parking_taz = allocate_parking_to_taz(weights_df, taz)
    
    # Validation
    print(f"\nValidating results...")
    original_total_offnres = parking_capacity['off_nres'].sum()
    original_total_onall = parking_capacity['on_all'].sum()
    allocated_total_offnres = parking_taz['off_nres'].sum()
    allocated_total_onall = parking_taz['on_all'].sum()
    
    print(f"  Original block group totals:")
    print(f"    off_nres: {original_total_offnres:,.0f}")
    print(f"    on_all: {original_total_onall:,.0f}")
    print(f"  Allocated TAZ totals:")
    print(f"    off_nres: {allocated_total_offnres:,.0f}")
    print(f"    on_all: {allocated_total_onall:,.0f}")
    
    # Check conservation (within 0.1% tolerance)
    offnres_diff_pct = abs(allocated_total_offnres - original_total_offnres) / original_total_offnres * 100
    onall_diff_pct = abs(allocated_total_onall - original_total_onall) / original_total_onall * 100
    
    if offnres_diff_pct < 0.1 and onall_diff_pct < 0.1:
        print(f"  ✓ Conservation check passed (< 0.1% difference)")
    else:
        print(f"  ⚠ Warning: Conservation check failed")
        print(f"    off_nres difference: {offnres_diff_pct:.2f}%")
        print(f"    on_all difference: {onall_diff_pct:.2f}%")
    
    # Write output if requested
    if write:
        OUT_FILE = Path(__file__).parent / "parking_capacity_taz.gpkg"
        print(f"\nWriting parking TAZ data to: {OUT_FILE}")
        parking_taz.to_file(OUT_FILE, driver="GPKG", index=False)
    
    print(f"\n{'='*60}")
    print(f"Parking allocation complete!")
    print(f"{'='*60}\n")
    
    return parking_taz


def main():
    """
    Execute script directly with optional command-line flags.
    Usage:
        python parking_capacity.py [--write]
    """
    write = "--write" in sys.argv
    
    parking_taz = get_parking_capacity(write=write)
    print(f"\nParking capacity processing complete.")
    print(f"Total TAZ records: {len(parking_taz)}")
    print(f"Total off-street parking: {parking_taz['off_nres'].sum():,.0f}")
    print(f"Total on-street parking: {parking_taz['on_all'].sum():,.0f}")


if __name__ == "__main__":
    main()


