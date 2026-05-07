"""Generate an HTML report comparing CTRAMP UEC coefficients with ActivitySim specs.

Reads submodel definitions from ablation_config.yaml, parses CTRAMP .xls UEC
workbooks and ActivitySim spec/coefficient CSVs, writes a single HTML file.

Usage:
    python scripts/migration_validation/compare_coefficients.py
"""

import contextlib
import csv
import html
import logging
import re
import sys
from pathlib import Path

import xlrd
import yaml
from uec_mappings import MAPPINGS, NOTES, SIZE_TERMS_CROSSWALK

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "ablation_config.yaml"

# UEC sheet layout constants
ALT_NAMES_ROW = 3
FIRST_ALT_COL = 6

esc = html.escape


# -- UEC reader ---------------------------------------------------------------

def read_uec_sheets(ctramp_dir: Path, filename: str, sheet_names: list[str]) -> list[dict]:
    """Parse UEC sheets into structured dicts."""
    path = ctramp_dir / filename
    if not path.exists():
        log.warning("UEC not found: %s", path)
        return []
    wb = xlrd.open_workbook(str(path))
    results = []
    for sn in sheet_names:
        try:
            sh = wb.sheet_by_name(sn)
        except xlrd.biffh.XLRDError:
            log.warning("Sheet %r not in %s", sn, path)
            continue
        alts = [str(sh.cell(ALT_NAMES_ROW, c).value).strip() or f"Alt{c - FIRST_ALT_COL + 1}"
                for c in range(FIRST_ALT_COL, sh.ncols)]
        rows = []
        for r in range(ALT_NAMES_ROW + 1, sh.nrows):
            no = sh.cell(r, 0).value
            if not no and no != 0:
                continue
            try:
                no = int(no)
            except (TypeError, ValueError):
                continue
            coeffs = {}
            for ci, alt in enumerate(alts):
                v = sh.cell(r, FIRST_ALT_COL + ci).value
                if v != "":
                    coeffs[alt] = v
            if coeffs:
                rows.append({
                    "no": no, "desc": str(sh.cell(r, 2).value).strip(),
                    "filter": str(sh.cell(r, 3).value).strip(),
                    "formula": str(sh.cell(r, 4).value).strip(),
                    "coeffs": coeffs,
                })
        results.append({"sheet_name": sn, "alt_names": alts, "rows": rows})
    return results


def read_uec_tokens(ctramp_dir: Path, filename: str, sheet_names: list[str]) -> dict[str, dict[str, str]]:
    """Read token section (rows before utility rows) from UEC sheets.

    Returns: {sheet_name: {token_name: formula_or_value_string}}
    """
    path = ctramp_dir / filename
    if not path.exists():
        return {}
    wb = xlrd.open_workbook(str(path))
    result: dict[str, dict[str, str]] = {}
    for sn in sheet_names:
        try:
            sh = wb.sheet_by_name(sn)
        except xlrd.biffh.XLRDError:
            continue
        tokens: dict[str, str] = {}
        for r in range(sh.nrows):
            token_name = str(sh.cell(r, 1).value).strip()
            if token_name and token_name.startswith("c_"):
                formula = sh.cell(r, 4).value
                if isinstance(formula, float):
                    tokens[token_name] = str(formula)
                else:
                    tokens[token_name] = str(formula).strip()
        result[sn] = tokens
    return result


# -- ActivitySim reader --------------------------------------------------------

def _resolve(dirs: list[Path], filename: str) -> Path | None:
    """Find first occurrence of filename across config dirs (priority order)."""
    for d in dirs:
        p = d / filename
        if p.exists():
            return p
    return None


# Sheet name → template purpose column mapping (for Mode Choice models)
SHEET_TO_PURPOSE: dict[str, str] = {
    "Work": "work", "University": "univ", "School": "school",
    "Escort": "escort", "Shopping": "shopping", "EatOut": "eatout",
    "OthMaint": "othmaint", "Social": "social", "OthDiscr": "othdiscr",
    "WorkBased": "atwork",
}

# CTRAMP token → ASim YAML constant name (for tokens that use YAML CONSTANTS
# instead of template coefficients). The comparison extracts the multiplier from
# the CTRAMP formula "M * c_ivt" and compares it to the YAML constant value.
TOKEN_TO_YAML: dict[str, str] = {
    "c_ivt_lrt": "ivt_lrt_multiplier",
    "c_ivt_ferry": "ivt_ferry_multiplier",
    "c_ivt_exp": "ivt_exp_multiplier",
    "c_ivt_hvy": "ivt_hvy_multiplier",
    "c_ivt_com": "ivt_com_multiplier",
    "c_walkTimeShort": "walktimeshort_multiplier",
    "c_walkTimeLong": "walktimelong_multiplier",
    "c_bikeTimeShort": "biketimeshort_multiplier",
    "c_bikeTimeLong": "biketimelong_multiplier",
    "c_cost": "ivt_cost_multiplier",
    "c_shortiWait": "short_i_wait_multiplier",
    "c_longiWait": "long_i_wait_multiplier",
    "c_wacc": "wacc_multiplier",
    "c_wegr": "wegr_multiplier",
    "c_waux": "waux_multiplier",
    "c_dtim": "dtim_multiplier",
    "c_xwait": "xwait_multiplier",
    "c_dacc_ratio": "dacc_ratio",
    "c_xfers_wlk": "xfers_wlk_multiplier",
    "c_xfers_drv": "xfers_drv_multiplier",
    "c_drvtrn_distpen_0": "drvtrn_distpen_0_multiplier",
    "c_drvtrn_distpen_max": "drvtrn_distpen_max",
    "c_densityIndex": "density_index_multiplier",
    "c_topology_walk": "topology_walk_multiplier",
    "c_topology_bike": "topology_bike_multiplier",
    "c_topology_trn": "topology_trn_multiplier",
    "c_originDensityIndex": "origin_density_index_multiplier",
    "c_originDensityIndexMax": "origin_density_index_max",
}

# Known genuine coefficient differences between CTRAMP and ASim Trip MC.
# These are NOT data bugs — the ASim migration intentionally changed these values.
# Each entry: YAML constant name → (CTRAMP IVT mult, ASim IVT mult, explanation)
KNOWN_TRIP_MC_DIFFS: dict[str, tuple[float, float, str]] = {
    "density_index_multiplier": (-0.2, -5, "25x — same variable (density_index) and same data; intentional re-calibration for Trip MC"),
    "origin_density_index_multiplier": (-0.6, -15, "25x — consistent with density_index_multiplier change"),
    "walktimelong_multiplier": (10, 5, "0.5x — reduced walk-time penalty beyond threshold"),
    "xfers_wlk_multiplier": (15, 5, "0.33x — reduced walk-transit transfer penalty"),
    "xfers_drv_multiplier": (20, 15, "0.75x — reduced drive-transit transfer penalty"),
    "ivt_exp_multiplier": (1.0, -0.0175, "LIKELY BUG: ASim=-0.0175 looks like an accidental paste of coef_ivt_othmaint_social; Tour MC correctly has 1.0"),
    "ivt_cost_multiplier": (0.6, 0.6, "CTRAMP formula is (0.6*c_ivt)/vot; ASim uses ivt_cost_multiplier * df.ivot * coef_ivt — structurally equivalent"),
}


def _read_yaml_constants(configs_dirs: list[Path], yaml_file: str) -> dict[str, float]:
    """Read CONSTANTS section from an ActivitySim model YAML file."""
    path = _resolve(configs_dirs, yaml_file)
    if not path:
        return {}
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    consts = cfg.get("CONSTANTS", {})
    # Only keep scalar numeric values
    return {k: v for k, v in consts.items() if isinstance(v, (int, float))}


