"""Frequency-based transit assignment (Spiess-Florian optimal strategies) for AequilibraE.

Cube's TRNBUILD performs a frequency-based optimal-strategy (hyperpath) transit
assignment; AequilibraE ships the same algorithm as
:class:`aequilibrae.paths.cython.public_transport.HyperpathGenerating`.  This module
builds the Spiess-Florian transit graph from a Cube-style transit network and drives
that solver, reproducing Cube's per-line boardings.

Perceived-cost model (matched to ``TransitAssign.job``):

* wait = half headway, perceived x ``wait_perceive`` (iwaitfac/xwaitfac = 2.8);
* walk perceived x ``walk_factor`` (2.0);
* in-vehicle time x a per-mode factor and modes excluded per line-haul run
  (``modefac`` / ``skipmodes``, from ``aeq_params.yaml`` via :class:`TransitParams`);
* Cube's *escalating* boarding penalties (boardpen 0/30/45/...) via a **layered
  ("journey levels") graph**: layer k of a stop means "k boardings so far", and
  boarding is the only edge that moves up a layer, charging the k-th penalty.  This
  gives the memoryless hyperpath the boarding-count memory the escalating penalty
  needs (the same device as Emme's journey levels).

One boarding point per (line, stop) is used: interior stops appear as both ``stopB``
of the incoming link and ``stopA`` of the outgoing link, and adding both would create
parallel boarding edges whose frequencies ADD in Spiess-Florian (halving the wait).

Cube's transfer prohibitors (``transferprohibitors_*.block``) are walk-chain rules,
encoded here as stop *states* composed with the layers:

* state ``A`` (arrived by walk access, layer 0 only) -- may only board;
* state ``B(k)`` (just alighted, k boardings) -- may board, egress, or take ONE
  stop-to-stop transfer walk;
* state ``C(k)`` (arrived by transfer walk) -- may only board.

This forbids access->transfer-walk chains, transfer-walk->egress, walk-only paths
through the transit network, and chained transfer walks, exactly as Cube's NOX table.

Not yet modelled: fares as skims, drive (PNR/KNR) access legs, Cube's 5-minute
combined-headway window (S&F spreads over the full attractive line set).
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from aequilibrae.paths.cython.public_transport import HyperpathGenerating

INF_FREQ = 1.0e20

# ACTUAL-value component skim columns accumulated along the hyperpath (minutes / counts;
# see skim_transit).  sk_edge = perceived NON-wait edge time (walk x factor, IVT x ivf,
# boardpen -- NOT board_cost) so wait = (u - sk_edge) / wait_perceive stays exact under
# any spread_window.  w_first/w_xfer = per-line half-headway markers for the iwait/xwait
# split.  boards counts boardings.  fare = boarding XFARE + farelinks (cents); keydist =
# key-mode in-vehicle distance (miles) for the rail distance-curve fare.
SKIM_COLS = ("ivt", "keyivt", "ferryivt", "wacc", "waux", "wegr",
             "boards", "sk_edge", "detwait", "w_first", "w_xfer", "fare", "keydist",
             "dtim", "ddist")   # dtim/ddist = drive access/egress time (min) / dist (mi)
# detwait = the DETERMINISTIC boarding wait slice (perceived).  It is part of the routing
# cost (so it stays out of sk_edge), but it is subtracted back out when reporting the wait:
# see skim_transit -- what remains is the S&F frequency term, which IS Cube's
# combined-headway wait (deflated by exactly spread_window, so rescaling recovers it).


@dataclass
class TransitParams:
    """Perceived-cost parameters (minutes) for one transit graph build.

    All MODEL POLICY values (boarding penalties, per-line-haul mode factors and
    exclusions, IWAITMAX, key bands) live in ``base-models/assignment/aeq_params.yaml``
    and are resolved into this object by the caller (see
    ``transit_skims.skim_params``); the neutral defaults below build a bare
    no-policy graph.
    """

    wait_perceive: float = 1.0            # perceived factor on waits (iwaitfac/xwaitfac)
    walk_factor: float = 1.0              # perceived factor on walk links
    board_penalties: tuple = (0.0,)       # escalating boardpen (layered graph)
    linehaul: str | None = None           # label; keys the fare structures (faremat)
    skip: tuple = ()                      # ((lo, hi), ...) excluded mode ranges
    fac: tuple = ()                       # ((lo, hi, factor), ...) perceived-IVT factors
    key_band: tuple | None = None         # premier band -> KEYIVT; None = no premier
    ferry_band: tuple | None = None       # ferry sub-band -> FERRYIVT
    iwaitmax_min: float = 0.0             # initial-wait cost cap (min); 0 modes = off
    iwaitmax_modes: tuple = ()            # modes whose first boarding is capped
    wait_combine: str = "line"            # how boarding lines pool for the wait charge:
    # "line"    -- each line alone (deterministic slice = half its own headway);
    # "service" -- lines leaving the stop toward the SAME next stop pool into one
    #              service, charged half their COMBINED headway (Cube's COMBINE);
    # "node"    -- every line at the stop pools (over-pools where routes diverge)
    inveh_factor: dict = field(default_factory=dict)  # extra {mode: factor} overrides
    spread_window: float | None = None    # None: full S&F frequency spreading;
    # 0: fully deterministic expected wait (TRNBUILD best path, no spreading);
    # W>0: capped wait -- pay (expected wait - W) in the boarding cost and keep only
    # W perceived minutes frequency-based, shrinking the attractive-set window to ~W
    # (emulates TRNBUILD's combined-headways rule: spread only over near-equal lines)


@dataclass
class TransitGraph:
    """Layered SF transit graph ready for :class:`HyperpathGenerating`."""

    edges: pd.DataFrame                 # columns a_node, b_node, trav_time, freq
    n_vertices: int
    centroid_vertex: dict               # zone id -> ORIGIN vertex id (access edges out)
    dest_vertex: dict                   # zone id -> DESTINATION vertex id (egress in);
    # origins and destinations are split so no path can pass THROUGH a centroid
    # (egress -> re-access would reset the boarding-count/state machine)
    board_rows: dict                    # line name -> np.ndarray of boarding-edge rows
    ride_rows: pd.DataFrame | None = None  # ride edges -> (line, A, B) physical link, for
    # per-link assignment volumes (link_volumes); only populated on fare_states="none" graphs
    spread_window: float | None = None  # the frequency inflation this graph was built with;
    # skim_transit rescales the frequency wait by it (see the detwait note above), so it is
    # carried on the graph rather than passed separately -- they must never disagree.


def build_transit_graph(
    links: pd.DataFrame,
    headways: dict,
    params: TransitParams | None = None,
    *,
    n_zones: int = 1475,
    fares=None,
    fare_states: str = "none",
    access_mode: int = 1,
    egress_mode: int = 6,
) -> TransitGraph:
    """Build the layered Spiess-Florian graph from a Cube-style transit link table.

    *links* has one row per directional link (``A, B, time, mode, stopA, stopB,
    name`` and optional ``distance``); transit links have ``mode >= 10`` and a line
    ``name``, walk/support links carry ``mode`` < 10.  *headways* maps line name ->
    headway (minutes).  *fares* is an optional :class:`fares.TransitFares`; when given,
    the ``fare`` skim column is populated (boarding ``XFARE`` + ``farelinks``) and
    ``keydist`` carries key-mode in-vehicle distance for the rail distance-curve fare.

    *fare_states* controls how much previous-mode memory the stop states carry, so a
    re-boarding can charge the exact transfer fare ``XFARE[prev][cur]``:

    * ``"none"`` -- B(k)/C(k) carry no previous-mode label (single copy).  Fast; used for
      the per-iteration level-of-service skims (IVT/wait/boardings/walk), which do not
      need fare.  Transfer fare is not resolved (kept 0).
    * ``"operator"`` -- one B(k)/C(k) copy per *present transit mode* (operator), so
      ``XFARE[prev_mode][cur_mode]`` is exact -- matches Cube.  Larger graph; fares are
      static, so this pass is run once and cached rather than every iteration.  Only the
      REACHABLE (node, operator) state pairs are materialized (you can only "remember"
      an operator whose line stops within a transfer walk), keeping the graph ~20x
      smaller than the dense product with identical results.
    """
    params = params or TransitParams()
    pens = np.asarray(params.board_penalties, dtype=float)
    n_layers = len(pens) + 1                    # layers 0..L-1; board from 0..L-2
    links = links.copy()
    links["A"] = links["A"].astype(int)
    links["B"] = links["B"].astype(int)

    transit = links[(links["mode"] >= 10) & links["name"].notna()].copy()
    transit["hw"] = transit["name"].map(headways)
    transit = transit[transit["hw"] > 0]

    mode = transit["mode"].to_numpy()
    if params.skip:
        drop = np.zeros(len(transit), dtype=bool)
        for lo, hi in params.skip:
            drop |= (mode >= lo) & (mode <= hi)
        transit = transit[~drop]
        mode = transit["mode"].to_numpy()
    ivf = np.ones(len(transit))
    for lo, hi, fac in params.fac:
        ivf[(mode >= lo) & (mode <= hi)] = fac
    for m, fac in params.inveh_factor.items():
        ivf[mode == int(m)] = fac

    if "distance" not in transit:
        transit["distance"] = 0.0
    # active access/egress + transfer(3)/aux(4)/funnel(5); drive access/egress use
    # mode 2/7 (access_mode/egress_mode) instead of walk 1/6.  Only the ACTIVE access
    # and egress modes are included so inactive walk/drive connectors are not usable.
    active = {access_mode, egress_mode, 3, 4, 5}
    walk = links[links["mode"].isin(active)].copy()
    if "distance" not in walk:
        walk["distance"] = 0.0

    # previous-mode fare-state resolution: "operator" -> one state per present mode
    # (exact XFARE[prev][cur]); "none" -> a single state (fast LOS graph, no transfer
    # fare).  fare_state_of maps a transit mode to its state index; fare_prev_mode maps
    # a state index back to a representative previous mode for the XFARE lookup.
    present_modes = sorted({int(m) for m in mode})
    if fare_states == "operator" and fares is not None:
        # one state per distinct XFARE row among present modes: modes with identical
        # transfer-fare behaviour are interchangeable, so this is exact with fewer states.
        rows: dict[bytes, list[int]] = {}
        for m in present_modes:
            rows.setdefault(fares.xfare[m].tobytes(), []).append(m)
        reps = [ms[0] for ms in rows.values()]
        fare_state_of = {m: i for i, ms in enumerate(rows.values()) for m in ms}
        fare_prev_mode = np.array(reps, dtype=int)
    else:
        fare_state_of = dict.fromkeys(present_modes, 0)
        fare_prev_mode = np.array([0], dtype=int)
    G = len(fare_prev_mode)

    # one boarding point per (line, stop) -- see module docstring.  mode is carried so
    # the boarding fare (XFARE[access][line_mode]) can be charged per boarding edge.
    sa = (transit.loc[transit["stopA"] == 1, ["name", "A", "hw", "mode"]]
          .rename(columns={"A": "node"}))
    sb = (transit.loc[transit["stopB"] == 1, ["name", "B", "hw", "mode"]]
          .rename(columns={"B": "node"}))
    stops = pd.concat([sa, sb]).drop_duplicates(["name", "node"]).reset_index(drop=True)

    # walk edges by NOX role: access (1) -> A; egress (6) from B(k) only;
    # transfer walk (3) B(k) -> C(k) only. Other walk modes (funnels) state-preserving.
    # (classified before vertex allocation: the reachable-state closure needs them)
    wa, wb = walk["A"].to_numpy(), walk["B"].to_numpy()
    w_actual = walk["time"].to_numpy()
    w_dist = walk["distance"].to_numpy(dtype=float)
    wt = w_actual * params.walk_factor
    wm = walk["mode"].to_numpy()
    acc = (wm == access_mode) & (wa <= n_zones) & (wb > n_zones)
    egr = (wm == egress_mode) & (wa > n_zones) & (wb <= n_zones)
    xfr = (wm == 3) & (wa > n_zones) & (wb > n_zones)
    oth = ~(acc | egr | xfr)            # funnels etc.: preserve state (aux walk)
    o_nc = oth & (wa > n_zones) & (wb > n_zones)

    # ---- vertex ids ----
    # stop states x layers: A (walk-accessed, layer 0, board-only), then per layer
    # k = 1..L-1: B(k, g) (alighted from a group-g line; board/egress/one transfer walk)
    # and C(k, g) (arrived by transfer walk from a group-g line; board-only).  The
    # mode-group g of the last-ridden line is carried so a re-boarding charges the exact
    # transfer fare XFARE[g][to].  Onboard vertices per (line-stop, layer 1..L-1).
    all_nodes = pd.concat([links["A"], links["B"]])
    centroids = sorted({int(x) for x in all_nodes if x <= n_zones})
    cidx = {c: i for i, c in enumerate(centroids)}
    pnodes = sorted({int(x) for x in all_nodes if x > n_zones})
    pidx = {n: i for i, n in enumerate(pnodes)}
    pn = len(pidx)
    obk = pd.unique(pd.concat([transit["name"] + "|" + transit["A"].astype(str),
                               transit["name"] + "|" + transit["B"].astype(str)]))
    obidx = {k: i for i, k in enumerate(obk)}

    # ---- reachable (node, fare-group) states ----
    # B(n, k, g) is enterable only by alighting from a group-g line at n or by a funnel
    # walk from a node that can; C(n, k, g) only by a transfer walk out of an enterable
    # B (then funnels).  States outside this closure have no in-edges -- dead weight --
    # so the operator fare graph materializes only the reachable (node, g) pairs
    # (measured ~24x fewer B/C states on the com run; results are identical).  LOS
    # graphs (G=1) admit every state, preserving the validated dense topology exactly.
    s_grp = np.array([fare_state_of[int(m)] for m in stops["mode"]])
    pi_s = np.array([pidx[int(n)] for n in stops["node"]], dtype=np.int64)
    pi_egr = np.array([pidx[int(n)] for n in wa[egr]], dtype=np.int64)
    xa = np.array([pidx[int(n)] for n in wa[xfr]], dtype=np.int64)
    xb = np.array([pidx[int(n)] for n in wb[xfr]], dtype=np.int64)
    fa = np.array([pidx[int(n)] for n in wa[o_nc]], dtype=np.int64)
    fb = np.array([pidx[int(n)] for n in wb[o_nc]], dtype=np.int64)
    if fare_states == "operator" and fares is not None:
        def _close(adm):                # fixpoint over funnel walks (short chains)
            while True:
                n0 = int(adm.sum())
                np.logical_or.at(adm, fb, adm[fa])
                if int(adm.sum()) == n0:
                    return adm

        admB = np.zeros((pn, G), dtype=bool)
        admB[pi_s, s_grp] = True                       # alight from a group-g line
        admB = _close(admB)
        admC = np.zeros((pn, G), dtype=bool)
        np.logical_or.at(admC, xb, admB[xa])           # transfer walk out of B
        admC = _close(admC)
    else:
        admB = np.ones((pn, G), dtype=bool)
        admC = np.ones((pn, G), dtype=bool)

    # dense ids for the admitted states: each admitted (node, g) pair owns a block of
    # KL = n_layers-1 consecutive vertices (one per layer k = 1..L-1)
    KL = n_layers - 1
    b_pair = np.full((pn, G), -1, dtype=np.int64)
    b_pair[admB] = np.arange(int(admB.sum()))
    c_pair = np.full((pn, G), -1, dtype=np.int64)
    c_pair[admC] = np.arange(int(admC.sum()))
    d0 = len(cidx)                              # destination copies of the centroids
    s0 = d0 + len(cidx)                         # A states: one per physical node
    b0 = s0 + pn
    c0v = b0 + int(admB.sum()) * KL
    o0 = c0v + int(admC.sum()) * KL

    # premier-rail boarding-station tracking, for the exact FAREMAT[board][alight] OD fare.
    # ONLY when a faremat exists for this line-haul (rail/ferry -- bus fare is a flat boarding
    # charge, no OD matrix) and we are on a fare graph (fare_states != "none").  Rail onboard
    # vertices then carry the boarding station; bus onboard does not.  Fares do not affect
    # routing, so the path is unchanged -- only the accumulated fare differs.
    _fb = fares.rail_band.get(params.linehaul or "") if fares is not None else None
    track_board = bool(fare_states != "none" and fares is not None and _fb
                       and (params.linehaul or "") in getattr(fares, "faremat", {}))
    if track_board:
        _lm = dict(zip(transit["name"], transit["mode"], strict=False))     # line -> mode
        rail_keys = [k for k in obidx if _fb[0] <= _lm.get(k.split("|")[0], 0) <= _fb[1]]
        bus_keys = [k for k in obidx if k not in set(rail_keys)]
        bus_i = {k: i for i, k in enumerate(bus_keys)}
        rail_i = {k: i for i, k in enumerate(rail_keys)}
        # per-LINE fare stations: a rail onboard vertex can only have boarded at a station
        # on its own line, so its copies span that line's stops -- not the whole fare band
        # (the band pools operators: all-band copies were ~4-8x dead vertices/edges).
        line_stns: dict[str, list] = {}
        for k in rail_keys:
            ln, nd = k.split("|")
            line_stns.setdefault(ln, set()).add(int(nd))
        line_stns = {ln: sorted(v) for ln, v in line_stns.items()}
        line_sidx = {ln: {s: i for i, s in enumerate(v)} for ln, v in line_stns.items()}
        key_off: dict[str, int] = {}                          # copy-block offset per key
        _tot = 0
        for k in rail_keys:
            key_off[k] = _tot
            _tot += len(line_stns[k.split("|")[0]])
        nb = len(bus_keys)
        _rail0 = o0 + nb * (n_layers - 1)                     # rail onboard block start
        n_vertices = _rail0 + _tot * (n_layers - 1)
    else:
        n_vertices = o0 + len(obidx) * (n_layers - 1)

    def cv(nodes):                              # origin centroid vertices
        return np.array([cidx[int(n)] for n in nodes])

    def dvx(nodes):                             # destination centroid vertices
        return np.array([d0 + cidx[int(n)] for n in nodes])

    def av(nodes):                      # state A: walk-accessed, 0 boardings
        return s0 + np.array([pidx[int(n)] for n in nodes])

    def bv(pi, k, g):                   # state B(k, g); pi = pidx array, (n, g) admitted
        return b0 + b_pair[pi, g] * KL + (k - 1)

    def cvw(pi, k, g):                  # state C(k, g); pi = pidx array, (n, g) admitted
        return c0v + c_pair[pi, g] * KL + (k - 1)

    def ov(names, nodes, j, board=None):
        if not track_board:
            keys = [obidx[f"{a}|{int(b)}"] for a, b in zip(names, nodes, strict=False)]
            return o0 + np.array(keys) * (n_layers - 1) + (j - 1)
        # bus onboard: (line-stop, layer); rail onboard: (line-stop, layer, boarding-station)
        keys = [f"{a}|{int(b)}" for a, b in zip(names, nodes, strict=False)]
        out = np.empty(len(keys), dtype=np.int64)
        for i, k in enumerate(keys):
            if k in rail_i:
                ln = k.split("|")[0]
                nsl = len(line_stns[ln])
                s = line_sidx[ln][int(board[i])] if board is not None else 0
                out[i] = _rail0 + key_off[k] * (n_layers - 1) + (j - 1) * nsl + s
            else:
                out[i] = o0 + bus_i[k] * (n_layers - 1) + (j - 1)
        return out

    frames: list[pd.DataFrame] = []

    def add(a, b, t, f, **cols):
        n = len(a)
        d = {"a_node": a, "b_node": b, "trav_time": t, "freq": f}
        for c in SKIM_COLS:
            v = cols.get(c, 0.0)
            d[c] = v if hasattr(v, "__len__") else np.full(n, v, dtype=float)
        frames.append(pd.DataFrame(d))

    # walk-edge skims: actual walk minutes to wacc/wegr/waux by role; sk_edge =
    # perceived (x walk factor)
    acc_drive = access_mode in (2, 7)   # drive access -> dtim/ddist not wacc
    egr_drive = egress_mode in (2, 7)
    _acc_cols = ({"dtim": w_actual[acc], "ddist": w_dist[acc]} if acc_drive
                 else {"wacc": w_actual[acc]})
    _egr_cols = ({"dtim": w_actual[egr], "ddist": w_dist[egr]} if egr_drive
                 else {"wegr": w_actual[egr]})
    if acc.any():
        add(cv(wa[acc]), av(wb[acc]), wt[acc], INF_FREQ, sk_edge=wt[acc], **_acc_cols)
    # egress / transfer-walk / funnel emanate from the ADMITTED mode-group copies of
    # B(k)/C(k); walking never changes the last-ridden mode, so the group g is
    # preserved (funnel/transfer targets admit g by the reachability closure).
    dv_e, wt_e = dvx(wb[egr]), wt[egr]
    wt_x, wa_x = wt[xfr], w_actual[xfr]
    wt_f, wa_f = wt[o_nc], w_actual[o_nc]
    for g in range(G):
        mE, mX = admB[pi_egr, g], admB[xa, g]
        mB, mC = admB[fa, g], admC[fa, g]
        for k in range(1, n_layers):
            if mE.any():
                add(bv(pi_egr[mE], k, g), dv_e[mE], wt_e[mE], INF_FREQ,
                    sk_edge=wt_e[mE], **{c: v[mE] for c, v in _egr_cols.items()})
            if mX.any():
                add(bv(xa[mX], k, g), cvw(xb[mX], k, g), wt_x[mX], INF_FREQ,
                    sk_edge=wt_x[mX], waux=wa_x[mX])
            if mB.any():
                add(bv(fa[mB], k, g), bv(fb[mB], k, g), wt_f[mB], INF_FREQ,
                    sk_edge=wt_f[mB], waux=wa_f[mB])
            if mC.any():
                add(cvw(fa[mC], k, g), cvw(fb[mC], k, g), wt_f[mC], INF_FREQ,
                    sk_edge=wt_f[mC], waux=wa_f[mC])
    if o_nc.any():                       # state-A funnels (pre-first-board), no group yet
        add(av(wa[o_nc]), av(wb[o_nc]), wt_f, INF_FREQ, sk_edge=wt_f, waux=wa_f)

    # ride: onboard chains per layer 1..L-1.  skims: actual IVT to ivt (all) + keyivt /
    # ferryivt by mode band; sk_edge = perceived IVT (x ivf).
    tn = transit["name"].to_numpy()
    ta, tb = transit["A"].to_numpy(), transit["B"].to_numpy()
    t_actual = transit["time"].to_numpy()
    t_dist = transit["distance"].to_numpy(dtype=float)
    tt = t_actual * ivf
    kb = params.key_band
    is_key = ((mode >= kb[0]) & (mode <= kb[1])) if kb else np.zeros(len(transit), bool)
    fyb = params.ferry_band
    is_ferry = (((mode >= fyb[0]) & (mode <= fyb[1])) if fyb
                else np.zeros(len(transit), bool))
    ivt_key = np.where(is_key, t_actual, 0.0)
    ivt_ferry = np.where(is_ferry, t_actual, 0.0)
    # distance for the rail fare curve accumulates over the FARE band (distance-priced
    # modes: ferry 100-109 for lrf, commuter 130-139 for com, BART for hvy) -- distinct
    # from the KEYIVT band (lrf key spans 100-119 but light rail 110-119 is flat-fare).
    fb = fares.rail_band.get(params.linehaul or "") if fares is not None else None
    is_fare = ((mode >= fb[0]) & (mode <= fb[1])) if fb else np.zeros(len(transit), bool)
    key_dist = np.where(is_fare, t_dist, 0.0)
    # per-link farelinks surcharge (cents) on the matching (mode, a, b) ride links
    fl = np.zeros(len(transit))
    if fares is not None and fares.farelinks:
        fll = fares.farelinks
        fl = np.array([fll.get((int(m), int(a), int(b)), 0.0)
                       for m, a, b in zip(mode, ta, tb, strict=False)])
    ride_meta: list = []                 # (row_start, line, A, B) per ride add, for link_volumes
    for j in range(1, n_layers):
        if not track_board:
            _rs = sum(len(f) for f in frames)
            add(ov(tn, ta, j), ov(tn, tb, j), tt, INF_FREQ,
                sk_edge=tt, ivt=t_actual, keyivt=ivt_key, ferryivt=ivt_ferry,
                keydist=key_dist, fare=fl)
            ride_meta.append((_rs, tn, ta, tb))
            continue
        bm = ~is_fare                                  # bus ride links: single onboard copy
        if bm.any():
            add(ov(tn[bm], ta[bm], j), ov(tn[bm], tb[bm], j), tt[bm], INF_FREQ,
                sk_edge=tt[bm], ivt=t_actual[bm], keyivt=ivt_key[bm],
                ferryivt=ivt_ferry[bm], keydist=key_dist[bm], fare=fl[bm])
        if is_fare.any():                # rail: one copy per boarding station OF ITS LINE
            for ln in np.unique(tn[is_fare]):
                rm = is_fare & (tn == ln)
                for s in line_stns[ln]:
                    sarr = np.full(int(rm.sum()), s)
                    add(ov(tn[rm], ta[rm], j, sarr), ov(tn[rm], tb[rm], j, sarr),
                        tt[rm], INF_FREQ, sk_edge=tt[rm], ivt=t_actual[rm],
                        keyivt=ivt_key[rm], ferryivt=ivt_ferry[rm],
                        keydist=key_dist[rm], fare=fl[rm])

    # boarding (charges pens[k] for the (k+1)-th boarding) and alighting
    freq_scale = 2.0 / params.wait_perceive     # SF wait 1/freq == perceived half-headway
    s_name = stops["name"].to_numpy()
    s_node = stops["node"].to_numpy()
    s_hw = stops["hw"].to_numpy()
    board_line_rows: dict[str, list] = {}

    s_mode = stops["mode"].to_numpy()   # (s_grp / pi_s computed with the state closure)
    # first-boarding fare = XFARE[walk-access mode 1][line mode]; transfer fare from a
    # state-g line (prev mode fare_prev_mode[g]) into a stop's line = XFARE[prev][cur].
    # With fare_states="operator" this is exact per mode-pair (free for same operator,
    # full for cross-operator); with "none" (G=1, prev mode 0) transfers are free.
    if fares is not None:
        board_fare = fares.xfare[access_mode, s_mode]         # boarding fare from access
        tf_grp = fares.xfare[fare_prev_mode][:, s_mode]        # (G, n_stops) exact XFARE
    else:
        board_fare = np.zeros(len(stops))
        tf_grp = np.zeros((G, len(stops)))
    # IWAITMAX: Cube caps the INITIAL wait only (TRNBUILD `factor IWAITMAX[mode]`,
    # transit_combined_headways.block: "people time their arrivals for the schedules").
    # Faithful analog: FIRST-boarding edges of capped modes use the capped headway in BOTH
    # the deterministic boarding cost and the S&F frequency (a lone capped line then prices
    # at exactly wait_perceive*25, Cube's number, with splits staying frequency-
    # proportional); RE-boarding (transfer) edges use the raw headway -- Cube charges the
    # full transfer wait to board a sparse line mid-path.  (Setting freq=INF instead of
    # capping the frequency's headway breaks attractive-set combination -- tested, backfired.)
    hw_first = np.where(np.isin(s_mode, params.iwaitmax_modes),
                        np.minimum(s_hw, 2.0 * params.iwaitmax_min), s_hw)

    # COMBINE (transit_combined_headways.block): Cube pools the lines a rider waits for
    # together at a stop into ONE service and charges half their COMBINED headway -- four
    # 15-min BART lines through the same tunnel are a 3.75-min service, not four 15-min
    # ones.  The S&F frequency term below already does exactly that (its wait is
    # 1/sum(freq) over the attractive set); what breaks the reported wait is the
    # DETERMINISTIC slice, a per-boarding constant that acts as a floor and does not
    # shrink as lines are added (+100% at a 4-line rail station).  That slice is required
    # in the ROUTING cost -- it is what keeps the perceived cost of waiting correct while
    # the inflated frequencies shrink the attractive set -- so it is charged here and
    # carried as the `detwait` skim column, then subtracted back out when the wait is
    # reported (see skim_transit).  Pooling it over a static group instead was tested and
    # fails: any structural pool (shared next stop, whole node) is far larger than the
    # destination-dependent attractive set, over-correcting to -26% / -64% on rail waits.
    def _board_cost_freq(hw):
        """Deterministic wait slice + S&F frequency, from the line's own headway."""
        wait_exp = params.wait_perceive * hw / 2.0        # expected perceived wait
        w = params.spread_window
        if w is None:
            return np.zeros(len(stops)), freq_scale / hw
        if w <= 0:
            return wait_exp, np.full(len(stops), INF_FREQ)
        if w <= 1.0:
            return (np.maximum(wait_exp - w, 0.0),
                    np.where(wait_exp > w, 1.0 / w, freq_scale / hw))
        # w > 1 acts as a frequency-inflation factor alpha: all line frequencies are
        # scaled up by alpha (shrinking the attractive-set window by ~alpha while keeping
        # frequency-PROPORTIONAL splits) and the removed share of the expected wait is
        # paid deterministically in the boarding cost.
        return wait_exp * (1.0 - 1.0 / w), w * freq_scale / hw

    cost_first, freq_first = _board_cost_freq(hw_first)   # initial: IWAITMAX-capped
    _, freq_xfer = _board_cost_freq(s_hw)                 # transfer kernel: raw headway
    cost_xfer_capped = cost_first                         # deterministic slice stays capped
    half_first, half_xfer = hw_first / 2.0, s_hw / 2.0    # iwait/xwait split markers

    def _board(from_v, k, first, fare_arr, sel=None):
        start = sum(len(f) for f in frames)
        # sk_edge carries ONLY the non-wait boardpen (board_cost is wait -> stays inside
        # u - sk_edge). first vs re-boarding half-headways feed the iwait/xwait split.
        # fare = first-boarding XFARE (from walk) or the group-g transfer fare.  board=
        # s_node sets the rail boarding station (ignored for bus onboard) for the faremat
        # lookup.  sel restricts to the stops whose node admits the source (g) state.
        # transfers: raw headway drives the kernel frequency (real expected wait) and the
        # xwait marker (Cube reports raw transfer waits), but the deterministic spread
        # slice stays capped -- with w>1 that slice is charged per LINE, not per combined
        # service, so raw sparse headways overcharge multi-pattern stops vs Cube's COMBINE
        # (tested: raw slice collapses com recall 96.5% -> 84.9% via the 300-min cap).
        idx = np.arange(len(stops)) if sel is None else np.flatnonzero(sel)
        board_cost = (cost_first if first else cost_xfer_capped)[idx]
        board_freq = (freq_first if first else freq_xfer)[idx]
        add(from_v, ov(s_name[idx], s_node[idx], k + 1, board=s_node[idx]),
            board_cost + pens[k], board_freq,
            boards=1.0, sk_edge=np.full(len(idx), pens[k]), detwait=board_cost,
            w_first=(half_first[idx] if first else 0.0),
            w_xfer=(0.0 if first else half_xfer[idx]), fare=fare_arr[idx])
        for i, ln in enumerate(s_name[idx]):
            board_line_rows.setdefault(ln, []).append(start + i)

    _board(av(s_node), 0, True, board_fare)     # first boarding from access state
    for g in range(G):                          # re-boarding from admitted B(k)/C(k)
        selB, selC = admB[pi_s, g], admC[pi_s, g]
        for k in range(1, n_layers - 1):
            if selB.any():
                _board(bv(pi_s[selB], k, g), k, False, tf_grp[g], selB)
            if selC.any():
                _board(cvw(pi_s[selC], k, g), k, False, tf_grp[g], selC)
    fm_lh = fares.faremat.get(params.linehaul or "", {}) if (track_board and fares) else {}
    for j in range(1, n_layers):                # alight from line M -> B(j, group(M))
        for g in range(G):
            m = s_grp == g
            if not m.any():
                continue
            pim = pi_s[m]
            if not track_board:
                add(ov(s_name[m], s_node[m], j), bv(pim, j, g),
                    np.zeros(int(m.sum())), INF_FREQ)
                continue
            mnm, mn = s_name[m], s_node[m]
            is_r = np.array([f"{a}|{int(b)}" in rail_i for a, b in zip(mnm, mn, strict=False)])
            if (~is_r).any():                          # bus alight: no fare
                add(ov(mnm[~is_r], mn[~is_r], j), bv(pim[~is_r], j, g),
                    np.zeros(int((~is_r).sum())), INF_FREQ)
            if is_r.any():                             # rail alight: charge FAREMAT[board][alight]
                rnm, rmn, rpi = mnm[is_r], mn[is_r], pim[is_r]
                for ln in np.unique(rnm):              # one alight edge per boarding station
                    lm2 = rnm == ln                    # of the alighting LINE
                    for s in line_stns[ln]:
                        sarr = np.full(int(lm2.sum()), s)
                        farr = np.array([fm_lh.get((s, int(t)), 0.0) for t in rmn[lm2]])
                        add(ov(rnm[lm2], rmn[lm2], j, sarr), bv(rpi[lm2], j, g),
                            np.zeros(int(lm2.sum())), INF_FREQ, fare=farr)

    edges = pd.concat(frames, ignore_index=True)
    board_rows = {k: np.array(v) for k, v in board_line_rows.items()}
    ride_rows = None
    if ride_meta:                        # ride edge -> physical (line, A, B), for link_volumes
        ride_rows = pd.DataFrame({
            "row": np.concatenate([np.arange(s, s + len(t)) for s, t, _, _ in ride_meta]),
            "line": np.concatenate([t for _, t, _, _ in ride_meta]),
            "A": np.concatenate([a for _, _, a, _ in ride_meta]),
            "B": np.concatenate([b for _, _, _, b in ride_meta])})
    centroid_vertex = {c: cidx[c] for c in centroids}
    dest_vertex = {c: d0 + cidx[c] for c in centroids}
    return TransitGraph(edges=edges, n_vertices=n_vertices,
                        centroid_vertex=centroid_vertex, dest_vertex=dest_vertex,
                        board_rows=board_rows, ride_rows=ride_rows,
                        spread_window=params.spread_window)


