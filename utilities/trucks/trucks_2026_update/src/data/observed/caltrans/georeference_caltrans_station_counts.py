"""
Georeference control stations by attaching a spatial geometry to each (DISTRICT, CONTROLNO, direction) combination.

The 2018 Traffic Counts files map CONTROLNO → (Route, County, Postmile,
Direction).  The SHN postmile shapefile contains a point every 0.1 miles for
all California state highways, also keyed by (Route, County, Postmile) but
with direction coded as NB / SB / EB / WB.

This module matches each unique (CONTROLNO, Direction) to the closest SHN
point by:
  1. Filtering on Route + County + normalised direction
  2. Minimising the absolute postmile difference

Input
-----
counts_dir/        : 12 district CSVs from '2018 Traffic Counts/'
                     columns include CONTROLNO, ROUTE, COUNTY, POSTMILE, DIRECTION
shn_shapefile      : SHN_Postmiles_Tenth.shp — point every 0.1 mi

Output
------
station_locations.gpkg  (GeoPackage; Shapefile 10-char column limit avoided)
    CONTROLNO, direction, route, county, postmile,
    shn_pm_matched, postmile_diff, shn_direction, longitude, latitude, geometry
"""

import glob
import logging
import os

import geopandas as gpd
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def load_shn(path: str, crs: str) -> gpd.GeoDataFrame:
    """
    Read the SHN postmile shapefile and reproject to the target CRS.

    Adds a 'direction_norm' column that maps NB/SB/EB/WB → N/S/E/W so it can
    be joined directly against the normalised direction in the counts lookup.

    Parameters
    ----------
    path : str
        Path to SHN_Postmiles_Tenth.shp.
    crs : str
        Target projected CRS (e.g. 'EPSG:26910') for distance calculations.

    Returns
    -------
    gpd.GeoDataFrame
        Columns: Route (int), County (str), PM (float), Direction (str),
                 direction_norm (str), geometry (Point).
    """
    logger.info("Loading SHN shapefile: %s", path)
    shn = gpd.read_file(path)
    shn = shn.to_crs(crs)

    direction_map = {"NB": "N", "SB": "S", "EB": "E", "WB": "W"}
    shn["direction_norm"] = shn["Direction"].map(direction_map)

    # Keep only columns needed downstream
    keep = ["Route", "County", "PM", "Direction", "direction_norm", "geometry"]
    shn = shn[keep].copy()

    logger.info("SHN loaded: %d postmile points", len(shn))
    return shn


def load_caltrans_control_stations(counts_dir: str, pattern: str) -> pd.DataFrame:
    """
    Load all district Traffic Counts CSV files and return a deduplicated table
    of unique count station locations.

    Each row is one (CONTROLNO, direction) pair with its route/county/postmile.
    The hourly count data columns (HR1…HR24) are discarded — this lookup is
    used only for spatial location.

    Parameters
    ----------
    counts_dir : str
        Folder containing one CSV per Caltrans district (e.g. '2018 Traffic Counts/').
    pattern : str
        Filename glob, e.g. '*.csv'.

    Returns
    -------
    pd.DataFrame
        Columns: CONTROLNO (float), route (int), county (str),
                 postmile (float), direction (str).
        One row per unique (CONTROLNO, direction) combination.
    """
    cols = ["DISTRICT", "CONTROLNO", "ROUTE", "COUNTY", "POSTMILE", "DIRECTION"]

    files = sorted(glob.glob(os.path.join(counts_dir, pattern)))
    if not files:
        raise FileNotFoundError(
            f"No files matching '{pattern}' found in: {counts_dir}"
        )
    logger.info("Loading %d Traffic Counts files from %s", len(files), counts_dir)

    dfs = []
    for fpath in files:
        df = pd.read_csv(fpath, low_memory=False)
        # Strip whitespace from column names (some files have trailing spaces)
        df.columns = [str(c).strip() for c in df.columns]
        dfs.append(df[cols])

    combined = pd.concat(dfs, ignore_index=True)

    # Clean ROUTE: convert to numeric, drop rows with non-numeric/garbage values
    combined["ROUTE"] = pd.to_numeric(combined["ROUTE"], errors="coerce")
    before = len(combined)
    combined = combined.dropna(subset=cols)
    combined["ROUTE"] = combined["ROUTE"].astype(int)
    dropped = before - len(combined)

    
    logger.warning(
            "Dropped %d rows with missing or invalid key fields",
            dropped,
        ) 
    
    # Final deduplication on (DISTRICT, CONTROLNO, DIRECTION) 
    # NOTE: In a small number of cases, the same (DISTRICT, CONTROLNO, DIRECTION)
    # appears associated with multiple COUNTY values. This occurs where a
    # count station lies exactly on a county boundary and is reported under
    # both counties in the source files.
    #
    # In practice, these records refer to the same physical station location.
    # Since downstream joins rely on (DISTRICT, CONTROLNO, DIRECTION) only,
    # we intentionally retain a only one record for each (DISTRICT, CONTROLNO, DIRECTION) 
    # combination.

    lookup = (
        combined[cols]
        .drop_duplicates(subset=["DISTRICT", "CONTROLNO", "DIRECTION"])
        .reset_index(drop=True)
    )

    logger.info(
        "Final counts lookup contains %d unique (DISTRICT, CONTROLNO, DIRECTION) combinations",
        len(lookup),
    )

    return lookup


