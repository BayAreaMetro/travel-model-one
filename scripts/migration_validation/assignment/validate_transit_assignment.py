"""Validate the aeq transit ASSIGNMENT against the reference Cube run.

Feeds Cube's *own* transit trip tables (main/trips{period}.tpp, one table per run type) to
the aeq Spiess-Florian assignment and compares the loaded network to Cube's:

* **per-line boardings** vs ``trn/trnline.csv`` (``total boardings`` by ``path id``);
* **per-link volumes** vs ``trn/trnlink.csv`` (``AB_VOL`` by ``(A, B)``, transit links only).

Feeding Cube's trips isolates the *assignment* (path/mode loading) from demand.  Cube
reports the single best path (integer boardings); aeq reports the strategy-expected value
(fractional) -- so per-OD differs, but per-line/per-link aggregates should agree.

    python scripts/validate_transit_assignment.py --threads 16 --log assign.log

Writes ``{--out}.csv`` (one row per run type x period) + a summary.
"""

import argparse
import logging
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from cubeio import read_tpp
from tm1.assignment.aeq.params import load_aeq_params
from tm1.assignment.aeq.transit import (assign_transit, boardings_by_line,
                                        build_transit_graph, link_volumes)
from tm1.assignment.aeq.transit_network import build_ride_links, bus_time_table, parse_lin
from tm1.assignment.aeq.transit_skims import _assemble, skim_params

LINEHAULS = ("loc", "lrf", "exp", "hvy", "com")
log = logging.getLogger("assign_val")


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.corrcoef(a, b)[0, 1]) if len(a) > 1 and a.std() and b.std() else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", default=r"E:\aeq_inputs")
    ap.add_argument("--reference", default=r"E:\ref_2023_TM161")
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--out", default="scorecard_assign")
    ap.add_argument("--log", default="assign_val.log")
    ap.add_argument("--runs", default="", help="comma-separated run types (default all 15)")
    ap.add_argument("--periods", default="AM,MD,PM,EV,EA")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s",
                        handlers=[logging.FileHandler(args.log, mode="w"), logging.StreamHandler()])
    inp, ref = Path(args.inputs), Path(args.reference)
    P = load_aeq_params()
    awp = P.transit_cost.assign_wait_perceive
    aemodes = {(a, e): (am, em) for a, e, am, em in P.skim_output.access_egress}
    run_types = (args.runs.split(",") if args.runs
                 else [f"{a}_{lh}_{e}" for a, e, _, _ in P.skim_output.access_egress
                       for lh in LINEHAULS])
    periods = args.periods.split(",")

    log.info("transit ASSIGNMENT validation | %d run types x %d periods | %d threads",
             len(run_types), len(periods), args.threads)

    links = pd.read_csv(inp / "highway_links.csv"); links.columns = [c.strip() for c in links.columns]
    lines = parse_lin(inp / "transitLines.lin")
    ld = pd.read_parquet(inp / "link_distance.parquet")
    link_dist = {(int(a), int(b)): float(x) for a, b, x in zip(ld.A, ld.B, ld.distance, strict=False)}
    rtd = pd.read_parquet(inp / "ref_ride_time.parquet")
    ref_time = {(int(a), int(b)): float(t) for a, b, t in zip(rtd.A, rtd.B, rtd.time, strict=False)}
    sl = pd.read_parquet(inp / "support_links.parquet")
    trnline = pd.read_csv(ref / "trn" / "trnline.csv")
    trnlink = pd.read_csv(ref / "trn" / "trnlink.csv",
                          usecols=["A", "B", "mode", "AB_VOL", "source"])
    trnlink = trnlink[trnlink["mode"] >= 10]                     # transit ride links only

    csv_path = Path(args.out).with_suffix(".csv")
    csv_f = csv_path.open("w")
    csv_f.write("run,period,board_cube,board_aeq,board_pct,board_r,n_lines,"
                "link_cube,link_aeq,link_pct,link_r,n_links\n")
    rows, done, t0 = [], 0, time.time()
    total = len(run_types) * len(periods)

    for period in periods:
        ride, hw = build_ride_links(lines, period, bus_time_table(links, period, P.bus_time),
                                    link_dist, ref_time, bus_cfg=P.bus_time,
                                    freq_field=P.periods.freq_field)
        demand = read_tpp(str(ref / "main" / f"trips{period.upper()}.tpp"))["data"]
        for rt in run_types:
            acc, lh, egr = rt.split("_")
            amode, emode = aemodes[(acc, egr)]
            dem = np.asarray(demand[rt], float)
            prm = replace(skim_params(lh, acc, egr, P), wait_perceive=awp)
            g = build_transit_graph(_assemble(ride, sl[sl.run_type == rt]), hw, prm,
                                    n_zones=P.n_taz, fares=None, fare_states="none",
                                    access_mode=amode, egress_mode=emode)
            vol = assign_transit(g, dem, threads=args.threads)

            # boardings vs trnline
            brd = boardings_by_line(vol, g)
            cb = trnline[trnline["path id"] == f"{period.lower()}_{rt}"].set_index("name")["total boardings"]
            jb = pd.DataFrame({"aeq": brd, "cube": cb}).fillna(0.0)
            jb = jb[(jb["aeq"] > 0) | (jb["cube"] > 0)]
            b_a, b_c = jb["aeq"].sum(), jb["cube"].sum()

            # link volumes vs trnlink
            alv = link_volumes(vol, g)
            cl = trnlink[trnlink["source"].astype(str).str.contains(f"{period.lower()}_{rt}", na=False)]
            clg = cl.groupby(["A", "B"], as_index=False)["AB_VOL"].sum()
            jl = alv.merge(clg, on=["A", "B"], how="outer").fillna(0.0)
            l_a, l_c = jl["vol"].sum(), jl["AB_VOL"].sum()

            r = (run_types.index(rt), period)
            row = (rt, period, b_c, b_a, 100 * (b_a - b_c) / max(b_c, 1e-9),
                   _corr(jb["aeq"].to_numpy(), jb["cube"].to_numpy()), len(jb),
                   l_c, l_a, 100 * (l_a - l_c) / max(l_c, 1e-9),
                   _corr(jl["vol"].to_numpy(), jl["AB_VOL"].to_numpy()), len(jl))
            rows.append(row)
            csv_f.write(",".join(f"{x:.4f}" if isinstance(x, float) else str(x) for x in row) + "\n")
            csv_f.flush()
            done += 1
            log.info("  [%2d/%d] %-13s %s  board %+6.1f%% r%.3f  link %+6.1f%% r%.3f",
                     done, total, rt, period, row[4], row[5], row[9], row[10])

    csv_f.close()
    df = pd.DataFrame(rows, columns=["run", "period", "board_cube", "board_aeq", "board_pct",
                                     "board_r", "n_lines", "link_cube", "link_aeq", "link_pct",
                                     "link_r", "n_links"])
    log.info("\n=== ASSIGNMENT SUMMARY (median over %d run-period cells) ===", len(df))
    log.info("  boardings:  |%%diff| med %.1f%%   corr med %.3f",
             df["board_pct"].abs().median(), df["board_r"].median())
    log.info("  link volume:|%%diff| med %.1f%%   corr med %.3f",
             df["link_pct"].abs().median(), df["link_r"].median())
    log.info("  wrote %s  (%.0fs)", csv_path, time.time() - t0)


if __name__ == "__main__":
    main()
