"""At-Work Subtour tab renderer — TLFD + mode shares in a compact tab."""

import json

import polars as pl

from .helpers import (
    MODE_COLOURS,
    MODE_GROUPS,
    append_overall_fit,
    compute_fit_row,
    esc,
    esc_js,
    fit_table,
    normalise_shares,
    pick_datasets,
    pp_delta_cell,
    render_pairs,
    tlfd_traces_nway,
    wrap_chart,
)


def render(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
    *,
    survey_labels: set[str] | None = None,
) -> str:
    parts: list[str] = []

    # --- TLFD section ---
    tlfd_datasets = pick_datasets(per_label, labels, "atwork_tlfd")
    if len(tlfd_datasets) >= 2:  # noqa: PLR2004
        _bins, traces = tlfd_traces_nway(tlfd_datasets, survey_labels=survey_labels)
        fit_rows: list[dict] = []
        _idx0, _lbl0, ref_df = tlfd_datasets[0]
        _rb, ref_share, _rs = normalise_shares(ref_df)
        for _idx_m, mod_label, mod_df in tlfd_datasets[1:]:
            _mb, mod_share, _ms = normalise_shares(mod_df)
            fit_rows.append(compute_fit_row(ref_share, mod_share, mod_label))

        parts.append("<h3>At-Work Subtour Trip Length Distribution</h3>")
        div_id = "atwork_tlfd_chart"
        js = (
            f"Plotly.newPlot('{div_id}', {json.dumps(traces)}, {{"
            f"title:'At-Work Subtour TLFD', "
            f"xaxis:{{title:'Distance (miles)', dtick:5}}, "
            f"yaxis:{{title:'Share', tickformat:'.1%'}}, "
            f"legend:{{orientation:'h', y:-0.15, x:0.5, xanchor:'center'}}"
            f"}});"
        )
        parts.append(wrap_chart(div_id, js))

        # Fit + avg trip length side-by-side
        avg_datasets = pick_datasets(per_label, labels, "atwork_avg_trip_length")
        parts.append(
            "<div style='display:flex;gap:24px;flex-wrap:wrap;align-items:start;'>",
        )
        if len(avg_datasets) >= 2:  # noqa: PLR2004
            parts.append("<div><h3>Average Trip Length (miles)</h3>")
            parts.append(render_pairs(avg_datasets, _render_avg_pair))
            parts.append("</div>")
        if fit_rows:
            append_overall_fit(fit_rows)
            parts.append("<div><h3>Goodness of Fit — Trip Length</h3>")
            parts.append(fit_table(fit_rows))
            parts.append("</div>")
        parts.append("</div>")

    # --- Mode share section ---
    mode_datasets = pick_datasets(per_label, labels, "atwork_mode_summary")
    if len(mode_datasets) >= 2:  # noqa: PLR2004
        parts.append("<h3>At-Work Subtour Mode Shares</h3>")
        parts.append(render_pairs(mode_datasets, _render_mode_pair))

    if not parts:
        msg = (
            "At-Work Subtours renderer called but no data found. "
            "Expected atwork_tlfd and atwork_mode_summary in results."
        )
        raise RuntimeError(msg)
    return "\n".join(parts)


def _render_avg_pair(
    obs_label: str,
    obs: pl.DataFrame,
    mod_label: str,
    mod: pl.DataFrame,
) -> str:
    obs_avg = obs["avg_trip_length"][0] if obs.height > 0 else 0.0
    mod_avg = mod["avg_trip_length"][0] if mod.height > 0 else 0.0
    delta = mod_avg - obs_avg
    pct = (delta / obs_avg * 100) if obs_avg else 0.0
    colour = "green" if abs(pct) < 5 else ("orange" if abs(pct) < 10 else "red")
    return (
        f"<table class='cal-table'><thead><tr>"
        f"<th>{esc(obs_label)}</th><th>{esc(mod_label)}</th><th>Diff</th><th>% Diff</th>"
        f"</tr></thead><tbody><tr>"
        f"<td>{obs_avg:.2f}</td><td>{mod_avg:.2f}</td>"
        f"<td>{delta:+.2f}</td>"
        f"<td style='color:{colour}'>{pct:+.1f}%</td>"
        f"</tr></tbody></table>"
    )


def _render_mode_pair(
    obs_label: str,
    obs: pl.DataFrame,
    mod_label: str,
    mod: pl.DataFrame,
) -> str:
    parts: list[str] = []

    # Group modes
    obs_g = _group_modes(obs)
    mod_g = _group_modes(mod)

    obs_total = obs_g["num_tours"].sum()
    mod_total = mod_g["num_tours"].sum()

    obs_lookup = {r["mode_group"]: r["num_tours"] for r in obs_g.to_dicts()}
    mod_lookup = {r["mode_group"]: r["num_tours"] for r in mod_g.to_dicts()}

    mode_groups = list(MODE_GROUPS)

    header = (
        "<table class='cal-table'><thead><tr>"
        "<th>Mode</th>"
        f"<th>{esc(obs_label)}</th><th>{esc(mod_label)}</th><th>Delta (pp)</th>"
        "</tr></thead><tbody>"
    )
    body = ""
    for mg in mode_groups:
        o = (obs_lookup.get(mg, 0) / obs_total) if obs_total else 0.0
        m = (mod_lookup.get(mg, 0) / mod_total) if mod_total else 0.0
        body += (
            f"<tr><td>{esc(mg)}</td>"
            f"<td>{o:.1%}</td><td>{m:.1%}</td>"
            f"{pp_delta_cell(o, m)}</tr>"
        )
    parts.append(header + body + "</tbody></table>")

    # Bar chart
    chart_id = f"atwork_mode_{obs_label}_{mod_label}".replace(" ", "_")
    x_labels = mode_groups
    obs_vals = [(obs_lookup.get(mg, 0) / obs_total) if obs_total else 0.0 for mg in mode_groups]
    mod_vals = [(mod_lookup.get(mg, 0) / mod_total) if mod_total else 0.0 for mg in mode_groups]

    colours = MODE_COLOURS
    traces = [
        f"{{name:'{esc_js(obs_label)}', x:{json.dumps(x_labels)}, y:{obs_vals!r}, "
        f"type:'bar', marker:{{color:'{colours[0]}'}}}}" ,
        f"{{name:'{esc_js(mod_label)}', x:{json.dumps(x_labels)}, y:{mod_vals!r}, "
        f"type:'bar', marker:{{color:'{colours[1]}'}}}}" ,
    ]
    js = (
        f"Plotly.newPlot('{chart_id}', [{', '.join(traces)}], {{"
        f"barmode:'group', "
        f"title:'At-Work Subtour Mode Shares', "
        f"yaxis:{{tickformat:'.0%', title:'Share'}}, "
        f"legend:{{orientation:'h', y:-0.15, x:0.5, xanchor:'center'}}"
        f"}});"
    )
    parts.append(wrap_chart(chart_id, js, height=350))

    return "\n".join(parts)


def _group_modes(df: pl.DataFrame) -> pl.DataFrame:
    mode_map: dict[int, str] = {}
    for group_name, modes in MODE_GROUPS.items():
        for m in modes:
            mode_map[m] = group_name
    return (
        df.with_columns(
            pl.col("tour_mode")
            .replace_strict(mode_map, default="Other")
            .alias("mode_group"),
        )
        .group_by("mode_group")
        .agg(pl.col("num_tours").sum())
        .sort("mode_group")
    )
