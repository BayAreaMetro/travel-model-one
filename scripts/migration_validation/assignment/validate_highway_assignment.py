"""Validate the aeq HIGHWAY assignment link volumes against the reference Cube run.

Feeds Cube's *own* demand (CT-RAMP ``main/trips{period}.tpp`` + nonres OMX, folded into the
13 vehicle classes exactly as ``HwyAssign.job`` does -- incl. TNC->AV) to the aeq Frank-Wolfe
assignment, and compares per-link volumes to Cube's loaded network
``hwy/iter3/avgload5period_vehclasses.csv`` -- per class AND the PCE-combined total.  The
network file *is* the aeq input ``highway_links.csv`` (same node order), so links join by row.

    python scripts/validate_highway_assignment.py --cores 16 --out scorecard_hwy_assign

Writes ``{--out}.csv`` (class x period) + a summary.
"""
import argparse
import logging
from pathlib import Path

import numpy as np
import openmatrix as omx
import pandas as pd

from cubeio import read_tpp
from tm1.assignment.aeq.classes import CLASS_ORDER, build_vehicle_classes
from tm1.assignment.aeq.highway import equilibrium_assignment
from tm1.assignment.aeq.network import build_cube_graph
from tm1.assignment.aeq.params import load_aeq_params

log = logging.getLogger("hwy_val")
# CLASS_ORDER key -> avgload5period_vehclasses.csv volume-column suffix
SUF = {"da": "da", "sr2": "s2", "sr3": "s3", "sml": "sm", "lrg": "hv", "datoll": "dat",
       "sr2toll": "s2t", "sr3toll": "s3t", "smltoll": "smt", "lrgtoll": "hvt",
       "daav": "daav", "s2av": "s2av", "s3av": "s3av"}


def _pad(m: np.ndarray, n: int) -> np.ndarray:
    a = np.asarray(m, float)
    if a.shape[0] == n:
        return a
    out = np.zeros((n, n)); out[:a.shape[0], :a.shape[1]] = a
    return out


