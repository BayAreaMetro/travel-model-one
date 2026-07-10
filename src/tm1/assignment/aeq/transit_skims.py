"""Assemble the full ActivitySim transit skim set from the SF component skims.

ActivitySim reads transit level-of-service as matrices named
``{ACCESS}_{LINEHAUL}_{EGRESS}_{TOKEN}`` (per time period), where ACCESS/EGRESS are
WLK/DRV, LINEHAUL is LOC/LRF/EXP/HVY/COM and TOKEN is one of the component skims.  This
module drives :func:`tm1.assignment.aeq.transit.skim_transit` over the 15 access /
line-haul / egress run types x 5 periods and packs the result into that naming.

Two graphs per run (see ``transit.build_transit_graph``):

* the **fast LOS graph** (``fare_states="none"``) is skimmed every iteration for the
  congestion-dependent components (IVT/wait/boardings/walk/drive);
* the **operator fare graph** (``fare_states="operator"``) is expensive but fares are
  static, so it is skimmed once and cached, then merged into every iteration's matrices.
"""

from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from tm1.assignment.aeq.transit import (
    DRIVE_BOARD_PENALTIES,
    WALK_BOARD_PENALTIES,
    TransitParams,
    build_transit_graph,
    skim_transit,
)

PERIODS = ("EA", "AM", "MD", "PM", "EV")
LINEHAULS = ("loc", "lrf", "exp", "hvy", "com")

# Cube SKIM perceived-cost settings (TransitSkims.job), distinct from assignment:
# iwaitfac/xwaitfac = 2.0, maxpathtime = 300 (perceived).  IWAITMAX (Caltrain/ferry wait
# cap) and modefac/skipmodes live in build_transit_graph.
# TODO(perf): the 5-level boardpen grows the fare graph ~2x; once fidelity is locked in,
# revisit trimming to 3 levels (0,20,45) -- 4th/5th boardings are ~2% of trips.
SKIM_WAIT_PERCEIVE = 2.0
SKIM_MAXPATH_PERCEIVED = 300.0


def _skim_params(linehaul: str, access: str, egress: str, spread_window):
    """SKIM-config TransitParams: Cube wait factor + access-dependent boardpen."""
    boardpen = WALK_BOARD_PENALTIES if (access, egress) == ("wlk", "wlk") else DRIVE_BOARD_PENALTIES
    return TransitParams(linehaul=linehaul, spread_window=spread_window,
                         wait_perceive=SKIM_WAIT_PERCEIVE, board_penalties=boardpen)
# run type -> (access token, line-haul, egress token, access mode, egress mode)
ACCESS_EGRESS = (("wlk", "wlk", 1, 6), ("drv", "wlk", 2, 6), ("wlk", "drv", 1, 7))

# component (skim_transit key) -> ActivitySim token; None-valued skips.  Cube stores
# times and distances x100, fare in cents, boardings as a count.
_TOKEN_SCALE = {
    "TOTIVT": 100.0, "KEYIVT": 100.0, "FERRYIVT": 100.0, "IWAIT": 100.0,
    "XWAIT": 100.0, "WAUX": 100.0, "DTIM": 100.0, "DDIST": 100.0,
    "BOARDS": 1.0, "FARE": 1.0,
}
# ActivitySim matrix token name for each skim_transit component ('FARE' -> 'FAR')
_TOKEN_NAME = {"FARE": "FAR"}
# which tokens each line-haul actually publishes (others are absent / all-zero)
_LINEHAUL_TOKENS = {
    "loc": ("TOTIVT", "IWAIT", "XWAIT", "WAUX", "BOARDS", "FARE"),
    "lrf": ("TOTIVT", "KEYIVT", "FERRYIVT", "IWAIT", "XWAIT", "WAUX", "BOARDS", "FARE"),
    "exp": ("TOTIVT", "KEYIVT", "IWAIT", "XWAIT", "WAUX", "BOARDS", "FARE"),
    "hvy": ("TOTIVT", "KEYIVT", "IWAIT", "XWAIT", "WAUX", "BOARDS", "FARE"),
    "com": ("TOTIVT", "KEYIVT", "IWAIT", "XWAIT", "WAUX", "BOARDS", "FARE"),
}
_DRIVE_TOKENS = ("DTIM", "DDIST")   # added when access or egress is drive


def run_prefix(access: str, linehaul: str, egress: str) -> str:
    """ActivitySim matrix prefix, e.g. ('drv','loc','wlk') -> 'DRV_LOC_WLK'."""
    return f"{access}_{linehaul}_{egress}".upper()


def matrix_name(access: str, linehaul: str, egress: str, token: str, period: str) -> str:
    """Full OMX matrix name, matching the highway skims' ``{key}__{period}``."""
    tok = _TOKEN_NAME.get(token, token)
    return f"{run_prefix(access, linehaul, egress)}_{tok}__{period.upper()}"


