"""Work from Home tab renderer."""

import polars as pl

from .helpers import (
    DATASET_COLOURS,
    esc,
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
        return "<p>Need at least two datasets for WFH comparison.</p>"

    chart_html = _nway_chart(datasets)
    tables_html = render_pairs(datasets, _render_pair)
    overall_html = _overall_table(per_label, labels)

    return (
        f"{overall_html}"
        "<div style='display:grid;grid-template-columns:max-content 1fr;"
        "gap:1rem;align-items:start;margin-top:1rem;'>"
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
    obs_rows = obs.sort("county").to_dicts()
    mod_by_county: dict[str, dict] = {
        r["county_name"]: r for r in mod.sort("county").to_dicts()
    }

    header = (
        "<table class='cal-table' style='width:auto;table-layout:auto;'>"
        "<thead><tr>"
        "<th>County</th>"
        f"<th>{esc(obs_label)} Rate</th>"
        f"<th>{esc(mod_label)} Rate</th>"
        "<th>Delta (pp)</th>"
        "</tr></thead><tbody>"
    )
    body = ""
    for row in obs_rows:
        county = row["county_name"]
        mr = mod_by_county.get(county, {})
        o_rate = row.get("wfh_rate", 0) or 0
        m_rate = mr.get("wfh_rate", 0) or 0
        body += (
            f"<tr><td>{esc(str(county))}</td>"
            f"<td>{o_rate:.1%}</td><td>{m_rate:.1%}</td>"
            f"{pp_delta_cell(o_rate, m_rate)}</tr>"
        )

    # Total row
    o_total = sum(r.get("wfh", 0) or 0 for r in obs_rows)
    o_workers = sum(r.get("workers", 0) or 0 for r in obs_rows)
    m_total = sum(r.get("wfh", 0) or 0 for r in mod_by_county.values())
    m_workers = sum(r.get("workers", 0) or 0 for r in mod_by_county.values())
    o_rate = o_total / o_workers if o_workers else 0
    m_rate = m_total / m_workers if m_workers else 0
    body += (
        f"<tr style='font-weight:bold'><td>Total</td>"
        f"<td>{o_rate:.1%}</td><td>{m_rate:.1%}</td>"
        f"{pp_delta_cell(o_rate, m_rate)}</tr>"
    )

    return "<h3>WFH Rate by County</h3>" + header + body + "</tbody></table>"


def _overall_table(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    """Render a compact overall summary (FT/PT/Total) across all datasets."""
    datasets = [
        (label, per_label[label]["overall_summary"])
        for label in labels
        if "overall_summary" in per_label.get(label, {})
    ]
    if not datasets:
        return ""

    header = "<table class='cal-table' style='width:auto;margin-bottom:1rem;'><thead><tr><th>Category</th>"
    for label, _ in datasets:
        header += f"<th>{esc(label)} WFH Rate</th>"
    header += "</tr></thead><tbody>"

    # Collect all categories
    all_cats: list[str] = []
    for _, df in datasets:
        for c in df["category"].to_list():
            if c not in all_cats:
                all_cats.append(c)

    body = ""
    for cat in all_cats:
        body += f"<tr><td>{esc(cat)}</td>"
        for _, df in datasets:
            row = df.filter(pl.col("category") == cat)
            if row.height > 0:
                rate = row["wfh_rate"][0]
                body += f"<td>{rate:.1%}</td>"
            else:
                body += "<td>—</td>"
        body += "</tr>"

    return "<h3>WFH Rate Overview</h3>" + header + body + "</tbody></table>"


def _nway_chart(datasets: list[tuple[int, str, pl.DataFrame]]) -> str:
    """Grouped bar chart of WFH rate by county, one bar per dataset."""
    counties = datasets[0][2].sort("county")["county_name"].to_list()

    traces = []
    for i, (gi, label, df) in enumerate(datasets):
        rates = []
        by_county = {r["county_name"]: r for r in df.to_dicts()}
        for c in counties:
            r = by_county.get(c, {})
            rates.append(round((r.get("wfh_rate", 0) or 0) * 100, 1))
        colour = DATASET_COLOURS[gi % len(DATASET_COLOURS)]
        traces.append(
            f"{{x: {counties!r}, y: {rates}, name: '{label}', "
            f"type: 'bar', marker: {{color: '{colour}'}}}}"
        )

    data_js = ",\n".join(traces)
    layout = (
        "{barmode:'group', title:'WFH Rate by County',"
        " yaxis:{title:'WFH Rate (%)', rangemode:'tozero'},"
        " margin:{t:40,b:80}}"
    )
    return wrap_chart(data_js, layout, height=350)
