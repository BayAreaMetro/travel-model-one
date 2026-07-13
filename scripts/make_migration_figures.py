"""Regenerate the aequilibrae_migration.md figures from the validation scorecard.

Reads ``docs/aeq_scorecards/scorecard_final.csv`` (written by
``scripts/validate_transit_skims.py``) and writes ``fit_scatter.png``,
``fit_dist.png`` and ``perf_bars.png`` to ``docs/figures/`` at 140 dpi.
Palette: dataviz validated categorical (blue #2a78d6, orange #eb6834), light surface.
The perf-bar minutes are measured constants (see the doc's Section 3); update them
there and here together.

``--od`` additionally rebuilds ``fit_od_scatter.png`` (the OD-level density panels:
local-bus IVT, commuter IVT, commuter fare, AM peak).  That mode recomputes the two
AM skims from source (~6 min; needs ``E:/aeq_inputs`` and the reference trnskm TPPs).
"""
# ruff: noqa: E402  (mpl backend and sys.path must be configured before their imports)
import argparse
import sys
from pathlib import Path

import matplotlib as mpl
import numpy as np
import pandas as pd

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from cubeio import read_tpp
from tm1.assignment.aeq.fares import load_fares
from tm1.assignment.aeq.transit import build_transit_graph, skim_transit
from tm1.assignment.aeq.transit_network import build_ride_links, bus_time_table, parse_lin
from tm1.assignment.aeq.params import load_aeq_params
from tm1.assignment.aeq.transit_skims import _assemble, _union_service, skim_params

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID, BASE, SURF = "#0b0b0b", "#898781", "#e1e0d9", "#c3c2b7", "#ffffff"
mpl.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": BASE, "axes.labelcolor": INK, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
})

OUT = REPO / "docs" / "figures"
OUT.mkdir(exist_ok=True)
df = pd.read_csv(REPO / "docs" / "aeq_scorecards" / "scorecard_final.csv")

# component display: (scorecard key, label, unit)
COMP = [("TOTIVT", "In-vehicle time", "min"), ("KEYIVT", "Premier-mode IVT", "min"),
        ("IWAIT", "Initial wait", "min"), ("XWAIT", "Transfer wait", "min"),
        ("WAUX", "Transfer walk", "min"), ("BOARDS", "Boardings", "#"),
        ("FARE", "Fare", "cents"), ("DTIM", "Drive time", "min"),
        ("DDIST", "Drive dist", "mi")]

# ---- Fig 1: cell-level Aeq vs Cube scatter, one facet per component, y=x ----
fig, axes = plt.subplots(3, 3, figsize=(8.4, 8.2))
for ax, (c, name, unit) in zip(axes.flat, COMP, strict=True):
    d = df[df.comp == c]
    lo, hi = 0, max(d.cube.max(), d.aeq.max()) * 1.06
    ax.plot([lo, hi], [lo, hi], color=MUTED, lw=1.0, ls="--", zorder=1)
    ax.scatter(d.cube, d.aeq, s=26, color=BLUE, alpha=0.75, edgecolor="white",
               linewidth=0.4, zorder=2)
    r = np.corrcoef(d.cube, d.aeq)[0, 1]
    ax.set_title(f"{name}  (r={r:.3f})", fontsize=9.5, color=INK, pad=4)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.tick_params(labelsize=8)
    ax.set_xlabel(f"Cube ({unit})", fontsize=8)
    ax.set_ylabel(f"Aeq ({unit})", fontsize=8)
fig.suptitle("Transit skims: AequilibraE vs Cube, each point one run x period x "
             "component (610 cells)", fontsize=11.5, color=INK, y=0.998)
fig.text(0.5, 0.965, "dashed line = exact agreement (y=x)", ha="center",
         fontsize=8.5, color=MUTED)
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig(OUT / "fit_scatter.png", dpi=140)
plt.close(fig)

# ---- Fig 2: distribution of per-cell % difference, box per component ----
fig, ax = plt.subplots(figsize=(7.6, 4.6))
data = [df[df.comp == c].pct.to_numpy() for c, _, _ in COMP]
labels = [n for _, n, _ in COMP]
ax.axvspan(-5, 5, color="#eef4fb", zorder=0)                 # +-5% acceptance band
ax.axvline(0, color=BASE, lw=1.0, zorder=1)
ax.boxplot(data, vert=False, widths=0.62, patch_artist=True, showfliers=True,
           flierprops={"marker": "o", "ms": 3, "mfc": ORANGE, "mec": "none", "alpha": 0.6},
           medianprops={"color": "white", "lw": 1.6},
           whiskerprops={"color": BASE}, capprops={"color": BASE},
           boxprops={"facecolor": BLUE, "edgecolor": "none"})
