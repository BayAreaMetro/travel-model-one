"""
Match each control station to a network link.

A control station is a point with a direction (N/S/E/W) and a state route
number.  The MTC network links carry ROUTENUM and ROUTEDIR attributes that
make the match explicit: rather than relying on proximity alone (which would
pick up wrong parallel streets), the route number and direction are used as
the primary filter and proximity is
       Tier 1 — ROUTEDIR == station direction
       Tier 2 — ROUTEDIR is a different direction
  4. Select best: prefer tier-1 (nearest), fall back to tier-2.
  5. Quality label:
       good    — tier-1 selected, nearest tier-1 is clearly closer than
                 the next tier-1 candidonly used to choose among links on the same route.

Matching strategy (route-first)
---------------------------------
For each station:
  1. Filter the FULL network to links where ROUTENUM == station route.
     No facility-type pre-filter — the route number itself is the constraint.
  2. Among those route-matching links, find the n nearest by distance.
  3. Score each candidate:ate (or is the only one).
       suspect — tier-2 only, OR two tier-1 candidates nearly equidistant.
       no_match — route number does not appear in the network at all.

A separate 'needs_review.csv' is written with all candidates for SUSPECT
stations so the analyst can add a row to 'manual_overrides.csv'.
Re-running picks up overrides and promotes those rows to match_quality='manual'.

Input
-----
station_locations (GeoDataFrame)  output of V2a — one row per (CONTROLNO, direction)
network_shapefile                 full MTC network; no embedded CRS (assign network_crs)
manual_overrides.csv              hand-curated; empty DataFrame if file absent

Output
------
count_link_crosswalk.csv
    CONTROLNO, direction, link_id, distance_m, match_quality
    match_quality ∈ {good, suspect, manual, no_match}

needs_review.csv
    All candidates (all ranks) for SUSPECT stations, sorted by distance.
"""

import logging
import os
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)



def load_network(path: str, crs: str) -> gpd.GeoDataFrame:
    """
    Read the MTC network link shapefile and assign the given CRS.

    The MTC links shapefile ships without an embedded projection definition.
    The coordinates are already in the target CRS; we just need to label them.
    A 'link_id' column is constructed as '{A}-{B}' using the from/to node IDs.

    Parameters
    ----------
    path : str
        Path to mtc_links.shp.
    crs : str
        CRS to assign, e.g. 'EPSG:26910'.

    Returns
    -------
    gpd.GeoDataFrame
        Columns include: link_id (str), A, B, FT, ROUTENUM, ROUTEDIR, geometry.
    """
    logger.info("Loading network: %s", path)
    network = gpd.read_file(path)
    network = network.set_crs(crs, allow_override=True)
    network["link_id"] = (
        network["A"].astype(int).astype(str)
        + "-"
        + network["B"].astype(int).astype(str)
    )
    logger.info("Network loaded: %d links", len(network))
    return network


def load_manual_overrides(path: Optional[str]) -> pd.DataFrame:
    """
    Read the manually curated station → link assignments.

    Returns an empty DataFrame (not an error) when the file does not yet exist.

    Parameters
    ----------
    path : str
        Path to manual_overrides.csv.
        Expected columns: CONTROLNO, direction, link_id.

    Returns
    -------
    pd.DataFrame
        Empty if the file does not exist.
    """
    if path is None:
        logger.info("No manual_overrides path provided — skipping overrides")
        return pd.DataFrame(columns=["CONTROLNO", "direction", "link_id"])
    overrides = pd.read_csv(path)
    logger.info("Loaded %d manual overrides from %s", len(overrides), path)
    return overrides