def assign_transit(graph: TransitGraph, demand: np.ndarray, *,
                   threads: int | None = None) -> np.ndarray:
    """Run the Spiess-Florian hyperpath assignment; return per-edge volume."""
    o, d = np.nonzero(demand)
    vol = demand[o, d]
    cvert = graph.centroid_vertex
    dvert = graph.dest_vertex
    ov = np.array([cvert.get(int(x + 1), -1) for x in o])
    dv = np.array([dvert.get(int(x + 1), -1) for x in d])
    ok = (ov >= 0) & (dv >= 0)

    hp = HyperpathGenerating(
        graph.edges[["a_node", "b_node", "trav_time", "freq"]],
        tail="a_node", head="b_node",
        nodes_to_indices=np.arange(graph.n_vertices, dtype=np.int64),
        o_vert_ids=np.arange(graph.n_vertices, dtype=np.int64),
        d_vert_ids=np.arange(graph.n_vertices, dtype=np.int64),
    )
    hp.assign(ov[ok].astype(np.uint32), dv[ok].astype(np.uint32),
              vol[ok].astype(np.float64), threads=threads)
    return hp._edges["volume"].to_numpy()  # noqa: SLF001 -- fork exposes volumes via _edges only


def boardings_by_line(volume: np.ndarray, graph: TransitGraph) -> pd.Series:
    """Total boardings per line = sum of volume over that line's boarding edges."""
    return pd.Series({ln: float(volume[rows].sum()) for ln, rows in graph.board_rows.items()})