def _read_template(configs_dirs: list[Path], template_file: str, coeff_file: str) -> dict[str, dict[str, float]]:
    """Read coefficient template and pre-resolve values per purpose.

    Returns: {generic_coeff_name: {purpose: resolved_numeric_value}}
    """
    # First read the base coefficients file
    coeff_path = _resolve(configs_dirs, coeff_file)
    coeffs: dict[str, float] = {}
    if coeff_path:
        with coeff_path.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    coeffs[row["coefficient_name"].strip()] = float(row["value"])
                except (ValueError, KeyError):
                    pass

    # Read the template
    tpl_path = _resolve(configs_dirs, template_file)
    if not tpl_path:
        return {}
    result: dict[str, dict[str, float]] = {}
    with tpl_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        purposes = [c for c in (reader.fieldnames or []) if c != "coefficient_name"]
        for row in reader:
            generic = (row.get("coefficient_name") or "").strip()
            if not generic or generic.startswith("#"):
                continue
            purpose_map: dict[str, float] = {}
            for p in purposes:
                specific = (row.get(p) or "").strip()
                if not specific:
                    # Empty cell = use generic name directly
                    if generic in coeffs:
                        purpose_map[p] = coeffs[generic]
                else:
                    if specific in coeffs:
                        purpose_map[p] = coeffs[specific]
            if purpose_map:
                result[generic] = purpose_map
    return result


def read_asim_spec(configs_dirs: list[Path], spec_file: str, coeff_file: str) -> dict:  # noqa: C901
    """Parse spec + coefficients into {alt_names, rows: [{label, desc, expr, coeffs}]}."""
    # Coefficient lookup
    coeff_path = _resolve(configs_dirs, coeff_file)
    coeffs: dict[str, float] = {}
    if coeff_path:
        with coeff_path.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    coeffs[row["coefficient_name"].strip()] = float(row["value"])
                except (ValueError, KeyError):
                    coeffs[row["coefficient_name"].strip()] = row.get("value", "")

    spec_path = _resolve(configs_dirs, spec_file)
    if not spec_path:
        return {"alt_names": [], "rows": []}

    with spec_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        skip = {"Label", "Description", "Expression", "coefficient", ""}
        alt_names = [c for c in fields if c not in skip]

        has_label_col = "Label" in fields
        rows = []
        for row in reader:
            label = (row.get("Label") or row.get("Description") or "").strip() if has_label_col else (row.get("Description") or "").strip()
            if not label or label.startswith("#"):
                continue
            single = (row.get("coefficient") or "").strip()
            resolved: dict[str, float | str] = {}
            if alt_names:
                for alt in alt_names:
                    cn = (row.get(alt) or "").strip()
                    if not cn:
                        continue
                    resolved[alt] = coeffs.get(cn, cn)
                    if isinstance(resolved[alt], str):
                        with contextlib.suppress(ValueError):
                            resolved[alt] = float(resolved[alt])
            elif single:
                resolved["coeff"] = coeffs.get(single, single)
            if resolved:
                rows.append({
                    "label": label, "desc": (row.get("Description") or "").strip(),
                    "expr": (row.get("Expression") or "").strip(), "coeffs": resolved,
                })
        return {"alt_names": alt_names, "rows": rows}


# -- Mapped comparison table ---------------------------------------------------