def build_station_candidates(
    stations: gpd.GeoDataFrame,
    network: gpd.GeoDataFrame,
    lookup_buffer: int = 1000,
) -> gpd.GeoDataFrame:
    """"
    Build candidate network links for each station.

    For each station:
    - compute distance to all routed network links
    - keep all links within lookup_buffer
    - rank candidates by distance (1 = closest)
    - if no links fall within the buffer, still return one row for the station
      with link-related fields set to missing values

    Parameters
    ----------
    stations : gpd.GeoDataFrame
        Must contain CONTROLNO, direction, route, geometry.
    network : gpd.GeoDataFrame
        Network links. Must contain link_id, ROUTENUM, ROUTEDIR, geometry.
    lookup_buffer : float, default 1000
        Maximum distance in CRS units for a link to be considered a candidate.

    Returns
    -------
    gpd.GeoDataFrame
        One or more rows per station.
        If candidates are found, returns one row per candidate link.
        If no candidate is found, returns one row with missing link fields.
    """
    matched = (
        stations.loc[stations.geometry.notna()].copy()
        .reset_index(drop=True)
    )

    routed_net = network.loc[
        network["ROUTENUM"].fillna(0).astype(int) > 0
    ].copy()

    records: list[dict] = []

    for station in matched.itertuples(index=False):
        routed_net["distance_m"] = routed_net.geometry.distance(station.geometry)
        nearby_links = routed_net.loc[routed_net["distance_m"] <= lookup_buffer].copy()
        nearby_links = nearby_links.sort_values("distance_m")

        if nearby_links.empty:
            records.append(
                {
                    "control_station_id": station.control_station_id,
                    "CONTROLNO": station.CONTROLNO,
                    "direction": station.DIRECTION,
                    "route": int(station.ROUTE),
                    "link_id": str(-1),
                    "ROUTENUM": int(-1),
                    "ROUTEDIR": str(-1),
                    "distance_m": -1,
                    "rank": int(99),
                    "station_geometry": station.geometry,
                    "link_geometry": -1,
                }
            )
            continue

        nearby_links["rank"] = np.arange(1, len(nearby_links) + 1)

        for link in nearby_links.itertuples(index=False):
            records.append(
                {
                    "control_station_id": station.control_station_id,
                    "CONTROLNO": station.CONTROLNO,
                    "direction": station.DIRECTION,
                    "route": int(station.ROUTE),
                    "link_id": link.link_id,
                    "ROUTENUM": int(link.ROUTENUM),
                    "ROUTEDIR": str(link.ROUTEDIR),
                    "distance_m": float(link.distance_m),
                    "rank": int(link.rank),
                    "station_geometry": station.geometry,
                    "link_geometry": link.geometry,
                }
            )

    if not records:
        return gpd.GeoDataFrame(columns=[
            "control_station_id",
            "CONTROLNO",
            "direction",
            "route",
            "link_id",
            "ROUTENUM",
            "ROUTEDIR",
            "distance_m",
            "rank",
            "station_geometry",
            "link_geometry",
        ], crs=stations.crs)

    columns = [
        "control_station_id",
        "CONTROLNO",
        "direction",
        "route",
        "link_id",
        "ROUTENUM",
        "ROUTEDIR",
        "distance_m",
        "rank",
        "station_geometry",
        "link_geometry",
    ]
    return gpd.GeoDataFrame(records, columns=columns, crs=stations.crs, geometry="station_geometry")


