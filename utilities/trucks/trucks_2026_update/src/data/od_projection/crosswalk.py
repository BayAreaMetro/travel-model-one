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
    from_centroids = from_zones.copy()
    from_centroids["geometry"] = from_centroids.geometry.centroid
    matched_centroids = gpd.sjoin(from_centroids, to_zones, how="inner", predicate="within")
    internal_from_zones = from_zones.loc[matched_centroids.index].copy()
    
    overlay = gpd.overlay(internal_from_zones.reset_index(), to_zones.reset_index(), how="intersection", keep_geom_type=False)
    overlay = overlay.explode(index_parts=False).reset_index(drop=True)
    overlay = overlay[overlay.geometry.geom_type == "Polygon"].copy()
    
    logger.info("Overlay produced %d polygon fragments", len(overlay))

    clean_overlay = remove_slivers(overlay, from_zones.geometry.area, sliver_cfg)

    collapsed = (
        overlay.dissolve(by=["from_zone_id", "to_zone_id"])
        .reset_index()
    )
    return collapsed


def remove_slivers(overlay: gpd.GeoDataFrame, from_areas: pd.Series, sliver_cfg: Optional[dict] = None) -> gpd.GeoDataFrame:
    """Filters out thin or tiny intersection fragments using geometric compactness metrics."""

    if sliver_cfg is None:
        return overlay
    
    overlay = overlay.copy()
    
    overlay["_area"] = overlay.geometry.area
    overlay["_perimeter"] = overlay.geometry.length
    overlay["_from_area"] = overlay["from_zone_id"].map(from_areas)
    overlay["_compactness"] = (4 * math.pi * overlay["_area"]) / overlay["_perimeter"].clip(lower=1e-9) ** 2
    overlay["_area_fraction"] = overlay["_area"] / overlay["_from_area"].clip(lower=1e-9)

    mask = (
        (overlay["_area"] >= sliver_cfg["min_area_m2"])
        & (overlay["_area_fraction"] >= sliver_cfg["min_area_fraction"])
        & (overlay["_compactness"] >= sliver_cfg["min_compactness"])
    )
    
    n_removed = int((~mask).sum())
    filtered_overlay = overlay[mask].drop(columns=["_perimeter", "_from_area", "_compactness", "_area_fraction"])

    if n_removed:
        logger.info("Sliver removal: dropped %d fragments", n_removed)
    return filtered_overlay