def _mapped_table(name: str, sheets: list[dict], spec: dict, template_resolve: dict[str, dict[str, float]] | None = None) -> str:
    """Render an outer-join comparison table if a mapping exists for this submodel."""
    crosswalk = MAPPINGS.get(name)
    if not crosswalk:
        return ""

    # Detect multi-segment: sheets share the same row numbers
    multi_seg = len(sheets) > 1 and len({r["no"] for s in sheets for r in s["rows"]}) < sum(len(s["rows"]) for s in sheets)

    # Index CTRAMP rows by (sheet_name, no) for multi-seg, or just no for single-sheet
    ctramp_by_sheet_no: dict[tuple[str, int], dict] = {}
    ctramp_by_no: dict[int, dict] = {}
    for s in sheets:
        for r in s["rows"]:
            ctramp_by_sheet_no[(s["sheet_name"], r["no"])] = r
            ctramp_by_no[r["no"]] = r

    # Index ActivitySim rows by label
    asim_by_label: dict[str, dict] = {}
    for r in spec["rows"]:
        asim_by_label[r["label"]] = r

    asim_alts = spec.get("alt_names", [])
    used_ctramp: set[int] = set()
    used_asim: set[str] = set()

    def _coeff_val(row: dict) -> str:
        if not row or not row.get("coeffs"):
            return ""
        return next(iter(row["coeffs"].values()))

    def _coeff_for_alt(row: dict, alt: str) -> str:
        if not row or not row.get("coeffs"):
            return ""
        return row["coeffs"].get(alt, "")

    def _diff_cell(c_val, a_val) -> str:
        if c_val == "" or a_val == "":
            return "<td></td>"
        try:
            diff = float(a_val) - float(c_val)
            cls = "match" if abs(diff) < 1e-6 else "diff"
            return f"<td class='num {cls}'>{diff:+.4f}</td>"
        except (ValueError, TypeError):
            return "<td></td>"

    def _ctramp_expr(row: dict) -> str:
        """Combine CTRAMP filter + formula into a single expression string."""
        if not row:
            return ""
        f, e = row.get("filter", ""), row.get("formula", "")
        if f and e:
            return f"[{f}] {e}"
        return e or f

    # Detect multi-alt: single sheet with multiple CTRAMP alts matching ASim alts by position
    ctramp_alts = sheets[0].get("alt_names", []) if len(sheets) == 1 else []
    multi_alt = not multi_seg and len(asim_alts) > 1 and len(ctramp_alts) > 1

    body = ""

    def _resolve_for_purpose(row: dict, purpose: str) -> float | str:
        """Resolve the primary ASim coefficient for a given purpose using template."""
        if not row or not row.get("coeffs"):
            return ""
        for alt, val in row["coeffs"].items():
            if isinstance(val, (int, float)):
                return val  # Already resolved (literal like -999, or shared coeff)
            # Unresolved string — try template
            if template_resolve and val in template_resolve:
                return template_resolve[val].get(purpose, val)
            return val  # Can't resolve, return raw name
        return ""

    def _pair_cells(c_val, a_val, rowspan: str = "") -> str:
        """Render a CTRAMP/ASim value pair with match/diff highlighting."""
        if c_val == "" and a_val == "":
            return f"<td class='num'></td><td class='num'{rowspan}></td>"
        try:
            match = abs(float(a_val) - float(c_val)) < 1e-6
        except (ValueError, TypeError):
            match = str(c_val) == str(a_val)
        cls = "match" if match else "diff"
        c_str = _fmt(c_val) if c_val != "" else ""
        a_str = _fmt(a_val) if a_val != "" else ""
        return f"<td class='num {cls}'>{c_str}</td><td class='num {cls}'{rowspan}>{a_str}</td>"

    if multi_seg and template_resolve:
        # Template-based multi-segment (Mode Choice): structural mapping only.
        # Coefficient comparison is done in the separate constants crosswalk table
        # because CTRAMP embeds coefficients in formulas (alt column is always 1.0).
        seg_names = [s["sheet_name"] for s in sheets]
        h = ("<table class='coeff mapped sortable'><thead><tr>"
             "<th>ASim Label</th><th>No.</th><th>Description</th>"
             "<th>CTRAMP Expression</th><th>ASim Expression</th>"
             "</tr></thead><tbody>")

        for asim_label, ctramp_ref in crosswalk.items():
            ctramp_nos = ctramp_ref if isinstance(ctramp_ref, list) else [ctramp_ref]
            ar = asim_by_label.get(asim_label)
            used_asim.add(asim_label)

            for i, ctramp_no in enumerate(ctramp_nos):
                used_ctramp.add(ctramp_no)
                cr_any = ctramp_by_sheet_no.get((seg_names[0], ctramp_no))
                show_asim = (i == 0)
                rowspan = f" rowspan='{len(ctramp_nos)}'" if show_asim and len(ctramp_nos) > 1 else ""

                body += "<tr>"
                if show_asim:
                    body += f"<td{rowspan}>{esc(asim_label)}</td>"
                body += f"<td>{ctramp_no}</td>"
                body += f"<td>{esc(cr_any['desc']) if cr_any else ''}</td>"
                body += f"<td>{esc(_ctramp_expr(cr_any))}</td>"
                if show_asim:
                    body += f"<td{rowspan}>{esc(ar['expr']) if ar else ''}</td>"
                body += "</tr>"

        # Unmatched CTRAMP rows
        for s in sheets:
            for r in s["rows"]:
                if r["no"] not in used_ctramp:
                    used_ctramp.add(r["no"])
                    body += (
                        f"<tr class='ctramp-only'><td></td><td>{r['no']}</td>"
                        f"<td>{esc(r['desc'])}</td><td>{esc(_ctramp_expr(r))}</td><td></td></tr>"
                    )

        # Unmatched ASim rows
        for r in spec["rows"]:
            if r["label"] not in used_asim:
                body += (
                    f"<tr class='asim-only'><td>{esc(r['label'])}</td><td></td>"
                    f"<td></td><td></td><td>{esc(r['expr'])}</td></tr>"
                )

    elif multi_seg:
        # Multi-segment table: one coeff column per segment
        seg_names = [s["sheet_name"] for s in sheets]
        coeff_hdrs = "".join(
            f"<th>CTRAMP {esc(sn)}</th><th>ASim {esc(alt)}</th><th>Diff</th>"
            for sn, alt in zip(seg_names, asim_alts)
        )
        h = ("<table class='coeff mapped sortable'><thead><tr>"
             "<th>ASim Label</th><th>No.</th><th>Description</th>"
             f"<th>CTRAMP Expression</th><th>ASim Expression</th>{coeff_hdrs}"
             "</tr></thead><tbody>")

        for asim_label, ctramp_ref in crosswalk.items():
            ctramp_nos = ctramp_ref if isinstance(ctramp_ref, list) else [ctramp_ref]
            ar = asim_by_label.get(asim_label)
            used_asim.add(asim_label)

            for i, ctramp_no in enumerate(ctramp_nos):
                used_ctramp.add(ctramp_no)
                cr_any = ctramp_by_sheet_no.get((seg_names[0], ctramp_no))
                show_asim = (i == 0)
                rowspan = f" rowspan='{len(ctramp_nos)}'" if show_asim and len(ctramp_nos) > 1 else ""

                body += "<tr>"
                if show_asim:
                    body += f"<td{rowspan}>{esc(asim_label)}</td>"
                body += f"<td>{ctramp_no}</td>"
                body += f"<td>{esc(cr_any['desc']) if cr_any else ''}</td>"
                body += f"<td>{esc(_ctramp_expr(cr_any))}</td>"
                if show_asim:
                    body += f"<td{rowspan}>{esc(ar['expr']) if ar else ''}</td>"

                # One pair of coeff columns per segment
                for sn, alt in zip(seg_names, asim_alts):
                    cr = ctramp_by_sheet_no.get((sn, ctramp_no))
                    c_val = _coeff_val(cr)
                    a_val = _coeff_for_alt(ar, alt) if ar else ""
                    body += f"<td class='num'>{_fmt(c_val) if c_val != '' else ''}</td>"
                    if show_asim:
                        body += f"<td class='num'{rowspan}>{_fmt(a_val) if a_val != '' else ''}</td>"
                    body += _diff_cell(c_val, a_val)
                body += "</tr>"

        # Unmatched CTRAMP rows (use first sheet as reference)
        for s in sheets:
            for r in s["rows"]:
                if r["no"] not in used_ctramp:
                    used_ctramp.add(r["no"])
                    body += (
                        f"<tr class='ctramp-only'><td></td><td>{r['no']}</td>"
                        f"<td>{esc(r['desc'])}</td><td>{esc(_ctramp_expr(r))}</td><td></td>"
                    )
                    for sn, alt in zip(seg_names, asim_alts):
                        cr = ctramp_by_sheet_no.get((sn, r["no"]))
                        c_val = _coeff_val(cr)
                        body += f"<td class='num'>{_fmt(c_val) if c_val != '' else ''}</td><td></td><td></td>"
                    body += "</tr>"

        # Unmatched ASim rows
        for r in spec["rows"]:
            if r["label"] not in used_asim:
                body += f"<tr class='asim-only'><td>{esc(r['label'])}</td><td></td><td></td><td></td><td>{esc(r['expr'])}</td>"
                for sn, alt in zip(seg_names, asim_alts):
                    a_val = _coeff_for_alt(r, alt)
                    body += f"<td></td><td class='num'>{_fmt(a_val) if a_val != '' else ''}</td><td></td>"
                body += "</tr>"

    elif multi_alt:
        # Multi-alt table: single sheet with per-alt coefficient columns
        alt_pairs = list(zip(ctramp_alts, asim_alts))
        coeff_hdrs = "".join(
            f"<th>CTRAMP {esc(a_alt)}</th><th>ASim {esc(a_alt)}</th><th>Diff</th>"
            for _, a_alt in alt_pairs
        )
        h = ("<table class='coeff mapped sortable'><thead><tr>"
             "<th>ASim Label</th><th>No.</th><th>Description</th>"
             f"<th>CTRAMP Expression</th><th>ASim Expression</th>{coeff_hdrs}"
             "</tr></thead><tbody>")

        for asim_label, ctramp_ref in crosswalk.items():
            ctramp_nos = ctramp_ref if isinstance(ctramp_ref, list) else [ctramp_ref]
            ar = asim_by_label.get(asim_label)
            used_asim.add(asim_label)

            for i, ctramp_no in enumerate(ctramp_nos):
                used_ctramp.add(ctramp_no)
                cr = ctramp_by_no.get(ctramp_no)
                show_asim = (i == 0)
                rowspan = f" rowspan='{len(ctramp_nos)}'" if show_asim and len(ctramp_nos) > 1 else ""

                body += "<tr>"
                if show_asim:
                    body += f"<td{rowspan}>{esc(asim_label)}</td>"
                body += f"<td>{ctramp_no}</td>"
                body += f"<td>{esc(cr['desc']) if cr else ''}</td>"
                body += f"<td>{esc(_ctramp_expr(cr))}</td>"
                if show_asim:
                    body += f"<td{rowspan}>{esc(ar['expr']) if ar else ''}</td>"

                for c_alt, a_alt in alt_pairs:
                    c_val = _coeff_for_alt(cr, c_alt)
                    a_val = _coeff_for_alt(ar, a_alt) if ar else ""
                    body += f"<td class='num'>{_fmt(c_val) if c_val != '' else ''}</td>"
                    if show_asim:
                        body += f"<td class='num'{rowspan}>{_fmt(a_val) if a_val != '' else ''}</td>"
                    body += _diff_cell(c_val, a_val)
                body += "</tr>"

        # Unmatched CTRAMP rows
        for r in sheets[0]["rows"]:
            if r["no"] not in used_ctramp:
                used_ctramp.add(r["no"])
                body += (
                    f"<tr class='ctramp-only'><td></td><td>{r['no']}</td>"
                    f"<td>{esc(r['desc'])}</td><td>{esc(_ctramp_expr(r))}</td><td></td>"
                )
                for c_alt, a_alt in alt_pairs:
                    c_val = _coeff_for_alt(r, c_alt)
                    body += f"<td class='num'>{_fmt(c_val) if c_val != '' else ''}</td><td></td><td></td>"
                body += "</tr>"

        # Unmatched ASim rows
        for r in spec["rows"]:
            if r["label"] not in used_asim:
                body += f"<tr class='asim-only'><td>{esc(r['label'])}</td><td></td><td></td><td></td><td>{esc(r['expr'])}</td>"
                for c_alt, a_alt in alt_pairs:
                    a_val = _coeff_for_alt(r, a_alt)
                    body += f"<td></td><td class='num'>{_fmt(a_val) if a_val != '' else ''}</td><td></td>"
                body += "</tr>"

    else:
        # Single-segment table
        h = ("<table class='coeff mapped sortable'><thead><tr>"
             "<th>ASim Label</th><th>No.</th><th>Description</th>"
             "<th>CTRAMP Expression</th><th>ASim Expression</th>"
             "<th>CTRAMP Coeff</th><th>ASim Coeff</th><th>Diff</th>"
             "</tr></thead><tbody>")

        # Matched rows (driven by crosswalk: asim_label → ctramp_no or [ctramp_nos])
        for asim_label, ctramp_ref in crosswalk.items():
            ctramp_nos = ctramp_ref if isinstance(ctramp_ref, list) else [ctramp_ref]
            ar = asim_by_label.get(asim_label)
            used_asim.add(asim_label)

            a_coeff = _coeff_val(ar)

            for i, ctramp_no in enumerate(ctramp_nos):
                cr = ctramp_by_no.get(ctramp_no)
                used_ctramp.add(ctramp_no)

                c_coeff = _coeff_val(cr)

                cls = ""
                if cr and ar:
                    try:
                        cls = "match" if abs(float(c_coeff) - float(a_coeff)) < 1e-6 else "diff"
                    except (ValueError, TypeError):
                        cls = "diff"
                elif cr:
                    cls = "ctramp-only"
                elif ar:
                    cls = "asim-only"

                # Show ASim label/expr/coeff only on the first row of a group
                show_asim = (i == 0)
                rowspan = f" rowspan='{len(ctramp_nos)}'" if show_asim and len(ctramp_nos) > 1 else ""

                body += f"<tr class='{cls}'>"
                if show_asim:
                    body += f"<td{rowspan}>{esc(asim_label)}</td>"
                body += (
                    f"<td>{cr['no'] if cr else ''}</td>"
                    f"<td>{esc(cr['desc']) if cr else ''}</td>"
                    f"<td>{esc(_ctramp_expr(cr))}</td>"
                )
                if show_asim:
                    body += f"<td{rowspan}>{esc(ar['expr']) if ar else ''}</td>"
                body += (
                    f"<td class='num'>{_fmt(c_coeff) if c_coeff != '' else ''}</td>"
                )
                if show_asim:
                    body += f"<td class='num'{rowspan}>{_fmt(a_coeff) if a_coeff != '' else ''}</td>"
                body += (
                    f"{_diff_cell(c_coeff, a_coeff)}"
                    "</tr>"
                )

        # Unmatched CTRAMP rows
        for s in sheets:
            for r in s["rows"]:
                if r["no"] not in used_ctramp:
                    c_coeff = _coeff_val(r)
                    body += (
                        f"<tr class='ctramp-only'>"
                        f"<td></td>"
                        f"<td>{r['no']}</td>"
                        f"<td>{esc(r['desc'])}</td>"
                        f"<td>{esc(_ctramp_expr(r))}</td>"
                        f"<td></td>"
                        f"<td class='num'>{_fmt(c_coeff) if c_coeff != '' else ''}</td>"
                        f"<td></td><td></td></tr>"
                    )

        # Unmatched ActivitySim rows
        for r in spec["rows"]:
            if r["label"] not in used_asim:
                a_coeff = _coeff_val(r)
                body += (
                    f"<tr class='asim-only'>"
                    f"<td>{esc(r['label'])}</td>"
                    f"<td></td><td>{esc(r['desc'])}</td><td></td>"
                    f"<td>{esc(r['expr'])}</td>"
                    f"<td></td>"
                    f"<td class='num'>{_fmt(a_coeff) if a_coeff != '' else ''}</td>"
                    f"<td></td></tr>"
                )

    legend = (
        "<div class='legend'>"
        "<span class='swatch match'></span> Match "
        "<span class='swatch diff'></span> Differs "
        "<span class='swatch ctramp-only'></span> CTRAMP only "
        "<span class='swatch asim-only'></span> ASim only"
        "</div>"
    )

    # Render explanatory notes for many-to-one or unmatched rows
    notes_dict = NOTES.get(name, {})
    notes_html = ""
    if notes_dict:
        notes_html = "<details class='mapping-notes'><summary>Mapping Notes</summary><dl>"
        for label, note in notes_dict.items():
            notes_html += f"<dt><code>{esc(label)}</code></dt><dd>{esc(note)}</dd>"
        notes_html += "</dl></details>"

    return f"<h3>Mapped Comparison</h3>{legend}<div class='mapped-wrap'>{h}{body}</tbody></table></div>{notes_html}"