def filter_shn_by_route_county(
    shn_gdf: gpd.GeoDataFrame,
    route: int,
    county: str,
) -> gpd.GeoDataFrame:
    """
    Return the SHN subset for a specific Route + County combination.

    Parameters
    ----------
    shn_gdf : gpd.GeoDataFrame
        Full SHN dataset (output of load_shn).
    route : int
        Highway route number, e.g. 680.
    county : str
        3-letter county code as it appears in the SHN, e.g. 'ALA'.

    Returns
    -------
    gpd.GeoDataFrame
        Filtered rows; empty GeoDataFrame if no match found.
    """
    return shn_gdf[(shn_gdf["Route"] == route) & (shn_gdf["County"] == county)]


def filter_shn_by_direction(
    shn_segment: gpd.GeoDataFrame,
    direction: str,
) -> gpd.GeoDataFrame:
    """
    Further filter an SHN segment to rows matching the normalised direction.

    Falls back to the full segment (all directions) when the direction-filtered
    subset is empty — this can happen on undivided highways that have only one
    set of postmile points.

    Parameters
    ----------
    shn_segment : gpd.GeoDataFrame
        SHN rows already filtered to Route + County.
    direction : str
        Normalised direction: 'N', 'S', 'E', or 'W'.

    Returns
    -------
    gpd.GeoDataFrame
        Direction-filtered rows, or full segment if direction produces no rows.
    """
    filtered = shn_segment[shn_segment["direction_norm"] == direction]
    if filtered.empty:
        logger.debug(
            "No SHN rows for direction '%s' — using all directions as fallback",
            direction,
        )
        return shn_segment
    return filtered


def find_nearest_shn_point(
    postmile: float,
    shn_segment: gpd.GeoDataFrame,
) -> pd.Series:
    """
    Find the SHN point whose PM value is closest to the target postmile.

    Parameters
    ----------
    postmile : float
        Target postmile of the count station (e.g. 2.50).
    shn_segment : gpd.GeoDataFrame
        SHN rows already filtered to Route + County (+ optionally direction).

    Returns
    -------
    pd.Series
        Single row from shn_segment with columns from load_shn, plus
        'shn_pm_matched' and 'postmile_diff'.
        Returns an empty Series when shn_segment is empty.
    """
    if shn_segment.empty:
        return pd.Series(dtype=object)

    diffs = (shn_segment["PM"] - postmile).abs()
    idx = diffs.idxmin()
    row = shn_segment.loc[idx].copy()
    row["shn_pm_matched"] = row["PM"]
    row["postmile_diff"] = float(diffs[idx])
    return row


