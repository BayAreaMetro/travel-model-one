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
import string
import sys
from pathlib import Path

import xlrd
import yaml
from uec_mappings import (
    ALT_MAPPINGS,
    COEFF_OVERRIDES,
    CONSTANTS_NOTES,
    MAPPINGS,
    NOTES,
    SIZE_TERMS_CROSSWALK,
    get_token_map,
)

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "ablation_config.yaml"

# UEC sheet layout constants
ALT_NAMES_ROW = 3
FIRST_ALT_COL = 6

esc = html.escape

LEGEND_FULL = (
    "<div class='legend'>"
    "<span class='swatch match'></span> Match "
    "<span class='swatch diff'></span> Differs "
    "<span class='swatch ctramp-only'></span> CTRAMP only "
    "<span class='swatch asim-only'></span> ASim only"
    "</div>"
)
LEGEND_MATCH_DIFF = (
    "<div class='legend'>"
    "<span class='swatch match'></span> Match "
    "<span class='swatch diff'></span> Differs"
    "</div>"
)

# Module-level accumulator for diff records (populated during _mapped_table).
# Each entry: (submodel, asim_label, ctramp_no, purpose, ctramp_val, asim_val, category)
# Categories: UNRESOLVED, SIGN_DIFF, MAG_DIFF (ratio>3x), SIMILAR, ONE_SIDE_MISSING
_DIFF_RECORDS: list[tuple] = []


def _categorize_diff(c_val, a_val) -> str:
    """Categorize a numeric diff by sign/magnitude."""
    try:
        c = float(c_val)
        a = float(a_val)
    except (ValueError, TypeError):
        return "UNRESOLVED"
    if (c > 0 and a < 0) or (c < 0 and a > 0):
        return "SIGN_DIFF"
    if c == 0 or a == 0:
        return "ZERO_VS_NONZERO"
    ratio = max(abs(c), abs(a)) / min(abs(c), abs(a))
    if ratio > 3.0:
        return "MAG_DIFF"
    return "SIMILAR"


# -- CTRAMP properties reader -------------------------------------------------

_PROP_PATTERN = re.compile(r"%([^%]+)%")


def read_ctramp_properties(filepath: Path) -> dict[str, str]:
    """Read a Java-style .properties file into a dict."""
    props: dict[str, str] = {}
    if not filepath.exists():
        log.warning("Properties file not found: %s", filepath)
        return props
    with filepath.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                props[k.strip()] = v.strip()
    return props


def resolve_ctramp_formula(formula: str, props: dict[str, str]) -> tuple[str, float | None]:
    """Resolve %property% references in a CTRAMP formula.

    Returns (resolved_display_string, numeric_property_product_or_None).
    The numeric product is the multiplication of all resolved %prop% values
    (used to compute the effective coefficient = UEC_coeff * product).
    If any property is non-numeric or unresolvable, returns None for the product.
    """
    if "%" not in formula:
        return formula, None

    product = 1.0
    has_props = False

    def _replacer(m: re.Match) -> str:
        nonlocal product, has_props
        prop_name = m.group(1)
        val = props.get(prop_name)
        if val is None:
            return m.group(0)  # Leave unresolved
        has_props = True
        try:
            product *= float(val)
        except ValueError:
            pass
        return val

    resolved = _PROP_PATTERN.sub(_replacer, formula)
    return resolved, product if has_props else None


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


def _read_yaml_constants(configs_dirs: list[Path], yaml_file: str) -> dict[str, float]:
    """Read CONSTANTS section from an ActivitySim model YAML file.

    Merges across all config dirs (base first, overlay wins), matching
    ActivitySim's config override behavior.
    """
    merged: dict[str, float] = {}
    # Read in reverse so overlay (first in list) wins
    for d in reversed(configs_dirs):
        p = d / yaml_file
        if p.exists():
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
            consts = cfg.get("CONSTANTS", {})
            for k, v in consts.items():
                if isinstance(v, (int, float)):
                    merged[k] = v
    return merged


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
                elif specific in coeffs:
                    purpose_map[p] = coeffs[specific]
            if purpose_map:
                result[generic] = purpose_map
    return result


def read_asim_spec(configs_dirs: list[Path], spec_file: str, coeff_file: str) -> dict:
    """Parse spec + coefficients into {alt_names, rows: [{label, desc, expr, coeffs}]}."""
    # Coefficient lookup
    coeff_path = _resolve(configs_dirs, coeff_file)
    coeffs: dict[str, float] = {}
    if coeff_path:
        with coeff_path.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    coeffs[row["coefficient_name"].strip()] = float(row["value"])
                except (ValueError, KeyError, TypeError):
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

