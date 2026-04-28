"""Shared formatting helpers and template loading for calibration reports."""

import html
import math
from collections.abc import Sequence
from pathlib import Path
from string import Template

import polars as pl

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_NEAR_ZERO = 1e-9


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


def pick_pair(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
    table_key: str,
) -> tuple[str, pl.DataFrame, str, pl.DataFrame] | None:
    """Return ``(obs_label, obs_df, mod_label, mod_df)`` for *table_key*, or None."""
    frames: dict[str, pl.DataFrame] = {}
    for label in labels:
        df = per_label.get(label, {}).get(table_key)
        if df is not None:
            frames[label] = df
    present = [lb for lb in labels if lb in frames]
    if len(present) < 2:  # noqa: PLR2004
        return None
    return present[0], frames[present[0]], present[1], frames[present[1]]


def wrap_chart(
    div_id: str, js_body: str, *, width: int = 900, height: int = 450,
) -> str:
    """Wrap a Plotly JS snippet in a div + script block."""
    return (
        f"<div id='{div_id}' style='width:{width}px;height:{height}px;'></div>\n"
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
