"""One-time conversion of Cube-era inputs into the Cube-free AequilibraE input set.

Run once (or whenever the source network/reference changes) to (re)build everything
the ``tm1.assignment.aeq`` track needs, so the per-iteration model runs with no Cube
license, no Cube binaries, and no network shares:

    python scripts/build_aeq_inputs.py --reference //MODEL3-C/.../2023_TM161_IPA_35_testrun \
        --out E:/aeq_inputs

Produces under --out:

  highway_links.csv          copy of the Cube net2csv link export (per-link attrs,
                             tolls, use codes, capclass; the aeq highway network)
  transitLines.lin           copy of the master TRNBUILD line file (ASCII source)
  fares/                     .far / fare block files (ASCII, for fare skims later)
  support_links.parquet      modes 1-9 access/egress/transfer/funnel links per
                             run type (extracted once from the reference's built
                             networks -- static geometry/policy, not run outputs)
  link_distance.parquet      directional link distances (rail RUNTIME distribution)
  ref_ride_time.parquet      reference in-vehicle times per (A,B,mode) -- fallback
                             for rail links whose line has no RUNTIME
  nonres/trips{P}.omx        non-residential demand (IX/truck/air/HSR) converted
                             TPP -> OMX

The reference run is used purely as a data source for one-time extraction; nothing
here runs Cube.
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import openmatrix as omx
import pandas as pd

from cubeio import read_tpp

PERIODS = ("EA", "AM", "MD", "PM", "EV")
# one representative built network per access/line-haul run type (support links are
# static per run type; AM used as the representative period)
RUN_TYPES = [f"{a}_{m}_{e}" for a, e in (("wlk", "wlk"), ("drv", "wlk"), ("wlk", "drv"))
             for m in ("loc", "exp", "lrf", "hvy", "com")]
_TRNLINK_COLS = ["A", "B", "time", "mode", "plot", "stopA", "stopB", "distance", "name",
                 "owner", "AB_VOL", "AB_BRDA", "AB_XITA", "AB_BRDB", "AB_XITB",
                 "BA_VOL", "BA_BRDA", "BA_XITA", "BA_BRDB", "BA_XITB", "prn"]
_NONRES = ("IX", "trk", "AirPax", "Hsr")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", required=True, help="reference run root (data source)")
    ap.add_argument("--out", required=True, help="output directory for aeq inputs")
    args = ap.parse_args()
    ref = Path(args.reference)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # 1. highway network link export
    shutil.copy2(ref / "hwy" / "iter3" / "avgload5period_vehclasses.csv",
                 out / "highway_links.csv")
    print("highway_links.csv")

    # 2. transit line + fare sources (ASCII)
    shutil.copy2(ref / "trn" / "transitLines.lin", out / "transitLines.lin")
    fares = out / "fares"
    fares.mkdir(exist_ok=True)
    for f in (ref / "trn").glob("*.far"):
        shutil.copy2(f, fares / f.name)
    print("transitLines.lin + fares/")

    # 3. support links, link distances, reference ride times (from built networks)
    sup_frames, dist_frames, time_frames = [], [], []
    trn_dir = ref / "trn" / "TransitAssignment.iter3"
    for rt in RUN_TYPES:
        src = trn_dir / f"trnlinkam_{rt}.csv"
        if not src.exists():
            print(f"  ! missing {src.name} -- skipped")
            continue
        lk = pd.read_csv(src, header=None, names=_TRNLINK_COLS)
        sup = lk[lk["mode"] < 10][["A", "B", "time", "mode", "distance"]].copy()
        sup["run_type"] = rt
        sup_frames.append(sup)
        tr = lk[lk["mode"] >= 10]
        dist_frames.append(tr[["A", "B", "distance"]])
        time_frames.append(tr[["A", "B", "mode", "time"]])
        print(f"  support links {rt}: {len(sup):,}")
    pd.concat(sup_frames, ignore_index=True).astype(
        {"A": np.int32, "B": np.int32, "mode": np.int16}
    ).to_parquet(out / "support_links.parquet")
    (pd.concat(dist_frames, ignore_index=True)
       .drop_duplicates(["A", "B"]).astype({"A": np.int32, "B": np.int32})
       .to_parquet(out / "link_distance.parquet"))
    (pd.concat(time_frames, ignore_index=True)
       .drop_duplicates(["A", "B", "mode"]).astype({"A": np.int32, "B": np.int32})
       .to_parquet(out / "ref_ride_time.parquet"))
    print("support_links.parquet / link_distance.parquet / ref_ride_time.parquet")

    # 4. non-residential demand TPP -> OMX
    nr = out / "nonres"
    nr.mkdir(exist_ok=True)
    for per in PERIODS:
        dest = nr / f"trips{per}.omx"
        if dest.exists():
            dest.unlink()
        with omx.open_file(str(dest), "w") as f:
            for src_name in _NONRES:
                tpp = ref / "nonres" / f"trips{src_name}{per}.tpp"
                if not tpp.exists():
                    continue
                for tbl, mat in read_tpp(str(tpp))["data"].items():
                    f[f"{src_name}_{tbl}"] = np.asarray(mat, dtype=np.float64)
        print(f"  nonres/trips{per}.omx")
    print("done.")


if __name__ == "__main__":
    main()
