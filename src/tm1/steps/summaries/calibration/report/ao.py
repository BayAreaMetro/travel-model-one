"""Auto Ownership tab renderer."""

import polars as pl

from .helpers import (
    add_shares,
    compute_fit_row,
    delta_cell,
    esc,
    esc_js,
    fit_table,
    load_template,
    pct_cell,
    wrap_chart,
)


def render(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    """Return HTML fragment for the Auto Ownership tab."""
    frames: dict[str, pl.DataFrame] = {}
    for label in labels:
        df = per_label.get(label, {}).get("county_summary")
        if df is not None:
            frames[label] = df

    if len(frames) < 2:  # noqa: PLR2004
        return "<p>Need at least two datasets for comparison.</p>"

    present = [lb for lb in labels if lb in frames]
    obs_label = present[0]
    mod_label = present[1]
    obs = frames[obs_label]
    mod = frames[mod_label]

    county_col = "county_name" if "county_name" in obs.columns else obs.columns[0]

    # Use the union of vehicle columns across both datasets so that missing
    # columns (e.g. AO=5 only in survey) get filled with zeros.
    non_veh = {"county", "county_name"}
    all_veh = sorted(
        {c for c in [*obs.columns, *mod.columns] if c not in non_veh},
        key=lambda x: (int(x) if x.isdigit() else float("inf"), x),
    )
    for vc in all_veh:
        if vc not in obs.columns:
            obs = obs.with_columns(pl.lit(0).alias(vc))
        if vc not in mod.columns:
            mod = mod.with_columns(pl.lit(0).alias(vc))
    veh_cols = all_veh

    parts: list[str] = [
        "<h3>County &times; Auto Ownership</h3>",
        _comparison_table(obs, mod, obs_label, mod_label, county_col, veh_cols),
        "<h3>Goodness of Fit</h3>",
        _ao_fit_table(obs, mod, county_col, veh_cols),
        _chart(obs, mod, obs_label, mod_label, county_col, veh_cols),
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _comparison_table(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
    county_col: str,
    veh_cols: list[str],
) -> str:
    obs = add_shares(obs, veh_cols)
    mod = add_shares(mod, veh_cols)

    obs_rows = obs.sort(county_col).to_dicts()
    mod_by_county: dict[str, dict] = {
        r[county_col]: r for r in mod.sort(county_col).to_dicts()
    }

    ncols = len(veh_cols)
    header = "<table class='cal-table'><thead><tr>"
    header += "<th rowspan='2'>County</th>"
    header += f"<th colspan='{ncols}'>{esc(obs_label)} (Share)</th>"
    header += f"<th colspan='{ncols}'>{esc(mod_label)} (Share)</th>"
    header += f"<th colspan='{ncols}'>Delta</th>"
    header += "</tr><tr>"
    for _ in range(3):
        for vc in veh_cols:
            header += f"<th>{esc(vc)}</th>"
    header += "</tr></thead><tbody>"

    body = ""
    for row in obs_rows:
        county_name = row[county_col]
        mr = mod_by_county.get(county_name, {})
        body += f"<tr><td>{esc(str(county_name))}</td>"
        for vc in veh_cols:
            body += pct_cell(row.get(f"{vc}_share"))
        for vc in veh_cols:
            body += pct_cell(mr.get(f"{vc}_share"))
        for vc in veh_cols:
            obs_val = row.get(f"{vc}_share", 0) or 0
            mod_val = mr.get(f"{vc}_share", 0) or 0
            body += delta_cell(mod_val - obs_val)
        body += "</tr>"

    return header + body + "</tbody></table>"


def _ao_fit_table(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    county_col: str,
    veh_cols: list[str],
) -> str:
    """Fit metrics per county, comparing AO share distributions."""
    obs_s = add_shares(obs, veh_cols).sort(county_col)
    mod_s = add_shares(mod, veh_cols).sort(county_col)
    obs_rows = obs_s.to_dicts()
    mod_by_c = {r[county_col]: r for r in mod_s.to_dicts()}

    fit_rows: list[dict] = []
    for row in obs_rows:
        county = row[county_col]
        mr = mod_by_c.get(county, {})
        obs_sh = [row.get(f"{vc}_share", 0) or 0 for vc in veh_cols]
        mod_sh = [mr.get(f"{vc}_share", 0) or 0 for vc in veh_cols]
        fit_rows.append(compute_fit_row(obs_sh, mod_sh, str(county), label_key="County"))

    # Overall: average of per-county metrics
    if fit_rows:
        n = len(fit_rows)
        overall = {
            "County": "Overall",
            "rmse": sum(r["rmse"] for r in fit_rows) / n,
            "dissim": sum(r["dissim"] for r in fit_rows) / n,
            "hellinger": sum(r["hellinger"] for r in fit_rows) / n,
            "_bold": True,
        }
        fit_rows.append(overall)

    return fit_table(fit_rows, label_key="County")


_VEH_COLOURS = ["#4e79a7", "#59a14f", "#f28e2b", "#e15759", "#76b7b2", "#edc949"]


def _chart(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
    county_col: str,
    veh_cols: list[str],
) -> str:
    """Horizontal stacked-bar chart: paired bars per county, segments = veh categories."""
    obs_s = add_shares(obs, veh_cols).sort(county_col, descending=True)
    mod_s = add_shares(mod, veh_cols).sort(county_col, descending=True)
    counties = obs_s[county_col].to_list()

    # Y-axis labels: paired rows per county with blank spacer between groups
    # Each spacer must be unique or Plotly merges them into one category.
    y_labels: list[str] = []
    spacer_idx = 0
    for idx, c in enumerate(counties):
        if idx > 0:
            spacer_idx += 1
            y_labels.append(" " * spacer_idx)  # unique invisible spacer
        y_labels.append(f"{c} ({esc(mod_label)})")
        y_labels.append(f"{c} ({esc(obs_label)})")

    traces: list[str] = []
    for i, vc in enumerate(veh_cols):
        colour = _VEH_COLOURS[i % len(_VEH_COLOURS)]
        obs_vals = obs_s[f"{vc}_share"].to_list()
        mod_vals = mod_s[f"{vc}_share"].to_list()
        x_vals: list[float] = []
        for idx, (o, m) in enumerate(zip(obs_vals, mod_vals, strict=True)):
            if idx > 0:
                x_vals.append(0)  # spacer
            x_vals.extend([m, o])
        hover = [f"{vc}: {v:.1%}" if v > 0 else "" for v in x_vals]
        traces.append(
            f"{{name:'{esc_js(vc)}', "
            f"y:{y_labels!r}, x:{x_vals!r}, type:'bar', "
            f"orientation:'h', "
            f"hovertext:{hover!r}, hoverinfo:'text+name', "
            f"textposition:'none', "
            f"marker:{{color:'{colour}'}}}}",
        )

    n_counties = len(counties)
    chart_height = max(400, n_counties * 85 + 100)
    tmpl = load_template("ao_chart.js")
    js = tmpl.substitute(div_id="ao_chart", traces=", ".join(traces))
    return wrap_chart("ao_chart", js, width=1000, height=chart_height)
