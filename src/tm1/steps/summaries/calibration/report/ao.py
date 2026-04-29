"""Auto Ownership tab renderer."""

import polars as pl

from .helpers import (
    add_shares,
    compute_fit_row,
    esc,
    esc_js,
    fit_table,
    load_template,
    pair_selector,
    pick_datasets,
    wrap_chart,
)


def render(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    """Return HTML fragment for the Auto Ownership tab."""
    datasets = pick_datasets(per_label, labels, "county_summary")
    if len(datasets) < 2:  # noqa: PLR2004
        return "<p>Need at least two datasets for comparison.</p>"

    # N-way chart (all datasets at once) — rendered outside pair_selector
    chart_html = _nway_chart(datasets)

    # Pair-toggled tables + fit metrics
    tables_html = pair_selector(datasets, "ao", _render_pair)

    # Side-by-side: tables left (natural width), chart fills remaining space
    return (
        "<div style='display:grid;grid-template-columns:max-content 1fr;"
        "gap:1rem;align-items:start;'>"
        f"<div>{tables_html}</div>"
        f"<div>{chart_html}</div>"
        "</div>"
    )


def _render_pair(
    obs_label: str,
    obs: pl.DataFrame,
    mod_label: str,
    mod: pl.DataFrame,
) -> str:
    """Render a single (reference, model) comparison — tables only."""
    county_col = "county_name" if "county_name" in obs.columns else obs.columns[0]
    veh_cols = _union_veh_cols(obs, mod)
    obs, mod = _fill_missing(obs, mod, veh_cols=veh_cols)

    parts: list[str] = [
        "<h3>County &times; Auto Ownership</h3>",
        _comparison_table(obs, mod, obs_label, mod_label, county_col, veh_cols),
        "<h3>Goodness of Fit</h3>",
        _ao_fit_table(obs, mod, county_col, veh_cols),
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _union_veh_cols(*frames: pl.DataFrame) -> list[str]:
    """Return sorted union of vehicle-ownership columns across all DataFrames."""
    non_veh = {"county", "county_name", "_total"}
    cols: set[str] = set()
    for df in frames:
        cols.update(c for c in df.columns if c not in non_veh and not c.endswith("_share"))
    return sorted(cols, key=lambda x: (int(x) if x.isdigit() else float("inf"), x))


def _fill_missing(
    *frames: pl.DataFrame,
    veh_cols: list[str],
) -> tuple[pl.DataFrame, ...]:
    """Add zero-filled columns for any missing *veh_cols*."""
    out: list[pl.DataFrame] = []
    for df in frames:
        for vc in veh_cols:
            if vc not in df.columns:
                df = df.with_columns(pl.lit(0).alias(vc))
        out.append(df)
    return tuple(out)


def _comparison_table(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
    county_col: str,
    veh_cols: list[str],
) -> str:
    """Long-format table: one row per County × AO level."""
    obs = add_shares(obs, veh_cols)
    mod = add_shares(mod, veh_cols)

    obs_rows = obs.sort(county_col).to_dicts()
    mod_by_county: dict[str, dict] = {
        r[county_col]: r for r in mod.sort(county_col).to_dicts()
    }

    header = (
        "<table class='cal-table' style='width:auto;table-layout:auto;'>"
        "<thead><tr>"
        "<th>County</th><th>HH Vehicles</th>"
        f"<th style='text-align:right'>{esc(obs_label)}</th>"
        f"<th style='text-align:right'>{esc(mod_label)}</th>"
        "<th style='text-align:right'>Delta</th>"
        "</tr></thead><tbody>"
    )
    body = ""
    for row in obs_rows:
        county_name = row[county_col]
        mr = mod_by_county.get(county_name, {})
        first = True
        for vc in veh_cols:
            o = row.get(f"{vc}_share", 0) or 0
            m = mr.get(f"{vc}_share", 0) or 0
            d = m - o
            d_color = "red" if abs(d) > 0.05 else "inherit"
            p_cell = (
                f"<td rowspan='{len(veh_cols)}'>{esc(str(county_name))}</td>"
                if first else ""
            )
            body += (
                f"<tr>{p_cell}<td style='text-align:center'>{esc(vc)}</td>"
                f"<td style='text-align:right'>{o:.1%}</td>"
                f"<td style='text-align:right'>{m:.1%}</td>"
                f"<td style='text-align:right;color:{d_color}'>{d:+.1%}</td></tr>"
            )
            first = False

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


# Sequential blue ramp endpoints (light → dark) for ordinal AO levels.
_BLUE_LO = (198, 219, 239)  # #c6dbef
_BLUE_HI = (8, 81, 156)     # #08519c


def _seq_palette(n: int) -> list[str]:
    """Interpolate *n* hex colours from light to dark blue."""
    if n == 1:
        return ["#3182bd"]
    return [
        "#{:02x}{:02x}{:02x}".format(
            *(
                int(_BLUE_LO[c] + (_BLUE_HI[c] - _BLUE_LO[c]) * i / (n - 1))
                for c in range(3)
            ),
        )
        for i in range(n)
    ]


def _nway_chart(datasets: list[tuple[str, pl.DataFrame]]) -> str:
    """Horizontal stacked-bar chart with all datasets grouped per county."""
    # Determine common columns
    all_frames = [df for _, df in datasets]
    veh_cols = _union_veh_cols(*all_frames)
    filled = _fill_missing(*all_frames, veh_cols=veh_cols)

    county_col = "county_name" if "county_name" in all_frames[0].columns else all_frames[0].columns[0]

    # Prepare per-dataset share DataFrames, sorted descending for Plotly y-axis
    ds_shares: list[tuple[str, pl.DataFrame]] = []
    for (label, _raw), df in zip(datasets, filled, strict=True):
        ds_shares.append((label, add_shares(df, veh_cols).sort(county_col, descending=True)))

    counties = ds_shares[0][1][county_col].to_list()
    n_ds = len(ds_shares)
    ao_colours = _seq_palette(len(veh_cols))

    # Y-axis: for each county, one bar per dataset, with spacers between groups.
    # Within a group, datasets are listed top-to-bottom in reverse order so
    # the first dataset appears at the top visually (Plotly renders bottom-up).
    y_labels: list[str] = []
    spacer_idx = 0
    for ci, county in enumerate(counties):
        if ci > 0:
            spacer_idx += 1
            y_labels.append(" " * spacer_idx)
        for label, _ in reversed(ds_shares):
            y_labels.append(f"{county} ({esc(label)})")

    # One Plotly trace per AO level (stacked segments)
    traces: list[str] = []
    for vi, vc in enumerate(veh_cols):
        colour = ao_colours[vi]
        x_vals: list[float] = []
        for ci in range(len(counties)):
            if ci > 0:
                x_vals.append(0)  # spacer
            for _label, sdf in reversed(ds_shares):
                x_vals.append(sdf[f"{vc}_share"][ci])
        hover = [f"{vc}: {v:.1%}" if v > 0 else "" for v in x_vals]
        traces.append(
            f"{{name:'{esc_js(vc)}', "
            f"y:{y_labels!r}, x:{x_vals!r}, type:'bar', "
            f"orientation:'h', "
            f"hovertext:{hover!r}, hoverinfo:'text+name', "
            f"textposition:'none', "
            f"marker:{{color:'{colour}'}}}}",
        )

    chart_id = "ao_chart_nway"
    n_counties = len(counties)
    chart_height = max(400, n_counties * (35 * n_ds + 25) + 100)
    tmpl = load_template("ao_chart.js")
    js = tmpl.substitute(div_id=chart_id, traces=", ".join(traces))
    return wrap_chart(chart_id, js, width="100%", height=chart_height)
