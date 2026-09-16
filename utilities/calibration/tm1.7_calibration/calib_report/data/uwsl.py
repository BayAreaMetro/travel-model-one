import pandas as pd
from calib_report import tables, figures
from matplotlib.ticker import PercentFormatter


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

def plot_tlfd(observed_file, 
              ylabel, 
              observed_label="Observed", 
              additional_file=None, 
              additional_label="Modeled", 
              ax=None):
    """Plot one or two distance-frequency distributions as shares.

    Each input file is converted from counts by distance bins to shares of the
    total distribution before plotting. The observed distribution is plotted
    first, followed optionally by a second distribution for comparison.

    Parameters
    ----------
        observed_file: path-like
            Path to the observed TLFD CSV file. The file must contain a 
            ``distbin`` column and either a ``Total`` column or numeric count
            columns that can be summed across rows.

        ylabel: str
            Label for the y-axis. Defaults to ``"Observed"`` when not specified

        observed_label: str, default = "Observed"
            Legend label for the first, observed distribution.

        additional_file: path-like, optional
            Path to an optional second TLFD CSV file to plot

        additional_label: str, optional
            Legend label for the second series. Defaults to ``"Modeled"`` when ``additional_file`` 
            is provided and ``file_label`` is not specified

        ax: matplotlib.axes.Axes, optional 
            Existing axes on which to draw the plot. If not provided, a new figure
            and axes are created

    Returns
    ----------
        matplotlib.axes.Axes: the axes containing the plot
    """

    dataframes = [format_distance_freq(observed_file)]
    labels = [observed_label]

    if additional_file is not None:
        dataframes.append(format_distance_freq(additional_file))
        labels.append(additional_label)

    return figures.create_line_plot(
        dataframes=dataframes,
        x="distbin",
        y="share",
        labels=labels,
        xlabel="Distance (miles)",
        ylabel=ylabel,
        ylabel_format=PercentFormatter(1.0),
        linestyle="-",
        marker="o",
        ax=ax,
    )