def pack_run_matrices(access: str, linehaul: str, egress: str, period: str,
                      skims: dict, fare: np.ndarray | None = None) -> dict:
    """Map one run's component skims to named, scaled ActivitySim matrices.

    ``skims`` is a :func:`skim_transit` result (actual units); ``fare`` optionally
    overrides ``skims['FARE']`` with the cached exact operator-graph fare.
    """
    tokens = list(_LINEHAUL_TOKENS[linehaul])
    if access == "drv" or egress == "drv":
        tokens += list(_DRIVE_TOKENS)
    out = {}
    for tok in tokens:
        mat = fare if (tok == "FARE" and fare is not None) else skims[tok]
        out[matrix_name(access, linehaul, egress, tok, period)] = mat * _TOKEN_SCALE[tok]
    return out


def skim_all_runs(
    ride_links_by_period: dict,
    support_by_runtype: dict,
    headways_by_period: dict,
    fares,
    *,
    n_zones: int = 1475,
    threads: int | None = None,
    spread_window: float | None = 1.5,
    fare_cache: dict | None = None,
    workers: int = 1,
    fare_threads: int | None = None,
    fare_workers: int = 1,
) -> dict:
    """Skim every run type x period into the ActivitySim matrix set.

    Parameters
    ----------
    ride_links_by_period
        ``period -> ride-link DataFrame`` (A, B, time, mode, stopA, stopB, distance,
        name) with the period's congested bus times.
    support_by_runtype
        ``run_type ('wlk_loc_wlk', ...) -> support-link DataFrame`` (access / egress /
        transfer connectors, mode < 10, with distance).
    headways_by_period
        ``period -> {line name: headway}``.
    fares
        :class:`tm1.assignment.aeq.fares.TransitFares`.
    fare_cache
        Optional ``run_type -> fare matrix`` from a previous exact operator-graph
        pass; missing run types are computed once here (union-service network, see
        :func:`compute_fare_cache`) and reused across periods (fares are static).
    fare_workers
        Concurrent processes for the one-time fare pass (the sparse operator graphs
        are LOS-sized and no longer bandwidth-bound, so workers scale: measured
        21 min sequential @12T -> ~2.16x with 3 workers).

    Returns a flat ``{omx_matrix_name: n_zones x n_zones array}`` dict.
    """
    out: dict = {}
    fare_cache = {} if fare_cache is None else fare_cache
    if fare_threads is None:
        fare_threads = threads

    missing = {f"{a}_{lh}_{e}" for a, e, _, _ in ACCESS_EGRESS
               for lh in LINEHAULS} - set(fare_cache)
    if missing:
        fare_cache.update(compute_fare_cache(
            ride_links_by_period, support_by_runtype, headways_by_period, fares,
            n_zones=n_zones, threads=fare_threads, spread_window=spread_window,
            workers=fare_workers, runs=missing))

    # --- level-of-service skims (run type x period, refreshed every iteration): the graphs
    # are small (~2 GB) so these scale well run CONCURRENTLY across run types (measured 1.9x,
    # 30->16 min for the 75 skims).  Each worker skims at `threads` threads; `workers` of
    # them run at once (workers * threads ~= cores).  workers=1 -> sequential (unchanged).
    jobs = [(a, e, am, em, lh, p)
            for a, e, am, em in ACCESS_EGRESS for lh in LINEHAULS for p in PERIODS]
    ctx = {"ride": ride_links_by_period, "hw": headways_by_period,
           "support": support_by_runtype, "fares": fares, "n_zones": n_zones,
           "spread_window": spread_window, "threads": threads, "fare_cache": fare_cache}
    if workers and workers > 1:
        with ProcessPoolExecutor(max_workers=workers, initializer=_init_los_worker,
                                 initargs=(ctx,)) as ex:
            for res in ex.map(_skim_los_job, jobs):
                out.update(res)
    else:
        _init_los_worker(ctx)
        for job in jobs:
            out.update(_skim_los_job(job))
    return out


def compute_fare_cache(
    ride_links_by_period: dict,
    support_by_runtype: dict,
    headways_by_period: dict,
    fares,
    *,
    n_zones: int = 1475,
    threads: int | None = None,
    spread_window: float | None = 1.5,
    workers: int = 1,
    runs: set | None = None,
) -> dict:
    """One-time exact operator-graph fare pass: ``run_type -> FARE matrix`` (cents).

    Runs on the UNION-service network (every period's lines at their best headway) so
    coverage spans every period's reachable pairs -- an AM-only pass left structural
    fare=0 on the 7-20% of off-peak pairs AM cannot reach; fares are period-invariant.

    The sparse reachable-state operator graphs are LOS-sized (~1M edges, ~0.15 GB), so
    unlike the earlier dense graphs this pass scales on both axes (measured: com skim
    123.7s @12T -> 58.8s @48T; 3 workers @12T = 2.16x throughput).  ``workers``
    processes each skim at ``threads`` threads; heavy line-hauls are dispatched first
    for pool balance.  Fares are static: cache the result across iterations and across
    runs of the same network.
    """
    ride_u, hw_u = _union_service(ride_links_by_period, headways_by_period)
    heavy = {lh: i for i, lh in enumerate(("com", "hvy", "exp", "lrf", "loc"))}
    jobs = sorted(((a, e, am, em, lh)
                   for a, e, am, em in ACCESS_EGRESS for lh in LINEHAULS
                   if runs is None or f"{a}_{lh}_{e}" in runs),
                  key=lambda j: heavy[j[4]])
    ctx = {"ride_u": ride_u, "hw_u": hw_u, "support": support_by_runtype,
           "fares": fares, "n_zones": n_zones, "spread_window": spread_window,
           "threads": threads}
    if workers and workers > 1:
        with ProcessPoolExecutor(max_workers=workers, initializer=_init_los_worker,
                                 initargs=(ctx,)) as ex:
            return dict(ex.map(_fare_job, jobs))
    _init_los_worker(ctx)
    return dict(map(_fare_job, jobs))


