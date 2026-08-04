"""Reusable helpers for loading and formatting CDAP (daily activity pattern) survey summaries."""
import pandas as pd

from calib_report import tables

# Standard CTRAMP person-type codes -> readable labels.
# TODO: Use the CTRAMP Data Model for this
PERSON_TYPE = {
    1: "Full-time worker",
    2: "Part-time worker",
    3: "University student",
    4: "Non-worker",
    5: "Retired",
    6: "Student of driving age",
    7: "Student of non-driving age",
    8: "Child too young for school",
}

# Person types whose BATS 2023 targets are unreliable (proxy reporting
# under-reports tours for people under 18), so they are sourced from CHTS.
UNDER_18_PERSON_TYPES = [
    "Student of driving age",
    "Student of non-driving age",
    "Child too young for school",
]


def load_cdap_summary(file, index_col, columns_col, values_col, index_labels=PERSON_TYPE, index_name="Person Type"):
    """Load a CDAP summary CSV and pivot to a person-type x activity-pattern table.

    Args:
        file: Path to the CDAP summary CSV.
        index_col: Column to use as the pivot index (e.g. person type).
        columns_col: Column to spread across the pivot columns (e.g. activity pattern).
        values_col: Column holding the frequency/count values to aggregate.
        index_labels: Optional mapping of raw ``index_col`` values to readable
            labels. Defaults to :data:`PERSON_TYPE`; pass ``None`` to keep the
            original values.
        index_name: Optional label for the pivot table's index header. Pass
            ``None`` to keep the original ``index_col`` name.

    Returns:
        tuple[pandas.DataFrame, pandas.DataFrame]: The raw DataFrame and the
        pivoted summary table.
    """
    df = pd.read_csv(file)

    summary = df.pivot_table(
        index=index_col,
        columns=columns_col,
        values=values_col,
    )

    # Remap the pivot table's index (person-type codes) to readable labels.
    if index_labels is not None:
        summary = summary.rename(index=index_labels)

    # Rename the index header itself.
    if index_name is not None:
        summary.index.name = index_name

    return df, summary


def blend_summaries(base, override, override_rows=UNDER_18_PERSON_TYPES):
    """Blend two summaries by replacing selected index rows in ``base``.

    Used to build the adjusted calibration targets: keep BATS 2023 values for
    most person types, but substitute CHTS values for the person types whose
    BATS estimates are unreliable. Because :func:`calib_report.tables.to_shares`
    normalizes each row independently, the differing survey totals do not
    distort the shares.

    Args:
        base: The primary summary (e.g. BATS 2023).
        override: The summary supplying replacement rows (e.g. CHTS).
        override_rows: Index labels to take from ``override`` instead of ``base``.
            Defaults to :data:`UNDER_18_PERSON_TYPES`.

    Returns:
        pandas.DataFrame: A copy of ``base`` with ``override_rows`` replaced by
        the corresponding rows from ``override``.
    """
    blended = base.copy()
    blended.loc[override_rows] = override.loc[override_rows]
    return blended


def format_cdap_table(summary, as_share=False, num_fmt=None):
    """Format the pivoted summary for Markdown display.

    Uses the shared helpers in :mod:`calib_report.tables` for number formatting
    and bold headers. Render the result in a chapter with ``tables.to_quarto``.

    Args:
        summary: Pivoted summary table from :func:`load_cdap_summary`.
        as_share: If True, convert counts to within-person-type shares before
            formatting.
        num_fmt: Optional Python format spec applied to value columns. Defaults
            to a percentage format when ``as_share`` is True, otherwise an
            integer count format.

    Returns:
        pandas.DataFrame: A display-ready DataFrame with formatted values and
        bold headers.
    """
    table = tables.to_shares(summary) if as_share else summary
    if num_fmt is None:
        num_fmt = ".1%" if as_share else ",.0f"

    # Move the person-type index into a column so it appears in the table.
    index_name = summary.index.name
    table = table.reset_index()

    table = tables.format_numeric(table, num_fmt, skip_cols=[index_name])
    return tables.bold_headers(table)
