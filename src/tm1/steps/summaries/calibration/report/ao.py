"""Auto Ownership tab renderer."""

import polars as pl

from .helpers import (
    add_shares,
    append_overall_fit,
    compute_fit_row,
    esc,
    esc_js,
    fit_table,
    load_template,
    pick_datasets,
    pp_delta_cell,
    render_pairs,
    wrap_chart,
)


def render(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    datasets = pick_datasets(per_label, labels, "county_summary")
    if len(datasets) < 2:  # noqa: PLR2004
        return "<p>Need at least two datasets for comparison.</p>"

    # N-way chart (always visible, not pair-toggled)
    chart_html = _nway_chart(datasets)
    # Pair-toggled tables
    tables_html = render_pairs(datasets, _render_pair)

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


def _union_veh_cols(*frames: pl.DataFrame) -> list[str]:
    non_veh = {"county", "county_name", "_total"}
    cols: set[str] = set()
    for df in frames:
        cols.update(c for c in df.columns if c not in non_veh and not c.endswith("_share"))
    return sorted(cols, key=lambda x: (int(x) if x.isdigit() else float("inf"), x))


def _fill_missing(*frames: pl.DataFrame, veh_cols: list[str]) -> tuple[pl.DataFrame, ...]:
    out: list[pl.DataFrame] = []
    for df in frames:
        for vc in veh_cols:
            if vc not in df.columns:
                df = df.with_columns(pl.lit(0).alias(vc))
        out.append(df)
    return tuple(out)


def _comparison_table(
    obs: pl.DataFrame, mod: pl.DataFrame,
    obs_label: str, mod_label: str,
    county_col: str, veh_cols: list[str],
) -> str:
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
        f"<th>{esc(obs_label)}</th>"
        f"<th>{esc(mod_label)}</th>"
        "<th>Delta (pp)</th>"
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
            p_cell = (
                f"<td rowspan='{len(veh_cols)}'>{esc(str(county_name))}</td>"
                if first else ""
            )
            body += (
                f"<tr>{p_cell}<td style='text-align:center'>{esc(vc)}</td>"
                f"<td>{o:.1%}</td><td>{m:.1%}</td>"
                f"{pp_delta_cell(o, m)}</tr>"
            )
            first = False

    return header + body + "</tbody></table>"


def _ao_fit_table(
    obs: pl.DataFrame, mod: pl.DataFrame,
    county_col: str, veh_cols: list[str],
) -> str:
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
        fit_rows.append(compute_fit_row(obs_sh, mod_sh, str(county)))

    append_overall_fit(fit_rows)
    return fit_table(fit_rows)


_BLUE_LO = (198, 219, 239)
_BLUE_HI = (8, 81, 156)


def _seq_palette(n: int) -> list[str]:
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


def _nway_chart(datasets: list[tuple[int, str, pl.DataFrame]]) -> str:
    all_frames = [df for _, _, df in datasets]
    veh_cols = _union_veh_cols(*all_frames)
    filled = _fill_missing(*all_frames, veh_cols=veh_cols)

    county_col = "county_name" if "county_name" in all_frames[0].columns else all_frames[0].columns[0]

    ds_shares: list[tuple[str, pl.DataFrame]] = []
    for (_idx, label, _raw), df in zip(datasets, filled, strict=True):
        ds_shares.append((label, add_shares(df, veh_cols).sort(county_col, descending=True)))

    counties = ds_shares[0][1][county_col].to_list()
    ao_colours = _seq_palette(len(veh_cols))

    y_labels: list[str] = []
    spacer_idx = 0
    for ci, county in enumerate(counties):
        if ci > 0:
            spacer_idx += 1
            y_labels.append(" " * spacer_idx)
        for label, _ in reversed(ds_shares):
            y_labels.append(f"{county} ({esc(label)})")

    traces: list[str] = []
    for vi, vc in enumerate(veh_cols):
        colour = ao_colours[vi]
        x_vals: list[float] = []
        for ci in range(len(counties)):
            if ci > 0:
                x_vals.append(0)
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
    n_ds = len(ds_shares)
    chart_height = max(400, len(counties) * (35 * n_ds + 25) + 100)
    tmpl = load_template("ao_chart.js")
    js = tmpl.substitute(div_id=chart_id, traces=", ".join(traces))
    return wrap_chart(chart_id, js, width="100%", height=chart_height)
