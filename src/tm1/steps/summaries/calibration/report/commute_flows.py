"""County-to-County Commuting Flows tab renderer."""

import json

import polars as pl

from tm1.steps.summaries.calibration.enums import CTRAMPCounty

from .helpers import (
    add_shares,
    append_overall_fit,
    compute_fit_row,
    esc,
    fit_table,
    pct_cell,
    pick_datasets,
    pp_delta_cell,
    render_pairs,
)

_COUNTY_NAMES = [c.label for c in CTRAMPCounty]


def render(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    datasets = pick_datasets(per_label, labels, "county_summary")
    if len(datasets) < 2:  # noqa: PLR2004
        return "<p>Insufficient data for comparison.</p>"
    return render_pairs(datasets, _render_pair)


def _render_pair(
    obs_label: str,
    obs_df: pl.DataFrame,
    mod_label: str,
    mod_df: pl.DataFrame,
) -> str:
    parts: list[str] = [
        _scatter_chart(obs_df, mod_df, obs_label, mod_label),
        _flow_tables(obs_df, mod_df, obs_label, mod_label),
        "<h3>Goodness of Fit</h3>",
        _flows_fit_table(obs_df, mod_df),
    ]
    return "\n".join(parts)


def _scatter_chart(
    obs: pl.DataFrame, mod: pl.DataFrame,
    obs_label: str, mod_label: str,
) -> str:
    """Scatter plot of observed vs modeled commute flow shares per county pair."""
    county_col = "home_county_name"
    value_cols = [c for c in _COUNTY_NAMES if c in obs.columns or c in mod.columns]

    if not value_cols:
        return ""

    obs_s = add_shares(obs, value_cols)
    mod_s = add_shares(mod, value_cols)
    mod_by_hc = {r[county_col]: r for r in mod_s.to_dicts()}

    x_vals: list[float] = []
    y_vals: list[float] = []
    hover: list[str] = []

    for row in obs_s.to_dicts():
        hc = row[county_col]
        mr = mod_by_hc.get(hc, {})
        for vc in value_cols:
            obs_val = row.get(f"{vc}_share", 0) or 0
            mod_val = mr.get(f"{vc}_share", 0) or 0
            x_vals.append(round(obs_val * 100, 3))
            y_vals.append(round(mod_val * 100, 3))
            hover.append(f"{hc} → {vc}")

    if not x_vals:
        return ""

    # Diagonal reference line
    max_val = max(max(x_vals, default=1), max(y_vals, default=1))
    traces = [
        {
            "x": [0, max_val],
            "y": [0, max_val],
            "mode": "lines",
            "line": {"dash": "dash", "color": "#999", "width": 1},
            "showlegend": False,
            "hoverinfo": "skip",
        },
        {
            "x": x_vals,
            "y": y_vals,
            "mode": "markers",
            "marker": {"size": 7, "color": "#2196F3", "opacity": 0.7},
            "text": hover,
            "hovertemplate": "%{text}<br>Obs: %{x:.1f}%<br>Mod: %{y:.1f}%<extra></extra>",
            "showlegend": False,
        },
    ]
    layout = {
        "title": {"text": "Commute Flow Shares: Observed vs Modeled", "font": {"size": 14}},
        "xaxis": {"title": f"{obs_label} (%)", "rangemode": "tozero"},
        "yaxis": {"title": f"{mod_label} (%)", "rangemode": "tozero", "scaleanchor": "x"},
        "margin": {"l": 55, "r": 20, "t": 40, "b": 50},
        "width": 520,
        "height": 520,
    }
    div_id = "commute_scatter_" + "".join(c for c in f"{obs_label}_{mod_label}" if c.isalnum() or c == "_")
    js = f"Plotly.newPlot('{div_id}', {json.dumps(traces)}, {json.dumps(layout)}, {{responsive:true}});"
    return (
        f"<h3>Observed vs Modeled Flow Shares</h3>"
        f"<div id='{div_id}' style='width:540px;height:540px;margin:0 auto;'></div>"
        f"<script>{js}</script>"
    )


def _flow_tables(
    obs: pl.DataFrame, mod: pl.DataFrame,
    obs_label: str, mod_label: str,
) -> str:
    county_col = "home_county_name"
    value_cols = [c for c in _COUNTY_NAMES if c in obs.columns or c in mod.columns]

    obs_s = add_shares(obs, value_cols)
    mod_s = add_shares(mod, value_cols)

    county_order = {name: i for i, name in enumerate(_COUNTY_NAMES)}
    obs_rows = sorted(obs_s.to_dicts(), key=lambda r: county_order.get(r[county_col], 99))
    mod_rows = sorted(mod_s.to_dicts(), key=lambda r: county_order.get(r[county_col], 99))
    mod_by_hc: dict[str, dict] = {r[county_col]: r for r in mod_rows}

    out = f"<h3>{esc(obs_label)} (Share)</h3>"
    out += _matrix_html(obs_rows, county_col, value_cols)

    out += f"<h3>{esc(mod_label)} (Share)</h3>"
    out += _matrix_html(mod_rows, county_col, value_cols)

    out += "<h3>Delta (pp)</h3>"
    out += "<table class='cal-table'><thead><tr><th>Home County</th>"
    for vc in value_cols:
        out += f"<th>{esc(vc)}</th>"
    out += "</tr></thead><tbody>"
    for row in obs_rows:
        hc = row[county_col]
        mr = mod_by_hc.get(hc, {})
        out += f"<tr><td>{esc(str(hc))}</td>"
        for vc in value_cols:
            obs_val = row.get(f"{vc}_share", 0) or 0
            mod_val = mr.get(f"{vc}_share", 0) or 0
            out += pp_delta_cell(obs_val, mod_val)
        out += "</tr>"
    out += "</tbody></table>"
    return out


def _matrix_html(rows: list[dict], county_col: str, value_cols: list[str]) -> str:
    out = "<table class='cal-table'><thead><tr><th>Home County</th>"
    for vc in value_cols:
        out += f"<th>{esc(vc)}</th>"
    out += "</tr></thead><tbody>"
    for row in rows:
        out += f"<tr><td>{esc(str(row[county_col]))}</td>"
        for vc in value_cols:
            out += pct_cell(row.get(f"{vc}_share"))
        out += "</tr>"
    out += "</tbody></table>"
    return out


def _flows_fit_table(obs: pl.DataFrame, mod: pl.DataFrame) -> str:
    county_col = "home_county_name"
    value_cols = [c for c in _COUNTY_NAMES if c in obs.columns or c in mod.columns]

    obs_s = add_shares(obs, value_cols)
    mod_s = add_shares(mod, value_cols)

    county_order = {name: i for i, name in enumerate(_COUNTY_NAMES)}
    obs_rows = sorted(obs_s.to_dicts(), key=lambda r: county_order.get(r[county_col], 99))
    mod_by_hc = {r[county_col]: r for r in mod_s.to_dicts()}

    fit_rows: list[dict] = []
    for row in obs_rows:
        hc = row[county_col]
        mr = mod_by_hc.get(hc, {})
        obs_sh = [row.get(f"{vc}_share", 0) or 0 for vc in value_cols]
        mod_sh = [mr.get(f"{vc}_share", 0) or 0 for vc in value_cols]
        fit_rows.append(compute_fit_row(obs_sh, mod_sh, str(hc)))

    append_overall_fit(fit_rows)
    return fit_table(fit_rows)
