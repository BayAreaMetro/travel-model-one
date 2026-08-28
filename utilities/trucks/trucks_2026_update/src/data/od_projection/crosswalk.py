import logging
import math
from typing import Optional

import geopandas as gpd
import pandas as pd
import numpy as np

from src.utils import setup_logging

logger = logging.getLogger(__name__)

PROJECTED_CRS_FALLBACK = "EPSG:3310"


def compute_spatial_overlay(from_zones: gpd.GeoDataFrame, to_zones: gpd.GeoDataFrame, sliver_cfg: dict) -> gpd.GeoDataFrame:
    """
    Intersects FROM and TO layers. 
    Tracks parent indices through the geopandas overlay mechanism.
    """
    logger.info("Computing FROM × TO overlay …")

    mtc_counties =  [
        'Alameda',
        'Contra Costa',
        'Marin',
        'Napa',
        'San Francisco',
        'San Mateo', 
        'Santa Clara',
        'Solano',
        'Sonoma',
        ]

    internal_from_zones = from_zones[from_zones.County.isin(mtc_counties)]
   
    overlay = gpd.overlay(internal_from_zones.reset_index(), to_zones.reset_index(), how="intersection", keep_geom_type=False)
    overlay = overlay.explode(index_parts=False).reset_index(drop=True)
    overlay = overlay[overlay.geometry.geom_type == "Polygon"].copy()
    
    logger.info("Overlay produced %d polygon fragments", len(overlay))

    clean_overlay = remove_slivers(
        overlay, 
        from_zones.geometry.area, 
        to_zones.geometry.area,
        sliver_cfg
        )

    collapsed = (
        clean_overlay.dissolve(by=["from_zone_id", "to_zone_id"])
        .reset_index()
    )
    return collapsed


def remove_slivers(overlay: gpd.GeoDataFrame, from_areas: pd.Series, to_areas: pd.Series, sliver_cfg: Optional[dict] = None) -> gpd.GeoDataFrame:
    
    """ Remove likely sliver polygons from an overlay between two zoning systems.

    Slivers are small geometric artifacts that can be created by minor
    boundary misalignments during polygon overlay operations. An intersection
    is classified as a sliver if it satisfies one or more of the configured
    criteria:

    * Absolute intersection area is below a minimum threshold.
    * Intersection area represents a small fraction of both the source
    (``from_zone_id``) and target (``to_zone_id``) zone areas.
    * Polygon compactness falls below a minimum threshold, indicating a thin
    or highly irregular geometry.

    Parameters
    ----------
    overlay : geopandas.GeoDataFrame
        Overlay result containing intersection geometries and the columns
        ``from_zone_id`` and ``to_zone_id``.

    from_areas : pandas.Series
        Mapping from ``from_zone_id`` to original zone area.

    to_areas : pandas.Series
        Mapping from ``to_zone_id`` to original zone area.

    sliver_cfg : dict, optional
        Dictionary containing sliver-removal thresholds:

        * ``min_area_m2`` : float
            Minimum allowable intersection area.
        * ``min_area_fraction`` : float
            Minimum allowable fraction of both parent zones occupied by the
            intersection.
        * ``min_compactness`` : float
            Minimum allowable Polsby-Popper compactness ratio.

        If ``None``, no filtering is performed.

    Returns
    -------
    geopandas.GeoDataFrame
        Overlay with detected sliver polygons removed.

    Notes
    -----
    Compactness is computed as:

    ``4 * pi * area / perimeter²``

    Values near 1 indicate compact shapes, while values approaching 0
    indicate elongated or irregular geometries.
    """
    if sliver_cfg is None:
        return overlay
    
    logger.info(
        f"Applying sliver filters: "
        f"min_area_m2={sliver_cfg["min_area_m2"]}, "
        f"min_area_fraction={sliver_cfg["min_area_fraction"]:.2f}, "
        f"min_compactness={sliver_cfg["min_compactness"]:.2f}"
    )

    overlay = overlay.copy()
    overlay["_area"] = overlay.geometry.area
    overlay["_perimeter"] = overlay.geometry.length
    overlay["_from_area"] = overlay["from_zone_id"].map(from_areas)
    overlay["_to_area"] = overlay["to_zone_id"].map(to_areas)
    overlay["_compactness"] = (4 * math.pi * overlay["_area"]) / overlay["_perimeter"].clip(lower=1e-9) ** 2
    overlay["_from_area_fraction"] = overlay["_area"] / overlay["_from_area"].clip(lower=1e-9)
    overlay["_to_area_fraction"] = overlay["_area"] / overlay["_to_area"].clip(lower=1e-9)

    tiny_area = overlay["_area"] < sliver_cfg["min_area_m2"]

    small_fraction = (
        (overlay["_from_area_fraction"] < sliver_cfg["min_area_fraction"]) & 
        (overlay["_to_area_fraction"] < sliver_cfg["min_area_fraction"])
        )

    non_compact = (
        overlay["_compactness"] < sliver_cfg["min_compactness"]
        )

    slivers = tiny_area | small_fraction | non_compact

    filtered_overlay = overlay[~slivers].drop(
        columns=["_perimeter", "_from_area", "_to_area", "_compactness", "_from_area_fraction", "_to_area_fraction"])
    
    assert overlay.to_zone_id.nunique() == filtered_overlay.to_zone_id.nunique()
    assert overlay.from_zone_id.nunique() == filtered_overlay.from_zone_id.nunique()

    n_removed = int((slivers).sum())
    logger.info(f"Sliver detection: {n_removed:,}/{len(overlay):,} \n overlaps flagged "
                f"(tiny_area={int(tiny_area.sum()):,}, " 
                f"small_fraction={int(small_fraction.sum()):,}, "
                f"non_compact={int(non_compact.sum()):,}")
    
    return filtered_overlay

