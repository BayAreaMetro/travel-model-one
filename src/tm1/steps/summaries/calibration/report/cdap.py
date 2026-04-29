"""Daily Activity Pattern (CDAP) tab renderer."""

import math

import polars as pl

from tm1.steps.summaries.calibration.enums import CTRAMPPersonType

from .helpers import (
    add_shares,
    compute_fit_row,
    count_cell,
    esc,
    esc_js,
    fit_table,
    load_template,
    pair_selector,
    pct_cell,
    pick_datasets,
    wrap_chart,
)

PERSON_TYPE_LABELS: dict[int, str] = {pt.id: pt.label for pt in CTRAMPPersonType}

PATTERNS = ["H", "M", "N"]
PATTERN_COLOURS = {"H": "#76b7b2", "M": "#4e79a7", "N": "#f28e2b"}

_NEAR_ZERO = 1e-9
_MIN_SHARE = 1e-12

# Column geometry: 1 label (190px) + 9 value cols (90px each) = 1000px
_COLGROUP = (
    "<colgroup>"
    "<col style='width:190px'>"
    + "<col style='width:90px'>" * 9
    + "</colgroup>"
)


def render(
    per_label: dict[str, dict[str, pl.DataFrame]],
    labels: list[str],
) -> str:
    """Return HTML fragment for the CDAP tab."""
    datasets = pick_datasets(per_label, labels, "person_type_summary")
    if len(datasets) < 2:  # noqa: PLR2004
        return "<p>Need at least two datasets for comparison.</p>"

    return pair_selector(datasets, "cdap", _render_pair)


