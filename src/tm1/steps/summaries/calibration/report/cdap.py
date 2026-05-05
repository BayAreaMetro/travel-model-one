"""Daily Activity Pattern (CDAP) tab renderer."""

import polars as pl

from tm1.steps.summaries.calibration.enums import CTRAMPPersonType

from .helpers import (
    add_shares,
    append_overall_fit,
    compute_fit_row,
    count_cell,
    esc,
    esc_js,
    fit_table,
    load_template,
    pct_cell,
    pick_datasets,
    pp_delta_cell,
    render_pairs,
    wrap_chart,
)

PERSON_TYPE_LABELS: dict[int, str] = {pt.id: pt.label for pt in CTRAMPPersonType}

PATTERNS = ["H", "M", "N"]
PATTERN_COLOURS = {"H": "#76b7b2", "M": "#4e79a7", "N": "#f28e2b"}

_NEAR_ZERO = 1e-9

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
    datasets = pick_datasets(per_label, labels, "person_type_summary")
    if len(datasets) < 2:  # noqa: PLR2004
        return "<p>Need at least two datasets for comparison.</p>"
    return render_pairs(datasets, _render_pair)


def _render_pair(
    obs_label: str,
    obs_raw: pl.DataFrame,
    mod_label: str,
    mod_raw: pl.DataFrame,
) -> str:
    obs = add_shares(_label_person_types(obs_raw), PATTERNS)
    mod = add_shares(_label_person_types(mod_raw), PATTERNS)

    chart_id = f"cdap_{obs_label}_{mod_label}".replace(" ", "_")
    parts: list[str] = [
        "<h3>Share Comparison</h3>",
        _shares_table(obs, mod, obs_label, mod_label),
        "<h3>Absolute Counts</h3>",
        _counts_table(obs, mod, obs_label, mod_label),
        "<h3>Goodness of Fit</h3>",
        _fit_section(obs, mod),
        _chart(obs, mod, obs_label, mod_label, chart_id),
    ]
    return "\n".join(parts)


def _label_person_types(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.col("person_type").cast(pl.Int64)
        .replace_strict(PERSON_TYPE_LABELS, default="Unknown")
        .alias("person_type_label"),
    )


def _pt_label(row: dict) -> str:
    return esc(row.get("person_type_label", str(row["person_type"])))


def _two_row_header(obs_label: str, mod_label: str, third_label: str) -> str:
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


def _counts_table(obs: pl.DataFrame, mod: pl.DataFrame, obs_label: str, mod_label: str) -> str:
    rows_obs = obs.sort("person_type").to_dicts()
    mod_by_pt = {r["person_type"]: r for r in mod.sort("person_type").to_dicts()}

    out = _open_table()
    out += _two_row_header(obs_label, mod_label, "% Change")
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
            if i == 0:
                out += f"<td class='group-sep'>"
            else:
                out += "<td"
            # Use pct_change style for count deltas
            if abs(obs_val) < _NEAR_ZERO:
                out += ">—</td>" if i > 0 else "—</td>"
            else:
                diff_pct = (mod_val - obs_val) / obs_val * 100
                mag = abs(diff_pct)
                cls_extra = ""
                if mag > 10:
                    cls_extra = " err-bad"
                elif mag > 5:
                    cls_extra = " err-warn"
                sign = "+" if diff_pct >= 0 else ""
                if i == 0:
                    out = out.rstrip(">")
                    if cls_extra:
                        out = out.replace("class='group-sep'", f"class='group-sep{cls_extra}'")
                    out += f">{sign}{diff_pct:.1f}%</td>"
                else:
                    cls_attr = f" class='{cls_extra.strip()}'" if cls_extra else ""
                    out += f"{cls_attr}>{sign}{diff_pct:.1f}%</td>"
        out += "</tr>"
    return out + "</tbody></table>"


def _shares_table(obs: pl.DataFrame, mod: pl.DataFrame, obs_label: str, mod_label: str) -> str:
    rows_obs = obs.sort("person_type").to_dicts()
    mod_by_pt = {r["person_type"]: r for r in mod.sort("person_type").to_dicts()}

    out = _open_table()
    out += _two_row_header(f"{obs_label} (Share)", f"{mod_label} (Share)", "Delta (pp)")
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
            if i == 0:
                # First delta col needs group-sep — build cell manually
                diff = (mod_val - obs_val) * 100
                mag = abs(diff)
                cls = "group-sep"
                if mag > 10:
                    cls += " err-bad"
                elif mag > 5:
                    cls += " err-warn"
                sign = "+" if diff >= 0 else ""
                out += f"<td class='{cls}'>{sign}{diff:.1f} pp</td>"
            else:
                out += pp_delta_cell(obs_val, mod_val)
        out += "</tr>"
    return out + "</tbody></table>"





def _fit_section(obs: pl.DataFrame, mod: pl.DataFrame) -> str:
    rows_obs = obs.sort("person_type").to_dicts()
    mod_by_pt = {r["person_type"]: r for r in mod.sort("person_type").to_dicts()}

    fit_rows: list[dict] = []
    for row in rows_obs:
        mr = mod_by_pt.get(row["person_type"], {})
        obs_shares = [row.get(f"{p}_share", 0) or 0 for p in PATTERNS]
        mod_shares = [mr.get(f"{p}_share", 0) or 0 for p in PATTERNS]
        fit_rows.append(compute_fit_row(obs_shares, mod_shares, _pt_label(row)))

    append_overall_fit(fit_rows)
    return fit_table(fit_rows)


def _chart(
    obs: pl.DataFrame, mod: pl.DataFrame,
    obs_label: str, mod_label: str, chart_id: str,
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
