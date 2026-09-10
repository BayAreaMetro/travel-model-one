"""Truck-Updates evaluation pipeline.
Summary comparison of multiple scenario runs.

* a Tableau-ready validation shapefile (preserved from the original
  ``run_evaluation.py``),
* per-scenario / per-truck-type observed-vs-predicted scatter PNGs,
* per-truck-type VMT comparison PNGs, and
* a single comparison Excel workbook that embeds the same figures.

The design is deliberately flat: one function per output, one file per plot
type under ``plots/``. Adding a plot means adding a file there and two lines in
:func:`run_evaluation`. Steps fail loudly but independently — one broken step
never blocks the others.
"""
from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

import numpy as np
import pandas as pd
import geopandas as gpd

# from openpyxl import Workbook
# from openpyxl.drawing.image import Image as XLImage
# from openpyxl.styles import Alignment, Font, PatternFill
# from openpyxl.worksheet.worksheet import Worksheet
# from openpyxl.utils import get_column_letter

from src.evaluation.trip_ends import long_format_trips_by_scenario, build_trip_ends_flows_table, build_trip_ends_tod_table
from src.evaluation.trip_distribution import build_trip_distribution, build_average_trip_distance_table, build_coincidence_ratio_table, plot_trip_distributions
from src.evaluation.vmt import build_vmt_table, plot_vmt_comparison
from src.evaluation.plots.scatter_obs_vs_pred import plot_scatter_all_scenarios, read_network
from src.evaluation.excel import write_excel

from src.utils import setup_logging, save


logger = logging.getLogger(__name__)

# Rotating Color pallette for scenarios.
PALETTE = ["#4E79A7", "#F28E2B", "#59A14F", "#E15759", "#B07AA1", "#76B7B2"]

TRUCK_TYPES = ["HV", "SM"]
TRUCK_LABELS = {"HV": "Heavy Trucks (HV)", "SM": "Very Small, Small & Medium Trucks (SM)"}


