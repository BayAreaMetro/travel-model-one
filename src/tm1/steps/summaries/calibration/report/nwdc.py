"""Non-work Destination Choice tab renderer."""

import json

import polars as pl

from .helpers import (
    append_overall_fit,
    compute_fit_row,
    esc,
    fit_table,
    load_template,
    pick_pair,
    tlfd_shares,
    tlfd_trace_dicts,
)


def render(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    """Return HTML fragment for the Non-work Destination Choice tab."""
    parts: list[str] = []

    # TLFD grid — compute first so we have fit_rows for the tables row
    purposes = [
        ("nwdc_tlfd_escort", "Escort"),
        ("nwdc_tlfd_shopping", "Shopping"),
        ("nwdc_tlfd_maintenance", "Maintenance"),
        ("nwdc_tlfd_eating_out", "Eating Out"),
        ("nwdc_tlfd_visiting", "Visiting"),
        ("nwdc_tlfd_discretionary", "Discretionary"),
        ("nwdc_tlfd_atwork", "At-Work"),
    ]

    fit_rows: list[dict] = []
    grid_items: list[dict] = []

    for tlfd_key, purpose_title in purposes:
        pair = pick_pair(per_label, labels, tlfd_key)
        if not pair:
            continue
        item = _build_grid_item(pair[1], pair[3], pair[0], pair[2], tlfd_key, purpose_title)
        grid_items.append(item)
        fit_rows.extend(_compute_tlfd_fit(pair[1], pair[3], purpose_title))

    # Tables row: avg trip lengths + GOF side by side
    avg_pair = pick_pair(per_label, labels, "nwdc_avg_trip_lengths")
    has_tables = avg_pair or fit_rows
    if has_tables:
        parts.append(
            "<div style='display:flex;gap:24px;flex-wrap:wrap;align-items:start;'>"
        )
    if avg_pair:
        parts.append("<div><h3>Average Trip Lengths (miles)</h3>")
        parts.append(_avg_trip_table(avg_pair[1], avg_pair[3], avg_pair[0], avg_pair[2]))
        parts.append("</div>")
    if fit_rows:
        append_overall_fit(fit_rows)
        parts.append("<div><h3>Goodness of Fit — Trip Length</h3>")
        parts.append(fit_table(fit_rows, label_key="Purpose"))
        parts.append("</div>")
    if has_tables:
        parts.append("</div>")

    # Plot grid below the tables
    if grid_items:
        parts.append(_render_grid(grid_items))

    return "\n".join(parts) if parts else "<p>Insufficient data for comparison.</p>"


def _build_grid_item(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
    key: str,
    title: str,
) -> dict:
    """Build a single plot spec for the grid."""
    bins, obs_share, mod_share, mod_smooth = tlfd_shares(obs, mod)
    traces = tlfd_trace_dicts(bins, obs_share, mod_share, mod_smooth, obs_label, mod_label)
    return {"div_id": f"nwdc_{key}", "title": title, "traces": traces}


def _render_grid(items: list[dict]) -> str:
    """Render a 2-column CSS grid of TLFD charts."""
    grid_html = (
        "<div style='display:grid;grid-template-columns:1fr 1fr;"
        "gap:8px;margin:12px 0;'>\n"
    )
    for item in items:
        grid_html += (
            f"  <div id='{item['div_id']}' "
            f"style='width:100%;height:320px;position:relative;'></div>\n"
        )
    grid_html += "</div>\n"

    # Single script block drives all plots
    tmpl = load_template("nwdc_grid.js")
    purposes_json = json.dumps(items)
    js = tmpl.substitute(purposes=purposes_json)
    grid_html += f"<script>\n{js}\n</script>"
    return grid_html


def _compute_tlfd_fit(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    label: str,
) -> list[dict]:
    _bins, obs_share, mod_share, _smooth = tlfd_shares(obs, mod)
    return [compute_fit_row(obs_share, mod_share, label, label_key="Purpose")]


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
