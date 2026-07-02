"""Validate the Cube-free transit skims against the reference trnskm TPPs.

Builds every run type (15 access/line-haul/egress) x 5 periods from the SOURCE transit
network -- bus in-vehicle times from the reference congested network (avgload5period,
iter3) so the comparison is apples-to-apples with Cube -- LOS-skims each, validates one
exact operator-fare pass per run type, and writes a CUBE/Aeq/%diff/correlation
scorecard (per run-component CSV + a component-level summary).

Run it:

    python scripts/validate_transit_skims.py --threads 24 --log run.log

Monitor from another shell:

    tail -f run.log

``--skip-fare`` runs only the fast LOS skims (no expensive operator-fare graph) for a
quick ~20-minute LOS-only pass.  ``--runs wlk_loc_wlk,wlk_hvy_wlk`` limits the battery.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
from pathlib import Path

os.environ.setdefault("AEQ_SHOW_PROGRESS", "FALSE")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from cubeio import read_tpp
from tm1.assignment.aeq.fares import load_fares
from tm1.assignment.aeq.transit import build_transit_graph, skim_transit, TransitParams
from tm1.assignment.aeq.transit_network import build_ride_links, bus_time_table, parse_lin
from tm1.assignment.aeq.transit_skims import ACCESS_EGRESS, LINEHAULS, PERIODS, _assemble

# component -> (reference trnskm matrix, scale to actual units)
_REFKEY = {"TOTIVT": ("ivt", 100), "IWAIT": ("iwait", 100), "XWAIT": ("xwait", 100),
           "WAUX": ("waux", 100), "BOARDS": ("boards", 1), "FARE": ("fare", 1),
           "DTIM": ("dtime", 100), "DDIST": ("ddist", 100)}
_KEYIVT_REF = {"lrf": "ivtLRF", "exp": "ivtEXP", "hvy": "ivtHVY", "com": "ivtCOM"}

log = logging.getLogger("validate")

# a blocking skim gives no internal progress, so we tick elapsed vs a rough expected
# time (fare skim ~ vertices/4500 s; LOS ~ 18 s) -> a % that reads as progress.
_PHASE = {"label": "", "t0": 0.0, "exp": 1.0}


def _phase(label: str, exp: float = 1.0):
    _PHASE.update(label=label, t0=time.time(), exp=max(exp, 1.0))
    if label:                                   # announce start immediately (no silence)
        log.info("  > %s (expect ~%.0fs) ...", label, exp)


def _ticker():
    while True:
        time.sleep(30)
        if _PHASE["label"]:
            el = time.time() - _PHASE["t0"]
            log.info("    ... %s  %.0fs/~%.0fs (%.0f%%)", _PHASE["label"], el,
                     _PHASE["exp"], min(99, 100 * el / _PHASE["exp"]))


def _score(ref, aeq, reach):
    ref = np.asarray(ref, float)
    m = reach & ((ref > 0) | (aeq > 0))
    if int(m.sum()) < 3:
        return None
    cu, ae = ref[m], aeq[m]
    pct = 100 * (ae.mean() - cu.mean()) / cu.mean() if cu.mean() else 0.0
    return cu.mean(), ae.mean(), pct, float(np.corrcoef(cu, ae)[0, 1]), int(m.sum())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", default="E:/aeq_inputs", help="aeq transit inputs dir")
    ap.add_argument("--reference", default="//MODEL3-C/Model3C-Share/Projects/"
                    "2023_TM161_IPA_35_testrun", help="reference run (trnskm TPPs)")
    ap.add_argument("--threads", type=int, default=24, help="skim threads (default 24)")
    ap.add_argument("--out", default="transit_skim_scorecard", help="scorecard path stem")
    ap.add_argument("--log", default="transit_skim_validation.log", help="progress log")
    ap.add_argument("--skip-fare", action="store_true", help="LOS only (fast, no fare)")
    ap.add_argument("--runs", default="", help="comma-separated run types (default all)")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(args.log, mode="w")])
    inp, ref = Path(args.inputs), args.reference

    run_types = [f"{a}_{lh}_{e}" for a, e, _, _ in ACCESS_EGRESS for lh in LINEHAULS]
    if args.runs:
        want = set(args.runs.split(","))
        run_types = [r for r in run_types if r in want]
    total = len(run_types) * len(PERIODS)
    log.info("PID %d | %d run types x %d periods = %d skims | %d threads | fare=%s",
             os.getpid(), len(run_types), len(PERIODS), total, args.threads,
             not args.skip_fare)
    log.info("tail -f %s", Path(args.log).resolve())

    threading.Thread(target=_ticker, daemon=True).start()
    _phase("loading inputs + building ride networks", 60)
    links = pd.read_csv(inp / "highway_links.csv")
    links.columns = [c.strip() for c in links.columns]
    lines = parse_lin(inp / "transitLines.lin")
    ld = pd.read_parquet(inp / "link_distance.parquet")
    link_dist = {(int(a), int(b)): float(x) for a, b, x in zip(ld.A, ld.B, ld.distance)}
    rtd = pd.read_parquet(inp / "ref_ride_time.parquet")
    ref_time = {(int(a), int(b)): float(t) for a, b, t in zip(rtd.A, rtd.B, rtd.time)}
    fares = load_fares(inp / "fares", link_dist, lines)
    sl = pd.read_parquet(inp / "support_links.parquet")
    ride, hw = {}, {}
    for p in PERIODS:
        ride[p], hw[p] = build_ride_links(lines, p, bus_time_table(links, p),
                                          link_dist, ref_time)
    _phase("")
    log.info("inputs ready -- starting %d skims (%d run types x %d periods)",
             total, len(run_types), len(PERIODS))

    lh_of = {f"{a}_{lh}_{e}": (lh, am, em) for a, e, am, em in ACCESS_EGRESS for lh in LINEHAULS}
    rows, done, t0 = [], 0, time.time()
    for rt in run_types:
        lh, amode, emode = lh_of[rt]
        sup = sl[sl["run_type"] == rt]
        fare_mat = None
        if not args.skip_fare:
            tb = time.time()
            _phase(f"{rt} fare graph build", 90)
            gf = build_transit_graph(_assemble(ride["AM"], sup), hw["AM"],
                                     TransitParams(linehaul=lh, spread_window=1.5),
                                     n_zones=1475, fares=fares, fare_states="operator",
                                     access_mode=amode, egress_mode=emode)
            _phase(f"{rt} fare skim", gf.n_vertices / 4500)
            fare_mat = skim_transit(gf, linehaul=lh, fares=fares, threads=args.threads,
                                    max_path_min=180.0)["FARE"]
            _phase("")
            log.info("  %s: fare graph %d verts skimmed in %.0fs", rt, gf.n_vertices,
                     time.time() - tb)
        for p in PERIODS:
            _phase(f"{rt} {p} LOS skim", 18)
            g = build_transit_graph(_assemble(ride[p], sup), hw[p],
                                    TransitParams(linehaul=lh, spread_window=1.5),
                                    n_zones=1475, fares=fares, fare_states="none",
                                    access_mode=amode, egress_mode=emode)
            sk = skim_transit(g, linehaul=lh, fares=fares, threads=args.threads,
                              max_path_min=180.0)
            _phase("")
            if fare_mat is not None:
                sk["FARE"] = fare_mat
            try:
                R = read_tpp(f"{ref}/skims/trnskm{p.lower()}_{rt}.tpp")["data"]
            except Exception as e:  # noqa: BLE001
                log.warning("  %s %s: no reference (%s)", rt, p, str(e)[:50])
                done += 1
                continue
            reach = (np.asarray(R["ivt"], float) > 0) & (sk["TOTIVT"] > 0)
            comps = ["TOTIVT", "IWAIT", "XWAIT", "WAUX", "BOARDS"]
            if not args.skip_fare:
                comps.append("FARE")
            if lh in _KEYIVT_REF:
                comps.append("KEYIVT")
            if rt.startswith("drv") or rt.endswith("drv"):
                comps += ["DTIM", "DDIST"]
            cells = []
            for c in comps:
                refk = _KEYIVT_REF[lh] if c == "KEYIVT" else _REFKEY[c][0]
                scale = 1 if c == "KEYIVT" else _REFKEY[c][1]
                s = _score(np.asarray(R[refk], float) / scale, sk[c], reach)
                if s:
                    rows.append((rt, p, c, *s))
                    cells.append(f"{c} {s[2]:+.0f}%/{s[3]:.2f}")
            done += 1
            eta = (time.time() - t0) / done * (total - done)
            log.info("[%2d/%2d %3.0f%% ETA %4.1fm] %s %s (%s od): %s",
                     done, total, 100 * done / total, eta / 60, rt, p,
                     f"{int(reach.sum()):,}", "  ".join(cells))

    _phase("")
    df = pd.DataFrame(rows, columns=["run", "period", "comp", "cube", "aeq", "pct", "corr", "n"])
    df.to_csv(Path(args.out).with_suffix(".csv"), index=False)
    lines_out = [f"\nTRANSIT SKIM VALIDATION | {len(df)} cells | {time.time()-t0:.0f}s "
                 f"@ {args.threads} threads", f"{'component':9s} {'runs':>4s} "
                 f"{'%diff med':>9s} {'%diff mean':>10s} {'corr med':>9s}"]
    for c in ["TOTIVT", "KEYIVT", "IWAIT", "XWAIT", "WAUX", "BOARDS", "FARE", "DTIM", "DDIST"]:
        d = df[df["comp"] == c]
        if len(d):
            lines_out.append(f"{c:9s} {len(d):4d} {d['pct'].median():+9.1f} "
                             f"{d['pct'].mean():+10.1f} {d['corr'].median():9.3f}")
    summary = "\n".join(lines_out)
    Path(args.out).with_suffix(".txt").write_text(summary)
    log.info(summary)
    log.info("wrote %s.csv / .txt", args.out)


if __name__ == "__main__":
    main()