def _fare_job(job: tuple) -> tuple:
    """Skim one run type's exact operator-graph fare on the union-service network."""
    access, egress, amode, emode, linehaul = job
    c = _LOS_CTX
    rt = f"{access}_{linehaul}_{egress}"
    params = _skim_params(linehaul, access, egress, c["spread_window"])
    links = _assemble(c["ride_u"], c["support"][rt])
    gf = build_transit_graph(
        links, c["hw_u"], params, n_zones=c["n_zones"], fares=c["fares"],
        fare_states="operator", access_mode=amode, egress_mode=emode)
    fare = skim_transit(
        gf, linehaul=linehaul, fares=c["fares"], n_zones=c["n_zones"],
        threads=c["threads"], wait_perceive=SKIM_WAIT_PERCEIVE,
        max_perceived_min=SKIM_MAXPATH_PERCEIVED)["FARE"]
    return rt, fare


_LOS_CTX: dict = {}


def _init_los_worker(ctx: dict) -> None:
    """Pool initializer: stash the shared skim inputs in the worker process."""
    _LOS_CTX.clear()
    _LOS_CTX.update(ctx)


def _skim_los_job(job: tuple) -> dict:
    """Skim one (run type, period) level-of-service job -> packed matrices.

    Reads the shared inputs from ``_LOS_CTX`` (set by :func:`_init_los_worker`).
    """
    access, egress, amode, emode, linehaul, period = job
    c = _LOS_CTX
    rt = f"{access}_{linehaul}_{egress}"
    params = _skim_params(linehaul, access, egress, c["spread_window"])
    links = _assemble(c["ride"][period], c["support"][rt])
    g = build_transit_graph(
        links, c["hw"][period], params, n_zones=c["n_zones"], fares=c["fares"],
        fare_states="none", access_mode=amode, egress_mode=emode)
    sk = skim_transit(
        g, linehaul=linehaul, fares=c["fares"], n_zones=c["n_zones"], threads=c["threads"],
        wait_perceive=SKIM_WAIT_PERCEIVE, max_perceived_min=SKIM_MAXPATH_PERCEIVED,
        rail_curve_fallback=True)
    # exact union-pass fare where available; LOS fare (XFARE + distance curve) fills the
    # few pairs the union pass cannot reach
    fare_c = c["fare_cache"][rt]
    fare_p = np.where(fare_c > 0, fare_c, sk["FARE"])
    return pack_run_matrices(access, linehaul, egress, period, sk, fare=fare_p)


def _union_service(ride_links_by_period: dict, headways_by_period: dict):
    """Best-service network for the once-per-run-type fare pass.

    Union of every period's line set, each line at its minimum headway across periods;
    ride times come from AM where the line runs then, else from the first period that
    has it (fares do not depend on ride time, only on reach and boarding structure).
    """
    hw: dict = {}
    for per_hw in headways_by_period.values():
        for ln, h in per_hw.items():
            if ln not in hw or h < hw[ln]:
                hw[ln] = h
    frames: list[pd.DataFrame] = []
    have: set = set()
    for period in ("AM", *tuple(p for p in PERIODS if p != "AM")):
        r = ride_links_by_period[period]
        extra = r if not have else r[~r["name"].isin(have)]
        if len(extra):
            frames.append(extra)
            have |= set(extra["name"].unique())
    return pd.concat(frames, ignore_index=True), hw


def _assemble(ride: pd.DataFrame, support: pd.DataFrame) -> pd.DataFrame:
    """Concatenate ride + support links into the build_transit_graph input table."""
    cols = ["A", "B", "time", "mode", "stopA", "stopB", "distance", "name"]
    sup = support.copy()
    for c in ("stopA", "stopB"):
        sup[c] = 0
    if "name" not in sup:
        sup["name"] = None
    if "distance" not in sup:
        sup["distance"] = 0.0
    return pd.concat([ride[cols], sup[cols]], ignore_index=True)