def station_link_match_confidence(
    candidates: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Determine the best station-to-link match and assign a confidence classification.

    For each station, this function:
    - evaluates all candidate links
    - assigns a match priority based on route and direction agreement
    - selects the best candidate (lowest priority, then closest distance via rank)
    - labels the result with a match_quality indicator

    Match classification rules
    --------------------------
    0. "no_match"
        No candidate link exists within the lookup buffer

    1. "exact"
        Route and direction both match.

    2. "route_only"
        Route matches but direction does not

    3. "proximity:
        no route match but a nearby link exists.

    if multiple candidate links are found with the same confidence classification
    selects the one with the closest distance.

    Parameters
    ----------
    candidates : gpd.GeoDataFrame
        Candidate links per station, as produced by `build_station_candidates`.
        Must include:
        - control_station_id, route, direction
        - link_id, ROUTENUM, ROUTEDIR
        - rank (distance-based ordering; 1 = closest)

    Returns
    -------
    gpd.GeoDataFrame
        One row per station with:
        - the selected best link (if any)
        - match_quality classification: {"good", "review", "no_match"}
    """
    df = candidates.copy()
    no_match = df["link_id"] == "-1"
    route_match = df["route"] == df["ROUTENUM"]
    direction_match = df["direction"] == df["ROUTEDIR"]

    df = df.copy()
    df["match_priority"] = np.select(
        [
            no_match,
            route_match & direction_match,
            route_match,
        ],
        [
            0,
            1,
            2,
        ],
        default=3,
    )

    df["match_quality"] = df["match_priority"].replace(
        {0: "no_match", 1: "exact", 2: "route_only", 3: "proximity"}
    )

    best = (
        df
        .sort_values(["control_station_id", "match_priority", "rank"])
        .drop_duplicates(subset=["control_station_id"], keep="first")
        .drop(columns="match_priority")
        .copy()
    )

    return best


def apply_manual_overrides(
    df: pd.DataFrame,
    overrides: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """
    Replace automatically assigned link_ids with manually specified ones.

    Overridden rows receive match_quality = 'manual'.

    Parameters
    ----------
    df : pd.DataFrame
        Output of add_no_match_rows.
    overrides : pd.DataFrame
        Columns: CONTROLNO, direction, link_id.  Empty DataFrame is a no-op.

    Returns
    -------
    pd.DataFrame
        Crosswalk with overridden rows updated.
    """
    if overrides.empty:
        return df

    #TODO
    logger.info("Applied %d manual overrides", len(overrides))
    return df



def save_shapefile(
    gdf: gpd.GeoDataFrame,
    path: str,
    crs: Optional[str] = None,
) -> None:
    """
    Save a shapefile to disk.
    """
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    if crs is not None:
        gdf = gdf.set_crs(crs)
    gdf.to_file(path)


def match_stations_to_links(
    station_locations: gpd.GeoDataFrame,
    cfg: dict,
) -> pd.DataFrame:
    """
    # TODO: Documentation

    Parameters
    ----------
    station_locations : gpd.GeoDataFrame
    cfg : dict
        Full configuration loaded from config.yaml.
    
    Returns
    -------
    pd.DataFrame
        Columns: CONTROLNO, direction, link_id, distance_m, match_quality.
        match_quality ∈ {good, suspect, manual, no_match}.
        Saved to cfg['validation']['paths']['crosswalk'].
    """
    input_path = cfg["inputs"]
    output_path = cfg["outputs"]
    lookup_buffer = cfg["matching"]["search_radius_m"]

    network = load_network(input_path["mtc_network_links"], cfg["network_crs"])
    overrides = load_manual_overrides(input_path.get("overrides"))

    stations_links_candidates = build_station_candidates(station_locations, network, lookup_buffer)
    best_match = station_link_match_confidence(stations_links_candidates)
    best_match = apply_manual_overrides(best_match, overrides)
    crosswalk = best_match[~best_match["match_quality"].isin(["no_match"])]
    review = best_match[best_match["match_quality"].isin(["route_only", "proximity"])]

    save_shapefile(best_match, output_path["stations_tableau_shp"], crs="EPSG:4326")

    crosswalk_path = output_path["crosswalk"]
    os.makedirs(os.path.dirname(crosswalk_path), exist_ok=True)
    crosswalk.to_csv(crosswalk_path, index=False)

    review_path = output_path["stations_review"]
    os.makedirs(os.path.dirname(review_path), exist_ok=True)
    review.to_csv(review_path, index=False)

    logger.info("Crosswalk saved → %s", crosswalk_path)

    exact    = best_match[best_match["match_quality"] == "exact"].shape[0]
    review = review.shape[0]
    manual  = best_match[best_match["match_quality"] == "manual"].shape[0]
    no_match = best_match[best_match["match_quality"] == "no_match"].shape[0]
    logger.info(
        "Final crosswalk:  exact=%d  review=%d  manual=%d  no_match=%d  total=%d",
        exact, review, manual, no_match, len(crosswalk),
    )
    return crosswalk
