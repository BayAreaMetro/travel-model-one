"""Tour Mode Choice tab renderer."""

import polars as pl

from .helpers import (
    MODE_COLOURS,
    MODE_GROUPS,
    compute_fit_row,
    esc,
    esc_js,
    fit_table,
    pick_pair,
    wrap_chart,
)


def render(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    """Return HTML fragment for the Tour Mode Choice tab."""
    pair = pick_pair(per_label, labels, "tour_mode_summary")
    if not pair:
        return "<p>Insufficient data for comparison.</p>"

    obs_label, obs, mod_label, mod = pair
    parts: list[str] = []

    parts.append("<h3>Tour Mode Shares by Purpose</h3>")
    parts.append(_mode_share_table(obs, mod, obs_label, mod_label))
    parts.append("<h3>Goodness of Fit</h3>")
    parts.append(_fit_section(obs, mod))
    parts.append("<h3>Mode Share Chart</h3>")
    parts.append(_mode_chart(obs, mod, obs_label, mod_label))

    return "\n".join(parts)


def _group_modes(df: pl.DataFrame) -> pl.DataFrame:
    """Aggregate tour_mode into simplified mode groups."""
    # Build mode → group mapping
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


def _mode_share_table(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
) -> str:
    obs_g = _group_modes(obs)
    mod_g = _group_modes(mod)

    purposes = sorted(
        set(obs_g["simple_purpose"].unique().to_list())
        & set(mod_g["simple_purpose"].unique().to_list()),
    )
    mode_groups = list(MODE_GROUPS)

    # Compute shares within each purpose
    obs_totals = obs_g.group_by("simple_purpose").agg(pl.col("num_tours").sum().alias("total"))
    mod_totals = mod_g.group_by("simple_purpose").agg(pl.col("num_tours").sum().alias("total"))
    obs_g = obs_g.join(obs_totals, on="simple_purpose").with_columns(
        (pl.col("num_tours") / pl.col("total")).alias("share"),
    )
    mod_g = mod_g.join(mod_totals, on="simple_purpose").with_columns(
        (pl.col("num_tours") / pl.col("total")).alias("share"),
    )

    obs_lookup = {
        (r["simple_purpose"], r["mode_group"]): r["share"]
        for r in obs_g.to_dicts()
    }
    mod_lookup = {
        (r["simple_purpose"], r["mode_group"]): r["share"]
        for r in mod_g.to_dicts()
    }

    # Long format: one row per purpose × mode
    header = (
        "<table class='cal-table'><thead><tr>"
        "<th>Purpose</th><th>Mode</th>"
        f"<th>{esc(obs_label)}</th><th>{esc(mod_label)}</th><th>Delta</th>"
        "</tr></thead><tbody>"
    )
    body = ""
    for p in purposes:
        first = True
        for mg in mode_groups:
            o = obs_lookup.get((p, mg), 0.0)
            m = mod_lookup.get((p, mg), 0.0)
            d = m - o
            d_color = "red" if abs(d) > 0.05 else "inherit"
            p_cell = f"<td rowspan='{len(mode_groups)}'>{esc(p)}</td>" if first else ""
            body += (
                f"<tr>{p_cell}<td>{esc(mg)}</td>"
                f"<td>{o:.1%}</td><td>{m:.1%}</td>"
                f"<td style='color:{d_color}'>{d:+.1%}</td></tr>"
            )
            first = False

    return header + body + "</tbody></table>"


def _fit_section(obs: pl.DataFrame, mod: pl.DataFrame) -> str:
    obs_g = _group_modes(obs)
    mod_g = _group_modes(mod)

    purposes = sorted(
        set(obs_g["simple_purpose"].unique().to_list())
        & set(mod_g["simple_purpose"].unique().to_list()),
    )
    mode_groups = list(MODE_GROUPS)

    obs_totals = obs_g.group_by("simple_purpose").agg(pl.col("num_tours").sum().alias("total"))
    mod_totals = mod_g.group_by("simple_purpose").agg(pl.col("num_tours").sum().alias("total"))
    obs_g = obs_g.join(obs_totals, on="simple_purpose").with_columns(
        (pl.col("num_tours") / pl.col("total")).alias("share"),
    )
    mod_g = mod_g.join(mod_totals, on="simple_purpose").with_columns(
        (pl.col("num_tours") / pl.col("total")).alias("share"),
    )

    obs_lookup = {
        (r["simple_purpose"], r["mode_group"]): r["share"]
        for r in obs_g.to_dicts()
    }
    mod_lookup = {
        (r["simple_purpose"], r["mode_group"]): r["share"]
        for r in mod_g.to_dicts()
    }

    rows: list[dict] = []
    for p in purposes:
        obs_shares = [obs_lookup.get((p, mg), 0.0) for mg in mode_groups]
        mod_shares = [mod_lookup.get((p, mg), 0.0) for mg in mode_groups]
        rows.append(compute_fit_row(obs_shares, mod_shares, p, label_key="Purpose"))

    if rows:
        n = len(rows)
        rows.append({
            "Purpose": "Overall",
            "rmse": sum(r["rmse"] for r in rows) / n,
            "dissim": sum(r["dissim"] for r in rows) / n,
            "hellinger": sum(r["hellinger"] for r in rows) / n,
            "_bold": True,
        })

    return fit_table(rows, label_key="Purpose")


def _mode_chart(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
) -> str:
    """Stacked bar chart: one bar per purpose×dataset, segments are mode groups."""
    obs_g = _group_modes(obs)
    mod_g = _group_modes(mod)

    purposes = sorted(
        set(obs_g["simple_purpose"].unique().to_list())
        & set(mod_g["simple_purpose"].unique().to_list()),
    )
    mode_groups = list(MODE_GROUPS)

    # Total per purpose for shares
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

    # Y-axis: paired labels with spacer between purpose groups
    y_labels: list[str] = []
    spacer_idx = 0
    for p in reversed(purposes):
        if y_labels:
            spacer_idx += 1
            y_labels.append(" " * spacer_idx)  # unique invisible spacer
        y_labels.append(f"{p} ({mod_label})")
        y_labels.append(f"{p} ({obs_label})")

    traces: list[str] = []
    for i, mg in enumerate(mode_groups):
        colour = MODE_COLOURS[i % len(MODE_COLOURS)]
        x_vals: list[float] = []
        first = True
        for p in reversed(purposes):
            if not first:
                x_vals.append(0)  # spacer
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
        f"Plotly.newPlot('tmc_chart', [{', '.join(traces)}], {{"
        f"barmode:'stack', "
        f"title:'Tour Mode Shares by Purpose', "
        f"xaxis:{{tickformat:'.0%', title:'Share', range:[0,1]}}, "
        f"yaxis:{{automargin:true}}, "
        f"legend:{{orientation:'h', y:-0.12, x:0.5, xanchor:'center'}}, "
        f"margin:{{l:180, t:40, b:60}}"
        f"}});"
    )
    return wrap_chart("tmc_chart", js, width=1000, height=height)