def run_evaluation(cfg: dict, completed_scenarios: list[dict]) -> None:
    """
    Run every evaluation output for the scenarios that completed successfully.

    Parameters
    ----------
    cfg : dict
        The full config loaded from ``travel_model_scenarios.yaml``. Must
        contain ``"observed_data"``, ``"network_crs"``, and
        ``"evaluation_output"``.
    completed_scenarios : list of dict
        Scenario dicts (each with ``"name"`` and ``"path"`` keys) for runs that
        succeeded. Scenarios that failed are already excluded by the caller.

    Notes
    -----
    Each sub-step is wrapped in its own try/except: a failure is logged with a
    traceback and the remaining steps still run. Nothing here re-raises.
    """
    setup_logging(log_dir="data/logs", log_name="evaluation")
    iteration = cfg.get("iteration")

    logger.info("=" * 60)
    logger.info("Starting truck model evaluation pipeline")
    logger.info("Scenarios to evaluate: %s", [s["name"] for s in completed_scenarios])
    logger.info("=" * 60)

    if not completed_scenarios:
        logger.warning("No completed scenarios to evaluate Finished")
        return

    output_dir = Path(cfg["experiment_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(exist_ok=True)

    logger.info("Reading observed data")
    observed = read_observed(cfg)
    scenario_color_map = assign_colors(completed_scenarios)

    # ----------------
    #  Tables 
    # -----------------
    trips = _safe(long_format_trips_by_scenario, completed_scenarios, default = {})
    logger.info("Building Table - Trip Ends by Truck Type and Internal/External Flows")
    trip_ends_flows = _safe(build_trip_ends_flows_table, trips, default=pd.DataFrame())

    logger.info("Building Table - Trip Ends by Truck Type and Time of Day")
    trip_ends_tod = _safe(build_trip_ends_tod_table, trips, default=pd.DataFrame())

    logger.info("Building Table - Average Trip Distance by Truck Type")
    trip_distributions = _safe(build_trip_distribution, completed_scenarios, default={})
    average_trip_length = _safe(build_average_trip_distance_table, trip_distributions, default=pd.DataFrame())

    logger.info("Building Table - Trip Distribution Coincidence Ratio by Truck Type")
    coincidence_ratio = _safe(build_coincidence_ratio_table, trip_distributions, default=pd.DataFrame())

    logger.info("Building Table - Total VMT (full network) by Truck Type")
    vmt_table = _safe(build_vmt_table, completed_scenarios, iter = iteration, filters = None, default=pd.DataFrame())
    
    # ----------------
    #  Plots 
    # -----------------

    logger.info("Building Trip Distribution Plots")
    trip_distribution_figures = _safe(
        plot_trip_distributions,
        trip_distributions,  
        default={},
        )

    logger.info("Building observed-vs-predicted scatter plots")
    scatter_figures = _safe(
        plot_scatter_all_scenarios,
        completed_scenarios,
        observed,
        scenario_color_map,
        iteration,
        default={},
    )

    logger.info("Building VMT comparison plots")
    # Simulated VMT for links that have observed values. 
    observed_link_ids = set(observed["link_id"].astype(str))
    simulated_vmt = _safe(
        build_vmt_table, 
        completed_scenarios, 
        iter = iteration, 
        filters = observed_link_ids, 
        default=pd.DataFrame())

    # Link DISTANCE lives on the network. Derive a
    # link_id -> DISTANCE (miles) lookup from the first scenario's network. All
    # scenarios share the same link geometry. 
    reference_network = read_network(
        Path(completed_scenarios[0]["path"]), iteration
        )
    network_distance = reference_network.set_index("link_id")["DISTANCE"]

    vmt_figures = _safe(
            plot_vmt_comparison,
            simulated_vmt,
            observed,
            network_distance,
            scenario_color_map,
            default={},
        )

    # ----------------
    #  Excel 
    # -----------------
    try:
        write_excel(
            cfg=cfg,
            completed_scenarios=completed_scenarios,
            scenario_color_map=scenario_color_map,
            output_dir=output_dir,
            # Tables: 
            trip_ends_flows=trip_ends_flows, 
            trip_ends_tod=trip_ends_tod, 
            average_trip_length=average_trip_length, 
            coincidence_ratio=coincidence_ratio,
            vmt_table=vmt_table,
            # Plots: 
            trip_distribution_figures=trip_distribution_figures,
            scatter_figures=scatter_figures,
            vmt_figures=vmt_figures,
        )
    except Exception:
        logger.exception("Failed to write Excel workbook")

    # --- PNG export (also closes all figures) ---
    try:
        save_pngs(scatter_figures, vmt_figures, trip_distribution_figures, plots_dir)
    except Exception:
        logger.exception("Failed to save PNG figures")

    # --- Tableau shapefile (preserved from the original run_evaluation.py) ---
    try:
        save_tableau_shapefile(completed_scenarios, observed, cfg)
    except Exception:
        logger.exception("Failed to write Tableau shapefile")

    logger.info("Evaluation pipeline finished. Outputs in %s", output_dir)


def _safe(func, *args, default=None, **kwargs):
    """Call ``func(*args)`` returning ``default`` (logging a traceback) on error."""
    try:
        return func(*args, **kwargs)
    except Exception:
        logger.exception("Step %s failed", getattr(func, "__name__", func))
        return default


def read_observed(cfg: dict) -> pd.DataFrame:
    """
    Read the observed truck-count dataset.

    Parameters
    ----------
    cfg : dict
        Config dict; ``cfg["observed_data"]`` is the path to the CSV.

    Returns
    -------
    pd.DataFrame
        The observed dataset. A ``"truck_type_norm"`` column is added,
        normalising ``"truck_type_2"`` so tolled categories collapse onto the
        two assignment categories (``"HVT"`` → ``"HV"``, ``"SMT"`` → ``"SM"``).
        The geometry column is left as-is (only needed by the shapefile output).

    Notes
    -----
    Returned as a plain ``DataFrame`` rather than a ``GeoDataFrame`` — geometry
    is only materialised when writing the Tableau shapefile.
    """
    df = pd.read_csv(cfg["observed_data"])
    if "truck_type_2" in df.columns:
        df["truck_type_norm"] = (
            df["truck_type_2"].astype(str).str.replace(r"T$", "", regex=True)
        )
    if "link_id" in df.columns:
        df["link_id"] = df["link_id"].astype(str)
    return df


def clean_output(df, link_col="link_id"):
    """
    Enrich a long-format dataframe by propagating geometry and count metadata.

    Propagates, across all rows sharing a ``link_id``:
      - geometry (and ``ROUTENUM`` / ``ROUTEDIR`` / ``DISTANCE``)
      - ``count_location_id``

    Parameters
    ----------
    df : pandas.DataFrame or GeoDataFrame
        Input dataframe containing both observed and simulated rows.
    link_col : str
        Column used to join (default: ``"link_id"``).

    Returns
    -------
    pandas.DataFrame or GeoDataFrame
        Enriched dataframe with geometry and ``count_location_id`` filled, the
        ``vmt`` column added, and columns renamed to the 10-character shapefile
        limit.
    """
    out = df.copy()

    geom_lookup = (
        out[[link_col, "geometry", "ROUTENUM", "ROUTEDIR", "DISTANCE"]]
        .dropna(subset=["geometry"])
        .drop_duplicates(subset=[link_col])
    )

    count_lookup = (
        out[[link_col, "count_location_id"]]
        .dropna(subset=["count_location_id"])
        .drop_duplicates(subset=[link_col])
    )

    out = out.merge(geom_lookup, on=link_col, how="left", suffixes=("", "_geom"))
    out = out.merge(count_lookup, on=link_col, how="left", suffixes=("", "_count"))

    if "geometry_geom" in out.columns:
        out["geometry"] = out["geometry"].combine_first(out["geometry_geom"])
    if "ROUTEDIR_geom" in out.columns:
        out["ROUTEDIR"] = out["ROUTEDIR"].combine_first(out["ROUTEDIR_geom"])
    if "ROUTENUM_geom" in out.columns:
        out["ROUTENUM"] = out["ROUTENUM"].combine_first(out["ROUTENUM_geom"])
    if "DISTANCE_geom" in out.columns:
        out["DISTANCE"] = out["DISTANCE"].combine_first(out["DISTANCE_geom"])
    if "count_location_id_count" in out.columns:
        out["count_location_id"] = out["count_location_id"].combine_first(
            out["count_location_id_count"]
        )

    drop_cols = [
        "geometry_geom",
        "ROUTEDIR_geom",
        "ROUTENUM_geom",
        "DISTANCE_geom",
        "count_location_id_count",
    ]
    cols_to_drop = [c for c in drop_cols if c in out.columns]
    out = out.drop(columns=cols_to_drop)

    out["vmt"] = out["volume"] * out["DISTANCE"]

    out_cols = [
        "count_location_id",
        "link_id", "tod",
        "ROUTENUM",
        "ROUTEDIR",
        "DISTANCE",
        "truck_type_1",
        "truck_type_2",
        "volume",
        "vmt",
        "type",
        "source",
        "geometry",
    ]
    out = out[out_cols]

    rename_dict = {
        "count_location_id": "cnt_loc_id",
        "truck_type_1": "trk_typ_1",
        "truck_type_2": "trk_typ_2",
        "ROUTENUM": "route",
        "ROUTEDIR": "direction",
        "DISTANCE": "distance",
    }
    return out.rename(columns=rename_dict)


def summarize_predicted_counts(model_cfg: dict, cfg: dict) -> gpd.GeoDataFrame:
    """
    Melt a scenario's loaded network into long-format simulated truck counts.

    Parameters
    ----------
    model_cfg : dict
        Scenario dict with ``"name"`` and ``"path"`` keys.
    cfg : dict
        The full evaluation config (unused here but kept for signature
        compatibility with the original implementation).

    Returns
    -------
    gpd.GeoDataFrame
        Long-format rows with one record per link, time period, and truck type,
        tagged with ``type="simulated"`` and ``source=<scenario name>``.
    """
    scenario_name = model_cfg["name"]
    scenario_path = Path(model_cfg["path"])

    iteration = cfg.get("iteration")
    loaded_network = read_network(scenario_path, iteration)

    loaded_network["link_id"] = (
        loaded_network["A"].astype(str) + "-" + loaded_network["B"].astype(str)
    )

    tods = ["EA", "AM", "MD", "PM", "EV"]
    truck_types = {"HV": ("HV", "HVT"), "SM": ("SM", "SMT")}

    cols = []
    for tod in tods:
        for truck_type, (notoll, toll) in truck_types.items():
            name = f"VOL_{tod}_{truck_type}"
            loaded_network[name] = loaded_network[
                [f"VOL{tod}_{notoll}", f"VOL{tod}_{toll}"]
            ].sum(axis=1)
            cols.append(name)

    df_long = loaded_network.melt(
        id_vars=["link_id", "ROUTENUM", "ROUTEDIR", "DISTANCE", "geometry"],
        value_vars=cols,
        var_name="var",
        value_name="volume",
    )

    df_long["tod"] = df_long["var"].str[4:6]
    df_long["truck_type_2"] = df_long["var"].str[-2:]
    df_long["type"] = "simulated"
    df_long["source"] = scenario_name
    return df_long


def save_tableau_shapefile(
    completed_scenarios: list[dict], observed: pd.DataFrame, cfg: dict
) -> None:
    """
    Write the Tableau-ready validation shapefile (observed + simulated counts).

    Parameters
    ----------
    completed_scenarios : list of dict
        Scenario dicts with ``"name"`` and ``"path"`` keys.
    observed : pd.DataFrame
        Observed truck counts (must carry the ``geometry`` column, as WKT or
        shapely geometries).
    cfg : dict
        Config dict; ``cfg["network_crs"]`` is the network's projected CRS and
        ``cfg["evaluation_output"]`` is the output folder.

    Notes
    -----
    Preserves the behaviour of the original ``run_evaluation.py``: simulated
    rows from every scenario are concatenated with the observed rows, enriched
    by :func:`clean_output`, set to ``network_crs``, then written as
    ``validation_table.shp`` reprojected to ``EPSG:4326``.
    """
    obs = observed.copy()
    # Materialise WKT geometry strings into shapely objects if needed.
    if "geometry" in obs.columns and obs["geometry"].dtype == object:
        try:
            obs["geometry"] = gpd.GeoSeries.from_wkt(obs["geometry"])
        except Exception:
            logger.warning("Could not parse observed geometry as WKT; using as-is")

    # DISTANCE is not on the observed CSV — join it from the
    # network so clean_output can compute observed VMT. All scenarios share the
    # same link geometry, so the first one is sufficient.
    if "DISTANCE" not in obs.columns:
        try:
            iteration = cfg.get("iteration")
            ref = read_network(
                Path(completed_scenarios[0]["path"]), iteration
                )
            obs = obs.merge(
                ref.set_index("link_id")["DISTANCE"].rename("DISTANCE"),
                left_on="link_id",
                right_index=True,
                how="left",
            )
        except Exception:
            logger.exception("Could not join network DISTANCE onto observed data")

    summaries = [obs]
    for scenario in completed_scenarios:
        logger.info("  → Summary counts for: %s", scenario["name"])
        summaries.append(summarize_predicted_counts(scenario, cfg))

    out = pd.concat(summaries, axis=0)
    out = clean_output(out)
    out = gpd.GeoDataFrame(out, geometry="geometry")
    out = out.set_crs(cfg["network_crs"])

    out_path = Path(cfg["experiment_dir"]) / "assigned_volumnes.shp"
    save(out, out_path, crs="EPSG:4326")
    logger.info("Wrote Tableau shapefile: %s", out_path)


# --------------------------------------------------------------------------- #
# Colors and PNG export
# --------------------------------------------------------------------------- #
def assign_colors(completed_scenarios: list[dict]) -> dict[str, str]:
    """
    Map each scenario name to a hex color, cycling through the palette.

    Parameters
    ----------
    completed_scenarios : list of dict
        Scenario dicts with a ``"name"`` key.

    Returns
    -------
    dict of str to str
        Mapping from scenario name to a hex color string. This is the single
        place the palette is applied; plot functions and the Excel writer take
        the mapping as an argument.
    """
    return {
        s["name"]: PALETTE[i % len(PALETTE)]
        for i, s in enumerate(completed_scenarios)
    }


def save_pngs(
    scatter_figures: dict[tuple[str, str], Figure],
    vmt_figures: dict[str, Figure],
    trip_distribution: dict[tuple[str, str], Figure],
    plots_dir: Path,
) -> None:
    """
    Save all figures to ``plots_dir`` as 300-dpi PNGs, then close them.

    Parameters
    ----------
    scatter_figures : dict of (str, str) to Figure
        Keyed by ``(scenario_name, truck_type)``.
    vmt_figures : dict of str to Figure
        Keyed by truck type.
    plots_dir : Path
        Destination directory (already created by the caller).
    """
    for (scenario_name, truck_type), fig in scatter_figures.items():
        fname = plots_dir / f"scatter_{scenario_name}_{truck_type}.png"
        fig.savefig(fname, dpi=300, bbox_inches="tight")
        logger.info("Saved PNG: %s", fname)

    for (scenario_name, truck_type), fig in trip_distribution.items():
            fname = plots_dir / f"trip_distribution_{scenario_name}_{truck_type}.png"
            fig.savefig(fname, dpi=300, bbox_inches="tight")
            logger.info("Saved PNG: %s", fname)
    
    for truck_type, fig in vmt_figures.items():
        fname = plots_dir / f"vmt_comparison_{truck_type}.png"
        fig.savefig(fname, dpi=300, bbox_inches="tight")
        logger.info("Saved PNG: %s", fname)

    for fig in list(scatter_figures.values()) + list(vmt_figures.values()):
        plt.close(fig)

