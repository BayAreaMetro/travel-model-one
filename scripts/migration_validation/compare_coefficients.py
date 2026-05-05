"""Generate an HTML report comparing CTRAMP UEC coefficients with ActivitySim specs.

Reads submodel definitions from ablation_config.yaml, parses CTRAMP .xls UEC
workbooks and ActivitySim spec/coefficient CSVs, writes a single HTML file.

Usage:
    python scripts/migration_validation/compare_coefficients.py
"""

from __future__ import annotations

import contextlib
import csv
import html
import logging
import sys
from pathlib import Path

import xlrd
import yaml

from uec_mappings import MAPPINGS

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


# -- ActivitySim reader --------------------------------------------------------

def read_asim_spec(configs_dir: Path, spec_file: str, coeff_file: str) -> dict:  # noqa: C901
    """Parse spec + coefficients into {alt_names, rows: [{label, desc, expr, coeffs}]}."""
    # Coefficient lookup
    coeff_path = configs_dir / coeff_file
    coeffs: dict[str, float] = {}
    if coeff_path.exists():
        with coeff_path.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    coeffs[row["coefficient_name"].strip()] = float(row["value"])
                except (ValueError, KeyError):
                    coeffs[row["coefficient_name"].strip()] = row.get("value", "")

    spec_path = configs_dir / spec_file
    if not spec_path.exists():
        return {"alt_names": [], "rows": []}

    with spec_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        skip = {"Label", "Description", "Expression", "coefficient", ""}
        alt_names = [c for c in fields if c not in skip]

        rows = []
        for row in reader:
            label = (row.get("Label") or "").strip()
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