def _constants_table(
    tokens_by_sheet: dict[str, dict[str, str]],
    template_resolve: dict[str, dict[str, float]],
    sheet_names: list[str],
    yaml_constants: dict[str, float] | None = None,
    asim_spec: dict | None = None,
) -> str:
    """Render a constants crosswalk comparing CTRAMP token values to ASim coefficients.

    For each CTRAMP token (c_xxx), resolves the numeric value per purpose sheet and
    compares to the ASim template-resolved coefficient (coef_xxx) or YAML constant.

    YAML *_multiplier* constants are shown as IVT multipliers on both sides:
    - CTRAMP: extract M from ``M * c_ivt`` or divide pre-resolved value by c_ivt.
    - ASim: YAML value x any template coefficients embedded in the expression.
    """
    if not tokens_by_sheet or not template_resolve:
        return ""

    purposes = [SHEET_TO_PURPOSE.get(sn, sn.lower()) for sn in sheet_names]
    yaml_constants = yaml_constants or {}
    asim_spec = asim_spec or {}

    # -- Pre-scan ASim expressions to find buried template coefficient factors --
    # For each YAML constant referenced in an expression, find any co-multiplied
    # template coefficients (coef_*) and compute their product per purpose.
    # e.g. "@coef_biketimeshort_multiplier * biketimelong_multiplier * (...)" ->
    #   extra_factors["biketimelong_multiplier"] = {"work": 4.0, "school": 4.0, ...}
    extra_factors: dict[str, dict[str, float]] = {}
    for row in asim_spec.get("rows", []):
        expr = row.get("expr", "")
        for yaml_name in yaml_constants:
            if yaml_name not in expr:
                continue
            # Find co-multiplied template coefficients (coef_* patterns)
            coef_refs = re.findall(r'\bcoef_\w+', expr)
            coef_refs = [c for c in coef_refs if c != yaml_name]
            if not coef_refs:
                continue
            factors_for_purpose: dict[str, float] = {}
            for purpose in purposes:
                product = 1.0
                for cref in coef_refs:
                    tpl_vals = template_resolve.get(cref, {})
                    val = tpl_vals.get(purpose)
                    if val is not None:
                        product *= val
                factors_for_purpose[purpose] = product
            if any(abs(v - 1.0) > 1e-10 for v in factors_for_purpose.values()):
                extra_factors[yaml_name] = factors_for_purpose

    # Map CTRAMP token names to ASim coefficient names.
    # Priority: template coef_xxx > template coef_xxx_multiplier > YAML constant
    def _find_asim(token: str) -> tuple[str, str, float | None]:
        """Return (asim_name, source, yaml_value_or_None).

        source is 'template', 'yaml', or 'none'.
        """
        base = "coef_" + token[2:]
        if base in template_resolve:
            return base, "template", None
        mult = base + "_multiplier"
        if mult in template_resolve:
            return mult, "template", None
        # Check YAML constants mapping
        yaml_name = TOKEN_TO_YAML.get(token)
        if yaml_name and yaml_name in yaml_constants:
            return yaml_name, "yaml", yaml_constants[yaml_name]
        return base, "none", None

    # Collect all token names across sheets (union)
    all_tokens: list[str] = []
    seen: set[str] = set()
    for sn in sheet_names:
        for t in tokens_by_sheet.get(sn, {}):
            if t not in seen:
                all_tokens.append(t)
                seen.add(t)

    if not all_tokens:
        return ""

    # Extract multiplier from CTRAMP formula "M * c_ivt" → M (float)
    # Also handles "(M*c_ivt)/vot" → M (the cost coefficient formula).
    def _extract_multiplier(raw: str) -> float | None:
        m = re.match(r"^\s*([-\d.]+)\s*\*\s*c_ivt\s*$", raw)
        if m:
            return float(m.group(1))
        m = re.match(r"^\s*c_ivt\s*\*\s*([-\d.]+)\s*$", raw)
        if m:
            return float(m.group(1))
        # Handle "(M*c_ivt)/vot" or "(M*c_ivt)/valueOfTime" pattern used by c_cost
        m = re.match(r"^\s*\(\s*([-\d.]+)\s*\*\s*c_ivt\s*\)\s*/\s*\w+\s*$", raw)
        if m:
            return float(m.group(1))
        return None

    # Resolve CTRAMP token to IVT multiplier for YAML _multiplier constants,
    # or to the effective coefficient for template/direct constants.
    # For template _multiplier coefficients, auto-detect whether ASim stores
    # the raw multiplier M (IVT sub-mode tokens) or the pre-resolved product
    # M × c_ivt (demographic tokens like c_hhsize1_sr).
    def _resolve_ctramp(
        token: str, sheet: str, source: str, is_mult: bool, a_val,
        asim_name_: str = "",
    ) -> float | str:
        tokens = tokens_by_sheet.get(sheet, {})
        raw = tokens.get(token, "")
        if not raw:
            return ""

        # Determine if we should display as an IVT multiplier.
        # Always true for YAML _multiplier constants.
        show_as_mult = is_mult

        # Try as formula "M * c_ivt" (or "(M*c_ivt)/var") first
        mult = _extract_multiplier(raw)

        # For template _multiplier coefficients, auto-detect: compare the ASim
        # value against both M (raw multiplier) and M×c_ivt (product).  If ASim
        # is closer to M, it's a genuine IVT multiplier; otherwise it's a
        # pre-resolved product (demographic tokens).
        if (not show_as_mult
                and source == "template"
                and asim_name_.endswith("_multiplier")
                and mult is not None
                and a_val != ""):
            try:
                a_float = float(a_val)
                c_ivt_raw = tokens.get("c_ivt", "")
                c_ivt_val = float(c_ivt_raw) if c_ivt_raw else 0.0
                if abs(c_ivt_val) > 1e-10:
                    product = mult * c_ivt_val
                    if abs(a_float - mult) < abs(a_float - product):
                        show_as_mult = True
            except (ValueError, TypeError):
                pass

        if mult is not None:
            if show_as_mult:
                return mult  # Return the IVT multiplier directly
            c_ivt_raw = tokens.get("c_ivt", "")
            try:
                return mult * float(c_ivt_raw)
            except (ValueError, TypeError):
                return raw
        # Pre-resolved numeric
        try:
            val = float(raw)
        except ValueError:
            return raw
        if show_as_mult and token != "c_ivt":
            # Derive IVT multiplier by dividing by c_ivt
            c_ivt_raw = tokens.get("c_ivt", "")
            try:
                c_ivt_val = float(c_ivt_raw)
                if abs(c_ivt_val) > 1e-10:
                    return val / c_ivt_val
            except (ValueError, TypeError):
                pass
        # For template source, try both raw and multiplier to match ASim
        if source == "template" and a_val != "":
            try:
                a_float = float(a_val)
                if abs(val - a_float) < 1e-4:
                    return val
                if token != "c_ivt":
                    c_ivt_raw = tokens.get("c_ivt", "")
                    c_ivt_val = float(c_ivt_raw)
                    if abs(c_ivt_val) > 1e-10:
                        derived = val / c_ivt_val
                        if abs(derived - a_float) < 1e-4:
                            return derived
            except (ValueError, TypeError):
                pass
        return val

    # Build table header
    hdr_cells = "".join(
        f"<th colspan='2'>{esc(sn)}</th>" for sn in sheet_names
    )
    h = ("<table class='coeff mapped sortable'><thead><tr>"
         f"<th>CTRAMP Token</th><th>ASim Coefficient</th>{hdr_cells}"
         "</tr><tr><th></th><th></th>"
         + "".join("<th>CTRAMP</th><th>ASim</th>" for _ in sheet_names)
         + "</tr></thead><tbody>")

    body = ""
    n_match = 0
    n_diff = 0
    n_total = 0

    for token in all_tokens:
        asim_name, source, yaml_val = _find_asim(token)
        asim_map = template_resolve.get(asim_name, {})
        is_mult = source == "yaml" and asim_name.endswith("_multiplier")
        row_cells = ""
        any_val = False
        for sn, purpose in zip(sheet_names, purposes):
            # Determine ASim comparison value.
            # For _multiplier YAML constants, show as IVT multiplier:
            #   YAML value × any buried template coefficient factors.
            # Both sides are now "× IVT" — the raw multiplier before c_ivt is applied.
            if source == "yaml":
                if is_mult and yaml_val is not None:
                    ef = extra_factors.get(asim_name, {}).get(purpose, 1.0)
                    a_val = yaml_val * ef
                    if abs(ef - 1.0) > 1e-10:
                        a_ann = f"<br><small>({_fmt(yaml_val)} x {_fmt(ef)})</small>"
                    else:
                        a_ann = ""
                else:
                    a_val = yaml_val if yaml_val is not None else ""
                    a_ann = ""
            else:
                a_val = asim_map.get(purpose, "")
                a_ann = ""
            c_val = _resolve_ctramp(token, sn, source, is_mult, a_val, asim_name)
            if c_val == "" and a_val == "":
                row_cells += "<td class='num'></td><td class='num'></td>"
                continue
            any_val = True
            if a_val == "":
                # No ASim equivalent — show CTRAMP value as informational (neutral styling)
                c_str = _fmt(c_val) if c_val != "" else ""
                row_cells += f"<td class='num'>{c_str}</td><td class='num'></td>"
                continue
            n_total += 1
            try:
                match = abs(float(c_val) - float(a_val)) < 1e-6
            except (ValueError, TypeError):
                match = False
            cls = "match" if match else "diff"
            if match:
                n_match += 1
            else:
                n_diff += 1
            c_str = _fmt(c_val) if c_val != "" else ""
            a_str = (_fmt(a_val) + a_ann) if a_val != "" else ""
            row_cells += f"<td class='num {cls}'>{c_str}</td><td class='num {cls}'>{a_str}</td>"
        if any_val:
            if source == "template":
                indicator = "✓" if asim_map else "—"
            elif source == "yaml":
                indicator = "✓ (x IVT)" if is_mult else "✓ (YAML)"
            else:
                indicator = "—"
            # Check if this is a known genuine difference
            known_note = ""
            if source == "yaml" and asim_name in KNOWN_TRIP_MC_DIFFS:
                _, _, explanation = KNOWN_TRIP_MC_DIFFS[asim_name]
                known_note = (
                    f"<br><small style='color:#b45309' title='{esc(explanation)}'>"
                    f"&#9888; {esc(explanation)}</small>"
                )
            body += (
                f"<tr><td><code>{esc(token)}</code>{known_note}</td>"
                f"<td><code>{esc(asim_name)}</code> {indicator}</td>"
                f"{row_cells}</tr>"
            )

    summary = (
        f"<div style='margin:8px 0;font-size:13px'>"
        f"Constants compared: {n_total} cells &bull; "
        f"<span style='color:green'>{n_match} match</span> &bull; "
        f"<span style='color:red'>{n_diff} differ</span> &bull; "
        f"Unresolved formulas shown as raw text"
        f"</div>"
        f"<div style='margin:4px 0;font-size:12px;color:#555'>"
        f"<b>x IVT rows:</b> Both sides normalized to IVT multipliers "
        f"(the factor M in M &times; coef_ivt). CTRAMP pre-resolves M &times; c_ivt into a single token; "
        f"ASim stores M in YAML and applies coef_ivt via the alt column. "
        f"Where ASim expressions embed additional template coefficients (e.g. "
        f"<code>coef_biketimeshort_multiplier</code>), these are factored in and "
        f"shown in the <small>(val &times; factor)</small> annotation."
        f"</div>"
    )

    legend = (
        "<div class='legend'>"
        "<span class='swatch match'></span> Match "
        "<span class='swatch diff'></span> Differs"
        "</div>"
    )

    # Build a known-differences annotation if any diffs match KNOWN_TRIP_MC_DIFFS
    known_html = ""
    any_known = any(
        TOKEN_TO_YAML.get(t) in KNOWN_TRIP_MC_DIFFS
        for t in all_tokens
        if TOKEN_TO_YAML.get(t)
    )
    if any_known and n_diff > 0:
        items = ""
        for yaml_name, (c_mult, a_mult, explanation) in KNOWN_TRIP_MC_DIFFS.items():
            ratio = a_mult / c_mult if c_mult != 0 else float("inf")
            items += (
                f"<tr><td><code>{esc(yaml_name)}</code></td>"
                f"<td>{_fmt(c_mult)}</td><td>{_fmt(a_mult)}</td>"
                f"<td>{ratio:.1f}x</td>"
                f"<td>{esc(explanation)}</td></tr>"
            )
        known_html = (
            "<details open style='margin:12px 0'>"
            "<summary style='font-weight:bold;cursor:pointer'>"
            "&#9888; Known Genuine Differences (Trip MC)</summary>"
            "<div style='margin:8px 0;font-size:12px;color:#555'>"
            "These IVT multipliers differ between CTRAMP and ASim Trip MC. "
            "The variable definitions and input data are identical in both systems &mdash; "
            "same formula, same tazData/land_use fields. "
            "Both systems use NL=3 nested logit with identical nesting coefficients. "
            "These are intentional re-calibrations in the ASim migration, NOT data-scaling artifacts."
            "</div>"
            "<table class='coeff' style='font-size:12px'>"
            "<thead><tr><th>YAML Constant</th><th>CTRAMP</th><th>ASim</th>"
            "<th>Ratio</th><th>Note</th></tr></thead><tbody>"
            f"{items}</tbody></table></details>"
        )

    return (f"<h3>Constants Crosswalk (Token Section)</h3>{legend}{summary}"
            f"<div class='mapped-wrap'>{h}{body}</tbody></table></div>"
            f"{known_html}")


