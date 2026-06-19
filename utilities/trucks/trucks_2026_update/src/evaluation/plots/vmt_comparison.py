"""Total-VMT comparison bar charts, one per truck type.

Each figure compares observed VMT against every scenario's VMT for a single
truck type (``HV`` or ``SM``). Restricting both sides to the same set of
observed count locations is the caller's responsibility — the ``vmt_table``
passed in is expected to already be the observed-links-only variant so the
comparison is apples-to-apples.
"""
from __future__ import annotations

import logging

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)

TRUCK_TYPES = ["HV", "SM"]
TRUCK_LABELS = {"HV": "Heavy Trucks (HV)", "SM": "Small & Medium Trucks (SM)"}
OBSERVED_COLOR = "#AAAAAA"


def plot_vmt_comparison(
    vmt_table: pd.DataFrame,
    observed: pd.DataFrame,
    scenario_color_map: dict[str, str],
) -> dict[str, Figure]:
    """
    Build one VMT comparison bar chart per truck type.

    Parameters
    ----------
    vmt_table : pd.DataFrame
        Scenario VMT restricted to observed links, with truck types
        (``["HV", "SM"]``) as the index and one column per scenario name.
    observed : pd.DataFrame
        Observed truck counts. Must contain ``"volume"``, ``"DISTANCE"``, and
        ``"truck_type_norm"`` (``"HV"`` / ``"SM"``).
    scenario_color_map : dict of str to str
        Mapping from scenario name to the hex color used for that scenario's bar.

    Returns
    -------
    dict of str to matplotlib.figure.Figure
        Keyed by truck type (``"HV"`` or ``"SM"``). Each figure is a simple bar
        chart of ``Observed`` vs. each scenario.

    Notes
    -----
    Observed VMT is summed over the observed count locations only, matching the
    observed-links-only restriction already applied to ``vmt_table``.
    """
    obs_vmt = (
        observed.assign(_vmt=observed["volume"] * observed["DISTANCE"])
        .groupby("truck_type_norm")["_vmt"]
        .sum()
    )

    figures: dict[str, Figure] = {}
    for truck_type in TRUCK_TYPES:
        categories = ["Observed"]
        values = [float(obs_vmt.get(truck_type, 0.0))]
        colors = [OBSERVED_COLOR]

        for scenario_name in vmt_table.columns:
            categories.append(scenario_name)
            if truck_type in vmt_table.index:
                values.append(float(vmt_table.loc[truck_type, scenario_name]))
            else:
                values.append(float("nan"))
            colors.append(scenario_color_map.get(scenario_name, "#4E79A7"))

        fig = _plot_single_vmt(truck_type, categories, values, colors)
        # Attach the plotted values so the Excel writer can render a matching
        # numbers table without recomputing (parallels scatter's scenario_stats).
        fig.vmt_values = dict(zip(categories, values))
        figures[truck_type] = fig

    return figures


def _plot_single_vmt(
    truck_type: str, categories: list[str], values: list[float], colors: list[str]
) -> Figure:
    """Render one VMT bar chart with comma-formatted value labels."""
    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(categories, values, color=colors)

    ax.set_ylabel("Total VMT (vehicle-miles)")
    ax.set_title(f"VMT Comparison — {TRUCK_LABELS[truck_type]}")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    for bar, value in zip(bars, values):
        if value != value:  # NaN guard
            continue
        ax.annotate(
            f"{value:,.0f}",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center", va="bottom", fontsize=9,
        )

    fig.tight_layout()
    return fig
