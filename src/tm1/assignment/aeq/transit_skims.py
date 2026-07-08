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

from __future__ import annotations

import numpy as np
import pandas as pd

from tm1.assignment.aeq.transit import (
    DRIVE_BOARD_PENALTIES, WALK_BOARD_PENALTIES,
    TransitParams, build_transit_graph, skim_transit,
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
        Optional ``run_type -> {period -> fare matrix}`` from a previous exact
        operator-graph pass; if absent it is computed once here (period AM) and reused
        across periods (fares are static).

    Returns a flat ``{omx_matrix_name: n_zones x n_zones array}`` dict.
    """
    out: dict = {}
    fare_cache = {} if fare_cache is None else fare_cache
    for access, egress, amode, emode in ACCESS_EGRESS:
        for linehaul in LINEHAULS:
            rt = f"{access}_{linehaul}_{egress}"
            sup = support_by_runtype[rt]
            # exact fare once per run type (static), reused for every period
            params = _skim_params(linehaul, access, egress, spread_window)
            if rt not in fare_cache:
                p0 = "AM"
                links = _assemble(ride_links_by_period[p0], sup)
                gf = build_transit_graph(
                    links, headways_by_period[p0], params,
                    n_zones=n_zones, fares=fares, fare_states="operator",
                    access_mode=amode, egress_mode=emode)
                fare_cache[rt] = skim_transit(
                    gf, linehaul=linehaul, fares=fares, n_zones=n_zones, threads=threads,
                    wait_perceive=SKIM_WAIT_PERCEIVE,
                    max_perceived_min=SKIM_MAXPATH_PERCEIVED)["FARE"]
            for period in PERIODS:
                links = _assemble(ride_links_by_period[period], sup)
                g = build_transit_graph(
                    links, headways_by_period[period], params,
                    n_zones=n_zones, fares=fares, fare_states="none",
                    access_mode=amode, egress_mode=emode)
                sk = skim_transit(
                    g, linehaul=linehaul, fares=fares, n_zones=n_zones, threads=threads,
                    wait_perceive=SKIM_WAIT_PERCEIVE,
                    max_perceived_min=SKIM_MAXPATH_PERCEIVED)
                out.update(pack_run_matrices(access, linehaul, egress, period, sk,
                                             fare=fare_cache[rt]))
    return out


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