def cube_demand(ref: Path, inp: Path, period: str, n: int, occ2: float, occ3: float) -> dict:
    """The 13-class vehicle-trip demand Cube assigned, from its own inputs (HwyAssign.job)."""
    m = {k: _pad(v, n) for k, v in read_tpp(str(ref / "main" / f"trips{period}.tpp"))["data"].items()}
    with omx.open_file(str(inp / "nonres" / f"trips{period}.omx"), "r") as f:
        nr = {t: np.asarray(f[t], float) for t in f.list_matrices()}
    z = np.zeros((n, n))
    g = lambda d, k: d.get(k, z)
    d = {
        "da":      m["da"] + nr["IX_DA"] + nr["AirPax_DA"],
        "sr2":     m["sr2"] / occ2 + nr["IX_SR2"] + nr["AirPax_SR2"],
        "sr3":     m["sr3"] / occ3 + nr["IX_SR3"] + nr["AirPax_SR3"],
        "sml":     nr["trk_VSTRUCK"] + nr["trk_STRUCK"] + nr["trk_MTRUCK"],
        "lrg":     nr["trk_CTRUCK"],
        "datoll":  m["datoll"] + nr["IX_DATOLL"] + nr["AirPax_DATOLL"],
        "sr2toll": m["sr2toll"] / occ2 + nr["IX_SR2TOLL"] + nr["AirPax_SR2TOLL"] + nr["Hsr_taxi_veh"],
        "sr3toll": m["sr3toll"] / occ3 + nr["IX_SR3TOLL"] + nr["AirPax_SR3TOLL"],
        "smltoll": nr["trk_VSTRUCKTOLL"] + nr["trk_STRUCKTOLL"] + nr["trk_MTRUCKTOLL"],
        "lrgtoll": nr["trk_CTRUCKTOLL"],
        "daav":    g(m, "da_tnc") + g(m, "da_av"),
        "s2av":    (g(m, "s2_tnc") + g(m, "s2_av")) / occ2,
        "s3av":    (g(m, "s3_tnc") + g(m, "s3_av")) / occ3,
    }
    return {k: d[k] for k in CLASS_ORDER}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", default=r"E:\aeq_inputs")
    ap.add_argument("--reference", default=r"E:\ref_2023_TM161")
    ap.add_argument("--cores", type=int, default=16)
    ap.add_argument("--out", default="scorecard_hwy_assign")
    ap.add_argument("--log", default="hwy_assign_val.log")
    ap.add_argument("--periods", default="AM,MD,PM,EV,EA")
    ap.add_argument("--max-iter", type=int, default=100)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s",
                        handlers=[logging.FileHandler(args.log, mode="w"), logging.StreamHandler()])
    inp, ref = Path(args.inputs), Path(args.reference)
    P = load_aeq_params(); hw = P.highway
    occ2, occ3 = hw.occupancy["sr2"], hw.occupancy["sr3"]
    links = pd.read_csv(inp / "highway_links.csv"); links.columns = [c.strip() for c in links.columns]

    csv_f = Path(args.out).with_suffix(".csv").open("w")
    csv_f.write("period,class,cube_vol,aeq_vol,pct,corr\n")
    rows = []
    for period in args.periods.split(","):
        dem = cube_demand(ref, inp, period, P.n_taz, occ2, occ3)
        g, attrs = build_cube_graph(links, P.n_taz, capfac=P.periods.capfac[period], vdf=hw.vdf)
        classes = build_vehicle_classes(dem, links, period, hw, av_pce=1.0)
        res = equilibrium_assignment(g, attrs, classes, P.n_taz, hw.vdf,
                                     max_iter=args.max_iter, gap_target=1e-4, cores=args.cores)
        for k in CLASS_ORDER:
            c = links[f"vol{period}_{SUF[k]}"].to_numpy(float); a = res.flows[k]
            mask = (c > 0) | (a > 0)
            r = float(np.corrcoef(c[mask], a[mask])[0, 1]) if mask.sum() > 1 and c[mask].std() else float("nan")
            pct = 100 * (a.sum() - c.sum()) / max(c.sum(), 1e-9)
            rows.append((period, k, c.sum(), a.sum(), pct, r))
            csv_f.write(f"{period},{k},{c.sum():.1f},{a.sum():.1f},{pct:.3f},{r:.4f}\n")
        ct = links[f"vol{period}_tot"].to_numpy(float); at = res.total_pce
        mask = (ct > 0) | (at > 0)
        rt = float(np.corrcoef(ct[mask], at[mask])[0, 1])
        pct = 100 * (at.sum() - ct.sum()) / ct.sum()
        rows.append((period, "TOT_PCE", ct.sum(), at.sum(), pct, rt))
        csv_f.write(f"{period},TOT_PCE,{ct.sum():.1f},{at.sum():.1f},{pct:.3f},{rt:.4f}\n")
        csv_f.flush()
        log.info("  %s: gap %.1e/%diters  TOT_PCE %+.1f%% r%.3f  (class |%%| med %.1f%%, r med %.3f)",
                 period, res.gap, res.iterations, pct, rt,
                 np.median([abs(x[4]) for x in rows if x[0] == period and x[1] != "TOT_PCE"]),
                 np.median([x[5] for x in rows if x[0] == period and x[1] != "TOT_PCE" and not np.isnan(x[5])]))
    csv_f.close()
    df = pd.DataFrame(rows, columns=["period", "class", "cube", "aeq", "pct", "corr"])
    cl = df[df["class"] != "TOT_PCE"]; tp = df[df["class"] == "TOT_PCE"]
    log.info("\n=== HIGHWAY ASSIGNMENT SUMMARY ===")
    log.info("  per-class link vol: |%%| med %.1f%%   corr med %.3f", cl.pct.abs().median(), cl.corr.median())
    log.info("  total-PCE link vol: |%%| med %.1f%%   corr med %.3f", tp.pct.abs().median(), tp.corr.median())


if __name__ == "__main__":
    main()
