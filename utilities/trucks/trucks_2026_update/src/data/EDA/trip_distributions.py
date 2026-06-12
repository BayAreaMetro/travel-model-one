from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def compute_weighted_histograms(
    df,
    plot_pairs,
    bins_width=20,
    filters=None,
    group_col=None,
    group_values=None,
    exclude_values=None,
    plot_id=None
):
    """Compute trip-weighted histograms for each truck-type / skim-variable pair.

    Filters the input data, then for each ``(value_col, x_col)`` pair in
    ``plot_pairs`` builds a histogram weighted by trip counts and records
    bin centers, trip totals, and share of total trips per bin.

    Parameters
    ----------
    df : pd.DataFrame
        Long-format OD DataFrame containing trip volume columns and skim
        variable columns referenced in ``plot_pairs``.  Must contain a
        ``"source"`` column.
    plot_pairs : dict
        Mapping of trip-volume column name to skim variable column name,
        e.g. ``{"light_trucks": "time_comp_light_trucks"}``.
    bins : int, optional
        Number of histogram bins.  Default is 20.
    filters : dict or None, optional
        Column-to-values mapping used to ``isin``-filter rows before
        computing histograms, e.g.
        ``{"origin_county": ["Alameda", "San Francisco"]}``.
    group_col : str or None, optional
        Column to apply ``group_values`` / ``exclude_values`` filters on.
    group_values : list or None, optional
        Keep only rows where ``group_col`` is in this list.
    exclude_values : list or None, optional
        Remove rows where ``group_col`` is in this list.
    plot_id : str or None, optional
        Label attached to every output row identifying the plot configuration.

    Returns
    -------
    pd.DataFrame
        Tidy DataFrame with one row per bin per series, with columns
        ``plot_id``, ``source``, ``series``, ``x_col``, ``bins``,
        ``bin_id``, ``bin_start``, ``bin_end``, ``center``, ``trips``,
        and ``share``.  Series with zero total trips are skipped.
    """
    data = df.copy()

    # -------------------------
    # Filtering
    # -------------------------
    if filters:
        for col, vals in filters.items():
            data = data[data[col].isin(vals)]

    if group_col and group_values is not None:
        data = data[data[group_col].isin(group_values)]

    if group_col and exclude_values is not None:
        data = data[~data[group_col].isin(exclude_values)]

    source = data["source"].iloc[0] if "source" in data else "unknown"

    all_results = []

    # -------------------------
    # Histogram computation
    # -------------------------
    for value_col, x_col in plot_pairs.items():

        if data[value_col].sum() == 0:
            print(f"Warning: No trips for {value_col} in {source}. Skipping histogram.")
            continue

        max_val = data[x_col].max()
        bins = np.arange(0, max_val + bins_width, bins_width)

        hist, edges = np.histogram(
            data[x_col],
            bins=bins,
            weights=data[value_col]
        )

        centers = (edges[:-1] + edges[1:]) / 2
        total = hist.sum()
        shares = hist / total if total > 0 else hist

        temp = pd.DataFrame({
            "plot_id": plot_id,
            "source": source,
            "series": value_col,
            "x_col": x_col,
            "bin_width": bins_width,
            "bin_id": range(len(hist)),
            "bin_start": edges[:-1],
            "bin_end": edges[1:],
            "center": centers,
            "trips": hist,
            "share": shares
        })

        all_results.append(temp)

    return pd.concat(all_results, ignore_index=True)


