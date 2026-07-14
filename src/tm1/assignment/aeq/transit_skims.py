"""Assemble the full ActivitySim transit skim set from the SF component skims.

ActivitySim reads transit level-of-service as matrices named
``{ACCESS}_{LINEHAUL}_{EGRESS}_{TOKEN}`` (per time period), where ACCESS/EGRESS are
WLK/DRV, LINEHAUL is LOC/LRF/EXP/HVY/COM/TRN and TOKEN is one of the component skims.
This module drives :func:`tm1.assignment.aeq.transit.skim_transit` over the access /
line-haul / egress run types x periods and packs the result into that naming.

All run-type structure, cost policy, and publishing conventions come from
``base-models/assignment/aeq_params.yaml`` (see :mod:`tm1.assignment.aeq.params`).

Two graphs per run (see ``transit.build_transit_graph``):

* the **fast LOS graph** (``fare_states="none"``) is skimmed every iteration for the
  congestion-dependent components (IVT/wait/boardings/walk/drive);
* the **operator fare graph** (``fare_states="operator"``) is expensive but fares are
  static, so it is skimmed once and cached, then merged into every iteration's matrices.
"""

from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from tm1.assignment.aeq.params import AeqParams, SkimOutput, load_aeq_params
from tm1.assignment.aeq.transit import TransitParams, build_transit_graph, skim_transit


def skim_params(linehaul: str, access: str, egress: str, p: AeqParams) -> TransitParams:
    """Resolve one run type's :class:`TransitParams` from the model parameters.

    Skim-config perceived costs (TransitSkims.job): skim wait factor + the
    access-dependent boarding-penalty vector, plus the line-haul's mode policy.
    """
    tc = p.transit_cost
    lh = tc.linehauls[linehaul]
    boardpen = (tc.walk_board_penalties if (access, egress) == ("wlk", "wlk")
                else tc.drive_board_penalties)
    return TransitParams(
        linehaul=linehaul, spread_window=lh.spread_window,
        wait_perceive=tc.skim_wait_perceive, walk_factor=tc.walk_factor,
        board_penalties=boardpen, skip=lh.skip, fac=lh.fac, key_band=lh.key_band,
        ferry_band=tc.ferry_band, iwaitmax_min=tc.iwaitmax_min,
        iwaitmax_modes=tc.iwaitmax_modes, wait_combine=tc.wait_combine)


def run_prefix(access: str, linehaul: str, egress: str) -> str:
    """ActivitySim matrix prefix, e.g. ('drv','loc','wlk') -> 'DRV_LOC_WLK'."""
    return f"{access}_{linehaul}_{egress}".upper()


def matrix_name(access: str, linehaul: str, egress: str, token: str, period: str,
                out_cfg: SkimOutput) -> str:
    """Full OMX matrix name, matching the highway skims' ``{key}__{period}``."""
    tok = out_cfg.token_name.get(token, token)
    return f"{run_prefix(access, linehaul, egress)}_{tok}__{period.upper()}"


def pack_run_matrices(access: str, linehaul: str, egress: str, period: str,
                      skims: dict, out_cfg: SkimOutput,
                      fare: np.ndarray | None = None) -> dict:
    """Map one run's component skims to named, scaled ActivitySim matrices.

    ``skims`` is a :func:`skim_transit` result (actual units); ``fare`` optionally
    overrides ``skims['FARE']`` with the cached exact operator-graph fare.
    """
    tokens = list(out_cfg.linehaul_tokens[linehaul])
    if access == "drv" or egress == "drv":
        tokens += list(out_cfg.drive_tokens)
    out = {}
    for tok in tokens:
        mat = fare if (tok == "FARE" and fare is not None) else skims[tok]
        name = matrix_name(access, linehaul, egress, tok, period, out_cfg)
        out[name] = mat * out_cfg.token_scale[tok]
    return out


