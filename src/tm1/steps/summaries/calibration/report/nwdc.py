"""Non-work Destination Choice tab renderer."""

import json

import polars as pl

from .helpers import (
    append_overall_fit,
    compute_fit_row,
    esc,
    fit_table,
    load_template,
    normalise_shares,
    pair_selector,
    pick_datasets,
    tlfd_traces_nway,
)


def render(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    """Return HTML fragment for the Non-work Destination Choice tab."""
    parts: list[str] = []

    purposes = [
        ("nwdc_tlfd_escort", "Escort"),
        ("nwdc_tlfd_shopping", "Shopping"),
        ("nwdc_tlfd_maintenance", "Maintenance"),
        ("nwdc_tlfd_eating_out", "Eating Out"),
        ("nwdc_tlfd_visiting", "Visiting"),
        ("nwdc_tlfd_discretionary", "Discretionary"),
        ("nwdc_tlfd_atwork", "At-Work"),
    ]

    # --- TLFD grid: overlay all datasets on each purpose chart ---
    fit_rows: list[dict] = []
    grid_items: list[dict] = []

    for tlfd_key, purpose_title in purposes:
        datasets = pick_datasets(per_label, labels, tlfd_key)
        if len(datasets) < 2:  # noqa: PLR2004
            continue
        _bins, traces = tlfd_traces_nway(datasets)
        grid_items.append({
            "div_id": f"nwdc_{tlfd_key}",
            "title": purpose_title,
            "traces": traces,
        })
        # Fit metrics: one row per (ref, model_i) pair
        ref_label, ref_df = datasets[0]
        _rb, ref_share, _rs = normalise_shares(ref_df)
        for mod_label, mod_df in datasets[1:]:
            _mb, mod_share, _ms = normalise_shares(mod_df)
            row_label = (
                purpose_title if len(datasets) == 2  # noqa: PLR2004
                else f"{purpose_title} ({mod_label})"
            )
            fit_rows.append(
                compute_fit_row(ref_share, mod_share, row_label, label_key="Purpose"),
            )

    # --- Average trip lengths table: pair-toggled ---
    avg_datasets = pick_datasets(per_label, labels, "nwdc_avg_trip_lengths")
    has_tables = len(avg_datasets) >= 2 or fit_rows  # noqa: PLR2004
    if has_tables:
        parts.append(
            "<div style='display:flex;gap:24px;flex-wrap:wrap;align-items:start;'>",
        )
    if len(avg_datasets) >= 2:  # noqa: PLR2004
        parts.append("<div><h3>Average Trip Lengths (miles)</h3>")
        parts.append(pair_selector(avg_datasets, "nwdc_avg", _render_avg_pair))
        parts.append("</div>")
    if fit_rows:
        append_overall_fit(fit_rows)
        parts.append("<div><h3>Goodness of Fit — Trip Length</h3>")
        parts.append(fit_table(fit_rows, label_key="Purpose"))
        parts.append("</div>")
    if has_tables:
        parts.append("</div>")

    if grid_items:
        parts.append(_render_grid(grid_items))

    return "\n".join(parts) if parts else "<p>Insufficient data for comparison.</p>"


def _render_avg_pair(
    obs_label: str,
    obs: pl.DataFrame,
    mod_label: str,
    mod: pl.DataFrame,
) -> str:
    return _avg_trip_table(obs, mod, obs_label, mod_label)


def _render_grid(items: list[dict]) -> str:
    """Render a 2-column CSS grid of TLFD charts."""
    grid_html = (
        "<div style='display:grid;grid-template-columns:1fr 1fr;"
        "gap:8px;margin:12px 0;'>\n"
    )
    for item in items:
        grid_html += (
            f"  <div class='tlfd-cell'>\n"
            f"    <div id='{item['div_id']}' "
            f"style='width:100%;height:320px;'></div>\n"
            f"  </div>\n"
        )
    grid_html += "</div>\n"

    # Single script block drives all plots
    tmpl = load_template("nwdc_grid.js")
    purposes_json = json.dumps(items)
    js = tmpl.substitute(purposes=purposes_json)
    grid_html += f"<script>\n{js}\n</script>"
    return grid_html


def _avg_trip_table(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
) -> str:
    obs_rows = {r["purpose"]: r["avg_trip_length"] for r in obs.to_dicts()}
    mod_rows = {r["purpose"]: r["avg_trip_length"] for r in mod.to_dicts()}
    all_purposes = list(dict.fromkeys(list(obs_rows) + list(mod_rows)))

    header = (
        "<table class='cal-table'><thead><tr>"
        f"<th>Purpose</th><th>{esc(obs_label)}</th>"
        f"<th>{esc(mod_label)}</th><th>Delta</th>"
        "</tr></thead><tbody>"
    )
    body = ""
    for p in all_purposes:
        o = obs_rows.get(p)
        m = mod_rows.get(p)
        o_str = f"{o:.2f}" if o is not None else "—"
        m_str = f"{m:.2f}" if m is not None else "—"
        if o is not None and m is not None:
            d = m - o
            d_str = f"<td style='color:{'red' if abs(d)>2 else 'inherit'}'>{d:+.2f}</td>"
        else:
            d_str = "<td>—</td>"
        body += f"<tr><td>{esc(p)}</td><td>{o_str}</td><td>{m_str}</td>{d_str}</tr>"

    return header + body + "</tbody></table>"
