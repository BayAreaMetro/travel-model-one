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
import gc
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
from tm1.assignment.aeq.transit_skims import (
    ACCESS_EGRESS, LINEHAULS, PERIODS, SKIM_MAXPATH_PERCEIVED, SKIM_WAIT_PERCEIVE,
    _assemble, _skim_params)

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
    # only slow phases (>=30s: input load, fare graph) get a live bar; fast LOS skims
    # just print their result line.  The bar redraws one line in place on stderr, so it
    # never floods the log.
    if _PHASE["label"]:                                  # clear the previous bar line
        sys.stderr.write("\r" + " " * 78 + "\r")
        sys.stderr.flush()
    _PHASE.update(label=label if exp >= 30 else "", t0=time.time(), exp=max(exp, 1.0))


def _ticker():
    while True:
        time.sleep(2)
        lbl = _PHASE["label"]
        if lbl:
            el = time.time() - _PHASE["t0"]
            pct = min(99.0, 100 * el / _PHASE["exp"])
            n = int(pct / 100 * 22)
            sys.stderr.write(f"\r  {lbl:38.38s} [{'#'*n}{'.'*(22-n)}] {pct:2.0f}% ")
            sys.stderr.flush()


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
        level=logging.INFO, format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(args.log, mode="w")])
    inp, ref = Path(args.inputs), args.reference

    run_types = [f"{a}_{lh}_{e}" for a, e, _, _ in ACCESS_EGRESS for lh in LINEHAULS]
    if args.runs:
        want = set(args.runs.split(","))
        run_types = [r for r in run_types if r in want]
    total = len(run_types) * len(PERIODS)
    log.info("transit skim validation | %d skims | %d threads | fare %s (pid %d)",
             total, args.threads, "on" if not args.skip_fare else "off", os.getpid())
    log.info("tail: %s\n", Path(args.log).resolve())

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
    # separate fare / LOS timing so the ETA is not thrown off by the one-time fare cost
    rows, done, t0 = [], 0, time.time()
    fare_secs = los_secs = 0.0
    fare_n = los_n = 0
    n_rt = len(run_types)
    # write the CSV incrementally + flush so a stall/kill never loses finished work
    csv_path = Path(args.out).with_suffix(".csv")
    csv_f = csv_path.open("w")
    csv_f.write("run,period,comp,cube,aeq,pct,corr,n\n")
    for rt in run_types:
        lh, amode, emode = lh_of[rt]
        access, _, egress = rt.split("_")
        params = _skim_params(lh, access, egress, 1.5)
        sup = sl[sl["run_type"] == rt]
        fare_mat = None
        if not args.skip_fare:
            tb = time.time()
            _phase(f"{rt}: building fare graph", 90)
            gf = build_transit_graph(_assemble(ride["AM"], sup), hw["AM"], params,
                                     n_zones=1475, fares=fares, fare_states="operator",
                                     access_mode=amode, egress_mode=emode)
            _phase(f"{rt}: skimming fare ({gf.n_vertices/1000:.0f}k verts)", gf.n_vertices / 4500)
            fare_mat = skim_transit(gf, linehaul=lh, fares=fares, threads=args.threads,
                                    max_path_min=180.0, wait_perceive=SKIM_WAIT_PERCEIVE,
                                    max_perceived_min=SKIM_MAXPATH_PERCEIVED)["FARE"]
            _phase("")
            fare_secs += time.time() - tb
            fare_n += 1
            del gf                                   # free the big operator graph
            gc.collect()
        for p in PERIODS:
            tl = time.time()
            g = build_transit_graph(_assemble(ride[p], sup), hw[p], params,
                                    n_zones=1475, fares=fares, fare_states="none",
                                    access_mode=amode, egress_mode=emode)
            sk = skim_transit(g, linehaul=lh, fares=fares, threads=args.threads,
                              max_path_min=180.0, wait_perceive=SKIM_WAIT_PERCEIVE,
                              max_perceived_min=SKIM_MAXPATH_PERCEIVED)
            del g
            los_secs += time.time() - tl
            los_n += 1
            if fare_mat is not None:
                sk["FARE"] = fare_mat
            done += 1
            try:
                R = read_tpp(f"{ref}/skims/trnskm{p.lower()}_{rt}.tpp")["data"]
            except Exception as e:  # noqa: BLE001
                log.warning("  %s %s: no reference (%s)", rt, p, str(e)[:50])
                continue
            reach = (np.asarray(R["ivt"], float) > 0) & (sk["TOTIVT"] > 0)
            comps = ["TOTIVT", "IWAIT", "XWAIT", "WAUX", "BOARDS"]
            if not args.skip_fare:
                comps.append("FARE")
            if lh in _KEYIVT_REF:
                comps.append("KEYIVT")
            if rt.startswith("drv") or rt.endswith("drv"):
                comps += ["DTIM", "DDIST"]
            for c in comps:                          # full detail streamed to the CSV
                refk = _KEYIVT_REF[lh] if c == "KEYIVT" else _REFKEY[c][0]
                scale = 100 if c == "KEYIVT" else _REFKEY[c][1]   # ivt{MODE} is x100 too
                s = _score(np.asarray(R[refk], float) / scale, sk[c], reach)
                if s:
                    rows.append((rt, p, c, *s))
                    csv_f.write(f"{rt},{p},{c},{s[0]:.4f},{s[1]:.4f},{s[2]:.4f},{s[3]:.4f},{s[4]}\n")
            csv_f.flush()
            # ETA = remaining fare passes (one per run type) + remaining LOS skims
            avg_fare, avg_los = fare_secs / max(fare_n, 1), los_secs / max(los_n, 1)
            eta = ((n_rt - fare_n) * avg_fare + (total - done) * avg_los) / 60
            log.info("  [%2d/%d] %-11s %s   ETA %3.0fm", done, total, rt, p, eta)

    csv_f.close()
    _phase("")
    df = pd.DataFrame(rows, columns=["run", "period", "comp", "cube", "aeq", "pct", "corr", "n"])
    # report ABSOLUTE (n-weighted cube/aeq means, in native units) alongside % and corr, so a
    # big-% / small-minute residual is not mistaken for a real error (and vice versa).
    lines_out = [f"\nTRANSIT SKIM VALIDATION | {len(df)} cells | {time.time()-t0:.0f}s "
                 f"@ {args.threads} threads",
                 f"{'component':9s} {'runs':>4s} {'cube':>8s} {'aeq':>8s} {'d(abs)':>8s} "
                 f"{'%diff med':>9s} {'corr med':>9s}"]
    for c in ["TOTIVT", "KEYIVT", "IWAIT", "XWAIT", "WAUX", "BOARDS", "FARE", "DTIM", "DDIST"]:
        d = df[df["comp"] == c]
        if len(d):
            w = d["n"].to_numpy()
            cu, ae = np.average(d["cube"], weights=w), np.average(d["aeq"], weights=w)
            lines_out.append(f"{c:9s} {len(d):4d} {cu:8.2f} {ae:8.2f} {ae-cu:+8.2f} "
                             f"{d['pct'].median():+9.1f} {d['corr'].median():9.3f}")
    summary = "\n".join(lines_out)
    Path(args.out).with_suffix(".txt").write_text(summary)
    log.info("\n  done in %.0fm  ->  %s.csv", (time.time() - t0) / 60, args.out)
    log.info(summary)


if __name__ == "__main__":
    main()