ax.set_yticklabels(labels, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Per-cell difference, Aeq vs Cube (%)", fontsize=9.5)
ax.set_xlim(-30, 30)
ax.set_title("Every run x period x component cell (shaded = +-5% band)",
             fontsize=10.5, color=INK)
fig.tight_layout()
fig.savefig(OUT / "fit_dist.png", dpi=140)
plt.close(fig)

# ---- Fig 3: performance, grouped horizontal bars ----
steps = ["Highway\nassignment", "Transit\nassignment", "Transit skims\n(LOS, per iteration)"]
CUBE_MIN = [26.5, 11.0, 222.0]          # reference-run logs (MODEL3-C)
AEQ_MIN = [10.0, 6.0, 16.0]             # measured on TM2-B
FARE_ONE_TIME = 7.0                     # sparse-state exact-fare pass, 15 run types
y = np.arange(len(steps))
h = 0.36
fig, ax = plt.subplots(figsize=(7.6, 4.0))
ax.barh(y + h / 2, CUBE_MIN, h, color=ORANGE, label="Cube", zorder=2)
ax.barh(y - h / 2, AEQ_MIN, h, color=BLUE, label="AequilibraE", zorder=2)
# one-time exact-fare pass: same entity (Aeq blue) but not a recurring cost ->
# dashed outline, no fill, stacked after the per-iteration transit-skim bar
gap = 0.9                               # ~2px surface gap at this axis span
ax.barh(y[2] - h / 2, FARE_ONE_TIME, h, left=AEQ_MIN[2] + gap, facecolor="none",
        edgecolor=BLUE, linestyle=(0, (4, 3)), linewidth=1.3, zorder=2)
for yi, (cv, av) in enumerate(zip(CUBE_MIN, AEQ_MIN, strict=True)):
    ax.text(cv + 3, yi + h / 2, f"{cv:.0f}", va="center", fontsize=8.5, color="#52514e")
    if yi < len(steps) - 1:   # last row gets the combined per-iter + one-time label
        ax.text(av + 3, yi - h / 2, f"{av:.0f}", va="center", fontsize=8.5,
                color="#52514e")
ax.text(AEQ_MIN[2] + gap + FARE_ONE_TIME + 3, y[2] - h / 2,
        "16 /iter  +7 one-time fare pass", va="center", fontsize=8.5, color="#52514e")
ax.set_yticks(y)
ax.set_yticklabels(steps, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Wall-clock minutes per iteration", fontsize=9.5)
handles = [Patch(facecolor=ORANGE, label="Cube"),
           Patch(facecolor=BLUE, label="AequilibraE"),
           Patch(facecolor="none", edgecolor=BLUE, linestyle=(0, (4, 3)), linewidth=1.3,
                 label="Aeq one-time fare pass (cached)")]
ax.legend(handles=handles, frameon=False, fontsize=9, loc="upper right")
ax.grid(axis="y", visible=False)
ax.set_title("Runtime per iteration  (Cube recomputes fare every iteration; Aeq caches it)",
             fontsize=10, color=INK)
fig.text(0.01, -0.04,
         "Hardware: Both Xeon Gold 6338 (TM2-B: 24 cores/48 vCPUs; TM3-C: 8 cores/16 vCPUs).\n"
         "Cube hard-capped at 15 single-threaded processes; Aeq scales to 48 threads "
         "(6 workers x 8 threads for LOS, 4 workers x 12 threads for fare).\n"
         "Dashed = one-time exact-fare pass (cached); Cube recomputes fare each iteration.",
         fontsize=7.3, color=MUTED)
fig.tight_layout()
fig.savefig(OUT / "perf_bars.png", dpi=140, bbox_inches="tight")
plt.close(fig)

print("wrote:", "fit_scatter.png", "fit_dist.png", "perf_bars.png", "->", OUT)


# ---- Fig 4 (--od): OD-level density, AM peak -- recomputed from source ----
def make_od_scatter(inputs: str, reference: str, threads: int) -> None:
    """Rebuild fit_od_scatter.png: hexbin Aeq-vs-Cube at the OD-pair level, AM.

    Panels: local-bus IVT (wlk_loc_wlk), commuter IVT and commuter fare
    (wlk_com_wlk, exact union-service fare pass merged as in production).
    """
    inp = Path(inputs)
    links = pd.read_csv(inp / "highway_links.csv")
    links.columns = [c.strip() for c in links.columns]
    lines = parse_lin(inp / "transitLines.lin")
    ld = pd.read_parquet(inp / "link_distance.parquet")
    link_dist = {(int(a), int(b)): float(x) for a, b, x
                 in zip(ld.A, ld.B, ld.distance, strict=False)}
    rtd = pd.read_parquet(inp / "ref_ride_time.parquet")
    ref_time = {(int(a), int(b)): float(t) for a, b, t
                in zip(rtd.A, rtd.B, rtd.time, strict=False)}
    P = load_aeq_params()
    fares = load_fares(inp / "fares", link_dist, lines, rail_fare=P.rail_fare)
    sl = pd.read_parquet(inp / "support_links.parquet")
    ride, hw = {}, {}
    for p in P.periods.names:
        ride[p], hw[p] = build_ride_links(lines, p, bus_time_table(links, p, P.bus_time),
                                          link_dist, ref_time, bus_cfg=P.bus_time,
                                          freq_field=P.periods.freq_field)
    ride_u, hw_u = _union_service(ride, hw, P)

    def one_run(rt: str) -> dict:
        access, lh, egress = rt.split("_")
        params = skim_params(lh, access, egress, P)
        sup = sl[sl["run_type"] == rt]
        kw = {"linehaul": lh, "fares": fares, "threads": threads,
              "wait_perceive": params.wait_perceive,
              "max_perceived_min": P.transit_cost.skim_max_perceived_min,
              "premier": params.key_band is not None}
        g = build_transit_graph(_assemble(ride["AM"], sup), hw["AM"], params,
                                n_zones=P.n_taz, fares=fares, fare_states="none",
                                access_mode=1, egress_mode=6)
        sk = skim_transit(g, rail_curve_fallback=True, **kw)
        gf = build_transit_graph(_assemble(ride_u, sup), hw_u, params, n_zones=P.n_taz,
                                 fares=fares, fare_states="operator",
                                 access_mode=1, egress_mode=6)
        fare = skim_transit(gf, **kw)["FARE"]
        sk["FARE"] = np.where(fare > 0, fare, sk["FARE"])
        return sk

    panels = []
    for rt, comp, refk, scale, label, unit in (
            ("wlk_loc_wlk", "TOTIVT", "ivt", 100, "Local bus IVT", "min"),
            ("wlk_com_wlk", "TOTIVT", "ivt", 100, "Commuter IVT", "min"),
            ("wlk_com_wlk", "FARE", "fare", 1, "Commuter fare", "cents")):
        if not panels or rt != panels[-1][0]:
            sk = one_run(rt)
            ref = read_tpp(f"{reference}/skims/trnskmam_{rt}.tpp")["data"]
        cu = np.asarray(ref[refk], float) / scale
        ae = sk[comp]
        reach = (np.asarray(ref["ivt"], float) > 0) & (sk["TOTIVT"] > 0)
        m = reach & ((cu > 0) | (ae > 0))
        panels.append((rt, label, unit, cu[m], ae[m]))

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.4))
    for ax, (_, label, unit, cu, ae) in zip(axes, panels, strict=True):
        hi = np.percentile(np.concatenate([cu, ae]), 99.5)
        ax.hexbin(cu, ae, gridsize=55, bins="log", cmap="Blues",
                  extent=(0, hi, 0, hi), mincnt=1)
        ax.plot([0, hi], [0, hi], color=MUTED, lw=1.2, ls="--")
        r = np.corrcoef(cu, ae)[0, 1]
        ax.set_title(f"{label} ({unit})\nr={r:.3f}, n={len(cu):,}",
                     fontsize=12, color=INK)
        ax.set_xlim(0, hi)
        ax.set_ylim(0, hi)
        ax.set_xlabel("Cube")
        ax.set_ylabel("Aeq")
    fig.suptitle("Every reachable OD pair, AM peak - dashed line = exact agreement "
                 "(density, log scale)", fontsize=13.5, color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "fit_od_scatter.png", dpi=140)
    plt.close(fig)
    print("wrote: fit_od_scatter.png ->", OUT)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--od", action="store_true",
                    help="also rebuild fit_od_scatter.png (recomputes 2 AM skims, ~6 min)")
    ap.add_argument("--inputs", default="E:/aeq_inputs")
    ap.add_argument("--reference", default="//MODEL3-C/Model3C-Share/Projects/"
                    "2023_TM161_IPA_35_testrun")
    ap.add_argument("--threads", type=int, default=24)
    args = ap.parse_args()
    if args.od:
        make_od_scatter(args.inputs, args.reference, args.threads)
