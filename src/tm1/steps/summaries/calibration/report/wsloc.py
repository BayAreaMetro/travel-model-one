"""Work / School Location tab renderer."""

import json

import polars as pl

from .helpers import (
    DATASET_COLOURS,
    append_overall_fit,
    compute_fit_row,
    esc,
    fit_table,
    normalise_shares,
    pct_change_cell,
    pick_datasets,
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

    # Average trip lengths table — pair-toggled
    avg_datasets = pick_datasets(per_label, labels, "avg_trip_lengths")
    if len(avg_datasets) >= 2:  # noqa: PLR2004
        parts.append("<h3>Average Trip Lengths (miles)</h3>")
        parts.append(render_pairs(avg_datasets, _render_avg_pair))

    # Fit metrics across all datasets
    fit_rows: list[dict] = []
    trip_purposes = [
        ("trip_tlfd_work", "Work"),
        ("trip_tlfd_univ", "University"),
        ("trip_tlfd_school", "School"),
    ]
    for trip_key, trip_title in trip_purposes:
        ds = pick_datasets(per_label, labels, trip_key)
        if len(ds) < 2:  # noqa: PLR2004
            continue
        _idx0, _lbl0, ref_df = ds[0]
        _rb, ref_share, _rs = normalise_shares(ref_df)
        for _idx_m, mod_label, mod_df in ds[1:]:
            _mb, mod_share, _ms = normalise_shares(mod_df)
            row_label = (
                trip_title if len(ds) == 2  # noqa: PLR2004
                else f"{trip_title} ({mod_label})"
            )
            fit_rows.append(compute_fit_row(ref_share, mod_share, row_label))

    if fit_rows:
        append_overall_fit(fit_rows)
        parts.append("<h3>Goodness of Fit — Trip Length</h3>")
        parts.append(fit_table(fit_rows))

    # TLFD plots — all datasets overlaid, in a compact grid
    tlfd_items: list[tuple[str, str, list]] = []
    for trip_key, trip_title in trip_purposes:
        ds = pick_datasets(per_label, labels, trip_key)
        if len(ds) < 2:  # noqa: PLR2004
            continue
        tlfd_items.append((trip_key, trip_title, ds))

    if tlfd_items:
        parts.append("<h3>Trip Length Frequency Distribution</h3>")
        parts.append(
            "<button id='tlfd_log_toggle' style='margin:4px 0;padding:3px 8px;"
            "font-size:11px;cursor:pointer;' onclick=\""
            "var ids=[" + ",".join(
                f"'tlfd_{k}'" for k, _, _ in tlfd_items
            ) + "];"
            "var btn=this;var cur=(btn.textContent==='Log Scale')?'log':'linear';"
            "var fmt=(cur==='log')?'.1e':'.1%';"
            "ids.forEach(function(id){Plotly.relayout(id,{'yaxis.type':cur,'yaxis.tickformat':fmt});});"
            "btn.textContent=(cur==='log')?'Linear Scale':'Log Scale';"
            "\">Log Scale</button>"
        )
        parts.append(_tlfd_grid(tlfd_items, survey_labels=survey_labels))
        parts.append(
            "<p class='note'>* School comparisons exclude preschool-age "
            "children (ActivitySim ptype 8). ActivitySim assigns school "
            "locations to these children, but CTRAMP labels them "
            "&ldquo;Not student&rdquo; so they are omitted for "
            "apples-to-apples comparison.</p>"
        )
        parts.append(
            "<p class='note'>* School/university zone assignment variance "
            "is magnified by small sample rates. At 15% sampling, ~62% of "
            "persons receive different zone draws between models due to "
            "Monte Carlo randomness. This variance will shrink "
            "substantially with larger sample rates.</p>"
        )

    # Per-county violin + CDF plots
    dist_keys = [
        ("dist_samples_work", "Work"),
        ("dist_samples_school", "School"),
    ]
    for dist_key, dist_title in dist_keys:
        ds = pick_datasets(per_label, labels, dist_key)
        if len(ds) < 2:  # noqa: PLR2004
            continue
        parts.append(f"<h3>Distance Distribution by County — {dist_title}</h3>")
        parts.append(_violin_chart(ds, dist_key))
        parts.append(f"<h3>Distance CDF by County — {dist_title}</h3>")
        parts.append(_cdf_grid(ds, dist_key))

    return "\n".join(parts) if parts else "<p>Insufficient data for comparison.</p>"


def _render_avg_pair(
    obs_label: str,
    obs: pl.DataFrame,
    mod_label: str,
    mod: pl.DataFrame,
) -> str:
    return _avg_trip_table(obs, mod, obs_label, mod_label)


def _tlfd_grid(
    items: list[tuple[str, str, list]],
    *,
    survey_labels: set[str] | None = None,
) -> str:
    """Render TLFD charts in a 2-column grid."""
    parts = ["<div style='display:grid;grid-template-columns:repeat(2,1fr);gap:8px;max-width:100%;'>"]
    for trip_key, trip_title, ds in items:
        _bins, traces = tlfd_traces_nway(ds, survey_labels=survey_labels)
        div_id = f"tlfd_{trip_key}"
        layout = {
            "title": {"text": trip_title, "font": {"size": 13}},
            "xaxis": {"title": "Distance (mi)"},
            "yaxis": {"title": "Share", "tickformat": ".1%"},
            "legend": {"orientation": "h", "y": -0.3, "x": 0.5, "xanchor": "center"},
            "margin": {"l": 45, "r": 10, "t": 30, "b": 55},
            "height": 320,
        }
        js = f"Plotly.newPlot('{div_id}', {json.dumps(traces)}, {json.dumps(layout)}, {{responsive:true}});"
        parts.append(
            f"<div style='min-width:0;overflow:hidden;'>"
            f"<div id='{div_id}' style='width:100%;height:320px;'></div>"
            f"<script>{js}</script>"
            f"</div>"
        )
    parts.append("</div>")
    return "\n".join(parts)


def _avg_trip_table(
    obs: pl.DataFrame, mod: pl.DataFrame,
    obs_label: str, mod_label: str,
) -> str:
    trip_cols = [c for c in obs.columns if c != "county"]
    obs_rows = obs.sort("county").to_dicts()
    mod_by_c: dict[str, dict] = {
        r["county"]: r for r in mod.sort("county").to_dicts()
    }

    ncols = len(trip_cols)
    header = "<table class='cal-table'><thead><tr>"
    header += "<th rowspan='2'>County</th>"
    header += f"<th colspan='{ncols}'>{esc(obs_label)}</th>"
    header += f"<th colspan='{ncols}'>{esc(mod_label)}</th>"
    header += f"<th colspan='{ncols}'>% Change</th>"
    header += "</tr><tr>"
    for _ in range(3):
        for tc in trip_cols:
            header += f"<th>{esc(tc)}</th>"
    header += "</tr></thead><tbody>"

    body = ""
    for row in obs_rows:
        county = row["county"]
        mr = mod_by_c.get(county, {})
        body += f"<tr><td>{esc(str(county))}</td>"
        for tc in trip_cols:
            val = row.get(tc)
            body += f"<td>{val:.1f}</td>" if val is not None else "<td>—</td>"
        for tc in trip_cols:
            val = mr.get(tc)
            body += f"<td>{val:.1f}</td>" if val is not None else "<td>—</td>"
        for tc in trip_cols:
            obs_val = row.get(tc, 0) or 0
            mod_val = mr.get(tc, 0) or 0
            body += pct_change_cell(obs_val, mod_val)
        body += "</tr>"

    return header + body + "</tbody></table>"


# ---------------------------------------------------------------------------
# Violin chart (per-county, side-by-side datasets)
# ---------------------------------------------------------------------------

def _violin_chart(
    datasets: list[tuple[int, str, pl.DataFrame]],
    key: str,
) -> str:
    """Plotly violin plot: one violin per county, side-by-side per dataset."""
    traces: list[dict] = []
    for i, (_idx, label, df) in enumerate(datasets):
        colour = DATASET_COLOURS[i % len(DATASET_COLOURS)]
        for county in df["county"].unique().sort().to_list():
            vals = df.filter(pl.col("county") == county)["dist"].to_list()
            traces.append({
                "type": "violin",
                "y": vals,
                "x0": county,
                "name": label,
                "legendgroup": label,
                "scalegroup": county,
                "showlegend": county == df["county"].unique().sort().to_list()[0],
                "side": "negative" if i == 0 else "positive",
                "line": {"color": colour},
                "meanline": {"visible": True},
                "spanmode": "hard",
            })

    div_id = f"violin_{key}"
    layout = {
        "title": "",
        "violingap": 0,
        "violingroupgap": 0.05,
        "violinmode": "overlay",
        "yaxis": {"title": "Distance (miles)", "rangemode": "nonnegative"},
        "xaxis": {"title": "Home County"},
        "legend": {"orientation": "h", "y": -0.15, "x": 0.5, "xanchor": "center"},
        "margin": {"b": 80, "t": 40},
        "updatemenus": [{
            "type": "buttons",
            "direction": "left",
            "x": 0.01,
            "y": 1.08,
            "buttons": [
                {"label": "Linear", "method": "relayout", "args": [{"yaxis.type": "linear"}]},
                {"label": "Log", "method": "relayout", "args": [{"yaxis.type": "log"}]},
            ],
        }],
    }
    js = (
        f"Plotly.newPlot('{div_id}', {json.dumps(traces)}, {json.dumps(layout)});"
    )
    return wrap_chart(div_id, js, width="100%", height=500)


# ---------------------------------------------------------------------------
# CDF grid (per-county, overlaid datasets)
# ---------------------------------------------------------------------------

def _cdf_grid(
    datasets: list[tuple[int, str, pl.DataFrame]],
    key: str,
) -> str:
    """3-column grid of per-county CDF plots + one 'All' CDF."""
    # Collect all counties across datasets
    all_counties: list[str] = []
    for _idx, _label, df in datasets:
        all_counties.extend(df["county"].unique().to_list())
    counties = sorted(set(all_counties))

    items: list[dict] = []
    for county in [*counties, "All"]:
        div_id = f"cdf_{key}_{county.replace(' ', '_')}"
        traces: list[dict] = []
        for i, (_idx, label, df) in enumerate(datasets):
            if county == "All":
                vals = sorted(df["dist"].to_list())
            else:
                vals = sorted(
                    df.filter(pl.col("county") == county)["dist"].to_list()
                )
            if not vals:
                continue
            n = len(vals)
            cdf = [j / n for j in range(1, n + 1)]
            colour = DATASET_COLOURS[i % len(DATASET_COLOURS)]
            traces.append({
                "type": "scatter",
                "mode": "lines",
                "x": vals,
                "y": cdf,
                "name": label,
                "line": {"color": colour, "width": 2},
                "showlegend": county == (counties[0] if counties else "All"),
            })
        items.append({"div_id": div_id, "title": county, "traces": traces})

    # Render as a 2-column grid
    parts = ["<div style='display:grid;grid-template-columns:repeat(2,1fr);gap:8px;max-width:100%;'>"]
    for item in items:
        did = item["div_id"]
        parts.append(
            f"<div style='min-width:0;overflow:hidden;'>"
            f"<div id='{did}' style='width:100%;height:320px;'></div>"
            f"<script>Plotly.newPlot('{did}', {json.dumps(item['traces'])}, {{"
            f"title:{{text:'{esc(item['title'])}',font:{{size:13}}}},"
            f"xaxis:{{title:'Distance (mi)',range:[0,80]}}, "
            f"yaxis:{{title:'CDF',range:[0,1],tickformat:'.0%'}}, "
            f"legend:{{orientation:'h',y:-0.3,x:0.5,xanchor:'center'}}, "
            f"margin:{{l:45,r:10,t:30,b:55}},"
            f"height:320"
            f"}}, {{responsive:true}});</script>"
            f"</div>"
        )
    parts.append("</div>")
    return "\n".join(parts)
