"""Work / School Location tab renderer."""

import polars as pl

from .helpers import (
    compute_fit_row,
    delta_cell,
    esc,
    esc_js,
    fit_table,
    gaussian_smooth,
    load_template,
    pick_pair,
    wrap_chart,
)


def render(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    """Return HTML fragment for the Work / School Location tab."""
    parts: list[str] = []

    # Average trip lengths table FIRST
    pair = pick_pair(per_label, labels, "avg_trip_lengths")
    if pair:
        parts.append("<h3>Average Trip Lengths (miles)</h3>")
        parts.append(_avg_trip_table(pair[1], pair[3], pair[0], pair[2]))
        parts.append("<h3>Goodness of Fit — Trip Length</h3>")
        parts.append(_tlfd_fit_table(per_label, labels))

    # TLFD plots AFTER table
    for trip_key, trip_title in [
        ("trip_tlfd_work", "Work"),
        ("trip_tlfd_univ", "University"),
        ("trip_tlfd_school", "School"),
    ]:
        pair = pick_pair(per_label, labels, trip_key)
        if pair:
            parts.append(
                f"<h3>Trip Length Frequency Distribution — {trip_title}</h3>",
            )
            parts.append(
                _tlfd_chart(pair[1], pair[3], pair[0], pair[2], trip_key),
            )

    return "\n".join(parts) if parts else "<p>Insufficient data for comparison.</p>"


# ---------------------------------------------------------------------------
# TLFD chart with log-scale toggle
# ---------------------------------------------------------------------------


def _tlfd_chart(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
    key: str,
) -> str:
    bins = obs["distbin"].to_list()

    obs_total = obs["Total"].to_list() if "Total" in obs.columns else []
    mod_total = mod["Total"].to_list() if "Total" in mod.columns else []

    obs_sum = sum(obs_total) or 1
    mod_sum = sum(mod_total) or 1
    obs_share = [v / obs_sum for v in obs_total]
    mod_share = [v / mod_sum for v in mod_total]

    # Smoothed survey trace to reveal trend through sparse tail
    mod_smooth = gaussian_smooth(mod_share, sigma=2.0)

    traces = (
        f"{{name:'{esc_js(obs_label)}', x:{bins!r}, "
        f"y:{obs_share!r}, type:'scatter', mode:'lines'}}, "
        f"{{name:'{esc_js(mod_label)} (raw)', x:{bins!r}, "
        f"y:{mod_share!r}, type:'scatter', mode:'markers', "
        f"marker:{{size:4, opacity:0.4}}}}, "
        f"{{name:'{esc_js(mod_label)} (smoothed)', x:{bins!r}, "
        f"y:{mod_smooth!r}, type:'scatter', mode:'lines', "
        f"line:{{width:2}}}}"
    )

    div_id = f"tlfd_{key}"
    trip_title = key.replace("trip_tlfd_", "").title()
    tmpl = load_template("tlfd_chart.js")
    js = tmpl.substitute(div_id=div_id, traces=traces, trip_title=trip_title)
    return wrap_chart(div_id, js)


# ---------------------------------------------------------------------------
# Average trip lengths
# ---------------------------------------------------------------------------


def _avg_trip_table(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
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
    header += f"<th colspan='{ncols}'>Delta</th>"
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
            body += delta_cell(mod_val - obs_val, fmt=".1f")
        body += "</tr>"

    return header + body + "</tbody></table>"


# ---------------------------------------------------------------------------
# TLFD fit metrics
# ---------------------------------------------------------------------------


def _tlfd_fit_table(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    """Fit metrics comparing TLFD distributions for each trip purpose."""
    fit_rows: list[dict] = []
    for trip_key, trip_title in [
        ("trip_tlfd_work", "Work"),
        ("trip_tlfd_univ", "University"),
        ("trip_tlfd_school", "School"),
    ]:
        pair = pick_pair(per_label, labels, trip_key)
        if not pair:
            continue
        obs_df, mod_df = pair[1], pair[3]
        obs_total = obs_df["Total"].to_list() if "Total" in obs_df.columns else []
        mod_total = mod_df["Total"].to_list() if "Total" in mod_df.columns else []
        obs_sum = sum(obs_total) or 1
        mod_sum = sum(mod_total) or 1
        obs_sh = [v / obs_sum for v in obs_total]
        mod_sh = [v / mod_sum for v in mod_total]
        fit_rows.append(
            compute_fit_row(obs_sh, mod_sh, trip_title, label_key="Purpose"),
        )

    if not fit_rows:
        return ""

    if len(fit_rows) > 1:
        n = len(fit_rows)
        fit_rows.append({
            "Purpose": "Overall",
            "rmse": sum(r["rmse"] for r in fit_rows) / n,
            "dissim": sum(r["dissim"] for r in fit_rows) / n,
            "hellinger": sum(r["hellinger"] for r in fit_rows) / n,
            "_bold": True,
        })

    return fit_table(fit_rows, label_key="Purpose")
