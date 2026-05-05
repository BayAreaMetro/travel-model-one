"""Work / School Location tab renderer."""

import json

import polars as pl

from .helpers import (
    append_overall_fit,
    compute_fit_row,
    esc,
    fit_table,
    load_template,
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

    # TLFD plots — all datasets overlaid (not pair-toggled)
    for trip_key, trip_title in trip_purposes:
        ds = pick_datasets(per_label, labels, trip_key)
        if len(ds) < 2:  # noqa: PLR2004
            continue
        parts.append(f"<h3>Trip Length Frequency Distribution — {trip_title}</h3>")
        parts.append(_tlfd_chart(ds, trip_key, survey_labels=survey_labels))

    return "\n".join(parts) if parts else "<p>Insufficient data for comparison.</p>"


def _render_avg_pair(
    obs_label: str,
    obs: pl.DataFrame,
    mod_label: str,
    mod: pl.DataFrame,
) -> str:
    return _avg_trip_table(obs, mod, obs_label, mod_label)


def _tlfd_chart(
    datasets: list[tuple[int, str, pl.DataFrame]],
    key: str,
    *,
    survey_labels: set[str] | None = None,
) -> str:
    _bins, traces = tlfd_traces_nway(datasets, survey_labels=survey_labels)
    div_id = f"tlfd_{key}"
    trip_title = key.replace("trip_tlfd_", "").title()
    tmpl = load_template("tlfd_chart.js")
    js = tmpl.substitute(div_id=div_id, traces_json=json.dumps(traces), trip_title=trip_title)
    return wrap_chart(div_id, js)


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
