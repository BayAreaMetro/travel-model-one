"""Shared formatting helpers and template loading for calibration reports."""

import html
import math
from collections.abc import Sequence
from pathlib import Path
from string import Template

import polars as pl

from tm1.steps.summaries.calibration.enums import CTRAMPModeType

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_NEAR_ZERO = 1e-9

# ---------------------------------------------------------------------------
# Simplified mode groups for tour/trip mode charts and tables.
#
# Each key is the display label; the value is the list of integer mode codes
# drawn from CTRAMPModeType.  These groups collapse the 21 individual modes
# into 8 reporting categories used by both the tour-mode and trip-mode tabs.
# ---------------------------------------------------------------------------
M = CTRAMPModeType  # shorthand for readability

MODE_GROUPS: dict[str, list[int]] = {
    "Drive Alone": [M.DA.id, M.DA_TOLL.id],
    "Shared Ride 2": [M.SR2.id, M.SR2_TOLL.id],
    "Shared Ride 3+": [M.SR3.id, M.SR3_TOLL.id],
    "Walk": [M.WALK.id],
    "Bike": [M.BIKE.id],
    "Transit - Walk": [
        M.WLK_LOC_WLK.id, M.WLK_LRF_WLK.id, M.WLK_EXP_WLK.id,
        M.WLK_HVY_WLK.id, M.WLK_COM_WLK.id,
    ],
    "Transit - Drive": [
        M.DRV_LOC_WLK.id, M.DRV_LRF_WLK.id, M.DRV_EXP_WLK.id,
        M.DRV_HVY_WLK.id, M.DRV_COM_WLK.id,
    ],
    "Taxi/TNC": [M.TAXI.id, M.TNC.id, M.TNC2.id],
}

del M  # remove shorthand from module namespace

# Colours aligned 1:1 with MODE_GROUPS keys (8 groups → 8 colours).
MODE_COLOURS = [
    "#1f77b4",  # Drive Alone
    "#ff7f0e",  # Shared Ride 2
    "#2ca02c",  # Shared Ride 3+
    "#9467bd",  # Walk
    "#8c564b",  # Bike
    "#e377c2",  # Transit - Walk
    "#d62728",  # Transit - Drive
    "#bcbd22",  # Taxi/TNC
]


def load_template(name: str) -> Template:
    """Read a template file from the ``templates/`` directory."""
    return Template((_TEMPLATES_DIR / name).read_text(encoding="utf-8"))


def esc(s: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(s))


def esc_js(s: str) -> str:
    """Escape a string for embedding inside JS single-quoted strings."""
    return str(s).replace("'", "\\'").replace('"', '\\"')


def pct_cell(val: float | None) -> str:
    """Render a table cell with a percentage value."""
    if val is None:
        return "<td>—</td>"
    return f"<td>{val:.1%}</td>"


def count_cell(val: float | None) -> str:
    """Render a table cell with a comma-formatted count."""
    if val is None:
        return "<td>—</td>"
    return f"<td>{val:,.0f}</td>"


def delta_cell(val: float, fmt: str = ".1%") -> str:
    """Render a table cell with a delta value, coloured positive/negative."""
    if abs(val) < _NEAR_ZERO:
        return f"<td>{val:{fmt}}</td>"
    cls = "pos" if val > 0 else "neg"
    return f"<td class='{cls}'>{val:{fmt}}</td>"


def add_shares(df: pl.DataFrame, value_cols: list[str]) -> pl.DataFrame:
    """Add ``{col}_share`` columns normalised across *value_cols* per row."""
    total = pl.sum_horizontal(*[pl.col(c) for c in value_cols]).alias("_total")
    df = df.with_columns(total)
    for c in value_cols:
        df = df.with_columns(
            (pl.col(c) / pl.col("_total")).alias(f"{c}_share"),
        )
    return df


def pick_datasets(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
    table_key: str,
) -> list[tuple[str, pl.DataFrame]]:
    """Return all ``(label, df)`` pairs that have data for *table_key*.

    Order follows *labels* (config order).  The first entry is conventionally
    the reference / observed dataset; subsequent entries are models.
    """
    return [
        (label, per_label[label][table_key])
        for label in labels
        if table_key in per_label.get(label, {})
    ]


# ---------------------------------------------------------------------------
# Pair-selector widget for table-based tabs
# ---------------------------------------------------------------------------
# For tabs where an N-way comparison would make tables too wide, we let the
# user pick exactly 2 of N datasets via toggle buttons.  All C(N,2) pairs
# are pre-rendered as hidden sections; the JS tracks which 2 buttons are
# active and shows the matching section.  Clicking an inactive button bumps
# the oldest active one (FIFO).


