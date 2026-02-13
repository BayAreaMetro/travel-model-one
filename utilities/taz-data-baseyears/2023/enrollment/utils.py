from pathlib import Path
import os
import sys
import pandas as pd
import geopandas as gpd


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