# -- HTML rendering ------------------------------------------------------------

def _fmt(v: float | str) -> str:
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1000:  # noqa: PLR2004
            return f"{int(v)}"
        return f"{v:.4f}"
    return esc(str(v))


def _uec_table(sheet: dict) -> str:
    h = ("<table class='coeff'><thead><tr>"
         "<th>No</th><th>Description</th><th>Filter</th><th>Formula</th>"
         + "".join(f"<th>{esc(a)}</th>" for a in sheet["alt_names"])
         + "</tr></thead><tbody>")
    body = ""
    for r in sheet["rows"]:
        cells = "".join(
            f"<td class='num'>{_fmt(r['coeffs'][a])}</td>" if a in r["coeffs"] else "<td></td>"
            for a in sheet["alt_names"]
        )
        body += (f"<tr><td>{r['no']}</td><td>{esc(r['desc'])}</td>"
                 f"<td>{esc(r['filter'])}</td><td>{esc(r['formula'])}</td>{cells}</tr>")
    return f"<h3>CTRAMP: {esc(sheet['sheet_name'])}</h3>{h}{body}</tbody></table>"


def _asim_table(spec: dict) -> str:
    alts = spec["alt_names"] or ["coeff"]
    h = ("<table class='coeff'><thead><tr>"
         "<th>Label</th><th>Description</th><th>Expression</th>"
         + "".join(f"<th>{esc(a)}</th>" for a in alts)
         + "</tr></thead><tbody>")
    body = ""
    for r in spec["rows"]:
        cells = "".join(
            f"<td class='num'>{_fmt(r['coeffs'][a])}</td>" if a in r["coeffs"] else "<td></td>"
            for a in alts
        )
        body += (f"<tr><td>{esc(r['label'])}</td><td>{esc(r['desc'])}</td>"
                 f"<td>{esc(r['expr'])}</td>{cells}</tr>")
    return f"<h3>ActivitySim Spec</h3>{h}{body}</tbody></table>"