def find_shn_postmile(
    df: pd.DataFrame,
    shn_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Apply SHN matching to every row in df.

    For each (CONTROLNO, direction) pair:
      1. Filter SHN by route + county + direction (with direction fallback).
      2. Find nearest postmile point.
      3. Attach the SHN geometry.

    Stations with no Route + County match in the SHN receive a NaN geometry
    and are flagged shn_match = False so they can be investigated without
    crashing the pipeline.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing station information.
    shn_gdf : gpd.GeoDataFrame
        Full SHN dataset (output of load_shn).

    Returns
    -------
    gpd.GeoDataFrame
        One row per (CONTROLNO, direction) with geometry attached.
        Additional columns: shn_pm_matched, postmile_diff, shn_match (bool).
    """
    records = []
    no_shn_count = 0

    for _, row in df.iterrows():
        base = row.to_dict()

        segment = filter_shn_by_route_county(
            shn_gdf, int(row["ROUTE"]), str(row["COUNTY"])
        )

        if segment.empty:
            base["geometry"] = None
            base["shn_pm_matched"] = np.nan
            base["postmile_diff"] = np.nan
            base["shn_direction"] = None
            base["shn_match"] = False
            no_shn_count += 1
            records.append(base)
            continue

        segment_dir = filter_shn_by_direction(segment, str(row["DIRECTION"]))
        best = find_nearest_shn_point(float(row["POSTMILE"]), segment_dir)

        base["geometry"] = best["geometry"]
        base["shn_pm_matched"] = best["shn_pm_matched"]
        base["postmile_diff"] = best["postmile_diff"]
        base["shn_direction"] = best.get("Direction")
        base["shn_match"] = True
        records.append(base)

    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs=shn_gdf.crs)

    matched = gdf["shn_match"].sum()
    logger.info(
        "SHN matching: %d / %d stations located (%.1f%%);  %d with no SHN route/county match",
        matched,
        len(gdf),
        100 * matched / len(gdf) if len(gdf) else 0,
        no_shn_count,
    )
    return gdf


def add_lon_lat(stations: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Add 'longitude' and 'latitude' columns (EPSG:4326) for Tableau compatibility.

    Rows with null geometry receive NaN coordinates.

    Parameters
    ----------
    stations : gpd.GeoDataFrame
        Station geometries in any projected CRS.

    Returns
    -------
    gpd.GeoDataFrame
        Same rows; adds 'longitude' and 'latitude' float columns.
        CRS is unchanged (reprojection is done on a copy).
    """
    wgs84 = stations[stations.geometry.notna()].to_crs("EPSG:4326")
    stations = stations.copy()
    stations["longitude"] = np.nan
    stations["latitude"] = np.nan
    stations.loc[wgs84.index, "longitude"] = wgs84.geometry.x
    stations.loc[wgs84.index, "latitude"] = wgs84.geometry.y
    return stations


def add_additional_stations_info(df: pd.DataFrame, additional_info: pd.DataFrame) -> pd.DataFrame:
    """
    Merge additional station information into the main DataFrame.
        Additional info includes ROUTE, COUNTY, and POSTMILE from the original

    Parameters
    ----------
    df : pd.DataFrame
        Main DataFrame containing station information.
    additional_info : pd.DataFrame
        DataFrame containing additional information to merge.

    Returns
    -------
    pd.DataFrame
        DataFrame with additional information merged.
    """
    return df.merge(
        additional_info, 
        left_on=["DISTRICT", "CONTROLNO", "direction"], 
        right_on=["DISTRICT", "CONTROLNO", "DIRECTION"], 
        how="left"
        ).drop(columns=["direction"])


def georeference_control_stations(control_stations: pd.DataFrame, cfg: dict) -> gpd.GeoDataFrame:
    """
    load the Traffic Counts lookup, match each
    (CONTROLNO, direction) to the nearest SHN postmile point, and persist
    the result as a GeoPackage.

    Parameters
    ----------
    cfg : dict
        Full configuration loaded from config.yaml.

    Returns
    -------
    gpd.GeoDataFrame
        Columns: CONTROLNO, direction, route, county, postmile,
                 shn_pm_matched, postmile_diff, shn_direction, shn_match,
                 longitude, latitude, geometry.
        Saved to cfg['validation']['paths']['station_locations'].
    """
    paths = cfg["inputs"]
    working_crs = cfg["working_crs"]

    stations = control_stations[["control_station_id", "DISTRICT", "CONTROLNO", "direction"]].drop_duplicates().reset_index(drop=True)
    additional_info_df = load_caltrans_control_stations(paths["caltrans_control_stations"], "*.csv")
    shn = load_shn(paths["shn_postmiles"], working_crs)

    georeference_control_stations = (
        stations
        .pipe(add_additional_stations_info, additional_info=additional_info_df)
        .pipe(find_shn_postmile, shn_gdf=shn)
    )
    return georeference_control_stations