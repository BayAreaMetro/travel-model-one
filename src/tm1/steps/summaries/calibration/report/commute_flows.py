"""County-to-County Commuting Flows tab renderer."""

import polars as pl

from tm1.steps.summaries.calibration.enums import CTRAMPCounty

from .helpers import (
    add_shares,
    compute_fit_row,
    delta_cell,
    esc,
    fit_table,
    pct_cell,
    pick_pair,
)

_COUNTY_NAMES = [c.label for c in CTRAMPCounty]


def render(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    """Return HTML fragment for the Commuting Flows tab."""
    pair = pick_pair(per_label, labels, "county_summary")
    if not pair:
        return "<p>Insufficient data for comparison.</p>"

    obs_label, obs_df, mod_label, mod_df = pair
    parts: list[str] = [
        _flow_tables(obs_df, mod_df, obs_label, mod_label),
        "<h3>Goodness of Fit</h3>",
        _flows_fit_table(obs_df, mod_df),
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Flow matrices
# ---------------------------------------------------------------------------


def _flow_tables(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
) -> str:
    county_col = "home_county_name"
    value_cols = [c for c in obs.columns if c in _COUNTY_NAMES]

    obs_s = add_shares(obs, value_cols)
    mod_s = add_shares(mod, value_cols)
    obs_rows = obs_s.sort(county_col).to_dicts()
    mod_rows = mod_s.sort(county_col).to_dicts()
    mod_by_hc: dict[str, dict] = {r[county_col]: r for r in mod_rows}

    out = f"<h3>{esc(obs_label)} (Share)</h3>"
    out += _matrix_html(obs_rows, county_col, value_cols)

    out += f"<h3>{esc(mod_label)} (Share)</h3>"
    out += _matrix_html(mod_rows, county_col, value_cols)

    out += "<h3>Delta (Model &minus; Observed)</h3>"
    out += "<table class='cal-table'><thead><tr><th>Home County</th>"
    for vc in value_cols:
        out += f"<th>{esc(vc)}</th>"
    out += "</tr></thead><tbody>"
    for row in obs_rows:
        hc = row[county_col]
        mr = mod_by_hc.get(hc, {})
        out += f"<tr><td>{esc(str(hc))}</td>"
        for vc in value_cols:
            obs_val = row.get(f"{vc}_share", 0) or 0
            mod_val = mr.get(f"{vc}_share", 0) or 0
            out += delta_cell(mod_val - obs_val)
        out += "</tr>"
    out += "</tbody></table>"
    return out


def _matrix_html(
    rows: list[dict],
    county_col: str,
    value_cols: list[str],
) -> str:
    out = "<table class='cal-table'><thead><tr><th>Home County</th>"
    for vc in value_cols:
        out += f"<th>{esc(vc)}</th>"
    out += "</tr></thead><tbody>"
    for row in rows:
        out += f"<tr><td>{esc(str(row[county_col]))}</td>"
        for vc in value_cols:
            out += pct_cell(row.get(f"{vc}_share"))
        out += "</tr>"
    out += "</tbody></table>"
    return out


# ---------------------------------------------------------------------------
# Fit metrics
# ---------------------------------------------------------------------------


def _flows_fit_table(obs: pl.DataFrame, mod: pl.DataFrame) -> str:
    """Fit metrics per home county comparing destination distributions."""
    county_col = "home_county_name"
    value_cols = [c for c in obs.columns if c in _COUNTY_NAMES]

    obs_s = add_shares(obs, value_cols).sort(county_col)
    mod_s = add_shares(mod, value_cols).sort(county_col)
    obs_rows = obs_s.to_dicts()
    mod_by_hc = {r[county_col]: r for r in mod_s.to_dicts()}

    fit_rows: list[dict] = []
    for row in obs_rows:
        hc = row[county_col]
        mr = mod_by_hc.get(hc, {})
        obs_sh = [row.get(f"{vc}_share", 0) or 0 for vc in value_cols]
        mod_sh = [mr.get(f"{vc}_share", 0) or 0 for vc in value_cols]
        fit_rows.append(
            compute_fit_row(obs_sh, mod_sh, str(hc), label_key="Home County"),
        )

    if fit_rows:
        n = len(fit_rows)
        fit_rows.append({
            "Home County": "Overall",
            "rmse": sum(r["rmse"] for r in fit_rows) / n,
            "dissim": sum(r["dissim"] for r in fit_rows) / n,
            "hellinger": sum(r["hellinger"] for r in fit_rows) / n,
            "_bold": True,
        })

    return fit_table(fit_rows, label_key="Home County")
