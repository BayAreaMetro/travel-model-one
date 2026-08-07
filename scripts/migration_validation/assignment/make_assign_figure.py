"""Regenerate the aequilibrae_migration.md §3 assignment figure from the scorecards.

Reads the two assignment scorecards written by ``validate_highway_assignment.py`` and
``validate_transit_assignment.py`` and draws a 3-panel aeq-vs-Cube scatter (highway class
volumes, transit boardings, transit link volumes), log-log with a y=x reference line, one
colour per period. Writes ``docs/figures/assign_scatter.png``.

    python scripts/migration_validation/assignment/make_assign_figure.py

Unlike the ad-hoc original, this is committed and reproducible: rerun it after refreshing
the scorecards to update the figure.
"""
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / "docs" / "figures"
OUT.mkdir(exist_ok=True)

INK, MUTED, GRID, BASE, SURF = "#0b0b0b", "#898781", "#e1e0d9", "#c3c2b7", "#ffffff"
# one colour per period (AM,MD,PM,EV,EA)
PCOL = {"AM": "#2a78d6", "MD": "#eb6834", "PM": "#2ca089", "EV": "#9b59b6", "EA": "#c0392b"}
mpl.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": BASE, "axes.labelcolor": INK, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
})


def _panel(ax, cube, aeq, period, title):
    cube = np.asarray(cube, float)
    aeq = np.asarray(aeq, float)
    ok = (cube > 0) & (aeq > 0) & np.isfinite(cube) & np.isfinite(aeq)
    cube, aeq, period = cube[ok], aeq[ok], np.asarray(period)[ok]
    lo, hi = min(cube.min(), aeq.min()) * 0.7, max(cube.max(), aeq.max()) * 1.4
    ax.plot([lo, hi], [lo, hi], color=MUTED, lw=1.0, ls="--", zorder=1)
    for p in ["AM", "MD", "PM", "EV", "EA"]:
        m = period == p
        if m.any():
            ax.scatter(cube[m], aeq[m], s=28, color=PCOL[p], alpha=0.8,
                       edgecolor="white", linewidth=0.4, label=p, zorder=3)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    # headline stats: median |%diff| and pooled correlation (log space)
    pct = np.median(np.abs(aeq / cube - 1.0)) * 100
    r = np.corrcoef(np.log(cube), np.log(aeq))[0, 1]
    ax.set_title(f"{title}\nmed |%diff| {pct:.1f}%   r {r:.3f}", fontsize=10)
    ax.set_xlabel("Cube"); ax.set_ylabel("aeq")


hwy = pd.read_csv(HERE / "scorecard_hwy_assign.csv")
hwy = hwy[hwy["class"] != "TOT_PCE"]  # per-class points, not the aggregate
trn = pd.read_csv(HERE / "scorecard_transit_assign.csv")

fig, axes = plt.subplots(1, 3, figsize=(12.4, 4.5))
_panel(axes[0], hwy.cube_vol, hwy.aeq_vol, hwy.period, "Highway link volume (per class)")
_panel(axes[1], trn.board_cube, trn.board_aeq, trn.period, "Transit boardings (per line-haul)")
_panel(axes[2], trn.link_cube, trn.link_aeq, trn.period, "Transit link volume (AB_VOL)")
axes[2].legend(title="period", frameon=False, fontsize=8, loc="lower right")
fig.suptitle("AequilibraE vs Cube — same trips, loaded network", fontsize=12, y=1.02)
fig.tight_layout()
fig.savefig(OUT / "assign_scatter.png", dpi=140, bbox_inches="tight")
print("wrote:", OUT / "assign_scatter.png")
