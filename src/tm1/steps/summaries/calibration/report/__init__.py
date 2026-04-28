"""Calibration HTML report generation.

Public API::

    from tm1.steps.summaries.calibration.report import write_report
    write_report(all_results, output_dir)
"""

from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from . import ao, cdap, commute_flows, wsloc
from .helpers import esc, load_template

# (submodel_key, tab_title, render_function)
_RENDERERS: list[tuple[str, str, object]] = [
    ("daily_activity_pattern", "Daily Activity Pattern", cdap.render),
    ("auto_ownership", "Auto Ownership", ao.render),
    ("work_school_location", "Work / School Location", wsloc.render),
    ("work_school_location", "Commuting Flows", commute_flows.render),
]


def write_report(
    all_results: dict[str, dict[str, dict[str, pl.DataFrame]]],
    output_dir: Path,
) -> Path:
    """Write ``calibration_report.html`` to *output_dir* and return the path."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    labels = list(all_results)
    tabs: list[tuple[str, str]] = []

    for submodel_key, title, renderer in _RENDERERS:
        per_label = {
            label: all_results[label].get(submodel_key, {})
            for label in labels
        }
        if any(per_label.values()):
            tabs.append((title, renderer(per_label, labels)))

    dest = output_dir / "calibration_report.html"
    if not tabs:
        return dest

    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    tab_buttons = ""
    tab_panes = ""
    for i, (title, content) in enumerate(tabs):
        active = " active" if i == 0 else ""
        display = "block" if i == 0 else "none"
        tab_id = f"tab{i}"
        tab_buttons += (
            f"<button class='tab-btn{active}' "
            f"onclick='showTab(\"{tab_id}\")'>"
            f"{esc(title)}</button>\n"
        )
        tab_panes += (
            f"<div id='{tab_id}' class='tab-pane' "
            f"style='display:{display}'>\n{content}\n</div>\n"
        )

    page_tmpl = load_template("page.html")
    html_str = page_tmpl.substitute(
        timestamp=timestamp,
        tab_buttons=tab_buttons,
        tab_panes=tab_panes,
    )
    dest.write_text(html_str, encoding="utf-8")
    return dest
