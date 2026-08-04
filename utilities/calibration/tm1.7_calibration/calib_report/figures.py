import matplotlib.pyplot as plt


def create_line_plot(dataframes, x, y, labels=None, ax=None, title=None,
                        xlabel=None, ylabel=None, xlabel_format=None, 
                        ylabel_format=None, xlim=None, ylim=None,
                         **scatter_kwargs):
    """Plot multiple dataframes on the same axis as a scatter plot.

    Args:
        dataframes : pandas.DataFrame or sequence of pandas.DataFrame
            A single dataframe or a list/tuple of dataframes to plot. Each
            dataframe is drawn as a separate scatter series.
        x, y : str
            Column names to use for the x and y axes. Each dataframe must
            contain these columns.
        labels : sequence of str, optional
            Legend labels for each dataframe. If omitted, series are labeled
            "series 1", "series 2", etc.
        ax : matplotlib.axes.Axes, optional
            Existing axes to draw on. A new figure/axes is created if not given.
        title, xlabel, ylabel : str, optional
            Plot title and axis labels. Axis labels default to the column names.
        xlabel_format, ylabel_format: str, optional
            Python formatting for the axis labels. Format defaults to the dataframe formatting
        xlim, ylim: list, optional
            A list/tuple setting the minimum and maximum limit for the axis.
        **plot_kwargs
            Additional keyword arguments forwarded to ``ax.plot``.

    Returns:
        matplotlib.axes.Axes
            The axes containing the scatter plot.
    """
    # Normalize a single dataframe into a list.
    if not isinstance(dataframes, (list, tuple)):
        dataframes = [dataframes]

    if labels is None:
        labels = [f"series {i + 1}" for i in range(len(dataframes))]
    elif len(labels) != len(dataframes):
        raise ValueError("labels must have the same length as dataframes")

    if ax is None:
        _, ax = plt.subplots()

    for df, label in zip(dataframes, labels):
        ax.plot(df[x], df[y], label=label, **scatter_kwargs)

    ax.set_xlabel(xlabel if xlabel is not None else x)
    ax.set_ylabel(ylabel if ylabel is not None else y)
    if title is not None:
        ax.set_title(title)
    ax.legend()

    if xlabel_format is not None:
        ax.xaxis.set_major_formatter(xlabel_format)
    if ylabel_format is not None:
        ax.yaxis.set_major_formatter(ylabel_format)

    if xlim is not None:
        ax.set_xlim(xmin=xlim[0], xmax=xlim[1])
    if ylim is not None:
        ax.set_ylim(ymin=ylim[0], ymax=ylim[1])

    return ax

def create_bar_plot(dataframes):
    """Plot multiple dataframes in a bar plot"""