def pair_selector(
    datasets: list[tuple[str, pl.DataFrame]],
    tab_prefix: str,
    render_pair: object,
) -> str:
    """Build a "pick 2" dataset toggle for table/chart comparisons.

    *datasets* must have ≥ 2 entries.
    *tab_prefix* is a short unique string used for HTML id attributes.
    *render_pair* is called as ``render_pair(label_a, df_a, label_b, df_b)``
    and must return an HTML string for that pair.

    With exactly 2 datasets, content is rendered directly (no buttons).
    With 3+, one button per dataset is shown; exactly 2 are active at a time.
    """
    n = len(datasets)

    # Only one possible pair — render directly, no selector
    if n == 2:  # noqa: PLR2004
        return render_pair(
            datasets[0][0], datasets[0][1],
            datasets[1][0], datasets[1][1],
        )

    # --- 3+ datasets: build "pick 2" toggle buttons ---
    # One button per dataset; first two are active by default
    buttons: list[str] = []
    for k, (label, _df) in enumerate(datasets):
        active = " ds-btn-active" if k < 2 else ""  # noqa: PLR2004
        buttons.append(
            f"<button class='ds-btn{active}' "
            f"data-ds-group='{tab_prefix}' data-ds-idx='{k}' "
            f"onclick=\"toggleDataset('{tab_prefix}',{k})\">"
            f"{esc(label)}</button>",
        )

    # Pre-render all C(n,2) ordered pairs as hidden sections.
    # Pair (i,j) with i<j: datasets[i] is "obs", datasets[j] is "mod".
    sections: list[str] = []
    for i in range(n):
        for j in range(i + 1, n):
            pair_id = f"{tab_prefix}_p{i}_{j}"
            display = "block" if (i == 0 and j == 1) else "none"
            content = render_pair(
                datasets[i][0], datasets[i][1],
                datasets[j][0], datasets[j][1],
            )
            sections.append(
                f"<div class='{tab_prefix}_pairsec' "
                f"id='{pair_id}' style='display:{display}'>\n{content}\n</div>",
            )

    bar = "<div class='ds-bar'>" + "\n".join(buttons) + "</div>\n"
    return bar + "\n".join(sections)


def wrap_chart(
    div_id: str, js_body: str, *, width: int | str = 900, height: int | str = 450,
) -> str:
    """Wrap a Plotly JS snippet in a div + script block."""
    w = f"{width}px" if isinstance(width, int) else width
    h = f"{height}px" if isinstance(height, int) else height
    return (
        f"<div id='{div_id}' style='width:{w};height:{h};'></div>\n"
        f"<script>\n{js_body}\n</script>"
    )


# ---------------------------------------------------------------------------
# Gaussian smoothing for sparse distributions
# ---------------------------------------------------------------------------


def gaussian_smooth(values: list[float], *, sigma: float = 2.0) -> list[float]:
    """Apply Gaussian kernel smoothing to a 1-D signal.

    Uses a window of ±3*sigma, normalizing weights so they sum to 1 at edges.
    """
    n = len(values)
    if n == 0:
        return []
    radius = int(math.ceil(3 * sigma))
    # Pre-compute unnormalized kernel weights
    kernel = [math.exp(-0.5 * (d / sigma) ** 2) for d in range(radius + 1)]
    smoothed = []
    for i in range(n):
        wsum = 0.0
        vsum = 0.0
        for d in range(-radius, radius + 1):
            j = i + d
            if 0 <= j < n:
                w = kernel[abs(d)]
                wsum += w
                vsum += w * values[j]
        smoothed.append(vsum / wsum if wsum else 0.0)
    return smoothed


# ---------------------------------------------------------------------------
# Goodness-of-fit helpers (shared across tabs)
# ---------------------------------------------------------------------------

_FIT_HINTS = (
    "<div class='fit-hint'>"
    "<b>RMSE</b> — Root Mean Squared Error of share-point differences. "
    "Lower is better; 0 = perfect match.<br>"
    "<b>Dissimilarity Index</b> — Half the sum of absolute share differences. "
    "Ranges 0 (identical) to 1 (no overlap).<br>"
    "<b>Hellinger Distance</b> — "
    "H = &radic;(1 &minus; &Sigma;&radic;(p<sub>i</sub> q<sub>i</sub>)). "
    "Ranges 0 (identical) to 1 (no overlap). "
    "Purely share-based, unaffected by sample size."
    "</div>"
)


def hellinger(p: Sequence[float], q: Sequence[float]) -> float:
    """Hellinger distance between two discrete distributions."""
    bc = sum(math.sqrt(pi * qi) for pi, qi in zip(p, q, strict=True))
    return math.sqrt(max(0.0, 1.0 - bc))