def _render_pair(
    obs_label: str,
    obs_raw: pl.DataFrame,
    mod_label: str,
    mod_raw: pl.DataFrame,
) -> str:
    """Render a single (reference, model) comparison."""
    obs = add_shares(_label_person_types(obs_raw), PATTERNS)
    mod = add_shares(_label_person_types(mod_raw), PATTERNS)

    chart_id = f"cdap_{obs_label}_{mod_label}".replace(" ", "_")
    parts: list[str] = [
        "<h3>Absolute Counts</h3>",
        _counts_table(obs, mod, obs_label, mod_label),
        "<h3>Share Comparison</h3>",
        _shares_table(obs, mod, obs_label, mod_label),
        "<h3>Model Constant Adjustment ln(Target / Current)</h3>",
        _constants_table(obs, mod, obs_label, mod_label),
        "<h3>Goodness of Fit</h3>",
        _fit_table(obs, mod),
        _chart(obs, mod, obs_label, mod_label, chart_id),
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _label_person_types(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.col("person_type").cast(pl.Int64)
        .replace_strict(PERSON_TYPE_LABELS, default="Unknown")
        .alias("person_type_label"),
    )


def _pt_label(row: dict) -> str:
    return esc(row.get("person_type_label", str(row["person_type"])))


def _two_row_header(
    obs_label: str,
    mod_label: str,
    third_label: str,
) -> str:
    """Standard 2-row header: Person Type | dataset1 H M N | dataset2 H M N | third H M N."""
    ncols = len(PATTERNS)
    h = "<thead><tr><th rowspan='2'>Person Type</th>"
    h += f"<th colspan='{ncols}' class='group-sep'>{esc(obs_label)}</th>"
    h += f"<th colspan='{ncols}' class='group-sep'>{esc(mod_label)}</th>"
    h += f"<th colspan='{ncols}' class='group-sep'>{third_label}</th>"
    h += "</tr><tr>"
    for g in range(3):
        for p in PATTERNS:
            cls = " class='group-sep'" if g > 0 and p == PATTERNS[0] else ""
            h += f"<th{cls}>{p}</th>"
    h += "</tr></thead>"
    return h


def _open_table() -> str:
    return f"<table class='cal-table'>{_COLGROUP}"


# ---------------------------------------------------------------------------
# Counts table
# ---------------------------------------------------------------------------


def _counts_table(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
) -> str:
    rows_obs = obs.sort("person_type").to_dicts()
    mod_by_pt = {r["person_type"]: r for r in mod.sort("person_type").to_dicts()}

    out = _open_table()
    out += _two_row_header(obs_label, mod_label, "Difference")
    out += "<tbody>"

    for row in rows_obs:
        mr = mod_by_pt.get(row["person_type"], {})
        out += f"<tr><td>{_pt_label(row)}</td>"
        for p in PATTERNS:
            out += count_cell(row.get(p))
        for i, p in enumerate(PATTERNS):
            cls = " class='group-sep'" if i == 0 else ""
            val = mr.get(p)
            out += f"<td{cls}>{val:,.0f}</td>" if val is not None else f"<td{cls}>—</td>"
        for i, p in enumerate(PATTERNS):
            obs_val = row.get(p, 0) or 0
            mod_val = mr.get(p, 0) or 0
            diff = mod_val - obs_val
            cls_sep = " group-sep" if i == 0 else ""
            if abs(diff) < _NEAR_ZERO:
                out += f"<td class='{cls_sep.strip()}'>0</td>"
            else:
                colour = "pos" if diff > 0 else "neg"
                classes = f"{colour} {cls_sep}".strip()
                out += f"<td class='{classes}'>{diff:,.0f}</td>"
        out += "</tr>"

    return out + "</tbody></table>"


# ---------------------------------------------------------------------------
# Shares table
# ---------------------------------------------------------------------------


def _shares_table(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
) -> str:
    rows_obs = obs.sort("person_type").to_dicts()
    mod_by_pt = {r["person_type"]: r for r in mod.sort("person_type").to_dicts()}

    out = _open_table()
    out += _two_row_header(
        f"{obs_label} (Share)", f"{mod_label} (Share)", "Delta",
    )
    out += "<tbody>"

    for row in rows_obs:
        mr = mod_by_pt.get(row["person_type"], {})
        out += f"<tr><td>{_pt_label(row)}</td>"
        for p in PATTERNS:
            out += pct_cell(row.get(f"{p}_share"))
        for i, p in enumerate(PATTERNS):
            cls = " class='group-sep'" if i == 0 else ""
            val = mr.get(f"{p}_share")
            out += f"<td{cls}>{val:.1%}</td>" if val is not None else f"<td{cls}>—</td>"
        for i, p in enumerate(PATTERNS):
            obs_val = row.get(f"{p}_share", 0) or 0
            mod_val = mr.get(f"{p}_share", 0) or 0
            d = mod_val - obs_val
            cls_sep = " group-sep" if i == 0 else ""
            if abs(d) < _NEAR_ZERO:
                out += f"<td class='{cls_sep.strip()}'>{d:.1%}</td>"
            else:
                colour = "pos" if d > 0 else "neg"
                classes = f"{colour} {cls_sep}".strip()
                out += f"<td class='{classes}'>{d:.1%}</td>"
        out += "</tr>"

    return out + "</tbody></table>"


# ---------------------------------------------------------------------------
# Constant adjustment table
# ---------------------------------------------------------------------------


def _ln_ratio(numerator: float, denominator: float) -> float:
    """Safe ln(num/denom), clamped to avoid log(0)."""
    return math.log(max(numerator, _MIN_SHARE) / max(denominator, _MIN_SHARE))


def _const_cell(val: float, extra_cls: str = "") -> str:
    """Render a constant-adjustment cell (4 decimal places)."""
    classes = extra_cls
    if abs(val) >= _NEAR_ZERO:
        classes += " pos" if val > 0 else " neg"
    classes = classes.strip()
    cls_attr = f" class='{classes}'" if classes else ""
    txt = "0.0000" if abs(val) < _NEAR_ZERO else f"{val:.4f}"
    return f"<td{cls_attr}>{txt}</td>"


def _constants_table(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
) -> str:
    """Constants table: ln(target_share / current_share).

    First-dataset column: ln(second / first).
    Second-dataset column: ln(first / second).
    Delta column: difference between the two adjustments.

    ActivitySim uses opposite sign convention for CDAP ASCs compared to CTRAMP.
    When the model is ActivitySim, we negate its adjustment column so that the
    displayed value can be added directly to the ActivitySim coefficient file.
    """
    rows_obs = obs.sort("person_type").to_dicts()
    mod_by_pt = {r["person_type"]: r for r in mod.sort("person_type").to_dicts()}

    # Detect ActivitySim model — negate its column for direct applicability
    mod_is_asim = "activitysim" in mod_label.lower()
    obs_is_asim = "activitysim" in obs_label.lower()
    mod_sign = -1.0 if mod_is_asim else 1.0
    obs_sign = -1.0 if obs_is_asim else 1.0

    out = _open_table()
    out += _two_row_header(obs_label, mod_label, "Delta")
    out += "<tbody>"

    for row in rows_obs:
        mr = mod_by_pt.get(row["person_type"], {})
        out += f"<tr><td>{_pt_label(row)}</td>"
        for p in PATTERNS:
            obs_s = row.get(f"{p}_share", 0) or 0
            mod_s = mr.get(f"{p}_share", 0) or 0
            out += _const_cell(_ln_ratio(mod_s, obs_s) * obs_sign)
        for i, p in enumerate(PATTERNS):
            obs_s = row.get(f"{p}_share", 0) or 0
            mod_s = mr.get(f"{p}_share", 0) or 0
            sep = "group-sep" if i == 0 else ""
            out += _const_cell(_ln_ratio(obs_s, mod_s) * mod_sign, extra_cls=sep)
        for i, p in enumerate(PATTERNS):
            obs_s = row.get(f"{p}_share", 0) or 0
            mod_s = mr.get(f"{p}_share", 0) or 0
            adj1 = _ln_ratio(mod_s, obs_s) * obs_sign
            adj2 = _ln_ratio(obs_s, mod_s) * mod_sign
            sep = "group-sep" if i == 0 else ""
            out += _const_cell(adj1 - adj2, extra_cls=sep)
        out += "</tr>"

    out += "</tbody></table>"

    # Footnote about sign convention
    if mod_is_asim or obs_is_asim:
        out += (
            "<div class='fit-hint'>"
            "<b>Note:</b> ActivitySim uses the opposite sign convention for CDAP ASCs "
            "compared to CTRAMP. Values shown for ActivitySim columns have been "
            "negated so adjustments can be added directly to the ActivitySim "
            "<code>cdap_coefficients.csv</code> file."
            "</div>"
        )

    return out


# ---------------------------------------------------------------------------
# Goodness of fit
# ---------------------------------------------------------------------------


def _fit_table(obs: pl.DataFrame, mod: pl.DataFrame) -> str:
    """Summary statistics per person type + overall."""
    rows_obs = obs.sort("person_type").to_dicts()
    mod_by_pt = {r["person_type"]: r for r in mod.sort("person_type").to_dicts()}

    fit_rows: list[dict] = []
    for row in rows_obs:
        mr = mod_by_pt.get(row["person_type"], {})
        obs_shares = [row.get(f"{p}_share", 0) or 0 for p in PATTERNS]
        mod_shares = [mr.get(f"{p}_share", 0) or 0 for p in PATTERNS]
        fit_rows.append(
            compute_fit_row(
                obs_shares, mod_shares, _pt_label(row), label_key="Person Type",
            ),
        )

    if fit_rows:
        n = len(fit_rows)
        fit_rows.append({
            "Person Type": "Overall",
            "rmse": sum(r["rmse"] for r in fit_rows) / n,
            "dissim": sum(r["dissim"] for r in fit_rows) / n,
            "hellinger": sum(r["hellinger"] for r in fit_rows) / n,
            "_bold": True,
        })

    return fit_table(fit_rows, label_key="Person Type")


# ---------------------------------------------------------------------------
# Chart — grouped bar with tooltips showing both count and share
# ---------------------------------------------------------------------------


def _chart(
    obs: pl.DataFrame,
    mod: pl.DataFrame,
    obs_label: str,
    mod_label: str,
    chart_id: str = "cdap_chart",
) -> str:
    obs_sorted = obs.sort("person_type")
    mod_sorted = mod.sort("person_type")
    pt_labels = obs_sorted["person_type_label"].to_list()

    traces: list[str] = []
    for p in PATTERNS:
        colour = PATTERN_COLOURS[p]
        for source, df, opacity in [
            (obs_label, obs_sorted, 0.55),
            (mod_label, mod_sorted, 1.0),
        ]:
            shares = df[f"{p}_share"].to_list()
            counts = df[p].to_list()
            hover = [
                f"{p}: {s:.1%} ({c:,.0f})"
                for s, c in zip(shares, counts, strict=True)
            ]
            traces.append(
                f"{{name:'{p} ({esc_js(source)})', "
                f"x:{pt_labels!r}, y:{shares!r}, type:'bar', "
                f"hovertext:{hover!r}, hoverinfo:'text+name', "
                f"textposition:'none', "
                f"marker:{{color:'{colour}',opacity:{opacity}}}}}",
            )

    tmpl = load_template("cdap_chart.js")
    js = tmpl.substitute(div_id=chart_id, traces=", ".join(traces))
    return wrap_chart(chart_id, js)