def skim_all_runs(
    ride_links_by_period: dict,
    support_by_runtype: dict,
    headways_by_period: dict,
    fares,
    *,
    params: AeqParams | None = None,
    threads: int | None = None,
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
    params
        Loaded :class:`AeqParams`; None loads the default aeq_params.yaml.
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
    p = params or load_aeq_params()
    out: dict = {}
    fare_cache = {} if fare_cache is None else fare_cache
    if fare_threads is None:
        fare_threads = threads

    # trn (all-modes generic path) shares the per-access NOX rules, so its connector
    # set is the union of the fare linehauls' support links for that access/egress
    support_by_runtype = dict(support_by_runtype)
    for a, e, _, _ in p.skim_output.access_egress:
        rt = f"{a}_trn_{e}"
        if "trn" in p.skim_output.linehauls and rt not in support_by_runtype:
            parts = [support_by_runtype[f"{a}_{lh}_{e}"]
                     for lh in p.skim_output.fare_linehauls]
            support_by_runtype[rt] = (pd.concat(parts, ignore_index=True)
                                      .drop_duplicates(["A", "B", "mode"]))

    missing = {f"{a}_{lh}_{e}" for a, e, _, _ in p.skim_output.access_egress
               for lh in p.skim_output.fare_linehauls} - set(fare_cache)
    if missing:
        fare_cache.update(compute_fare_cache(
            ride_links_by_period, support_by_runtype, headways_by_period, fares,
            params=p, threads=fare_threads, workers=fare_workers, runs=missing))

    # --- level-of-service skims (run type x period, refreshed every iteration): the graphs
    # are small (~2 GB) so these scale well run CONCURRENTLY across run types (measured 1.9x,
    # 30->16 min for the 75 skims).  Each worker skims at `threads` threads; `workers` of
    # them run at once (workers * threads ~= cores).  workers=1 -> sequential (unchanged).
    jobs = [(a, e, am, em, lh, per)
            for a, e, am, em in p.skim_output.access_egress
            for lh in p.skim_output.linehauls for per in p.periods.names]
    ctx = {"ride": ride_links_by_period, "hw": headways_by_period,
           "support": support_by_runtype, "fares": fares, "params": p,
           "threads": threads, "fare_cache": fare_cache}
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
    params: AeqParams | None = None,
    threads: int | None = None,
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
    p = params or load_aeq_params()
    ride_u, hw_u = _union_service(ride_links_by_period, headways_by_period, p)
    heavy = {lh: i for i, lh in enumerate(("com", "hvy", "exp", "lrf", "loc"))}
    jobs = sorted(((a, e, am, em, lh)
                   for a, e, am, em in p.skim_output.access_egress
                   for lh in p.skim_output.fare_linehauls
                   if runs is None or f"{a}_{lh}_{e}" in runs),
                  key=lambda j: heavy.get(j[4], 99))
    ctx = {"ride_u": ride_u, "hw_u": hw_u, "support": support_by_runtype,
           "fares": fares, "params": p, "threads": threads}
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
    p: AeqParams = c["params"]
    rt = f"{access}_{linehaul}_{egress}"
    tp = skim_params(linehaul, access, egress, p)
    links = _assemble(c["ride_u"], c["support"][rt])
    gf = build_transit_graph(
        links, c["hw_u"], tp, n_zones=p.n_taz, fares=c["fares"],
        fare_states="operator", access_mode=amode, egress_mode=emode)
    fare = skim_transit(
        gf, linehaul=linehaul, fares=c["fares"], n_zones=p.n_taz,
        threads=c["threads"], wait_perceive=tp.wait_perceive,
        max_path_min=p.transit_cost.skim_max_path_min,
        max_perceived_min=p.transit_cost.skim_max_perceived_min,
        premier=tp.key_band is not None,
        combine_wait=p.transit_cost.linehauls[linehaul].wait_pool)["FARE"]
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
    p: AeqParams = c["params"]
    rt = f"{access}_{linehaul}_{egress}"
    tp = skim_params(linehaul, access, egress, p)
    links = _assemble(c["ride"][period], c["support"][rt])
    g = build_transit_graph(
        links, c["hw"][period], tp, n_zones=p.n_taz, fares=c["fares"],
        fare_states="none", access_mode=amode, egress_mode=emode)
    sk = skim_transit(
        g, linehaul=linehaul, fares=c["fares"], n_zones=p.n_taz, threads=c["threads"],
        wait_perceive=tp.wait_perceive,
        max_path_min=p.transit_cost.skim_max_path_min,
        max_perceived_min=p.transit_cost.skim_max_perceived_min,
        rail_curve_fallback=True, premier=tp.key_band is not None,
        combine_wait=p.transit_cost.linehauls[linehaul].wait_pool)
    # exact union-pass fare where available; LOS fare (XFARE + distance curve) fills the
    # few pairs the union pass cannot reach.  trn has no fare pass (and publishes no FARE).
    fare_c = c["fare_cache"].get(rt)
    fare_p = np.where(fare_c > 0, fare_c, sk["FARE"]) if fare_c is not None else None
    return pack_run_matrices(access, linehaul, egress, period, sk, p.skim_output,
                             fare=fare_p)


def _union_service(ride_links_by_period: dict, headways_by_period: dict,
                   p: AeqParams) -> tuple:
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
    for period in ("AM", *tuple(per for per in p.periods.names if per != "AM")):
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
