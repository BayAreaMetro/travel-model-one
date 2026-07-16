"""Validate the aeq HIGHWAY assignment link volumes against the reference Cube run.

Feeds Cube's *own* demand (CT-RAMP ``main/trips{period}.tpp`` + nonres OMX, folded into the
13 vehicle classes exactly as ``HwyAssign.job`` does -- incl. TNC->AV) to the aeq Frank-Wolfe
assignment, and compares per-link volumes to Cube's loaded network
``hwy/iter3/avgload5period_vehclasses.csv`` -- per class AND the PCE-combined total.  The
network file *is* the aeq input ``highway_links.csv`` (same node order), so links join by row.

Also breaks the total-PCE comparison down by facility type (``ft`` -- freeways 1/2/8/9,
arterials etc. 3/4/5/7/10, connectors 6; see ``tm1.assignment.aeq.vdf``), and compares
congested speed (Cube's ``cspd{period}`` vs aeq's ``distance / congested_time``) on loaded
links, since both are already computed from the same VDF.

    python scripts/validate_highway_assignment.py --cores 16

Writes ``{--out}.csv`` (class x period), ``{--out}_byft.csv`` (facility type x period),
``{--out}_speed.csv`` (facility type x period, loaded links only) + a summary.
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


def _compare(cube: np.ndarray, aeq: np.ndarray) -> tuple[float, float, float]:
    """Return (cube_sum, aeq_sum, pct_diff) for a slice; caller adds corr separately."""
    c_sum, a_sum = float(cube.sum()), float(aeq.sum())
    pct = 100 * (a_sum - c_sum) / max(c_sum, 1e-9)
    return c_sum, a_sum, pct


def _corr(cube: np.ndarray, aeq: np.ndarray) -> float:
    mask = (cube > 0) | (aeq > 0)
    if mask.sum() > 1 and cube[mask].std():
        return float(np.corrcoef(cube[mask], aeq[mask])[0, 1])
    return float("nan")


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
    ap.add_argument("--out", default="scripts/migration_validation/assignment/scorecard_hwy_assign")
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

    out_base = Path(args.out)
    byft_f = out_base.with_name(out_base.name + "_byft").with_suffix(".csv").open("w")
    byft_f.write("period,ft,cube_vol,aeq_vol,pct,corr\n")
    byft_rows = []

    speed_f = out_base.with_name(out_base.name + "_speed").with_suffix(".csv").open("w")
    speed_f.write("period,ft,cube_mph,aeq_mph,pct,corr,n_links\n")
    speed_rows = []

    ft = links["ft"].to_numpy(int)

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

        # --- By facility type: total-PCE volume, same convention as TOT_PCE above ---
        for ft_code in sorted(set(ft.tolist())):
            fm = ft == ft_code
            c_sum, a_sum, fpct = _compare(ct[fm], at[fm])
            fcorr = _corr(ct[fm], at[fm])
            byft_rows.append((period, ft_code, c_sum, a_sum, fpct, fcorr))
            byft_f.write(f"{period},{ft_code},{c_sum:.1f},{a_sum:.1f},{fpct:.3f},{fcorr:.4f}\n")
        byft_f.flush()

        # --- Congested speed: Cube's cspd{period} vs aeq distance/congested_time, ---
        # --- loaded links only (unloaded links trivially agree at free-flow speed). ---
        loaded = ct > 0
        cube_mph = links[f"cspd{period}"].to_numpy(float)
        aeq_mph = links["distance"].to_numpy(float) / np.maximum(res.congested_time, 1e-6) * 60.0
        for ft_code in sorted(set(ft.tolist())):
            fm = loaded & (ft == ft_code)
            if fm.sum() == 0:
                continue
            c_mean, a_mean = float(cube_mph[fm].mean()), float(aeq_mph[fm].mean())
            spct = 100 * (a_mean - c_mean) / max(c_mean, 1e-9)
            scorr = _corr(cube_mph[fm], aeq_mph[fm])
            speed_rows.append((period, ft_code, c_mean, a_mean, spct, scorr, int(fm.sum())))
            speed_f.write(f"{period},{ft_code},{c_mean:.2f},{a_mean:.2f},{spct:.3f},{scorr:.4f},{int(fm.sum())}\n")
        speed_f.flush()

        log.info("  %s: gap %.1e/%diters  TOT_PCE %+.1f%% r%.3f  (class |%%| med %.1f%%, r med %.3f)",
                 period, res.gap, res.iterations, pct, rt,
                 np.median([abs(x[4]) for x in rows if x[0] == period and x[1] != "TOT_PCE"]),
                 np.median([x[5] for x in rows if x[0] == period and x[1] != "TOT_PCE" and not np.isnan(x[5])]))
    csv_f.close()
    byft_f.close()
    speed_f.close()
    df = pd.DataFrame(rows, columns=["period", "class", "cube", "aeq", "pct", "corr"])
    cl = df[df["class"] != "TOT_PCE"]; tp = df[df["class"] == "TOT_PCE"]
    log.info("\n=== HIGHWAY ASSIGNMENT SUMMARY ===")
    log.info("  per-class link vol: |%%| med %.1f%%   corr med %.3f",
             cl["pct"].abs().median(), cl["corr"].median())      # "corr" collides with DataFrame.corr
    log.info("  total-PCE link vol: |%%| med %.1f%%   corr med %.3f",
             tp["pct"].abs().median(), tp["corr"].median())

    byft_df = pd.DataFrame(byft_rows, columns=["period", "ft", "cube", "aeq", "pct", "corr"])
    log.info("  by facility type:   |%%| med %.1f%%   corr med %.3f",
             byft_df["pct"].abs().median(), byft_df["corr"].median())
    for ft_code, g in byft_df.groupby("ft"):
        log.info("    ft=%d: |%%| med %.1f%%  corr med %.3f", ft_code, g["pct"].abs().median(), g["corr"].median())

    speed_df = pd.DataFrame(speed_rows, columns=["period", "ft", "cube", "aeq", "pct", "corr", "n_links"])
    log.info("  congested speed (loaded links): |%%| med %.1f%%   corr med %.3f",
             speed_df["pct"].abs().median(), speed_df["corr"].median())
    for ft_code, g in speed_df.groupby("ft"):
        log.info("    ft=%d: |%%| med %.1f%%  corr med %.3f  (n=%d)",
                 ft_code, g["pct"].abs().median(), g["corr"].median(), g["n_links"].sum())


if __name__ == "__main__":
    main()
