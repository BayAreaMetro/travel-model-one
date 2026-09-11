# %%
import pandas as pd
from calib_report import tables, figures, config

CHTS_PURPOSE_MAP = {
    "escort": ["esco"],
    "maintenance": ["imain", "jmain"],
    "discretionary":[ "idisc", "jdisc"],
    "atwork": ["atwork"]
}

def load_chts_tlfd(file: str, purpose: str) -> pd.DataFrame:
    """Load and normalize CHTS non-mandatory tour distance porfile to canonical schema"""
    df = pd.read_csv(file)

    # Standardize distance bin column if unnamed
    if "distbin" not in df.columns:
        if "Unnamed: 0" in df.columns:
            df = df.rename(columns = {"Unnamed: 0": "distbin"})
        else:
            df["distbin"] = range(1, len(df) + 1)

    # Map canonical purpose name to CHTS column name if needed
    source_col = CHTS_PURPOSE_MAP.get(purpose, purpose)

    result = df[["distbin"]].copy()
    result[purpose] = df[source_col].sum(axis=1)

    return result


def format_distance_freq(file, purpose: str, chts_source: bool = False):
    """Format a Tour Length Frequency Distribution file into shares by distance bin.
    
    Reads a TLFD CSV that has a ``distbin`` column and one column of counts per
    non-mandatory purpose, then converts the total counts into a share of
    the overall distribution (each ``distbin``'s fraction of all tours).

    Parameters
    ----------
        file: Path to the TLFD CSV.
        purpose: Non-Mandatory Purpose {escort, shopping, maintenance, eat out, 
            visit, discretionary, work-based}
        source: Data source of the file; specified for CHTS
            
    Returns
    ----------
        pandas.DataFrame: Columns ``distbin`` and ``share``, where ``share`` sums to 1.
    """
    if chts_source:
        df = load_chts_tlfd(file, purpose)
    else:
        df = pd.read_csv(file, usecols=["distbin", purpose])

    out = df[["distbin"]].copy()
    out["share"] = tables.to_shares(df[purpose])

    return out

def plot_tlfd(observed_file, 
              purpose,  
              ylabel, 
              chts_source: bool = False,
              modeled_file=None, 
              ax=None, 
              title=None):
    """Format observed (and optionally modeled) TLFD distance-share distribution
        
    Parameters
    ----------
        observed_file: Path to the observed TLFD csv
        purpose: Non-Mandatory Purpose
        ylabel: Y-axis label for the plot
        chts_source: Boolean specifying if data file is from chts
        modeled_file Optional path to the modeled TLFD csv. When provided, a
            second "Modeled" series is drawn on the same axes.
        ax: Optional matplotlib axes to draw on.
        title: Optional plot title

    Returns
    ----------
        matplotlib.axes.Axes: the axes containing the plot
    """

    dataframes = [format_distance_freq(observed_file, purpose, chts_source=chts_source)]
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
# %%