def calculate_area_weights(overlay: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Appends 'area_weight' as a direct percentage share of the intersected area.
    """
    overlay = overlay.copy()
    overlay["_area"] = overlay.geometry.area
    
    internal_sum = overlay.groupby("from_zone_id")["_area"].transform("sum")
    overlay["area_weight"] = overlay["_area"] / internal_sum.clip(lower=1e-9) 
    return overlay


def apply_variable_weights(overlay: gpd.GeoDataFrame, weights: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Appends dynamically named '<var>_weight' columns with fallback to area rules.
    """
    overlay = overlay.copy()
    
    for wname in weights.columns:
        weight_col_name = f"{wname}_weight"
        raw_vals = overlay["to_zone_id"].map(weights[wname]).fillna(0.0)
        
        sum_vals = overlay.groupby("from_zone_id")["to_zone_id"].transform(
            lambda x: x.map(weights[wname]).fillna(0.0).sum()
        )
        
        zero_mask = sum_vals == 0
        if zero_mask.any():
            logger.warning("Weight '%s': Zero-sum fallback to area triggered.", wname)

        overlay[weight_col_name] = np.where(
            sum_vals > 0,
            (raw_vals / sum_vals.clip(lower=1e-9)),
            overlay["area_weight"]
        )
    return overlay


def add_default_weights(
    gdf: gpd.GeoDataFrame, 
    weight_cols: list
) -> pd.DataFrame:
    
    for col in weight_cols:
        gdf[col] = 1.0
    return gdf

def route_to_nearest_gateway(
    gdf: gpd.GeoDataFrame, 
    to_gate_nodes: gpd.GeoDataFrame, 
    weight_cols: list
) -> pd.DataFrame:
    """
    Routes external geometries to the closest gateway and assigns 1.0 to all weights.
    """
    if gdf.empty:
        return pd.DataFrame(columns=["from_zone_id", "to_zone_id"] + weight_cols)
        
    gdf_centroids = gdf.copy()
    gdf_centroids["geometry"] = gdf_centroids.geometry.centroid
    
    gw_centroids = to_gate_nodes.copy()
    gw_centroids["geometry"] = gw_centroids.geometry.centroid
    gw_centroids = gw_centroids.rename_axis("to_zone_id").reset_index()[["to_zone_id", "geometry"]]
    
    joined = gpd.sjoin_nearest(gdf_centroids, gw_centroids, how="left")
    
    for col in weight_cols:
        joined[col] = 1.0
        
    return joined



def classify_gate_nodes(
    from_gate_nodes: gpd.GeoDataFrame, 
    to_zones: gpd.GeoDataFrame
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Spatially classifies gate nodes.
    - Internal: Nodes falling inside TO_ZONES polygon.
    - External: Nodes falling outside TO_ZONES polygon.
     Returns two GeoDataFrames with the same structure as from_gate_nodes, but with an additional
    """
    if from_gate_nodes.empty:
        return gpd.GeoDataFrame(crs=from_gate_nodes.crs), gpd.GeoDataFrame(crs=from_gate_nodes.crs)
        
    logger.info("Classifying %d network gate nodes ...", len(from_gate_nodes))
    
    
    # Generate a 100 m buffer (arbitrarily chosen).
    # This accounts for minor spatial inaccuracies: geometries may not be perfectly aligned,
    # and some centroids can fall just outside their corresponding polygons even though
    # they should logically lie within them.
    from_gate_nodes_buffer = gpd.GeoDataFrame(
        geometry=from_gate_nodes.buffer(100),
        crs=from_gate_nodes.crs
        )

    nodes_joined = gpd.sjoin(from_gate_nodes_buffer, to_zones, how="left", predicate="intersects")
    
    internal_mask = nodes_joined["to_zone_id"].notna()
    internal_gates = nodes_joined[internal_mask].copy()
    external_gates = nodes_joined[~internal_mask][["geometry"]].copy()

    logger.info(f"Total Internal Gates: {len(internal_gates)}")
    logger.info(f"Total External Gates: {len(external_gates)}")
    
    return internal_gates, external_gates


def normalize_weights(df: pd.DataFrame, weight_cols: list) -> pd.DataFrame:
    """
    Normalizes all specified weight columns to sum to 1.0 per from_zone_id.
    """
    df = df.copy()
    
    for col in weight_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        
    totals = df.groupby("from_zone_id")[weight_cols].transform("sum")
    
    # Check for invalid zones where the weight sum is completely zero
    zero_mask = (totals == 0).any(axis=1)
    if zero_mask.any():
        n_zero_zones = df[zero_mask]["from_zone_id"].nunique()
        logger.warning("Found %d zones with a total weight sum of zero.", n_zero_zones)
        
    df[weight_cols] = round(df[weight_cols] / totals.clip(lower=1e-9), 3)
    return df


def build_crosswalk(
    from_zones: gpd.GeoDataFrame, 
    from_gate_nodes: gpd.GeoDataFrame,
    to_zones: gpd.GeoDataFrame, 
    to_gate_nodes: gpd.GeoDataFrame, 
    weights: pd.DataFrame, 
    sliver_cfg: dict
) -> pd.DataFrame:
    """
    Complete transportation network crosswalk interface pipeline.
    Combines polygon overlapping, external gateways, and discrete TLN point logic.
    """
    variable_weight_cols = [f"{col}_weight" for col in weights.columns]
    all_weight_cols = ["area_weight"] + variable_weight_cols

    internal_gates, external_gates = classify_gate_nodes(from_gate_nodes, to_zones)

    # =========================================================================
    # PART 1: THE INTERNAL OVERLAY
    # =========================================================================
    # Internal Crosswaslk: FROM polygon zones → TO polygon zones (with area and variable weights)
    internal_zones_cw = (
        compute_spatial_overlay(from_zones, to_zones, sliver_cfg)
        .pipe(calculate_area_weights)
        .pipe(apply_variable_weights, weights)
        ).reset_index()
    internal_zones_cw["type"] = "internal_zone"

    internal_gates_cw = (
        internal_gates
        .pipe(add_default_weights, all_weight_cols)
    ).reset_index()
    internal_gates_cw["type"] = "internal_gate"

    # =========================================================================
    # PART 2: EXTERNALS ZONES AND GATES
    # =========================================================================
    intenal_zone_ids = internal_zones_cw["from_zone_id"].unique()
    external_zones = from_zones[~from_zones.index.isin(intenal_zone_ids)].copy()
    
    external_zones_cw = route_to_nearest_gateway(
            external_zones, to_gate_nodes, all_weight_cols
    ).reset_index()
    external_zones_cw["type"] = "external_zone"

    external_gates_cw = route_to_nearest_gateway(
            external_gates, to_gate_nodes, all_weight_cols
        ).reset_index()
    external_gates_cw["type"] = "external_gate"
    
    # 4. Consolidate and compile final matrix output
    final_crosswalk = pd.concat([internal_zones_cw, internal_gates_cw, external_zones_cw, external_gates_cw], ignore_index=True)
    final_crosswalk = final_crosswalk[["from_zone_id", "to_zone_id", "type"] + all_weight_cols]
    final_crosswalk = normalize_weights(final_crosswalk, all_weight_cols)
    logger.info("Zoning crosswalk compilation finished. Total rows generated: %d", len(final_crosswalk))
    
    return final_crosswalk