def _size_terms_table(ctramp_dir: Path, asim_dirs: list[Path], st_cfg: dict) -> str:
    def _read(p: Path | None) -> list[dict]:
        if not p or not p.exists():
            return []
        with p.open(encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    cr = _read(ctramp_dir / st_cfg["ctramp"])
    ar = _read(_resolve(asim_dirs, st_cfg["asim"]))
    if not cr and not ar:
        return "<p>No size-term data.</p>"

    def _ctramp_key(row: dict) -> str:
        p = (row.get("purpose") or "").strip().lower()
        s = (row.get("segment") or "").strip().lower()
        mapped = SIZE_TERMS_CROSSWALK.get((p, s))
        if mapped:
            return f"{mapped[0]}|{mapped[1]}"
        return f"{p}|{s}"

    def _asim_key(row: dict) -> str:
        p = (row.get("model_selector") or "").strip().lower()
        s = (row.get("segment") or "").strip().lower()
        return f"{p}|{s}"

    def _display_label(row: dict) -> str:
        p = row.get("purpose") or row.get("model_selector") or ""
        s = row.get("segment") or ""
        return f"{p} / {s}"

    sample = cr[0] if cr else ar[0]
    skip = {"purpose", "segment", "model_selector"}
    vcols = [k for k in sample if k.lower() not in skip]

    # Build indexed dicts
    cm: dict[str, dict] = {}
    for r in cr:
        cm[_ctramp_key(r)] = r
    am: dict[str, dict] = {}
    for r in ar:
        am[_asim_key(r)] = r
    keys = list(dict.fromkeys(list(cm) + list(am)))

    h = ("<table class='coeff mapped'><thead><tr>"
         "<th>CTRAMP Segment</th><th>ASim Segment</th>"
         + "".join(f"<th>{esc(v)}</th><th>CTRAMP</th><th>ASim</th><th>Diff</th>" for v in vcols)
         + "</tr></thead><tbody>")
    body = ""
    for k in keys:
        c, a = cm.get(k, {}), am.get(k, {})
        c_label = _display_label(c) if c else ""
        a_label = _display_label(a) if a else ""
        cells = ""
        for v in vcols:
            cv, av = c.get(v, ""), a.get(v, "")
            try:
                cf, af = float(cv), float(av)
                diff = af - cf
                cls = "match" if abs(diff) < 1e-6 else "diff"
                dcell = f"<td class='num {cls}'>{diff:+.6g}</td>" if abs(diff) >= 1e-6 else "<td class='num match'>0</td>"
                cells += f"<td class='num {cls}'>{cf:.6g}</td><td class='num {cls}'>{af:.6g}</td>{dcell}"
            except (ValueError, TypeError):
                cells += f"<td class='num'>{esc(str(cv))}</td><td class='num'>{esc(str(av))}</td><td></td>"
        cls = ""
        if c and not a:
            cls = " class='ctramp-only'"
        elif a and not c:
            cls = " class='asim-only'"
        body += f"<tr{cls}><td>{esc(c_label)}</td><td>{esc(a_label)}</td>{cells}</tr>"

    legend = (
        "<div class='legend'>"
        "<span class='swatch match'></span> Match "
        "<span class='swatch diff'></span> Differs "
        "<span class='swatch ctramp-only'></span> CTRAMP only "
        "<span class='swatch asim-only'></span> ASim only"
        "</div>"
    )
    note = (
        "<p class='mapping-note'><em>Note:</em> ASim-only <code>trip/*</code> rows are used by "
        "ActivitySim's <code>trip_destination</code> model. CTRAMP handles intermediate stop "
        "locations via a separate mechanism outside the size terms CSV.</p>"
    )
    return f"<h3>Size Terms Comparison</h3>{legend}{note}<div class='mapped-wrap'>{h}{body}</tbody></table></div>"


CSS = """\
<style>
body { font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f8f9fa; }
h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 8px; }
h3 { color: #5a6c7d; margin-top: 25px; }
.tab-bar { display: flex; flex-wrap: wrap; gap: 4px; }
.tab-bar button { padding: 8px 16px; border: 1px solid #ccc; border-bottom: none;
  background: #e8e8e8; cursor: pointer; border-radius: 4px 4px 0 0; font-size: 14px; }
.tab-bar button.active { background: #fff; font-weight: bold; }
.tab-content { display: none; padding: 20px; border: 1px solid #ccc; background: #fff; }
.tab-content.active { display: block; }
table.coeff { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 13px; }
table.coeff th, table.coeff td { border: 1px solid #ddd; padding: 4px 8px; }
table.coeff th { background: #f0f0f0; position: sticky; top: 0; }
table.coeff tr:nth-child(even) { background: #fafafa; }
table.coeff td.num { text-align: right; font-family: Consolas, monospace; }
table.coeff td.match { background: #d4edda; }
table.coeff td.diff { background: #f8d7da; }
table.mapped tr.match td { background: #d4edda; }
table.mapped tr.diff td { background: #f8d7da; }
table.mapped tr.ctramp-only td { background: #d6eaf8; }
table.mapped tr.asim-only td { background: #fdebd0; }
.mapped-wrap { overflow-x: auto; max-width: 100%; }
table.mapped td { white-space: nowrap; font-size: 12px; max-width: 180px;
  overflow: hidden; text-overflow: ellipsis; }
table.mapped td:nth-child(1) { font-family: Consolas, monospace; max-width: 260px; }
table.mapped td:nth-child(3), table.mapped td:nth-child(4),
table.mapped td:nth-child(5) { max-width: 200px; }
table.mapped th { font-size: 12px; white-space: nowrap; }
table.sortable th { cursor: pointer; user-select: none; }
table.sortable th[data-dir='asc']::after { content: ' \\25B2'; font-size: 10px; }
table.sortable th[data-dir='desc']::after { content: ' \\25BC'; font-size: 10px; }
.legend { margin: 8px 0; font-size: 13px; }
.legend .swatch { display: inline-block; width: 14px; height: 14px; vertical-align: middle;
  border: 1px solid #aaa; margin-right: 3px; margin-left: 10px; }
.legend .swatch.match { background: #d4edda; }
.legend .swatch.diff { background: #f8d7da; }
.legend .swatch.ctramp-only { background: #d6eaf8; }
.legend .swatch.asim-only { background: #fdebd0; }
.mapping-notes { margin: 10px 0; font-size: 13px; }
.mapping-notes summary { cursor: pointer; font-weight: bold; color: #555; }
.mapping-notes dl { margin: 8px 0 0 10px; }
.mapping-notes dt { font-weight: bold; margin-top: 6px; }
.mapping-notes dd { margin: 2px 0 0 20px; color: #555; }
.file-paths { margin: 10px 0; padding: 10px 15px; background: #f5f5f5; border-radius: 4px;
  font-size: 13px; line-height: 1.6; border: 1px solid #ddd; }
.file-paths code { background: #e8e8e8; padding: 2px 5px; border-radius: 3px; font-size: 12px; }
.toggle-bar { display: flex; align-items: center; gap: 12px; margin: 12px 0;
  padding: 8px 16px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px;
  font-size: 14px; }
.toggle-bar label { cursor: pointer; display: flex; align-items: center; gap: 6px; }
.toggle-bar input[type=checkbox] { width: 18px; height: 18px; }
.toggle-bar .overlay-path { font-family: Consolas, monospace; font-size: 12px; color: #856404; }
</style>"""


def build_report(cfg: dict) -> Path:
    repo = Path(cfg["repo_root"])
    cc = cfg["coefficient_comparison"]
    ctramp_dir = repo / cc["ctramp_model_dir"]
    # ActivitySim config dirs in priority order (scenario overrides first)
    asim_dirs = [repo / d for d in cc["asim_configs_dirs"]]
    out = Path(cfg["output_dir"]) / "coefficient_comparison.html"

    # Build submodel → stage mapping from stage definitions
    stages = cfg.get("stages", [])
    submodel_stages: dict[str, str] = {}
    for i, st in enumerate(stages, 1):
        for csm in st.get("calibration_submodels", []):
            # Map calibration submodel names to coefficient comparison tab names
            csm_to_tab = {
                "work_school_location": ["Workplace Location", "School Location"],
                "auto_ownership": ["Auto Ownership"],
                "daily_activity_pattern": ["CDAP"],
                "tour_mode_choice": ["Tour Mode Choice"],
                "trip_mode_choice": ["Trip Mode Choice"],
                "nonwork_dest_choice": [],
            }
            for tab_name in csm_to_tab.get(csm, []):
                if tab_name not in submodel_stages:
                    submodel_stages[tab_name] = f"Stage {i} ({st['name']})"

    tabs: list[tuple[str, str]] = []

    def _build_tab_body(sm: dict, dirs: list[Path]) -> str:
        """Generate one tab's comparison content using the given ASim config dirs."""
        sheets = read_uec_sheets(ctramp_dir, sm["ctramp_file"], sm["ctramp_sheets"])
        spec = read_asim_spec(dirs, sm["asim_spec"], sm["asim_coefficients"])

        # File paths banner
        spec_resolved = _resolve(dirs, sm["asim_spec"])
        coeff_resolved = _resolve(dirs, sm["asim_coefficients"])
        ctramp_path = cc["ctramp_model_dir"] + "/" + sm["ctramp_file"]
        stage_info = submodel_stages.get(sm["name"], "")
        stage_line = (
            f"<br><b>Ablation impact:</b> Introduced at {esc(stage_info)},"
            f" affects all subsequent stages"
        ) if stage_info else ""
        paths_html = (
            f"<div class='file-paths'>"
            f"<b>CTRAMP:</b> <code>{esc(ctramp_path)}</code> "
            f"[{', '.join(sm['ctramp_sheets'])}]<br>"
            f"<b>ActivitySim spec:</b> <code>"
            f"{esc(str(spec_resolved.relative_to(repo)) if spec_resolved else 'NOT FOUND')}"
            f"</code><br>"
            f"<b>ActivitySim coeff:</b> <code>"
            f"{esc(str(coeff_resolved.relative_to(repo)) if coeff_resolved else 'NOT FOUND')}"
            f"</code>"
            f"{stage_line}"
            f"</div>"
        )

        # 1:1 mapped comparison
        tpl_file = sm.get("asim_coefficients_template")
        tpl_resolve = None
        if tpl_file:
            tpl_resolve = _read_template(dirs, tpl_file, sm["asim_coefficients"])
        mapped_html = _mapped_table(sm["name"], sheets, spec, template_resolve=tpl_resolve)

        # Constants crosswalk for template-based models
        constants_html = ""
        if tpl_file and tpl_resolve:
            tokens_by_sheet = read_uec_tokens(
                ctramp_dir, sm["ctramp_file"], sm["ctramp_sheets"]
            )
            yaml_file = sm["asim_spec"].replace(".csv", ".yaml")
            yaml_consts = _read_yaml_constants(dirs, yaml_file)
            constants_html = _constants_table(
                tokens_by_sheet, tpl_resolve, sm["ctramp_sheets"], yaml_consts,
                asim_spec=spec,
            )

        # Original raw tables
        parts = [
            f"<div style='margin:10px 0;padding:10px;border-left:3px solid #3498db'>"
            f"{_uec_table(s)}</div>"
            for s in sheets
        ]
        if spec["rows"]:
            parts.append(
                f"<div style='margin:10px 0;padding:10px;"
                f"border-left:3px solid #e67e22'>{_asim_table(spec)}</div>"
            )
        n_uec = sum(len(s["rows"]) for s in sheets)
        summary = (
            f"<div style='margin:10px 0;padding:10px 15px;background:#eef;"
            f"border-radius:4px;font-size:14px'>"
            f"CTRAMP: {n_uec} rows / {len(sheets)} sheet(s) &bull; "
            f"ActivitySim: {len(spec['rows'])} rows</div>"
        )
        return paths_html + constants_html + mapped_html + summary + "\n".join(parts)

    # Determine overlay: first dir is the scenario overlay, rest are base.
    has_overlay = len(asim_dirs) > 1
    asim_dirs_base = asim_dirs[1:] if has_overlay else asim_dirs
    overlay_label = asim_dirs[0].relative_to(repo) if has_overlay else None

    for sm in cc["submodels"]:
        log.info("Processing %s ...", sm["name"])

        # Always generate with the full config stack (overlay first)
        body_overlay = _build_tab_body(sm, asim_dirs)

        if has_overlay:
            body_base = _build_tab_body(sm, asim_dirs_base)
            identical = body_overlay == body_base
            ident_note = (
                "<div style='padding:6px 12px;background:#e8f5e9;border:1px solid #a5d6a7;"
                "border-radius:4px;font-size:13px;margin-bottom:8px;color:#2e7d32'>"
                "&#x2714; No overlay differences — this submodel uses base configs only.</div>"
            ) if identical else ""
            tab_body = (
                f"<div class='layer-overlay'>{ident_note}{body_overlay}</div>"
                f"<div class='layer-base' style='display:none'>{body_base}</div>"
            )
        else:
            tab_body = body_overlay

        tabs.append((sm["name"], tab_body))

    if "size_terms" in cc:
        st_overlay = _size_terms_table(ctramp_dir, asim_dirs, cc["size_terms"])
        if has_overlay:
            st_base = _size_terms_table(ctramp_dir, asim_dirs_base, cc["size_terms"])
            identical = st_overlay == st_base
            ident_note = (
                "<div style='padding:6px 12px;background:#e8f5e9;border:1px solid #a5d6a7;"
                "border-radius:4px;font-size:13px;margin-bottom:8px;color:#2e7d32'>"
                "&#x2714; No overlay differences — this submodel uses base configs only.</div>"
            ) if identical else ""
            st_body = (
                f"<div class='layer-overlay'>{ident_note}{st_overlay}</div>"
                f"<div class='layer-base' style='display:none'>{st_base}</div>"
            )
        else:
            st_body = st_overlay
        tabs.append(("Size Terms", st_body))

    buttons, panels = [], []
    for i, (title, content) in enumerate(tabs):
        active = " active" if i == 0 else ""
        buttons.append(f"<button class='{active.strip()}' "
                       f"onclick=\"showTab('t{i}')\">{esc(title)}</button>")
        panels.append(f"<div id='t{i}' class='tab-content{active}'>{content}</div>")

    # Build overlay toggle bar (only when overlay dir exists)
    toggle_html = ""
    if has_overlay:
        toggle_html = (
            f"<div class='toggle-bar'>"
            f"<label><input type='checkbox' id='overlayToggle' checked "
            f"onchange='toggleOverlay(this.checked)'>"
            f"<b>Include scenario overlay</b></label>"
            f"<span class='overlay-path'>{esc(str(overlay_label))}</span>"
            f"<span style='color:#666;font-size:12px'>"
            f"(uncheck to see base configs only)</span>"
            f"</div>"
        )

    html_doc = f"""\
<!DOCTYPE html><html><head><meta charset="utf-8">
<title>CTRAMP vs ActivitySim Coefficients</title>{CSS}</head><body>
<h1>CTRAMP vs ActivitySim Coefficient Comparison</h1>
{toggle_html}
<div class="tab-bar">{"".join(buttons)}</div>
{"".join(panels)}
<script>
function showTab(id){{
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab-bar button').forEach(b=>b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  event.target.classList.add('active');
}}
function toggleOverlay(on){{
  document.querySelectorAll('.layer-overlay').forEach(el=>{{
    el.style.display=on?'':'none';
  }});
  document.querySelectorAll('.layer-base').forEach(el=>{{
    el.style.display=on?'none':'';
  }});
}}
document.querySelectorAll('table.sortable th').forEach(th=>{{
  th.style.cursor='pointer';
  th.addEventListener('click',()=>{{
    const table=th.closest('table'), tbody=table.querySelector('tbody');
    const idx=[...th.parentNode.children].indexOf(th);
    const rows=[...tbody.querySelectorAll('tr')];
    const dir=th.dataset.dir==='asc'?'desc':'asc';
    th.parentNode.querySelectorAll('th').forEach(h=>delete h.dataset.dir);
    th.dataset.dir=dir;
    rows.sort((a,b)=>{{
      let av=a.children[idx]?.textContent||'', bv=b.children[idx]?.textContent||'';
      let an=parseFloat(av), bn=parseFloat(bv);
      if(!isNaN(an)&&!isNaN(bn)) return dir==='asc'?an-bn:bn-an;
      return dir==='asc'?av.localeCompare(bv):bv.localeCompare(av);
    }});
    rows.forEach(r=>tbody.appendChild(r));
  }});
}});
</script></body></html>"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding="utf-8")
    log.info("Report: %s", out)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else CONFIG_PATH
    build_report(yaml.safe_load(config_path.read_text()))
