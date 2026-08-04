"""Generic table formatting helpers for Quarto output"""

import pandas as pd
from IPython.display import Markdown

def format_numeric(
        df: pd.DataFrame,
        num_fmt: str = ",.0f",
        skip_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Apply a number format string to all value columns.

    Args:
        df: The DataFrame to format.
        num_fmt: A Python format spec applied to each value cell (e.g. ``",.0f"``
            or ``".1%"``).
        skip_cols: Column names to leave untouched (e.g. label columns).

    Returns:
        pandas.DataFrame: A copy with value columns coerced to numeric and
        formatted as strings; non-numeric/NaN cells become empty strings.
    """
    skip_cols = skip_cols or []
    out = df.copy()
    for c in out.columns:
        if c in skip_cols:
            continue
        out[c] = pd.to_numeric(out[c], errors="coerce").map(
            lambda x: format(x, num_fmt) if pd.notna(x) else ""
        )
    return out

def to_shares(df: pd.DataFrame, axis: int = 1) -> pd.DataFrame:
    """Convert counts to shares along the given axis.

    Args:
        df: A numeric table (or Series) to normalize.
        axis: The axis to normalize over. ``1`` (default) normalizes each row so
            it sums to 1; ``0`` normalizes each column. Ignored for a Series,
            which is always normalized to sum to 1.

    Returns:
        pandas.DataFrame: A copy with values divided by their row or column total.
    """
    if isinstance(df, pd.Series):
        return df / df.sum()
    return df.div(df.sum(axis=axis), axis=1 - axis)

def bold_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Wrap column headers in Markdown bold.

    Args:
        df: The DataFrame whose column headers should be emphasized.

    Returns:
        pandas.DataFrame: A copy with each column name wrapped in ``**...**``.
    """
    out = df.copy()
    out.columns = [f"**{c}**" for c in out.columns]
    return out

def to_quarto(df: pd.DataFrame) -> Markdown:
    """Render a DataFrame as a Quarto-native Markdown table.

    Args:
        df: The (already formatted) DataFrame to render.

    Returns:
        IPython.display.Markdown: A Markdown object containing a pipe table,
        suitable for display in a Quarto code cell.
    """
    return Markdown(df.to_markdown(index=False))
