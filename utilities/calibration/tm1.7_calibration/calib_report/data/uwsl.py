import pandas as pd
from calib_report import tables, figures


## Process - need to load tlfd for each tour/trip purpose which includes distance and then numbers
## Numbers -> convert to share
# Shares plotted as a line chart with X axis as distance (miles) and y as percent of workers
# Need to include both modeled and observed data 

def format_distance_freq(file):
    """Format a Tour Length Frequency Distribution file into shares by distance bin.

    Reads a TLFD CSV that has a ``distbin`` column and one column of counts per
    county, sums across counties to a ``Total`` if needed, then converts the
    total counts into a share of the overall distribution (each ``distbin``'s
    fraction of all tours).

    Parameters
    ----------
        file: Path to the TLFD CSV.

    Returns
    ----------
        pandas.DataFrame: Columns ``distbin`` and ``share``, where ``share`` sums to 1.
    """
    df = pd.read_csv(file)
    value_cols = [c for c in df.columns if c not in ("distbin", "Total")]
    if "Total" not in df.columns:
        df["Total"] = df[value_cols].sum(axis=1)
    out = df[["distbin"]].copy()
    out["share"] = tables.to_shares(df["Total"])

    return out

def plot_tlfd(observed_file, ylabel, modeled_file=None, ax=None):
    """Format observed (and optionally modeled) TLFD distance-share distribution
    
    Parameters
    ----------
        observed_file: Path to the observed TLFD csv
        ylabel: Y-axis label for the plot
        modeled_file Optional path to the modeled TLFD csv. When provided, a
            second "Modeled" series is drawn on the same axes.
        ax: Optional matplotlib axes to draw on.

    Returns
    ----------
        matplotlib.axes.Axes: the axes containing the plot
    """

    dataframes = [format_distance_freq(observed_file)]
    labels = ["Observed"]

    if modeled_file is not None:
        dataframes.append(format_distance_freq(modeled_file))
        labels.append("Modeled")

    return figures.create_line_plot(
        dataframes=dataframes,
        x="distbin",
        y="share",
        labels=labels,
        xlabel="Distance (miles)",
        ylabel=ylabel,
        ylabel_format="{x:.1%}",
        linestyle="-",
        marker="o",
        ax=ax,
    )