def _mapped_table(name: str, sheets: list[dict], spec: dict, template_resolve: dict[str, dict[str, float]] | None = None, ctramp_props: dict[str, str] | None = None, tokens_by_sheet: dict[str, dict[str, str]] | None = None, yaml_constants: dict[str, float] | None = None) -> str:
    """Render an outer-join comparison table if a mapping exists for this submodel."""
    crosswalk = MAPPINGS.get(name)
    if not crosswalk:
        return ""

    props = ctramp_props or {}
    tokens_by_sheet = tokens_by_sheet or {}

    # Effective coefficient overrides (property-resolved values)
    overrides = COEFF_OVERRIDES.get(name, {})

    # Detect multi-segment: sheets share the same row numbers
    multi_seg = len(sheets) > 1 and len({r["no"] for s in sheets for r in s["rows"]}) < sum(len(s["rows"]) for s in sheets)

    # Index CTRAMP rows by (sheet_name, no) for multi-seg, or just no for single-sheet
    ctramp_by_sheet_no: dict[tuple[str, int], dict] = {}
    ctramp_by_no: dict[int, dict] = {}
    for s in sheets:
        for r in s["rows"]:
            ctramp_by_sheet_no[(s["sheet_name"], r["no"])] = r
            ctramp_by_no[r["no"]] = r

    # For multi-sheet models, rows may have different row numbers across sheets
    # but the same description. Build a desc-based index so the crosswalk
    # (keyed to reference sheet row numbers) resolves correctly in all sheets.
    # Only fill in entries not already populated (don't overwrite actual data).
    if multi_seg and len(sheets) > 1:
        ref_sheet = sheets[0]
        ref_by_no = {r["no"]: r for r in ref_sheet["rows"]}
        # Collect (sheet, row_no) pairs explicitly specified by per-sheet crosswalk dicts.
        # The desc-based code must not store at these keys because the per-sheet
        # dispatch uses them for direct row lookups.
        _explicit_sheet_rows: set[tuple[str, int]] = set()
        for ctramp_ref in crosswalk.values():
            refs = ctramp_ref if isinstance(ctramp_ref, list) else [ctramp_ref]
            for ref in refs:
                if isinstance(ref, dict):
                    for k, v in ref.items():
                        if k != "*":
                            _explicit_sheet_rows.add((k, v))
        # Also collect ref row numbers that have per-sheet dicts (their desc-based
        # matching is unreliable when multiple rows share the same description).
        _ref_rows_with_overrides: set[int] = set()
        for ctramp_ref in crosswalk.values():
            refs = ctramp_ref if isinstance(ctramp_ref, list) else [ctramp_ref]
            for ref in refs:
                if isinstance(ref, dict) and "*" in ref:
                    _ref_rows_with_overrides.add(ref["*"])
        for s in sheets[1:]:
            sn = s["sheet_name"]
            desc_to_row = {r["desc"].strip().lower(): r for r in s["rows"]}
            for ref_no, ref_row in ref_by_no.items():
                ref_desc = ref_row["desc"].strip().lower()
                matched = desc_to_row.get(ref_desc)
                if matched:
                    # Don't store if either:
                    # 1) The key (sn, ref_no) collides with a per-sheet dispatch target
                    # 2) The matched row's actual number is a per-sheet dispatch target
                    # 3) The ref_no already has a per-sheet dict (explicit dispatch)
                    key = (sn, ref_no)
                    if key in _explicit_sheet_rows:
                        continue
                    if (sn, matched["no"]) in _explicit_sheet_rows:
                        continue
                    if ref_no in _ref_rows_with_overrides:
                        continue
                    ctramp_by_sheet_no[key] = matched

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
        """Combine CTRAMP filter + formula into a single expression string.

        Resolves %property% references to show actual runtime values.
        """
        if not row:
            return ""
        f, e = row.get("filter", ""), row.get("formula", "")
        if f and e:
            raw = f"[{f}] {e}"
        else:
            raw = e or f
        if props and "%" in raw:
            resolved, _ = resolve_ctramp_formula(raw, props)
            return resolved
        return raw

    def _effective_coeff(row: dict, alt: str | None = None) -> float | str:
        """Get effective CTRAMP coefficient, resolving %property% in formula.

        When the UEC coefficient is 1.0 (passthrough) and the formula contains
        %property% references, the effective coefficient equals the resolved
        property product. This matches cases where CTRAMP uses:
            coeff=1 × expression=[filter] %PropertyValue%

        When the UEC coefficient is NOT 1.0, it's the estimated parameter and
        the %property% is a scaling factor in the expression (handled identically
        in ActivitySim via CONSTANTS). In that case, return the raw coefficient.
        """
        if not row:
            return ""
        # Get the raw UEC coefficient
        if alt:
            raw_coeff = row["coeffs"].get(alt, "")
        else:
            raw_coeff = next(iter(row["coeffs"].values()), "") if row.get("coeffs") else ""
        if raw_coeff == "":
            return ""
        # Check if formula has %property% references
        formula = row.get("formula", "")
        if props and "%" in formula:
            _, prop_product = resolve_ctramp_formula(formula, props)
            if prop_product is not None:
                try:
                    coeff_num = float(raw_coeff)
                    # Only fold in property product when coeff is a passthrough (1.0)
                    if abs(coeff_num - 1.0) < 1e-6:
                        return coeff_num * prop_product
                except (ValueError, TypeError):
                    pass
        return raw_coeff

    # Detect multi-alt: single sheet with multiple CTRAMP alts matching ASim alts by position
    ctramp_alts = sheets[0].get("alt_names", []) if len(sheets) == 1 else []
    multi_alt = not multi_seg and len(asim_alts) > 1 and len(ctramp_alts) > 1

    # Alt-level mapping override (e.g. CTRAMP has 11 HV/AV alts, ASim has 5)
    alt_map = ALT_MAPPINGS.get(name)
    if alt_map and multi_alt:
        # Build alt_pairs: one entry per CTRAMP alt, each mapped to its ASim alt
        # Shows all CTRAMP alts with the corresponding ASim alt repeated
        alt_pairs_override = [(c_alt, alt_map[c_alt]) for c_alt in ctramp_alts if c_alt in alt_map]
    else:
        alt_pairs_override = None

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
        # Treat blank as 0 for numeric comparison (e.g. ASim omits zero-valued coefficients)
        c_num = 0.0 if c_val == "" else None
        a_num = 0.0 if a_val == "" else None
        try:
            c_num = c_num if c_num is not None else float(c_val)
            a_num = a_num if a_num is not None else float(a_val)
            match = abs(a_num - c_num) < 1e-6
        except (ValueError, TypeError):
            match = str(c_val) == str(a_val)
        cls = "match" if match else "diff"
        c_str = _fmt(c_val) if c_val != "" else ""
        a_str = _fmt(a_val) if a_val != "" else ""
        return f"<td class='num {cls}'>{c_str}</td><td class='num {cls}'{rowspan}>{a_str}</td>"

    coeff_summary = ""

    if multi_seg and template_resolve:
        # Template-based multi-segment (Mode Choice): structural mapping with
        # per-purpose numeric comparison.  CTRAMP embeds coefficients as inline
        # numeric literals in the formula column (alt column is always 1.0).
        # We resolve the ASim template coefficient per purpose and compare.
        seg_names = [s["sheet_name"] for s in sheets]
        purposes = [SHEET_TO_PURPOSE.get(sn, sn.lower()) for sn in seg_names]

        # Header: structural columns + one CTRAMP/ASim pair per purpose
        coeff_hdrs = "".join(
            f"<th class='num'>CTRAMP {esc(sn)}</th><th class='num'>ASim {esc(sn)}</th>"
            for sn in seg_names
        )
        h = ("<table class='coeff mapped sortable'><thead><tr>"
             "<th>ASim Label</th><th>No.</th><th>Description</th>"
             f"<th>CTRAMP Expression</th><th>ASim Expression</th>{coeff_hdrs}"
             "</tr></thead><tbody>")

        n_match = 0
        n_diff = 0
        n_total = 0

        # Pre-resolve all tokens per sheet into numeric values
        _resolved_tokens: dict[str, dict[str, float]] = {}
        # Track which tokens are derived from c_ivt (multiplier × c_ivt)
        _ivt_derived: dict[str, set[str]] = {}  # sheet -> set of token names derived from c_ivt
        for _sn, _raw_tokens in tokens_by_sheet.items():
            resolved: dict[str, float] = {}
            ivt_derived: set[str] = set()
            # Pass 1: resolve literal numbers
            for _tk, _tv in _raw_tokens.items():
                try:
                    resolved[_tk] = float(_tv)
                    resolved[_tk.lower()] = float(_tv)
                except (ValueError, TypeError):
                    pass
            # Pass 2: evaluate formula tokens and detect c_ivt derivatives
            eval_ns: dict[str, float] = {}
            eval_ns.update(resolved)
            for _pk, _pv in props.items():
                try:
                    eval_ns[_pk] = float(_pv)
                except (ValueError, TypeError):
                    pass
            for _tk, _tv in _raw_tokens.items():
                if _tk in resolved:
                    continue
                # Check if this token is a multiplier of c_ivt
                # (e.g. "2.00 * c_ivt", "(0.60 * c_ivt) / valueOfTime")
                if "c_ivt" in _tv and _tk != "c_ivt":
                    ivt_derived.add(_tk)
                    ivt_derived.add(_tk.lower())
                try:
                    resolved[_tk] = float(eval(_tv, {"__builtins__": {}}, eval_ns))
                    resolved[_tk.lower()] = resolved[_tk]
                except Exception:
                    pass
            # Pass 3: detect numeric tokens that are multiples of c_ivt
            # (Trip MC stores c_densityIndex as pre-computed 0.0044 instead of
            # the formula "-0.20 * c_ivt")
            c_ivt_val = resolved.get("c_ivt")
            if c_ivt_val and abs(c_ivt_val) > 1e-10:
                for _tk, _tv in resolved.items():
                    if _tk in ivt_derived or _tk == "c_ivt":
                        continue
                    if not _tk.startswith("c_") or abs(_tv) < 1e-10:
                        continue
                    ratio = _tv / c_ivt_val
                    # Check if ratio is a "clean" multiplier (e.g. -0.2, 2.0, 270.0)
                    if abs(ratio - round(ratio, 1)) < 1e-6 and abs(ratio) < 300:
                        ivt_derived.add(_tk)
                        ivt_derived.add(_tk.lower())
            _resolved_tokens[_sn] = resolved
            _ivt_derived[_sn] = ivt_derived

        def _resolve_ctramp_formula_val(row: dict, sheet_name: str = "") -> float | str:
            """Extract the effective numeric coefficient from a CTRAMP UEC row.

            In CTRAMP mode choice UECs, the utility contribution for an alt is:
                formula_value * alt_column_value  (when filter passes)

            Four patterns:
            1. formula is the coefficient (e.g. -1.5593), alt column = 1.0
               → return formula (ASC rows, demographic coefficients)
            2. formula is a passthrough (1.0), alt column is the coefficient (e.g. -999)
               → return the alt column value (unavailability rows)
            3. formula is a token expression (c_ivt*...), alt column = 1.0
               → resolve the leading token to its numeric value for this sheet
            4. formula is unresolvable → return ""
            """
            if not row:
                return ""
            formula = row.get("formula", "")
            coeffs = row.get("coeffs", {})

            # Get the first alt column value (all should be the same for a given row)
            alt_vals = [v for v in coeffs.values() if isinstance(v, (int, float))]
            alt_val = alt_vals[0] if alt_vals else None

            try:
                f_val = float(formula)
            except (ValueError, TypeError):
                # Formula is a complex expression — try to resolve token references
                if sheet_name and _resolved_tokens:
                    resolved = _resolved_tokens.get(sheet_name, {})
                    ivt_derived = _ivt_derived.get(sheet_name, set())

                    # Before pattern-matching tokens, check if the formula
                    # multiplies by a %Property% that resolves to 0, or by a
                    # literal zero (e.g. "c_ivt*0.00").  If so the entire
                    # expression is effectively zero.
                    _prop_zero = False
                    if props:
                        for _pm in re.finditer(r'%(\w+)%', formula):
                            pname = _pm.group(1)
                            pval_str = props.get(pname, "")
                            try:
                                if float(pval_str) == 0.0:
                                    _prop_zero = True
                                    break
                            except (ValueError, TypeError):
                                pass
                    # Also catch literal zero multiplier: "c_xxx*0.00" or "c_xxx * 0"
                    if not _prop_zero and re.search(r'[*]\s*0+(\.0+)?\s*$', formula):
                        _prop_zero = True
                    if _prop_zero:
                        return 0.0

                    # Pattern A: "c_xxx * (skim_expression)" or "c_xxx*(...)"
                    # If c_xxx is derived from c_ivt (e.g. c_walkTimeShort = 2*c_ivt),
                    # the comparable coefficient is c_ivt because ASim separates the
                    # multiplier into the expression. This is provably equivalent:
                    #   CTRAMP: (MULT * c_ivt) * skim
                    #   ASim:   c_ivt * (MULT * skim)  [MULT verified in constants crosswalk]
                    token_match = re.match(r'\s*(c_\w+)\s*[*(/]', formula)
                    if token_match:
                        token_name = token_match.group(1)
                        tk_lower = token_name.lower()
                        # If token is derived from c_ivt, return c_ivt (the base coeff)
                        if token_name in ivt_derived or tk_lower in ivt_derived:
                            c_ivt_val = resolved.get("c_ivt")
                            if c_ivt_val is not None:
                                return c_ivt_val
                        # Otherwise return the token's resolved value directly
                        if token_name in resolved:
                            return resolved[token_name]
                        if tk_lower in resolved:
                            return resolved[tk_lower]
                    # Pattern A2: "(c_xxx - c_yyy) * skim" or "(c_xxx+c_yyy)*(...)"
                    # If ALL tokens in the prefix are ivt-derived (or c_ivt itself),
                    # the arithmetic is just a multiplier verified in constants crosswalk,
                    # so the comparable coefficient is still c_ivt.
                    multi_match = re.match(r'\s*(\([^)]*c_\w+[^)]*\))\s*\*', formula)
                    if multi_match:
                        expr_part = multi_match.group(1)
                        # Extract all token names from the prefix expression
                        prefix_tokens = re.findall(r'c_\w+', expr_part)
                        # Check if all are ivt-derived or c_ivt itself
                        all_ivt = all(
                            t == "c_ivt" or t in ivt_derived or t.lower() in ivt_derived
                            for t in prefix_tokens
                        )
                        if all_ivt and prefix_tokens:
                            c_ivt_val = resolved.get("c_ivt")
                            if c_ivt_val is not None:
                                return c_ivt_val
                        # Fallback: evaluate numerically
                        try:
                            val = float(eval(expr_part, {"__builtins__": {}}, resolved))
                            return val
                        except Exception:
                            pass
                    # Pattern A3: "min(0, expr)" or "max(expr1, expr2)" — piecewise
                    minmax_match = re.match(
                        r'\s*(min|max)\((.+)\)\s*$', formula, re.IGNORECASE
                    )
                    if minmax_match:
                        inner = minmax_match.group(2)
                        inner_tokens = re.findall(r'c_\w+', inner)
                        if inner_tokens:
                            # If the first c_ token is ivt-derived, return c_ivt
                            first_tk = inner_tokens[0]
                            if first_tk in ivt_derived or first_tk.lower() in ivt_derived:
                                c_ivt_val = resolved.get("c_ivt")
                                if c_ivt_val is not None:
                                    return c_ivt_val
                            # Otherwise return first token value
                            tv = resolved.get(first_tk) or resolved.get(first_tk.lower())
                            if tv is not None:
                                return tv
                    # Pattern B: formula is exactly a bare token name (e.g. "c_age1619_da")
                    bare_match = re.match(r'\s*(c_\w+)\s*$', formula)
                    if bare_match:
                        token_name = bare_match.group(1)
                        tok_val = resolved.get(token_name) or resolved.get(token_name.lower())
                        if tok_val is not None:
                            if alt_val is not None and abs(alt_val - 1.0) > 1e-10:
                                return tok_val * alt_val
                            return tok_val
                # Pattern C: filter/availability checks — return alt_val
                # Covers "==", ">", "<" comparisons that produce -999 in the alt column
                if alt_val is not None and re.search(r'[=<>]', formula):
                    return alt_val
                return "\u26a0UNRESOLVED"

            if alt_val is None:
                return "\u26a0UNRESOLVED"

            # Case 1: formula is the coefficient, alt column is passthrough (1.0)
            if abs(alt_val - 1.0) < 1e-10:
                return f_val
            # Case 2: formula is a passthrough (1.0), alt column is the coefficient
            if abs(f_val - 1.0) < 1e-10:
                return alt_val
            # Case 3: both are non-trivial — return the product
            return f_val * alt_val

        def _resolve_asim_for_purpose(ar: dict | None, purpose: str) -> float | str:
            """Resolve the ASim coefficient for a given purpose via template."""
            if not ar or not ar.get("coeffs"):
                return ""
            # Check if the expression multiplies by a YAML constant that equals 0.
            # If so, the entire utility row contributes nothing regardless of the
            # alt column value.
            if yaml_constants and ar.get("expr"):
                expr = ar["expr"]
                if '*' in expr and '==' not in expr:
                    for cname, cval in yaml_constants.items():
                        if cval == 0 and re.search(r'\b' + re.escape(cname) + r'\b', expr):
                            return 0.0
            # Check if expression filters by tour_type — if the current purpose
            # doesn't match the filter, the effective coefficient is 0.
            if ar.get("expr"):
                expr = ar["expr"]
                # Pattern: df.tour_type == 'X' — only applies to purpose X
                eq_match = re.search(r"df\.tour_type\s*==\s*'(\w+)'", expr)
                if eq_match:
                    allowed_purpose = eq_match.group(1)
                    if purpose != allowed_purpose:
                        return 0.0
                # Pattern: df.tour_type != 'X' — applies to all except X
                neq_match = re.search(r"df\.tour_type\s*!=\s*'(\w+)'", expr)
                if neq_match:
                    excluded_purpose = neq_match.group(1)
                    if purpose == excluded_purpose:
                        return 0.0
            # Get any coefficient name from the row (all alts share same generic name for ASCs)
            for _alt, val in ar["coeffs"].items():
                if isinstance(val, (int, float)):
                    return val  # Already resolved numeric
                # Unresolved string — look up in template
                if val in template_resolve:
                    return template_resolve[val].get(purpose, "")
                return ""
            return ""

        for asim_label, ctramp_ref in crosswalk.items():
            # ctramp_ref can be:
            #   int — same row on all sheets
            #   list[int] — multiple rows collapse to one ASim row
            #   dict — per-sheet row numbers: {"*": default, "SheetName": override}
            #   list[int|dict] — multiple rows, each possibly per-sheet
            ctramp_nos = ctramp_ref if isinstance(ctramp_ref, list) else [ctramp_ref]
            ar = asim_by_label.get(asim_label)
            used_asim.add(asim_label)

            for i, ctramp_no_spec in enumerate(ctramp_nos):
                # Resolve per-sheet row number helper
                def _row_for_sheet(sn: str, spec=ctramp_no_spec) -> int | None:
                    if isinstance(spec, dict):
                        return spec.get(sn, spec.get("*"))
                    return spec

                display_no = _row_for_sheet(seg_names[0])
                used_ctramp.add(display_no)
                # Also mark overridden row numbers as used
                if isinstance(ctramp_no_spec, dict):
                    for v in ctramp_no_spec.values():
                        used_ctramp.add(v)
                cr_any = ctramp_by_sheet_no.get((seg_names[0], display_no))
                show_asim = (i == 0)
                rowspan = f" rowspan='{len(ctramp_nos)}'" if show_asim and len(ctramp_nos) > 1 else ""

                # Per-purpose numeric comparison
                val_cells = ""
                for sn, purpose in zip(seg_names, purposes):
                    sheet_row = _row_for_sheet(sn)
                    cr = ctramp_by_sheet_no.get((sn, sheet_row)) if sheet_row else None
                    # Mark the actual resolved row number as used (may differ from sheet_row due to desc-matching)
                    if cr is not None:
                        used_ctramp.add(cr["no"])
                    c_val = _resolve_ctramp_formula_val(cr, sheet_name=sn)
                    a_val = _resolve_asim_for_purpose(ar, purpose) if show_asim else ""
                    c_is_unresolved = isinstance(c_val, str) and "UNRESOLVED" in c_val
                    a_is_unresolved = isinstance(a_val, str) and "UNRESOLVED" in a_val
                    # If crosswalk explicitly sets None for this sheet, CTRAMP
                    # intentionally omits this row — treat CTRAMP value as 0.
                    if sheet_row is None and isinstance(ctramp_no_spec, dict):
                        c_val = 0.0
                    if c_val == "" and a_val == "":
                        val_cells += "<td class='num'></td><td class='num'></td>"
                    elif c_is_unresolved or a_is_unresolved:
                        # One or both sides unresolved — count as unverified diff
                        n_total += 1
                        n_diff += 1
                        c_str = _fmt(c_val) if not c_is_unresolved else "\u26a0?"
                        a_str = _fmt(a_val) if not a_is_unresolved else "\u26a0?"
                        val_cells += f"<td class='num diff'>{c_str}</td><td class='num diff'>{a_str}</td>"
                        _DIFF_RECORDS.append((name, asim_label, display_no, purpose, c_val, a_val, "UNRESOLVED"))
                    elif c_val != "" and a_val != "":
                        n_total += 1
                        try:
                            match = abs(float(c_val) - float(a_val)) < 1e-4
                        except (ValueError, TypeError):
                            match = False
                        cls = "match" if match else "diff"
                        if match:
                            n_match += 1
                        else:
                            n_diff += 1
                            _DIFF_RECORDS.append((name, asim_label, display_no, purpose, c_val, a_val, _categorize_diff(c_val, a_val)))
                        val_cells += f"<td class='num {cls}'>{_fmt(c_val)}</td><td class='num {cls}'>{_fmt(a_val)}</td>"
                    else:
                        # One side blank (no row exists), other has value
                        # Treat zero vs absent as a match (zero contribution = no row)
                        try:
                            _present = float(c_val) if c_val != "" else float(a_val)
                        except (ValueError, TypeError):
                            _present = None
                        if _present is not None and abs(_present) < 1e-10:
                            n_total += 1
                            n_match += 1
                            val_cells += f"<td class='num match'>{_fmt(c_val) if c_val != '' else '—'}</td><td class='num match'>{_fmt(a_val) if a_val != '' else '—'}</td>"
                        else:
                            n_total += 1
                            n_diff += 1
                            c_str = _fmt(c_val) if c_val != "" else "—"
                            a_str = _fmt(a_val) if a_val != "" else "—"
                            val_cells += f"<td class='num diff'>{c_str}</td><td class='num diff'>{a_str}</td>"
                            _DIFF_RECORDS.append((name, asim_label, display_no, purpose, c_val, a_val, "ONE_SIDE_MISSING"))

                body += "<tr>"
                if show_asim:
                    body += f"<td{rowspan}>{esc(asim_label)}</td>"
                body += f"<td>{display_no}</td>"
                body += f"<td>{esc(cr_any['desc']) if cr_any else ''}</td>"
                body += f"<td>{esc(_ctramp_expr(cr_any))}</td>"
                if show_asim:
                    body += f"<td{rowspan}>{esc(ar['expr']) if ar else ''}</td>"
                body += val_cells
                body += "</tr>"

        # Unmatched CTRAMP rows
        empty_val_cells = "<td class='num'></td><td class='num'></td>" * len(seg_names)
        for s in sheets:
            for r in s["rows"]:
                if r["no"] not in used_ctramp:
                    used_ctramp.add(r["no"])
                    body += (
                        f"<tr class='ctramp-only'><td></td><td>{r['no']}</td>"
                        f"<td>{esc(r['desc'])}</td><td>{esc(_ctramp_expr(r))}</td>"
                        f"<td></td>{empty_val_cells}</tr>"
                    )

        # Unmatched ASim rows
        for r in spec["rows"]:
            if r["label"] not in used_asim:
                body += (
                    f"<tr class='asim-only'><td>{esc(r['label'])}</td><td></td>"
                    f"<td></td><td></td><td>{esc(r['expr'])}</td>{empty_val_cells}</tr>"
                )

        # Summary for this section
        if n_total > 0:
            coeff_summary = (
                f"<div style='margin:8px 0;font-size:13px'>"
                f"Inline coefficients compared: {n_total} cells &bull; "
                f"<span style='color:green'>{n_match} match</span> &bull; "
                f"<span style='color:red'>{n_diff} differ</span>"
                f"</div>"
            )
        else:
            coeff_summary = ""

    elif multi_seg:
        # Multi-segment table: one coeff column per segment
        seg_names = [s["sheet_name"] for s in sheets]
        coeff_hdrs = "".join(
            f"<th class='num'>CTRAMP {esc(sn)}</th><th class='num'>ASim {esc(alt)}</th>"
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

            for i, ctramp_no_spec in enumerate(ctramp_nos):
                def _row_for_sheet2(sn: str, spec=ctramp_no_spec) -> int | None:
                    if isinstance(spec, dict):
                        return spec.get(sn, spec.get("*"))
                    return spec

                display_no = _row_for_sheet2(seg_names[0])
                used_ctramp.add(display_no)
                if isinstance(ctramp_no_spec, dict):
                    for v in ctramp_no_spec.values():
                        used_ctramp.add(v)
                cr_any = ctramp_by_sheet_no.get((seg_names[0], display_no))
                show_asim = (i == 0)
                rowspan = f" rowspan='{len(ctramp_nos)}'" if show_asim and len(ctramp_nos) > 1 else ""

                body += "<tr>"
                if show_asim:
                    body += f"<td{rowspan}>{esc(asim_label)}</td>"
                body += f"<td>{display_no}</td>"
                body += f"<td>{esc(cr_any['desc']) if cr_any else ''}</td>"
                body += f"<td>{esc(_ctramp_expr(cr_any))}</td>"
                if show_asim:
                    body += f"<td{rowspan}>{esc(ar['expr']) if ar else ''}</td>"

                # One pair of coeff columns per segment
                for sn, alt in zip(seg_names, asim_alts):
                    sheet_row = _row_for_sheet2(sn)
                    cr = ctramp_by_sheet_no.get((sn, sheet_row)) if sheet_row else None
                    # Mark actual resolved row as used
                    if cr is not None:
                        used_ctramp.add(cr["no"])
                    c_val = _effective_coeff(cr)
                    a_val = _coeff_for_alt(ar, alt) if ar else ""
                    if show_asim:
                        body += _pair_cells(c_val, a_val, rowspan)
                    else:
                        # Only CTRAMP cell — ASim cell spans from first row
                        try:
                            match = abs(float(a_val) - float(c_val)) < 1e-6
                        except (ValueError, TypeError):
                            match = str(c_val) == str(a_val) if c_val != "" else c_val == ""
                        cls = f" {'match' if match else 'diff'}" if c_val != "" else ""
                        c_str = _fmt(c_val) if c_val != "" else ""
                        body += f"<td class='num{cls}'>{c_str}</td>"
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
                        body += f"<td class='num'>{_fmt(c_val) if c_val != '' else ''}</td><td></td>"
                    body += "</tr>"

        # Unmatched ASim rows
        for r in spec["rows"]:
            if r["label"] not in used_asim:
                body += f"<tr class='asim-only'><td>{esc(r['label'])}</td><td></td><td></td><td></td><td>{esc(r['expr'])}</td>"
                for sn, alt in zip(seg_names, asim_alts):
                    a_val = _coeff_for_alt(r, alt)
                    body += f"<td></td><td class='num'>{_fmt(a_val) if a_val != '' else ''}</td>"
                body += "</tr>"

    elif multi_alt:
        # Multi-alt table: single sheet with per-alt coefficient columns
        alt_pairs = alt_pairs_override or list(zip(ctramp_alts, asim_alts))
        coeff_hdrs = "".join(
            f"<th class='num'>CTRAMP {esc(a_alt)}</th><th class='num'>ASim {esc(a_alt)}</th>"
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
                    raw_c = _effective_coeff(cr, c_alt) if cr else ""
                    # Apply override only when the alt has a coefficient
                    c_val = overrides.get(ctramp_no, raw_c) if raw_c != "" else raw_c
                    a_val = _coeff_for_alt(ar, a_alt) if ar else ""
                    if show_asim:
                        body += _pair_cells(c_val, a_val, rowspan)
                    else:
                        # Only CTRAMP cell — ASim cell spans from first row
                        try:
                            match = abs(float(a_val) - float(c_val)) < 1e-6
                        except (ValueError, TypeError):
                            match = str(c_val) == str(a_val) if c_val != "" else c_val == ""
                        cls = f" {'match' if match else 'diff'}" if c_val != "" else ""
                        c_str = _fmt(c_val) if c_val != "" else ""
                        body += f"<td class='num{cls}'>{c_str}</td>"
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
                    body += f"<td class='num'>{_fmt(c_val) if c_val != '' else ''}</td><td></td>"
                body += "</tr>"

        # Unmatched ASim rows
        for r in spec["rows"]:
            if r["label"] not in used_asim:
                body += f"<tr class='asim-only'><td>{esc(r['label'])}</td><td></td><td></td><td></td><td>{esc(r['expr'])}</td>"
                for c_alt, a_alt in alt_pairs:
                    a_val = _coeff_for_alt(r, a_alt)
                    body += f"<td></td><td class='num'>{_fmt(a_val) if a_val != '' else ''}</td>"
                body += "</tr>"

    else:
        # Single-segment table
        h = ("<table class='coeff mapped sortable'><thead><tr>"
             "<th>ASim Label</th><th>No.</th><th>Description</th>"
             "<th>CTRAMP Expression</th><th>ASim Expression</th>"
             "<th>CTRAMP Coeff</th><th>ASim Coeff</th>"
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

                c_coeff = overrides.get(ctramp_no, _effective_coeff(cr))

                # Show ASim label/expr/coeff only on the first row of a group
                show_asim = (i == 0)
                rowspan = f" rowspan='{len(ctramp_nos)}'" if show_asim and len(ctramp_nos) > 1 else ""

                body += "<tr>"
                if show_asim:
                    body += f"<td{rowspan}>{esc(asim_label)}</td>"
                body += (
                    f"<td>{cr['no'] if cr else ''}</td>"
                    f"<td>{esc(cr['desc']) if cr else ''}</td>"
                    f"<td>{esc(_ctramp_expr(cr))}</td>"
                )
                if show_asim:
                    body += f"<td{rowspan}>{esc(ar['expr']) if ar else ''}</td>"
                if show_asim:
                    body += _pair_cells(c_coeff, a_coeff, rowspan)
                else:
                    # Only CTRAMP cell — ASim cell spans from first row
                    try:
                        match = abs(float(a_coeff) - float(c_coeff)) < 1e-6
                    except (ValueError, TypeError):
                        match = str(c_coeff) == str(a_coeff) if c_coeff != "" else c_coeff == ""
                    cls = f" {'match' if match else 'diff'}" if c_coeff != "" else ""
                    c_str = _fmt(c_coeff) if c_coeff != "" else ""
                    body += f"<td class='num{cls}'>{c_str}</td>"
                body += "</tr>"

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
                        f"<td></td></tr>"
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
                    f"</tr>"
                )

    return f"<h3>Mapped Comparison</h3>{LEGEND_FULL}{coeff_summary}<div class='mapped-wrap'>{h}{body}</tbody></table></div>"


def _constants_table(
    tokens_by_sheet: dict[str, dict[str, str]],
    template_resolve: dict[str, dict[str, float]],
    sheet_names: list[str],
    yaml_constants: dict[str, float] | None = None,
    asim_spec: dict | None = None,
    submodel_name: str = "",
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

    # CTRAMP tokens stored as M × c_ivt whose YAML name doesn't end in
    # "_multiplier" but should still be compared in IVT-multiplier space.
    _yaml_ivt_space: set[str] = {"origin_density_index_max"}

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
            coef_refs = re.findall(r"\bcoef_\w+", expr)
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

    # Map CTRAMP token names to ASim coefficient names using explicit crosswalk.
    token_map = get_token_map(submodel_name)

    def _find_asim(token: str) -> tuple[str, str, float | None]:
        """Return (asim_name, source, yaml_value_or_None).

        source is 'template', 'yaml', or 'none'.
        """
        entry = token_map.get(token)
        if entry is None:
            # Unmapped token — fall back to auto-derivation as safety net
            base = "coef_" + token[2:]
            if base in template_resolve:
                log.warning("Token %r resolved by auto-derivation — add to TOKEN_MAP", token)
                return base, "template", None
            return base, "none", None

        asim_name, source = entry
        if source == "template":
            if asim_name in template_resolve:
                return asim_name, "template", None
            return asim_name, "none", None
        # source == "yaml"
        if asim_name in yaml_constants:
            return asim_name, "yaml", yaml_constants[asim_name]
        return asim_name, "none", None

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
                        # Always show as multiplier for _multiplier coefficients
                        # so both sides are in comparable units, even when
                        # values don't match (e.g. atwork systematic bug).
                        if asim_name_.endswith("_multiplier") or abs(derived - a_float) < 1e-4:
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
        is_mult = source == "yaml" and (
            asim_name.endswith("_multiplier") or asim_name in _yaml_ivt_space
        )
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
            if c_val == "":
                # Token not present in this CTRAMP sheet — skip ASim side too
                # (the ASim value isn't purpose-specific for this token)
                row_cells += "<td class='num'></td><td class='num'></td>"
                continue
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
            body += (
                f"<tr><td><code>{esc(token)}</code></td>"
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

    return (f"<h3>Constants Crosswalk (Token Section)</h3>{LEGEND_MATCH_DIFF}{summary}"
            f"<div class='mapped-wrap'>{h}{body}</tbody></table></div>")


# -- HTML rendering ------------------------------------------------------------

def _fmt(v: float | str) -> str:
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1000:
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

    note = (
        "<p class='mapping-note'><em>Note:</em> ASim-only <code>trip/*</code> rows are used by "
        "ActivitySim's <code>trip_destination</code> model. CTRAMP handles intermediate stop "
        "locations via a separate mechanism outside the size terms CSV.</p>"
    )
    return f"<h3>Size Terms Comparison</h3>{LEGEND_FULL}{note}<div class='mapped-wrap'>{h}{body}</tbody></table></div>"


_TEMPLATE_PATH = Path(__file__).parent / "compare_template.html"
_TEMPLATE = string.Template(_TEMPLATE_PATH.read_text(encoding="utf-8"))


def build_report(cfg: dict) -> Path:
    repo = Path(cfg["repo_root"])
    cc = cfg["coefficient_comparison"]
    ctramp_dir = repo / cc["ctramp_model_dir"]
    # Load CTRAMP runtime properties for resolving %property% references in UEC formulas.
    # Prefer the ctramp_project_dir copy (has RuntimeConfiguration.py-resolved values),
    # fall back to repo copy (may have placeholders for some values).
    props_rel = cc.get("ctramp_properties_file", "model-files/runtime/mtcTourBased.properties")
    ctramp_project_dir = cfg.get("ctramp_project_dir")
    if ctramp_project_dir:
        project_props = Path(ctramp_project_dir) / "CTRAMP" / "runtime" / "mtcTourBased.properties"
        if project_props.exists():
            props_path = project_props
        else:
            props_path = repo / props_rel
    else:
        props_path = repo / props_rel
    ctramp_props = read_ctramp_properties(props_path)
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
                "daily_activity_pattern": ["CDAP", "Work From Home"],
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

        # Build unified Mapping Notes from both sources
        all_notes: list[tuple[str, str]] = []
        # Notes from uec_mappings.NOTES (mapped comparison notes)
        mapped_notes = NOTES.get(sm["name"], {})
        for label, note in mapped_notes.items():
            all_notes.append((label, note))
        # Notes from CONSTANTS_NOTES (constants crosswalk notes)
        all_notes.extend(CONSTANTS_NOTES.get(sm["name"], []))

        notes_html = ""
        if all_notes:
            items = ""
            for coeff_name, description in all_notes:
                desc_html = esc(description).replace("\n", "<br>")
                items += f"<dt><code>{esc(coeff_name)}</code></dt><dd>{desc_html}</dd>"
            notes_html = (
                "<details class='mapping-notes mapping-notes-lg'>"
                "<summary>Mapping Notes</summary>"
                f"<dl>{items}</dl>"
                "</details>"
            )

        # 1:1 mapped comparison
        tpl_file = sm.get("asim_coefficients_template")
        tpl_resolve = None
        if tpl_file:
            tpl_resolve = _read_template(dirs, tpl_file, sm["asim_coefficients"])

        # Read tokens early so _mapped_table can resolve expression rows
        tokens_by_sheet = None
        if tpl_file and tpl_resolve:
            tokens_by_sheet = read_uec_tokens(
                ctramp_dir, sm["ctramp_file"], sm["ctramp_sheets"]
            )

        # Read YAML constants early so _mapped_table can detect zero-valued expressions
        yaml_file = sm["asim_spec"].replace(".csv", ".yaml") if tpl_file else ""
        yaml_consts = _read_yaml_constants(dirs, yaml_file) if yaml_file else {}

        mapped_html = _mapped_table(sm["name"], sheets, spec, template_resolve=tpl_resolve, ctramp_props=ctramp_props, tokens_by_sheet=tokens_by_sheet, yaml_constants=yaml_consts)

        # Constants crosswalk for template-based models
        constants_html = ""
        if tpl_file and tpl_resolve:
            yaml_file = sm["asim_spec"].replace(".csv", ".yaml")
            yaml_consts = _read_yaml_constants(dirs, yaml_file)
            constants_html = _constants_table(
                tokens_by_sheet, tpl_resolve, sm["ctramp_sheets"], yaml_consts,
                asim_spec=spec,
                submodel_name=sm["name"],
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
        return paths_html + notes_html + constants_html + mapped_html + summary + "\n".join(parts)

    # Determine overlay: first dir is the scenario overlay, rest are base.
    has_overlay = len(asim_dirs) > 1
    asim_dirs_base = asim_dirs[1:] if has_overlay else asim_dirs
    overlay_label = asim_dirs[0].relative_to(repo) if has_overlay else None

    for sm in cc["submodels"]:
        log.info("Processing %s ...", sm["name"])

        # Always generate with the full config stack (overlay first)
        body_overlay = _build_tab_body(sm, asim_dirs)

        if has_overlay:
            _saved = len(_DIFF_RECORDS)
            body_base = _build_tab_body(sm, asim_dirs_base)
            del _DIFF_RECORDS[_saved:]  # discard diffs from base-only pass
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

    html_doc = _TEMPLATE.safe_substitute(
        TOGGLE_BAR=toggle_html,
        TAB_BUTTONS="".join(buttons),
        TAB_PANELS="".join(panels),
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding="utf-8")
    log.info("Report: %s", out)
    return out


def dump_diffs_csv(out_path: Path) -> None:
    """Write accumulated diff records to a CSV, sorted by category priority."""
    cat_order = {"UNRESOLVED": 0, "SIGN_DIFF": 1, "ZERO_VS_NONZERO": 2,
                 "MAG_DIFF": 3, "ONE_SIDE_MISSING": 4, "SIMILAR": 5}
    rows = sorted(_DIFF_RECORDS, key=lambda r: (cat_order.get(r[6], 99), r[0], r[3], r[1]))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["submodel", "asim_label", "ctramp_no", "purpose",
                    "ctramp_val", "asim_val", "category"])
        for rec in rows:
            w.writerow(rec)
    log.info("Diffs CSV (%d rows): %s", len(rows), out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)
    dump_diffs = "--dump-diffs" in sys.argv
    argv_rest = [a for a in sys.argv[1:] if a != "--dump-diffs"]
    config_path = Path(argv_rest[0]) if argv_rest else CONFIG_PATH
    cfg = yaml.safe_load(config_path.read_text())
    report_path = build_report(cfg)
    if dump_diffs:
        csv_path = report_path.with_suffix(".diffs.csv")
        dump_diffs_csv(csv_path)