def plot_distributions(
    df,
    title=None,
    x_label=None,
    outpath=None
):
    """Plot trip distribution curves (total trips and share) for each truck type.

    Produces a side-by-side figure: the left panel shows raw trip counts
    per bin and the right panel shows the share of total trips per bin,
    with one line per truck-type series.  Saves to disk when ``outpath``
    is provided.

    Parameters
    ----------
    df : pd.DataFrame
        Output of :func:`compute_weighted_histograms` with columns
        ``series``, ``center``, ``trips``, ``share``, and ``source``.
    title : str or None, optional
        Figure title prefix.  Defaults to ``"Distribution"`` if ``None``.
    x_label : str or None, optional
        X-axis label shared by both panels.  Defaults to ``"Value"`` if
        ``None``.
    outpath : path-like or None, optional
        Directory where the PNG figure is saved.  The filename is derived
        from ``source`` and ``title``.  If ``None``, the figure is
        rendered but not saved.

    Returns
    -------
    None
    """
    source = df["source"].iloc[0]

    palette = {
        "very_small_trucks": "#4C72B0", 
        "light_trucks": "#DD8452",   
        "small_trucks": "#DD8452",
        "medium_trucks": "#55A868",  
        "heavy_trucks": "#C44E52",  
        "large_trucks": "#C44E52"   
    }

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for series in df["series"].unique():
        subset = df[df["series"] == series]

        axes[0].plot(subset["center"], subset["trips"], marker="o", label=series, color=palette.get(series))
        axes[1].plot(subset["center"], subset["share"], marker="o", label=series, color=palette.get(series))

    # -------------------------
    # Formatting
    # -------------------------
    title = title or "Distribution"
    x_label = x_label or "Value"

    axes[0].set_title(f"{title} (Trips)\nSource: {source}")
    axes[0].set_xlabel(x_label)
    axes[0].set_ylabel("Trips")
    axes[0].grid(True)

    axes[1].set_title(f"{title} (Share)\nSource: {source}")
    axes[1].set_xlabel(x_label)
    axes[1].set_ylabel("Share")
    axes[1].grid(True)

    axes[0].legend()
    axes[1].legend()

    plt.tight_layout()
    sns.set_context("notebook", font_scale=1.0)
    if outpath:
        name = (
            title.lower()
            .replace(" - ", "_")
            .replace("-", "")
            .replace(" ", "_")
            .replace(":", "_")
        )
        filename = f"{source}_{name}.png"
        path = Path(outpath, filename)
        print(f"Saving {filename} to: {path}")
        plt.savefig(path)


def compute_trip_distributions(long_df, configs, outpath=None):
    """Run all histogram computations and plots defined in a configuration dictionary.

    Iterates over every plot configuration entry, calls
    :func:`compute_weighted_histograms` and :func:`plot_distributions` for
    each, and concatenates the results into a single DataFrame.

    Parameters
    ----------
    long_df : pd.DataFrame
        Long-format OD DataFrame passed through to
        :func:`compute_weighted_histograms`.  Must contain a ``"source"``
        column.
    configs : dict
        Mapping of ``plot_id`` to configuration dict.  Each entry must
        contain:

        ``"plot_pairs"`` : dict
            Truck-type-to-skim-variable mapping.
        ``"bins"`` : int
            Number of histogram bins.
        ``"title"`` : str
            Figure title.
        ``"x_label"`` : str
            X-axis label.
        ``"filters"`` : dict, optional
            Row-level filters forwarded to
            :func:`compute_weighted_histograms`.
    outpath : path-like or None, optional
        Directory for saving figures; forwarded to
        :func:`plot_distributions`.

    Returns
    -------
    pd.DataFrame
        Concatenation of all per-plot histogram DataFrames from
        :func:`compute_weighted_histograms`, with a unified ``"source"``
        column.
    """
    source = long_df["source"].iloc[0] if "source" in long_df else "unknown"
    all_results = []

    for plot_id, cfg in configs.items():

        df_out = compute_weighted_histograms(
            long_df,
            plot_pairs=cfg["plot_pairs"],
            bins_width=cfg["bins"],
            filters=cfg.get("filters"),
            plot_id=plot_id
        )

        plot_distributions(
            df_out,
            title=cfg["title"],
            x_label=cfg["x_label"],
            outpath=outpath
        )

        all_results.append(df_out)

    final_df = pd.concat(all_results, ignore_index=True)
    final_df["source"] = source
    return final_df