def calculate_area_weights(overlay: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Appends 'area_weight' as a direct percentage share of the intersected area.
    """
    overlay = overlay.copy()
    overlay["_area"] = overlay.geometry.area
    
    internal_sum = overlay.groupby("from_zone_id")["_area"].transform("sum")
    overlay["area_weight"] = overlay["_area"] / internal_sum.clip(lower=1e-9) 

    # Filter rows based on the 1% threshold
    dropped_count = (overlay["area_weight"] < 0.05).sum()
    overlay = overlay[overlay["area_weight"] >= 0.05].copy()

    if dropped_count > 0:
        logger.info("Filtered out %d minor fragments under the 1%% area threshold.", dropped_count)

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
    
    nodes_joined = gpd.sjoin(from_gate_nodes, to_zones, how="left", predicate="within")
    
    internal_mask = nodes_joined["to_zone_id"].notna()
    internal_gates = nodes_joined[internal_mask].copy()
    external_gates = nodes_joined[~internal_mask][["geometry"]].copy()
    
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


# def nearest_gateway_id(point: Point, gw_gdf: gpd.GeoDataFrame, to_col: str) -> int:
#     distances = gw_gdf.geometry.centroid.distance(point)
#     return int(gw_gdf.loc[distances.idxmin(), to_col])


# def remove_slivers(
#     overlay: gpd.GeoDataFrame,
#     from_areas: pd.Series,
#     from_col: str,
#     cfg: dict,
# ) -> gpd.GeoDataFrame:
#     """
#     Filter sliver polygons from an overlay result.

#     Three independent tests — a polygon is removed if it fails ANY one:
#       1. Absolute area  < slivers.min_area_m2
#       2. Relative area  < slivers.min_area_fraction  (share of parent FROM-zone area)
#       3. Compactness    < slivers.min_compactness
#              where compactness = 4π·A / P²  (0 = infinitely thin, 1 = perfect circle)

#     The _area column is kept for downstream weight calculations.
#     """
#     sc = cfg["slivers"]
#     overlay = overlay.copy()
#     overlay["_area"]          = overlay.geometry.area
#     overlay["_perimeter"]     = overlay.geometry.length
#     overlay["_from_area"]     = overlay[from_col].map(from_areas)
#     overlay["_compactness"]   = (
#         4 * math.pi * overlay["_area"]
#         / overlay["_perimeter"].clip(lower=1e-9) ** 2
#     )
#     overlay["_area_fraction"] = overlay["_area"] / overlay["_from_area"].clip(lower=1e-9)

#     before = len(overlay)
#     mask = (
#         (overlay["_area"]          >= sc["min_area_m2"])
#         & (overlay["_area_fraction"] >= sc["min_area_fraction"])
#         & (overlay["_compactness"]   >= sc["min_compactness"])
#     )
#     n_removed = int((~mask).sum())
#     overlay = overlay[mask].drop(
#         columns=["_perimeter", "_from_area", "_compactness", "_area_fraction"]
#     )

#     if n_removed:
#         logger.warning("Sliver removal: dropped %d / %d overlap polygons", n_removed, before)
#     else:
#         logger.info("Sliver removal: no slivers detected (%d overlap polygons)", before)

#     return overlay




# def build_crosswalk(
#         zone_clasification, 
#         from_zones, 
#         from_id_col,
#         # from_gate_nodes, 
#         to_zones, 
#         to_gate_nodes, 
#         to_id_col, 
#         weights: pd.DataFrame, 
#         sliver_cfg) -> pd.DataFrame:
#     from_col     = from_id_col
#     to_col       = to_id_col
#     # var_zone_col = cfg["columns"]["to_variable_zone_id"]
#     # proj_crs     = cfg["spatial"].get("projected_crs", PROJECTED_CRS_FALLBACK)
#     # weight_vars  = cfg["weights"]["variables"]   # {weight_name: csv_column}
#     # weight_names = list(weight_vars.keys())      # ordered list of weight names

#     from_zones = from_zones.copy()
#     to_zones   = to_zones.copy()
#     to_gate_nodes   = to_gate_nodes.copy()
#     weights = weights.copy() #Validate that this file has the expected shape (1454 TAZs for MTC)


#     # ── FROM GATE zones ────────────────────────────────────────────────────────
#     zone_df   = zone_clasification
#     from_gate_nodes = zone_df[zone_df["source"] == "gate_zone"]

#     # ── Pre-compute FROM zone areas and centroids ──────────────────────────────
#     from_areas     = from_zones.set_index(from_col).geometry.area
#     from_centroids = from_zones.set_index(from_col).geometry.centroid

#     # ── Polygon overlap via spatial-indexed overlay ────────────────────────────
#     logger.info("Computing FROM × TO overlay …")
#     overlay = gpd.overlay(from_zones, to_zones, how="intersection", keep_geom_type=False)
#     overlay = overlay.explode(index_parts=False).reset_index(drop=True)
#     overlay = overlay[overlay.geometry.geom_type == "Polygon"].copy()
#     logger.info("Overlay produced %d polygon fragments before sliver removal", len(overlay))

#     overlay = remove_slivers(overlay, from_areas, from_col, sliver_cfg)

#     # ── Internal fraction (always area-based) ──────────────────────────────────
#     overlay["_internal_area"] = overlay.groupby(from_col)["_area"].transform("sum")
#     overlay["_internal_frac"] = (
#         (overlay["_internal_area"] / overlay[from_col].map(from_areas).clip(lower=1e-9))
#         .clip(upper=1.0)
#     )

#     # ── Area weight (always computed) ──────────────────────────────────────────
#     # area[j] = internal_frac × overlap_area[j] / Σ_k overlap_area[k]
#     overlay["area"] = (
#         overlay["_internal_frac"]
#         * overlay["_area"]
#         / overlay["_internal_area"].clip(lower=1e-9)
#     )

#     # ── Variable weights ───────────────────────────────────────────────────────
#     # variable[j] = internal_frac × variable_value[j] / Σ_k variable_value[k]
#     # Area does NOT enter the numerator or denominator — pure variable ratio.
#     for wname in weights.columns:
#         var_map = weights[wname].to_dict()
#         overlay[f"_raw_{wname}"] = overlay[to_col].map(var_map).fillna(0.0)
#         overlay[f"_sum_{wname}"] = (
#             overlay.groupby(from_col)[f"_raw_{wname}"].transform("sum")
#         )

#         # Identify FROM zones where all overlapping TO zones have variable = 0
#         zero_mask = overlay[f"_sum_{wname}"] == 0
#         n_zero = int(overlay.loc[zero_mask, from_col].nunique())
#         if n_zero:
#             logger.warning(
#                 "Weight '%s': %d FROM zone(s) have zero variable sum — "
#                 "falling back to area weight for those zones.",
#                 wname, n_zero,
#             )

#         overlay[wname] = np.where(
#             overlay[f"_sum_{wname}"] > 0,
#             overlay["_internal_frac"]
#             * overlay[f"_raw_{wname}"]
#             / overlay[f"_sum_{wname}"].clip(lower=1e-9),
#             overlay["area"],   # fallback: area weight
#         )

#     # ── Keep only the output columns ───────────────────────────────────────────
#     keep_cols = [from_col, to_col, "_internal_frac", "area"] + weight_names
#     internal_rows = overlay[keep_cols].copy()

#     # ── Gateway rows for boundary / fully-external polygon zones ───────────────
#     from_fracs = (
#         internal_rows.drop_duplicates(from_col)
#         .set_index(from_col)["_internal_frac"]
#     )

#     gw_rows: list[dict] = []
#     all_weight_cols = ["area"] + weight_names

#     # Boundary zones: route external fraction to nearest gateway
#     for from_id, int_frac in from_fracs.items():
#         ext_frac = float(1.0 - int_frac)
#         if ext_frac > 1e-6:
#             gw_id = nearest_gateway_id(from_centroids[from_id], to_gate_nodes, to_col)
#             row = {"from_zone_id": from_id, "to_zone_id": gw_id}
#             row.update({col: ext_frac for col in all_weight_cols})
#             gw_rows.append(row)

#     # Fully external polygon zones: not in overlay at all
#     from_in_overlay = set(overlay[from_col].unique())
#     for from_id in from_zones[from_col]:
#         if from_id not in from_in_overlay:
#             gw_id = nearest_gateway_id(from_centroids[from_id], to_gate_nodes, to_col)
#             row = {"from_zone_id": from_id, "to_zone_id": gw_id}
#             row.update({col: 1.0 for col in all_weight_cols})
#             gw_rows.append(row)

#     n_boundary = sum(1 for r in gw_rows if r["area"] < 1.0)
#     n_external = len(gw_rows) - n_boundary
#     logger.info(
#         "Polygon zones — boundary (partial gateway): %d | fully external: %d",
#         n_boundary, n_external,
#     )

#     # ── TLN point zones ────────────────────────────────────────────────────────
#     tln_rows: list[dict] = []
#     gw_lo = cfg["zones"]["to_gateway_range"][0]

#     for _, rec in from_gate_nodes.iterrows():
#         zone_id = int(rec["zone_id"])
#         pt      = Point(rec["centroid_x"], rec["centroid_y"])

#         if rec["zone_class"] == "point_internal":
#             containing = to_zones[to_zones.geometry.contains(pt)]
#             if containing.empty:
#                 dists = to_zones.geometry.centroid.distance(pt)
#                 to_id = int(to_zones.loc[dists.idxmin(), to_col])
#             else:
#                 to_id = int(containing.iloc[0][to_col])
#         else:
#             to_id = nearest_gateway_id(pt, to_gate_nodes, to_col)

#         row = {"from_zone_id": zone_id, "to_zone_id": to_id}
#         row.update({col: 1.0 for col in all_weight_cols})
#         tln_rows.append(row)

#     n_tln_int = sum(1 for r in tln_rows if r["to_zone_id"] < gw_lo)
#     n_tln_ext = len(tln_rows) - n_tln_int
#     logger.info("TLN point zones — %d internal, %d external", n_tln_int, n_tln_ext)

#     # ── Combine ────────────────────────────────────────────────────────────────
#     internal_rows = (
#         internal_rows
#         .drop(columns=["_internal_frac"])
#         .rename(columns={from_col: "from_zone_id", to_col: "to_zone_id"})
#     )

#     df = pd.concat(
#         [internal_rows,
#          pd.DataFrame(gw_rows),
#          pd.DataFrame(tln_rows)],
#         ignore_index=True,
#     )

#     # Nenormalisation across all weight columns
#     for col in all_weight_cols:
#         totals = df.groupby("from_zone_id")[col].transform("sum")
#         df[col] = df[col] / totals.clip(lower=1e-9)

#     return df.sort_values(["from_zone_id", "to_zone_id"]).reset_index(drop=True)



# def build_crosswalk(cfg: dict) -> pd.DataFrame:
#     from_col     = cfg["columns"]["from_zone_id"]
#     to_col       = cfg["columns"]["to_zone_id"]
#     var_zone_col = cfg["columns"]["to_variable_zone_id"]
#     proj_crs     = cfg["spatial"].get("projected_crs", PROJECTED_CRS_FALLBACK)
#     weight_vars  = cfg["weights"]["variables"]   # {weight_name: csv_column}
#     weight_names = list(weight_vars.keys())      # ordered list of weight names

#     # ── Load spatial data ──────────────────────────────────────────────────────
#     from_gdf = gpd.read_file(cfg["paths"]["from_shapefile"])[[from_col, "geometry"]].to_crs(proj_crs)
#     to_gdf   = gpd.read_file(cfg["paths"]["to_shapefile"])[[to_col,   "geometry"]].to_crs(proj_crs)
#     gw_gdf   = gpd.read_file(cfg["paths"]["to_ext_special_zones"])[[to_col, "geometry"]].to_crs(proj_crs)

#     # ── Load weight variable data ──────────────────────────────────────────────
#     var_df = pd.read_csv(cfg["paths"]["to_variables_csv"]).set_index(var_zone_col)

#     # Validate that all referenced columns exist
#     for wname, vcol in weight_vars.items():
#         if vcol not in var_df.columns:
#             raise ValueError(
#                 f"Weight '{wname}': column '{vcol}' not found in "
#                 f"{cfg['paths']['to_variables_csv']}. "
#                 f"Available columns: {list(var_df.columns)}"
#             )
#     logger.info(
#         "Weight variables loaded: %s",
#         {wn: wv for wn, wv in weight_vars.items()},
#     )

#     # ── TLN point zones ────────────────────────────────────────────────────────
#     zone_df   = pd.read_csv(cfg["paths"]["zone_classification"])
#     tln_zones = zone_df[zone_df["source"] == "tln_point"]

#     # ── Pre-compute FROM zone areas and centroids ──────────────────────────────
#     from_areas     = from_gdf.set_index(from_col).geometry.area
#     from_centroids = from_gdf.set_index(from_col).geometry.centroid

#     # ── Polygon overlap via spatial-indexed overlay ────────────────────────────
#     logger.info("Computing FROM × TO overlay …")
#     overlay = gpd.overlay(from_gdf, to_gdf, how="intersection", keep_geom_type=False)
#     overlay = overlay.explode(index_parts=False).reset_index(drop=True)
#     overlay = overlay[overlay.geometry.geom_type == "Polygon"].copy()
#     logger.info("Overlay produced %d polygon fragments before sliver removal", len(overlay))

#     overlay = remove_slivers(overlay, from_areas, from_col, cfg)

#     # ── Internal fraction (always area-based) ──────────────────────────────────
#     overlay["_internal_area"] = overlay.groupby(from_col)["_area"].transform("sum")
#     overlay["_internal_frac"] = (
#         (overlay["_internal_area"] / overlay[from_col].map(from_areas).clip(lower=1e-9))
#         .clip(upper=1.0)
#     )

#     # ── Area weight (always computed) ──────────────────────────────────────────
#     # area[j] = internal_frac × overlap_area[j] / Σ_k overlap_area[k]
#     overlay["area"] = (
#         overlay["_internal_frac"]
#         * overlay["_area"]
#         / overlay["_internal_area"].clip(lower=1e-9)
#     )

#     # ── Variable weights ───────────────────────────────────────────────────────
#     # variable[j] = internal_frac × variable_value[j] / Σ_k variable_value[k]
#     # Area does NOT enter the numerator or denominator — pure variable ratio.
#     for wname, vcol in weight_vars.items():
#         var_map = var_df[vcol].to_dict()
#         overlay[f"_raw_{wname}"] = overlay[to_col].map(var_map).fillna(0.0)
#         overlay[f"_sum_{wname}"] = (
#             overlay.groupby(from_col)[f"_raw_{wname}"].transform("sum")
#         )

#         # Identify FROM zones where all overlapping TO zones have variable = 0
#         zero_mask = overlay[f"_sum_{wname}"] == 0
#         n_zero = int(overlay.loc[zero_mask, from_col].nunique())
#         if n_zero:
#             logger.warning(
#                 "Weight '%s': %d FROM zone(s) have zero variable sum — "
#                 "falling back to area weight for those zones.",
#                 wname, n_zero,
#             )

#         overlay[wname] = np.where(
#             overlay[f"_sum_{wname}"] > 0,
#             overlay["_internal_frac"]
#             * overlay[f"_raw_{wname}"]
#             / overlay[f"_sum_{wname}"].clip(lower=1e-9),
#             overlay["area"],   # fallback: area weight
#         )

#     # ── Keep only the output columns ───────────────────────────────────────────
#     keep_cols = [from_col, to_col, "_internal_frac", "area"] + weight_names
#     internal_rows = overlay[keep_cols].copy()

#     # ── Gateway rows for boundary / fully-external polygon zones ───────────────
#     from_fracs = (
#         internal_rows.drop_duplicates(from_col)
#         .set_index(from_col)["_internal_frac"]
#     )

#     gw_rows: list[dict] = []
#     all_weight_cols = ["area"] + weight_names

#     # Boundary zones: route external fraction to nearest gateway
#     for from_id, int_frac in from_fracs.items():
#         ext_frac = float(1.0 - int_frac)
#         if ext_frac > 1e-6:
#             gw_id = nearest_gateway_id(from_centroids[from_id], gw_gdf, to_col)
#             row = {"from_zone_id": from_id, "to_zone_id": gw_id}
#             row.update({col: ext_frac for col in all_weight_cols})
#             gw_rows.append(row)

#     # Fully external polygon zones: not in overlay at all
#     from_in_overlay = set(overlay[from_col].unique())
#     for from_id in from_gdf[from_col]:
#         if from_id not in from_in_overlay:
#             gw_id = nearest_gateway_id(from_centroids[from_id], gw_gdf, to_col)
#             row = {"from_zone_id": from_id, "to_zone_id": gw_id}
#             row.update({col: 1.0 for col in all_weight_cols})
#             gw_rows.append(row)

#     n_boundary = sum(1 for r in gw_rows if r["area"] < 1.0)
#     n_external = len(gw_rows) - n_boundary
#     logger.info(
#         "Polygon zones — boundary (partial gateway): %d | fully external: %d",
#         n_boundary, n_external,
#     )

#     # ── TLN point zones ────────────────────────────────────────────────────────
#     tln_rows: list[dict] = []
#     gw_lo = cfg["zones"]["to_gateway_range"][0]

#     for _, rec in tln_zones.iterrows():
#         zone_id = int(rec["zone_id"])
#         pt      = Point(rec["centroid_x"], rec["centroid_y"])

#         if rec["zone_class"] == "point_internal":
#             containing = to_gdf[to_gdf.geometry.contains(pt)]
#             if containing.empty:
#                 dists = to_gdf.geometry.centroid.distance(pt)
#                 to_id = int(to_gdf.loc[dists.idxmin(), to_col])
#             else:
#                 to_id = int(containing.iloc[0][to_col])
#         else:
#             to_id = nearest_gateway_id(pt, gw_gdf, to_col)

#         row = {"from_zone_id": zone_id, "to_zone_id": to_id}
#         row.update({col: 1.0 for col in all_weight_cols})
#         tln_rows.append(row)

#     n_tln_int = sum(1 for r in tln_rows if r["to_zone_id"] < gw_lo)
#     n_tln_ext = len(tln_rows) - n_tln_int
#     logger.info("TLN point zones — %d internal, %d external", n_tln_int, n_tln_ext)

#     # ── Combine ────────────────────────────────────────────────────────────────
#     internal_rows = (
#         internal_rows
#         .drop(columns=["_internal_frac"])
#         .rename(columns={from_col: "from_zone_id", to_col: "to_zone_id"})
#     )

#     df = pd.concat(
#         [internal_rows,
#          pd.DataFrame(gw_rows),
#          pd.DataFrame(tln_rows)],
#         ignore_index=True,
#     )

#     # Nenormalisation across all weight columns
#     for col in all_weight_cols:
#         totals = df.groupby("from_zone_id")[col].transform("sum")
#         df[col] = df[col] / totals.clip(lower=1e-9)

#     return df.sort_values(["from_zone_id", "to_zone_id"]).reset_index(drop=True)



# def main(config_path: str = "config/config.yaml") -> None:
#     setup_logging()
#     cfg = load_config(config_path)
#     Path(cfg["paths"]["crosswalk"]).parent.mkdir(parents=True, exist_ok=True)

#     logger.info("Building crosswalk …")
#     df = build_crosswalk(cfg)
#     df.to_csv(cfg["paths"]["crosswalk"], index=False)

#     weight_cols = ["area"] + list(cfg["weights"]["variables"].keys())
#     logger.info(
#         "FROM zones mapped: %d | crosswalk rows: %d | weight columns: %s → %s",
#         df["from_zone_id"].nunique(), len(df), weight_cols, cfg["paths"]["crosswalk"],
#     )


# if __name__ == "__main__":
#     main()