def _mapped_table(name: str, sheets: list[dict], spec: dict) -> str:
    """Render an outer-join comparison table if a mapping exists for this submodel."""
    crosswalk = MAPPINGS.get(name)
    if not crosswalk:
        return ""

    # Index CTRAMP rows by row number (across all sheets)
    ctramp_by_no: dict[int, dict] = {}
    for s in sheets:
        for r in s["rows"]:
            ctramp_by_no[r["no"]] = r

    # Index ActivitySim rows by label
    asim_by_label: dict[str, dict] = {}
    for r in spec["rows"]:
        asim_by_label[r["label"]] = r

    used_ctramp: set[int] = set()
    used_asim: set[str] = set()

    h = ("<table class='coeff mapped'><thead><tr>"
         "<th>ASim Label</th><th>CTRAMP No.</th>"
         "<th>CTRAMP Formula</th><th>ASim Expression</th>"
         "<th>CTRAMP Coeff</th><th>ASim Coeff</th><th>Diff</th>"
         "</tr></thead><tbody>")
    body = ""

    def _coeff_val(row: dict) -> str:
        if not row or not row.get("coeffs"):
            return ""
        return next(iter(row["coeffs"].values()))

    def _diff_cell(c_val, a_val) -> str:
        if c_val == "" or a_val == "":
            return "<td></td>"
        try:
            diff = float(a_val) - float(c_val)
            cls = "match" if abs(diff) < 1e-6 else "diff"
            return f"<td class='num {cls}'>{diff:+.6g}</td>"
        except (ValueError, TypeError):
            return "<td></td>"

    # Matched rows (driven by crosswalk: asim_label → ctramp_no)
    for asim_label, ctramp_no in crosswalk.items():
        cr = ctramp_by_no.get(ctramp_no)
        ar = asim_by_label.get(asim_label)
        used_ctramp.add(ctramp_no)
        used_asim.add(asim_label)

        c_coeff = _coeff_val(cr)
        a_coeff = _coeff_val(ar)

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

        body += (
            f"<tr class='{cls}'>"
            f"<td>{esc(asim_label)}</td>"
            f"<td>{cr['no'] if cr else ''}</td>"
            f"<td>{esc(cr['formula']) if cr else ''}</td>"
            f"<td>{esc(ar['expr']) if ar else ''}</td>"
            f"<td class='num'>{_fmt(c_coeff) if c_coeff != '' else ''}</td>"
            f"<td class='num'>{_fmt(a_coeff) if a_coeff != '' else ''}</td>"
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
                    f"<td>{esc(r['formula'])}</td>"
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
                f"<td></td><td></td>"
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
    return f"<h3>Mapped Comparison</h3>{legend}{h}{body}</tbody></table>"


# -- HTML rendering ------------------------------------------------------------

def _fmt(v: float | str) -> str:
    if isinstance(v, float):
        return f"{int(v)}" if v == int(v) and abs(v) < 1000 else f"{v:.6g}"  # noqa: PLR2004
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


def _size_terms_table(ctramp_dir: Path, asim_dir: Path, st_cfg: dict) -> str:
    def _read(p: Path) -> list[dict]:
        if not p.exists():
            return []
        with p.open(encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    cr = _read(ctramp_dir / st_cfg["ctramp"])
    ar = _read(asim_dir / st_cfg["asim"])
    if not cr and not ar:
        return "<p>No size-term data.</p>"

    def _key(row: dict) -> str:
        p = row.get("purpose") or row.get("model_selector", "")
        return f"{p}|{row.get('segment', '')}".lower().replace(" ", "")

    sample = cr[0] if cr else ar[0]
    skip = {"purpose", "segment", "model_selector"}
    vcols = [k for k in sample if k.lower() not in skip]
    cm, am = {_key(r): r for r in cr}, {_key(r): r for r in ar}
    keys = list(dict.fromkeys(list(cm) + list(am)))

    h = ("<table class='coeff'><thead><tr><th>Segment</th>"
         + "".join(f"<th>CTRAMP {esc(v)}</th><th>ASim {esc(v)}</th>" for v in vcols)
         + "</tr></thead><tbody>")
    body = ""
    for k in keys:
        c, a = cm.get(k, {}), am.get(k, {})
        cells = ""
        for v in vcols:
            cv, av = c.get(v, ""), a.get(v, "")
            try:
                cf, af = float(cv), float(av)
                cls = "match" if abs(cf - af) < 1e-6 else "diff"  # noqa: PLR2004
                cells += f"<td class='num {cls}'>{cf:.6g}</td><td class='num {cls}'>{af:.6g}</td>"
            except (ValueError, TypeError):
                cells += f"<td class='num'>{esc(str(cv))}</td><td class='num'>{esc(str(av))}</td>"
        body += f"<tr><td>{esc(k.replace('|', ' / '))}</td>{cells}</tr>"
    return f"<h3>Size Terms</h3>{h}{body}</tbody></table>"


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
table.mapped td { white-space: nowrap; max-width: 280px; overflow: hidden; text-overflow: ellipsis; }
table.mapped td:nth-child(1) { font-family: Consolas, monospace; font-size: 12px; }
.legend { margin: 8px 0; font-size: 13px; }
.legend .swatch { display: inline-block; width: 14px; height: 14px; vertical-align: middle;
  border: 1px solid #aaa; margin-right: 3px; margin-left: 10px; }
.legend .swatch.match { background: #d4edda; }
.legend .swatch.diff { background: #f8d7da; }
.legend .swatch.ctramp-only { background: #d6eaf8; }
.legend .swatch.asim-only { background: #fdebd0; }
.file-paths { margin: 10px 0; padding: 10px 15px; background: #f5f5f5; border-radius: 4px;
  font-size: 13px; line-height: 1.6; border: 1px solid #ddd; }
.file-paths code { background: #e8e8e8; padding: 2px 5px; border-radius: 3px; font-size: 12px; }
</style>"""


def build_report(cfg: dict) -> Path:
    repo = Path(cfg["repo_root"])
    cc = cfg["coefficient_comparison"]
    ctramp_dir = repo / cc["ctramp_model_dir"]
    asim_dir = repo / cc["asim_configs_dir"]
    out = Path(cfg["output_dir"]) / "coefficient_comparison.html"

    tabs: list[tuple[str, str]] = []
    for sm in cc["submodels"]:
        log.info("Processing %s ...", sm["name"])
        sheets = read_uec_sheets(ctramp_dir, sm["ctramp_file"], sm["ctramp_sheets"])
        spec = read_asim_spec(asim_dir, sm["asim_spec"], sm["asim_coefficients"])

        # File paths banner
        ctramp_path = cc["ctramp_model_dir"] + "/" + sm["ctramp_file"]
        asim_spec_path = cc["asim_configs_dir"] + "/" + sm["asim_spec"]
        asim_coeff_path = cc["asim_configs_dir"] + "/" + sm["asim_coefficients"]
        paths_html = (
            f"<div class='file-paths'>"
            f"<b>CTRAMP:</b> <code>{esc(ctramp_path)}</code> "
            f"[{', '.join(sm['ctramp_sheets'])}]<br>"
            f"<b>ActivitySim:</b> <code>{esc(asim_spec_path)}</code> + "
            f"<code>{esc(asim_coeff_path)}</code>"
            f"</div>"
        )

        # 1:1 mapped comparison (if mapping exists for this submodel)
        mapped_html = _mapped_table(sm["name"], sheets, spec)

        # Original raw tables
        parts = [f"<div style='margin:10px 0;padding:10px;border-left:3px solid #3498db'>"
                 f"{_uec_table(s)}</div>" for s in sheets]
        if spec["rows"]:
            parts.append(f"<div style='margin:10px 0;padding:10px;"
                         f"border-left:3px solid #e67e22'>{_asim_table(spec)}</div>")
        n_uec = sum(len(s["rows"]) for s in sheets)
        summary = (f"<div style='margin:10px 0;padding:10px 15px;background:#eef;"
                   f"border-radius:4px;font-size:14px'>"
                   f"CTRAMP: {n_uec} rows / {len(sheets)} sheet(s) &bull; "
                   f"ActivitySim: {len(spec['rows'])} rows</div>")
        tab_body = paths_html + mapped_html + summary + "\n".join(parts)
        tabs.append((sm["name"], tab_body))

    if "size_terms" in cc:
        tabs.append(("Size Terms", _size_terms_table(ctramp_dir, asim_dir, cc["size_terms"])))

    buttons, panels = [], []
    for i, (title, content) in enumerate(tabs):
        active = " active" if i == 0 else ""
        buttons.append(f"<button class='{active.strip()}' "
                       f"onclick=\"showTab('t{i}')\">{esc(title)}</button>")
        panels.append(f"<div id='t{i}' class='tab-content{active}'>{content}</div>")

    html_doc = f"""\
<!DOCTYPE html><html><head><meta charset="utf-8">
<title>CTRAMP vs ActivitySim Coefficients</title>{CSS}</head><body>
<h1>CTRAMP vs ActivitySim Coefficient Comparison</h1>
<div class="tab-bar">{"".join(buttons)}</div>
{"".join(panels)}
<script>
function showTab(id){{
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab-bar button').forEach(b=>b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  event.target.classList.add('active');
}}
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
