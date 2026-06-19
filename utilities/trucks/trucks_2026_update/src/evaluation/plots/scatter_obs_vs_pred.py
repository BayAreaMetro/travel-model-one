"""Observed-vs-predicted scatter plots, one per scenario and truck type.

The assignment only outputs two truck-type categories (``HV`` and ``SM``), so
every scenario produces exactly two scatter figures. Each figure overlays a 45°
"perfect fit" reference line and an ordinary-least-squares trend line, and
carries its fit statistics on a ``scenario_stats`` attribute so the Excel writer
can render them without recomputing.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from src.evaluation.run_evaluation import read_network

logger = logging.getLogger(__name__)

TRUCK_TYPES = ["HV", "SM"]
TRUCK_LABELS = {"HV": "Heavy Trucks (HV)", "SM": "Very Small, Small & Medium Trucks (SM)"}


def plot_scatter_all_scenarios(
    completed_scenarios: list[dict],
    observed: pd.DataFrame,
    scenario_color_map: dict[str, str],
) -> dict[tuple[str, str], Figure]:
    """
    Build an observed-vs-predicted scatter plot for every scenario and truck type.

    Parameters
    ----------
    completed_scenarios : list of dict
        Scenario configuration dicts, each containing at least ``"name"`` and
        ``"path"`` keys. Scenarios that failed are already excluded.
    observed : pd.DataFrame
        Observed truck counts, one row per count location, time period, and
        truck type. Must contain ``"link_id"``, ``"volume"``, and
        ``"truck_type_norm"`` (``"HV"`` / ``"SM"``).
    scenario_color_map : dict of str to str
        Mapping from scenario name to the hex color used for that scenario's
        points and trend line.

    Returns
    -------
    dict of (str, str) to matplotlib.figure.Figure
        Keyed by ``(scenario_name, truck_type)`` where ``truck_type`` is one of
        ``"HV"`` or ``"SM"``. Each figure has a ``scenario_stats`` attribute
        (dict with ``slope``, ``intercept``, ``r2``, ``n``).

    Notes
    -----
    The network is joined to the observed counts with an inner join on
    ``link_id``, so only links that have an observed count are plotted.
    """
    figures: dict[tuple[str, str], Figure] = {}
    for scenario in completed_scenarios:
        name = scenario["name"]
        color = scenario_color_map.get(name, "#4E79A7")
        try:
            gdf = read_network(Path(scenario["path"]))
        except Exception:
            logger.exception("Could not read network for scenario %s — skipping scatter", name)
            continue

        for truck_type in TRUCK_TYPES:
            merged = _prepare_scatter_data(gdf, truck_type, observed)
            fig = _plot_single_scatter(name, truck_type, merged, color)
            figures[(name, truck_type)] = fig

    return figures


def _prepare_scatter_data(
    gdf: pd.DataFrame, truck_type: str, observed: pd.DataFrame
) -> pd.DataFrame:
    """Inner-join predicted volumes onto observed counts for one truck type."""
    pred_col = "vol_HV" if truck_type == "HV" else "vol_SM"
    pred = gdf[["link_id", pred_col]].rename(columns={pred_col: "pred_volume"})

    obs = observed[observed["truck_type_norm"] == truck_type]
    obs = (
        obs.groupby("link_id", as_index=False)["volume"]
        .sum()
        .rename(columns={"volume": "obs_volume"})
    )

    return pred.merge(obs, on="link_id", how="inner")


def _plot_single_scatter(
    scenario_name: str, truck_type: str, merged: pd.DataFrame, color: str
) -> Figure:
    """Render one observed-vs-predicted scatter figure and attach its stats."""
    obs = merged["obs_volume"].to_numpy(dtype=float)
    pred = merged["pred_volume"].to_numpy(dtype=float)
    n = len(merged)

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(obs, pred, color=color, alpha=0.6, s=40, label="Count locations")

    max_val = float(max(obs.max(), pred.max())) if n else 1.0

    # 45-degree perfect-fit reference line.
    ax.plot(
        [0, max_val], [0, max_val],
        color="black", linestyle="--", linewidth=1, label="Perfect fit (slope=1)",
    )

    slope = intercept = r2 = float("nan")
    if n >= 2:
        slope, intercept = np.polyfit(obs, pred, 1)
        xs = np.array([0.0, max_val])
        ax.plot(xs, slope * xs + intercept, color=color, linewidth=1.5, label="Trend (OLS)")

        pred_fit = slope * obs + intercept
        ss_res = float(((pred - pred_fit) ** 2).sum())
        ss_tot = float(((pred - pred.mean()) ** 2).sum())
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

        ax.text(
            0.05, 0.95,
            f"y = {slope:.2f}x + {intercept:.0f}\nR² = {r2:.2f}",
            transform=ax.transAxes, va="top", ha="left", fontsize=9,
        )

    ax.set_xlabel("Observed Volume (vehicles/day)")
    ax.set_ylabel("Predicted Volume (vehicles/day)")
    ax.set_title(f"Obs vs. Pred — {scenario_name} — {TRUCK_LABELS[truck_type]}")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()

    fig.scenario_stats = {"slope": slope, "intercept": intercept, "r2": r2, "n": n}

    # Attach the underlying link-level data so write_excel can render a QA table
    # on the sheet without recomputing (parallels scenario_stats).
    scatter_data = merged[["link_id", "obs_volume", "pred_volume"]].copy()
    scatter_data.columns = ["link_id", "observed", "predicted"]
    scatter_data["diff"] = scatter_data["predicted"] - scatter_data["observed"]
    fig.scatter_data = scatter_data.sort_values("observed", ascending=False)
    return fig
