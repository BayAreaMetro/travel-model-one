import pandas as pd
from calib_report import tables, figures, config

def format_distance_freq(file, purpose: str):
    """Format a Tour Length Frequency Distribution file into shares by distance bin.
    
    Reads a TLFD CSV that has a ``distbin`` column and one column of counts per
    non-mandatory purpose, then converts the total counts into a share of
    the overall distribution (each ``distbin``'s fraction of all tours).

    Parameters
    ----------
        file: Path to the TLFD CSV.
        purpose: Non-Mandatory Purpose {escort, shopping, maintenance, eat out, 
            visit, discretionary, work-based}
            
    Returns
    ----------
        pandas.DataFrame: Columns ``distbin`` and ``share``, where ``share`` sums to 1.
    """
    df = pd.read_csv(file, usecols=["distbin", purpose])
    out = df[["distbin"]].copy()
    out["share"] = tables.to_shares(df[purpose])

    return out

def plot_tlfd(observed_file, purpose, ylabel, modeled_file=None, ax=None, title=None):
    """Format observed (and optionally modeled) TLFD distance-share distribution
        
    Parameters
    ----------
        observed_file: Path to the observed TLFD csv
        ylabel: Y-axis label for the plot
        modeled_file Optional path to the modeled TLFD csv. When provided, a
            second "Modeled" series is drawn on the same axes.
        ax: Optional matplotlib axes to draw on.
        title: Optional plot title

    Returns
    ----------
        matplotlib.axes.Axes: the axes containing the plot
    """

    dataframes = [format_distance_freq(observed_file, purpose)]
    labels = ["Observed"]

    if modeled_file is not None:
        dataframes.append(format_distance_freq(modeled_file, purpose))
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
        title=title
    )