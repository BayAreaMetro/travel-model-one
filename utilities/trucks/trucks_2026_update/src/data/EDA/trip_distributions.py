from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def compute_weighted_histograms(
    df,
    plot_pairs,
    bins=20,
    filters=None,
    group_col=None,
    group_values=None,
    exclude_values=None,
    plot_id=None
):
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
            "bins": bins,
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
    source = long_df["source"].iloc[0] if "source" in long_df else "unknown"
    all_results = []

    
    
    for plot_id, cfg in configs.items():

        df_out = compute_weighted_histograms(
            long_df,
            plot_pairs=cfg["plot_pairs"],
            bins=cfg["bins"],
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