def link_volumes(volume: np.ndarray, graph: TransitGraph, *, by_line: bool = False) -> pd.DataFrame:
    """Per physical directional transit link (A, B) passenger volume, summed over all
    boarding layers (and lines, unless ``by_line``).  Mirrors Cube ``trnlink`` ``AB_VOL``.

    Requires an assignment graph (``fare_states="none"``, which populates ``ride_rows``)."""
    rr = graph.ride_rows
    if rr is None:
        raise ValueError("graph has no ride_rows; build with fare_states='none' for assignment")
    df = pd.DataFrame({"A": rr["A"].to_numpy(), "B": rr["B"].to_numpy(),
                       "line": rr["line"].to_numpy(), "vol": volume[rr["row"].to_numpy()]})
    keys = ["A", "B", "line"] if by_line else ["A", "B"]
    return df.groupby(keys, as_index=False)["vol"].sum()


def skim_transit(
    graph: TransitGraph,
    *,
    linehaul: str | None = None,
    fares=None,
    wait_perceive: float = 2.8,
    n_zones: int = 1475,
    threads: int | None = None,
    max_path_min: float = 180.0,
    max_perceived_min: float | None = None,
    rail_curve_fallback: bool = False,
    premier: bool = False,
    combine_wait: bool = True,
) -> dict[str, np.ndarray]:
    """Skim the layered SF graph into Cube-style component matrices (actual units).

    The fork's :class:`HyperpathGenerating` accumulates each edge column as its
    strategy-expected value along the SAME optimal hyperpath -- Cube's optimal-strategy
    skim.  We ride the perceived-cost strategy and read out ACTUAL-minute components.
    Wait is not an edge attribute; it is isolated as ``(u - sk_edge) / wait_perceive``
    where ``u`` is the total perceived cost (is_travel_time) and ``sk_edge`` the
    accumulated perceived NON-wait edge time -- exact under any ``spread_window``.

    For skim parity with Cube build the graph with ``spread_window=1.5`` (matches
    Cube's combined-headway window); ``None`` (full spread) is more behaviourally
    correct but reports ~10% lower wait.

    ``premier`` applies Cube's hierarchical filter: a premium skim set keeps an OD
    only where the path actually uses the premier mode band (KEYIVT > 0; verified
    100% in the reference), so an OD without e.g. heavy rail is left to a lower set.
    ``loc``/``trn`` (no key band) pass ``premier=False`` and keep every reachable OD.
    ``linehaul`` labels the run and keys the fare structures (faremat / rail curve).

    Returns a dict of ``n_zones x n_zones`` arrays keyed by ActivitySim token:
    ``TOTIVT, KEYIVT, FERRYIVT, IWAIT, XWAIT, WAUX, BOARDS`` (minutes / boardings;
    x100 scaling and OMX naming happen at the wiring layer).  Unreachable ODs, those
    not using the premier mode, and those whose actual path time exceeds
    ``max_path_min`` (Cube's max-run prune) are 0.
    """
    zones = sorted(graph.centroid_vertex)                 # zone ids present as centroids
    o_vert = np.array([graph.centroid_vertex[z] for z in zones], dtype=np.int64)
    d_vert = np.array([graph.dest_vertex[z] for z in zones], dtype=np.int64)
    # kernel treats nodes_to_indices as identity (vertex->vertex); the per-taz vertex
    # ids in o/d_vert_ids drive the taz mapping (od_index_to_taz_index).
    n2i = np.arange(graph.n_vertices, dtype=np.int64)

    cols = list(SKIM_COLS)
    hp = HyperpathGenerating(
        graph.edges[["a_node", "b_node", "trav_time", "freq", *cols]],
        tail="a_node", head="b_node", trav_time="trav_time", freq="freq",
        skim_cols=["trav_time", *cols],
        o_vert_ids=o_vert, d_vert_ids=d_vert, nodes_to_indices=n2i,
    )
    # skimming covers every OD regardless of demand; pass a single dummy entry.
    hp.assign(o_vert[:1].astype(np.uint32), d_vert[:1].astype(np.uint32),
              np.zeros(1), threads=threads)
    sm = hp.skim_matrix
    zi = np.array(zones) - 1

    def zmat(name):
        out = np.zeros((n_zones, n_zones))
        out[np.ix_(zi, zi)] = np.asarray(sm.get_matrix(name), dtype=float)
        return out

    u = zmat("trav_time")
    ivt, keyivt, ferryivt = zmat("ivt"), zmat("keyivt"), zmat("ferryivt")
    wacc, waux, wegr = zmat("wacc"), zmat("waux"), zmat("wegr")
    boards = zmat("boards")
    w_first, w_xfer = zmat("w_first"), zmat("w_xfer")
    wsum = w_first + w_xfer
    # IWAITMAX on the REPORTED wait: the half-headway markers bound the reported wait --
    # w_first is IWAITMAX-capped (25 for Caltrain/ferry, Cube's initial-wait cap), w_xfer is
    # the raw half-headway (Cube does NOT cap transfer waits).  For normal modes the marker
    # sum >= the S&F combined wait, so this is a no-op; for long-headway capped modes it
    # reports Cube's capped initial wait instead of the uncapped frequency wait.
    # Cube's COMBINE wait, recovered exactly: (u - sk_edge) is the perceived wait the
    # router paid = the S&F FREQUENCY term + the DETERMINISTIC slice.  The frequency term
    # alone is 1/sum(freq) over the attractive set = half its combined headway, deflated
    # by exactly `spread_window` (every line's frequency was inflated by it).  So strip
    # the deterministic slice and rescale by that same factor: what comes back is half the
    # attractive set's COMBINED headway -- Cube's formula -- with routing untouched.
    # (A lone line is unchanged: freq term = w x half-headway, rescaled -> half-headway.)
    # combine_wait=False reproduces Cube's MAXDIFF[130]=10: commuter-rail patterns are
    # NOT combined for the headway calculation (a bullet does not pool with a local), so
    # the wait stays the boarded line's own -- i.e. the deterministic slice is kept.
    if combine_wait:
        sw = graph.spread_window
        freq_wait = np.maximum(u - zmat("sk_edge") - zmat("detwait"), 0.0)
        scale = sw if (sw and sw > 1.0) else 1.0
        wait_u = scale * freq_wait / wait_perceive
    else:
        wait_u = np.maximum(u - zmat("sk_edge"), 0.0) / wait_perceive
    wait = np.minimum(wait_u, wsum)
    # proportional iwait/xwait split by marker share.  (A sequential split -- iwait gets
    # first claim up to its marker -- was tested and overshoots both ways: the w_first
    # marker is a strategy expectation, not the realized first wait, so giving it full
    # priority over-allocates iwait and starves xwait.)
    with np.errstate(divide="ignore", invalid="ignore"):
        frac_i = np.where(wsum > 0, w_first / wsum, 1.0)
    iwait, xwait = wait * frac_i, wait * (1.0 - frac_i)

    # hierarchical premier-mode filter: premium sets keep only paths that use the
    # premier band (KEYIVT > 0); loc keeps every reachable OD (all paths are local).
    # fare = accumulated boarding XFARE + farelinks (cents), plus the rail distance
    # curve on the key-mode in-vehicle distance for hvy/com (0 for bus/light rail).
    fare = zmat("fare")
    # exact station-to-station faremat is accumulated in-graph (fare column); fall back to the
    # distance curve only for line-hauls without a faremat.
    # rail fare: exact FAREMAT is charged on the operator fare graph's alight edges; the
    # distance curve covers line-hauls without a fare matrix.  rail_curve_fallback adds
    # the curve on LOS graphs for faremat line-hauls too -- used to fill the few pairs
    # the union-service fare pass cannot reach (fare there would otherwise be 0).
    if fares is not None and ((linehaul or "") not in getattr(fares, "faremat", {})
                              or rail_curve_fallback):
        fare = fare + fares.rail_fare(linehaul, zmat("keydist"))

    dtim, ddist = zmat("dtim"), zmat("ddist")     # drive access/egress time / distance
    reach = (keyivt > 0) if premier else (u > 0)
    actual_total = ivt + wait + wacc + waux + wegr + dtim
    keep = reach & (actual_total <= max_path_min)
    if max_perceived_min is not None:            # Cube maxpathtime prune (perceived cost)
        keep = keep & (u <= max_perceived_min)
    out = {"TOTIVT": ivt, "KEYIVT": keyivt, "FERRYIVT": ferryivt, "IWAIT": iwait,
           "XWAIT": xwait, "WACC": wacc, "WAUX": waux, "WEGR": wegr, "BOARDS": boards,
           "FARE": fare, "DTIM": dtim, "DDIST": ddist}
    return {k: np.where(keep, v, 0.0) for k, v in out.items()}