def fit_table(
    rows: list[dict[str, float]],
    *,
    label_key: str = "label",
) -> str:
    """Build a fit-metrics table from pre-computed row dicts.

    Each dict must have keys: label_key, "rmse", "dissim", "hellinger".
    """
    out = "<table class='fit-table'><thead><tr>"
    out += f"<th>{esc(label_key.replace('_', ' ').title())}</th>"
    out += "<th>RMSE (share pts)</th>"
    out += "<th>Dissimilarity Index</th>"
    out += "<th>Hellinger Distance</th>"
    out += "</tr></thead><tbody>"

    for row in rows:
        bold = " style='font-weight:600;border-top:2px solid #333;'" if row.get("_bold") else ""
        out += f"<tr{bold}><td>{esc(str(row[label_key]))}</td>"
        out += f"<td>{row['rmse']:.4f}</td>"
        out += f"<td>{row['dissim']:.4f}</td>"
        out += f"<td>{row['hellinger']:.4f}</td></tr>"

    out += "</tbody></table>"
    out += _FIT_HINTS
    return out


def compute_fit_row(
    obs_shares: Sequence[float],
    mod_shares: Sequence[float],
    label: str,
    *,
    label_key: str = "label",
) -> dict[str, float | str]:
    """Compute RMSE, dissimilarity, and Hellinger for one row."""
    k = len(obs_shares)
    sse = sum((m - o) ** 2 for o, m in zip(obs_shares, mod_shares, strict=True))
    dissim_num = sum(abs(m - o) for o, m in zip(obs_shares, mod_shares, strict=True))
    return {
        label_key: label,
        "rmse": math.sqrt(sse / k) if k else 0.0,
        "dissim": dissim_num / 2,
        "hellinger": hellinger(obs_shares, mod_shares),
    }


# ---------------------------------------------------------------------------
# TLFD helpers (shared by nwdc and wsloc tabs)
# ---------------------------------------------------------------------------


def normalise_shares(
    df: pl.DataFrame,
    *,
    sigma: float = 2.0,
) -> tuple[list, list[float], list[float]]:
    """Compute normalised shares and smoothed curve from a single TLFD DataFrame.

    Returns ``(bins, share, smooth)``.
    """
    bins = df["distbin"].to_list()
    total = df["Total"].to_list() if "Total" in df.columns else []
    s = sum(total) or 1
    share = [v / s for v in total]
    smooth = gaussian_smooth(share, sigma=sigma)
    return bins, share, smooth


# Distinct colours for overlaying multiple datasets on line charts.
# Drawn from Tableau 10; first entry is typically the reference/survey.
DATASET_COLOURS = [
    "#4e79a7",  # blue
    "#e15759",  # red
    "#59a14f",  # green
    "#f28e2b",  # orange
    "#b07aa1",  # purple
    "#76b7b2",  # teal
    "#edc949",  # gold
]


def tlfd_traces_nway(
    datasets: list[tuple[str, pl.DataFrame]],
    *,
    sigma: float = 2.0,
    survey_labels: set[str] | None = None,
) -> tuple[list, list[dict]]:
    """Build Plotly trace dicts for an N-way TLFD comparison.

    Datasets whose label is in *survey_labels* get raw markers plus a
    Gaussian-smoothed line (useful for sparse survey data).  All other
    datasets are shown as solid lines only.

    If *survey_labels* is ``None``, the legacy behaviour applies: only the
    first dataset (index 0) is treated as survey.

    Returns ``(bins, traces)`` where *bins* comes from the first dataset.
    """
    traces: list[dict] = []
    bins: list = []
    for i, (label, df) in enumerate(datasets):
        b, share, smooth = normalise_shares(df, sigma=sigma)
        if i == 0:
            bins = b
        colour = DATASET_COLOURS[i % len(DATASET_COLOURS)]
        is_survey = (
            label in survey_labels if survey_labels is not None else i == 0
        )
        if is_survey:
            # Survey: raw markers + smoothed line
            traces.append({
                "name": f"{label} (raw)", "x": b, "y": share,
                "type": "scatter", "mode": "markers",
                "marker": {"size": 3, "opacity": 0.4, "color": colour},
            })
            traces.append({
                "name": f"{label} (smooth)", "x": b, "y": smooth,
                "type": "scatter", "mode": "lines",
                "line": {"width": 2, "color": colour},
            })
        else:
            # Model: solid line only (large-sample data doesn't need smoothing)
            traces.append({
                "name": label, "x": b, "y": share,
                "type": "scatter", "mode": "lines",
                "line": {"width": 2, "color": colour},
            })
    return bins, traces


def append_overall_fit(
    rows: list[dict],
    *,
    label_key: str = "Purpose",
) -> None:
    """Append a bold 'Overall' average row to *rows* (in-place)."""
    if not rows:
        return
    n = len(rows)
    rows.append({
        label_key: "Overall",
        "rmse": sum(r["rmse"] for r in rows) / n,
        "dissim": sum(r["dissim"] for r in rows) / n,
        "hellinger": sum(r["hellinger"] for r in rows) / n,
        "_bold": True,
    })
