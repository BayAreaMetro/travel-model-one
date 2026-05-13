"""Shared formatting helpers for calibration report."""

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
# Mode groups for tour/trip charts — collapses 21 modes into 8 categories
# ---------------------------------------------------------------------------
M = CTRAMPModeType

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

del M

MODE_COLOURS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd",
    "#8c564b", "#e377c2", "#d62728", "#bcbd22",
]

DATASET_COLOURS = [
    "#4e79a7", "#e15759", "#59a14f", "#f28e2b",
    "#b07aa1", "#76b7b2", "#edc949",
]


# ---------------------------------------------------------------------------
# Basic HTML helpers
# ---------------------------------------------------------------------------

def load_template(name: str) -> Template:
    return Template((_TEMPLATES_DIR / name).read_text(encoding="utf-8"))


def esc(s: str) -> str:
    return html.escape(str(s))


def esc_js(s: str) -> str:
    """Escape for embedding in JS single-quoted strings."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')


# ---------------------------------------------------------------------------
# Delta cells with colour coding
# ---------------------------------------------------------------------------

def pp_delta_cell(obs: float, mod: float) -> str:
    """Percentage-point difference cell. obs/mod are shares (0-1 scale).
    Displays as '+2.1 pp'. Highlights >5pp amber, >10pp pink."""
    diff = (mod - obs) * 100  # share → pp
    magnitude = abs(diff)
    cls = ""
    if magnitude > 10:
        cls = " class='err-bad'"
    elif magnitude > 5:
        cls = " class='err-warn'"
    sign = "+" if diff >= 0 else ""
    return f"<td{cls}>{sign}{diff:.1f} pp</td>"


def pct_change_cell(obs: float, mod: float) -> str:
    """Percent-change cell for absolute values.
    Displays as '+15.3%'. Highlights >5% amber, >10% pink."""
    if abs(obs) < _NEAR_ZERO:
        return "<td>—</td>"
    diff = (mod - obs) / obs * 100
    magnitude = abs(diff)
    cls = ""
    if magnitude > 10:
        cls = " class='err-bad'"
    elif magnitude > 5:
        cls = " class='err-warn'"
    sign = "+" if diff >= 0 else ""
    return f"<td{cls}>{sign}{diff:.1f}%</td>"


def pct_cell(val: float | None) -> str:
    if val is None:
        return "<td>—</td>"
    return f"<td>{val:.1%}</td>"


def count_cell(val: float | None) -> str:
    if val is None:
        return "<td>—</td>"
    return f"<td>{val:,.0f}</td>"


# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------

def pick_datasets(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
    table_key: str,
) -> list[tuple[int, str, pl.DataFrame]]:
    """Return (global_index, label, df) for labels that have *table_key*."""
    return [
        (i, label, per_label[label][table_key])
        for i, label in enumerate(labels)
        if table_key in per_label.get(label, {})
    ]


def add_shares(df: pl.DataFrame, value_cols: list[str]) -> pl.DataFrame:
    """Add ``{col}_share`` columns normalised across *value_cols* per row."""
    total = pl.sum_horizontal(*[pl.col(c) for c in value_cols]).alias("_total")
    df = df.with_columns(total)
    for c in value_cols:
        df = df.with_columns(
            (pl.col(c) / pl.col("_total")).alias(f"{c}_share"),
        )
    return df


# ---------------------------------------------------------------------------
# Pair-section wrapper (global toggle pattern)
# ---------------------------------------------------------------------------

def render_pairs(
    datasets: list[tuple[int, str, pl.DataFrame]],
    render_pair,
) -> str:
    """Pre-render all C(N,2) pair sections with data-pair attributes.

    Each dataset tuple is (global_index, label, df).
    render_pair is called as render_pair(label_a, df_a, label_b, df_b).
    """
    n = len(datasets)
    if n < 2:
        return ""
    if n == 2:
        gi, gj = datasets[0][0], datasets[1][0]
        key = f"{min(gi, gj)}_{max(gi, gj)}"
        content = render_pair(
            datasets[0][1], datasets[0][2],
            datasets[1][1], datasets[1][2],
        )
        return f"<div class='pair-section' data-pair='{key}'>\n{content}\n</div>"
    sections: list[str] = []
    for a in range(n):
        for b in range(a + 1, n):
            gi, gj = datasets[a][0], datasets[b][0]
            key = f"{min(gi, gj)}_{max(gi, gj)}"
            display = "" if (a == 1 and b == 2) else "display:none"
            content = render_pair(
                datasets[a][1], datasets[a][2],
                datasets[b][1], datasets[b][2],
            )
            sections.append(
                f"<div class='pair-section' data-pair='{key}'"
                f" style='{display}'>\n{content}\n</div>"
            )
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Plotly chart wrapper
# ---------------------------------------------------------------------------

def wrap_chart(
    div_id: str, js_body: str, *, width: int | str = 900, height: int | str = 450,
) -> str:
    w = f"{width}px" if isinstance(width, int) else width
    h = f"{height}px" if isinstance(height, int) else height
    return (
        f"<div id='{div_id}' style='width:{w};height:{h};'></div>\n"
        f"<script>\n{js_body}\n</script>"
    )


# ---------------------------------------------------------------------------
# Fit metrics (NRMSE + Dissimilarity only)
# ---------------------------------------------------------------------------

def compute_fit_row(
    obs_shares: Sequence[float],
    mod_shares: Sequence[float],
    label: str,
) -> dict:
    """Compute NRMSE and dissimilarity for one category/purpose."""
    k = len(obs_shares)
    sse = sum((m - o) ** 2 for o, m in zip(obs_shares, mod_shares, strict=True))
    dissim_num = sum(abs(m - o) for o, m in zip(obs_shares, mod_shares, strict=True))
    obs_range = max(obs_shares) - min(obs_shares) if obs_shares else 1.0
    rmse = math.sqrt(sse / k) if k else 0.0
    nrmse = rmse / obs_range if obs_range > _NEAR_ZERO else 0.0
    return {
        "label": label,
        "nrmse": nrmse,
        "dissim": dissim_num / 2,
    }


def fit_table(rows: list[dict]) -> str:
    """Build NRMSE + Dissimilarity table with optional bold Overall row."""
    out = "<table class='fit-table'><thead><tr>"
    out += "<th></th><th>NRMSE</th><th>Dissimilarity</th>"
    out += "</tr></thead><tbody>"
    for row in rows:
        bold = " style='font-weight:600;border-top:2px solid #333;'" if row.get("_bold") else ""
        out += f"<tr{bold}><td>{esc(str(row['label']))}</td>"
        out += f"<td>{row['nrmse']:.4f}</td>"
        out += f"<td>{row['dissim']:.4f}</td></tr>"
    out += "</tbody></table>"
    return out


def append_overall_fit(rows: list[dict]) -> None:
    """Append bold 'Overall' average row in place."""
    if not rows:
        return
    n = len(rows)
    rows.append({
        "label": "Overall",
        "nrmse": sum(r["nrmse"] for r in rows) / n,
        "dissim": sum(r["dissim"] for r in rows) / n,
        "_bold": True,
    })


# ---------------------------------------------------------------------------
# TLFD helpers
# ---------------------------------------------------------------------------

def gaussian_smooth(values: list[float], *, sigma: float = 2.0) -> list[float]:
    n = len(values)
    if n == 0:
        return []
    radius = int(math.ceil(3 * sigma))
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


def normalise_shares(
    df: pl.DataFrame, *, sigma: float = 2.0,
) -> tuple[list, list[float], list[float]]:
    """Compute normalised shares and smoothed curve from TLFD DataFrame."""
    bins = df["distbin"].to_list()
    total = df["Total"].to_list() if "Total" in df.columns else []
    s = sum(total) or 1
    share = [v / s for v in total]
    smooth = gaussian_smooth(share, sigma=sigma)
    return bins, share, smooth


def tlfd_traces_nway(
    datasets: list[tuple[int, str, pl.DataFrame]] | list[tuple[str, pl.DataFrame]],
    *,
    sigma: float = 2.0,
    survey_labels: set[str] | None = None,
) -> tuple[list, list[dict]]:
    """Build Plotly trace dicts for an N-way TLFD comparison."""
    traces: list[dict] = []
    bins: list = []
    for i, item in enumerate(datasets):
        # Support both (idx, label, df) and (label, df) forms
        if len(item) == 3:
            _, label, df = item
        else:
            label, df = item
        b, share, smooth = normalise_shares(df, sigma=sigma)
        if i == 0:
            bins = b
        colour = DATASET_COLOURS[i % len(DATASET_COLOURS)]
        is_survey = (
            label in survey_labels if survey_labels is not None else i == 0
        )
        if is_survey:
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
            traces.append({
                "name": label, "x": b, "y": share,
                "type": "scatter", "mode": "lines",
                "line": {"width": 2, "color": colour},
            })
    return bins, traces
