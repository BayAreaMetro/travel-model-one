"""Tour Mode Choice tab renderer."""

import polars as pl

from .helpers import (
    MODE_COLOURS,
    MODE_GROUPS,
    append_overall_fit,
    compute_fit_row,
    esc,
    esc_js,
    fit_table,
    pick_datasets,
    pp_delta_cell,
    render_pairs,
    wrap_chart,
)


def render(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    datasets = pick_datasets(per_label, labels, "tour_mode_summary")
    if len(datasets) < 2:  # noqa: PLR2004
        return "<p>Insufficient data for comparison.</p>"
    return render_pairs(datasets, _render_pair)


def _render_pair(
    obs_label: str,
    obs: pl.DataFrame,
    mod_label: str,
    mod: pl.DataFrame,
) -> str:
    chart_id = f"tmc_{obs_label}_{mod_label}".replace(" ", "_")
    parts: list[str] = [
        "<h3>Tour Mode Shares by Purpose</h3>",
        _mode_share_table(obs, mod, obs_label, mod_label),
        "<h3>Goodness of Fit</h3>",
        _fit_section(obs, mod),
        "<h3>Mode Share Chart</h3>",
        _mode_chart(obs, mod, obs_label, mod_label, chart_id),
    ]
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
        .group_by("simple_purpose", "mode_group")
        .agg(pl.col("num_tours").sum())
        .sort("simple_purpose", "mode_group")
    )


def _compute_shares(df: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    g = _group_modes(df)
    totals = g.group_by("simple_purpose").agg(pl.col("num_tours").sum().alias("total"))
    g = g.join(totals, on="simple_purpose").with_columns(
        (pl.col("num_tours") / pl.col("total")).alias("share"),
    )
    lookup = {
        (r["simple_purpose"], r["mode_group"]): r["share"]
        for r in g.to_dicts()
    }
    return g, lookup


def _mode_share_table(obs: pl.DataFrame, mod: pl.DataFrame, obs_label: str, mod_label: str) -> str:
    _obs_g, obs_lookup = _compute_shares(obs)
    _mod_g, mod_lookup = _compute_shares(mod)

    purposes = sorted(
        set(k[0] for k in obs_lookup) & set(k[0] for k in mod_lookup),
    )
    mode_groups = list(MODE_GROUPS)

    header = (
        "<table class='cal-table'><thead><tr>"
        "<th>Purpose</th><th>Mode</th>"
        f"<th>{esc(obs_label)}</th><th>{esc(mod_label)}</th><th>Delta (pp)</th>"
        "</tr></thead><tbody>"
    )
    body = ""
    for p in purposes:
        first = True
        for mg in mode_groups:
            o = obs_lookup.get((p, mg), 0.0)
            m = mod_lookup.get((p, mg), 0.0)
            p_cell = f"<td rowspan='{len(mode_groups)}'>{esc(p)}</td>" if first else ""
            body += (
                f"<tr>{p_cell}<td>{esc(mg)}</td>"
                f"<td>{o:.1%}</td><td>{m:.1%}</td>"
                f"{pp_delta_cell(o, m)}</tr>"
            )
            first = False

    return header + body + "</tbody></table>"


def _fit_section(obs: pl.DataFrame, mod: pl.DataFrame) -> str:
    _obs_g, obs_lookup = _compute_shares(obs)
    _mod_g, mod_lookup = _compute_shares(mod)

    purposes = sorted(
        set(k[0] for k in obs_lookup) & set(k[0] for k in mod_lookup),
    )
    mode_groups = list(MODE_GROUPS)

    fit_rows: list[dict] = []
    for p in purposes:
        obs_shares = [obs_lookup.get((p, mg), 0.0) for mg in mode_groups]
        mod_shares = [mod_lookup.get((p, mg), 0.0) for mg in mode_groups]
        fit_rows.append(compute_fit_row(obs_shares, mod_shares, p))

    append_overall_fit(fit_rows)
    return fit_table(fit_rows)


def _mode_chart(
    obs: pl.DataFrame, mod: pl.DataFrame,
    obs_label: str, mod_label: str, chart_id: str,
) -> str:
    obs_g = _group_modes(obs)
    mod_g = _group_modes(mod)

    purposes = sorted(
        set(obs_g["simple_purpose"].unique().to_list())
        & set(mod_g["simple_purpose"].unique().to_list()),
    )
    mode_groups = list(MODE_GROUPS)

    obs_totals = {
        r["simple_purpose"]: r["total"]
        for r in obs_g.group_by("simple_purpose")
        .agg(pl.col("num_tours").sum().alias("total"))
        .to_dicts()
    }
    mod_totals = {
        r["simple_purpose"]: r["total"]
        for r in mod_g.group_by("simple_purpose")
        .agg(pl.col("num_tours").sum().alias("total"))
        .to_dicts()
    }
    obs_lookup = {
        (r["simple_purpose"], r["mode_group"]): r["num_tours"]
        for r in obs_g.to_dicts()
    }
    mod_lookup = {
        (r["simple_purpose"], r["mode_group"]): r["num_tours"]
        for r in mod_g.to_dicts()
    }

    y_labels: list[str] = []
    spacer_idx = 0
    for p in reversed(purposes):
        if y_labels:
            spacer_idx += 1
            y_labels.append(" " * spacer_idx)
        y_labels.append(f"{p} ({mod_label})")
        y_labels.append(f"{p} ({obs_label})")

    traces: list[str] = []
    for i, mg in enumerate(mode_groups):
        colour = MODE_COLOURS[i % len(MODE_COLOURS)]
        x_vals: list[float] = []
        first = True
        for p in reversed(purposes):
            if not first:
                x_vals.append(0)
            first = False
            mod_share = mod_lookup.get((p, mg), 0) / (mod_totals.get(p) or 1)
            obs_share = obs_lookup.get((p, mg), 0) / (obs_totals.get(p) or 1)
            x_vals.append(mod_share)
            x_vals.append(obs_share)
        traces.append(
            f"{{name:'{esc_js(mg)}', "
            f"y:{y_labels!r}, x:{x_vals!r}, type:'bar', orientation:'h', "
            f"marker:{{color:'{colour}'}}}}",
        )

    height = max(400, len(purposes) * 100)
    js = (
        f"Plotly.newPlot('{chart_id}', [{', '.join(traces)}], {{"
        f"barmode:'stack', "
        f"title:'Tour Mode Shares by Purpose', "
        f"xaxis:{{tickformat:'.0%', title:'Share', range:[0,1]}}, "
        f"yaxis:{{automargin:true}}, "
        f"legend:{{orientation:'h', y:-0.12, x:0.5, xanchor:'center'}}, "
        f"margin:{{l:180, t:40, b:60}}"
        f"}});"
    )
    return wrap_chart(chart_id, js, width=1000, height=height)
