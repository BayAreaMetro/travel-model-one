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
  (``modefac`` / ``skipmodes``, see :data:`RUN_COST`);
* Cube's *escalating* boarding penalties (boardpen 0/30/45/...) via a **layered
  ("journey levels") graph**: layer k of a stop means "k boardings so far", and
  boarding is the only edge that moves up a layer, charging the k-th penalty.  This
  gives the memoryless hyperpath the boarding-count memory the escalating penalty
  needs (the same device as Emme's journey levels).

One boarding point per (line, stop) is used: interior stops appear as both ``stopB``
of the incoming link and ``stopA`` of the outgoing link, and adding both would create
parallel boarding edges whose frequencies ADD in Spiess-Florian (halving the wait).

Validation vs 2023_TM161_IPA_35 (AM, no calibrated constants):
local bus boardings -2.1% r=0.987; heavy-rail run rail boardings -2.3% r=0.962.

Not yet modelled: fares as skims, transfer prohibitors, drive (PNR/KNR) access legs.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from aequilibrae.paths.cython.public_transport import HyperpathGenerating

INF_FREQ = 1.0e20

# link mode codes (TransitAssign.job): walk access / egress / stop-to-stop transfer
WALK_MODES = (1, 6, 3)

# Cube's escalating boarding penalties (perceived min); index = boardings so far.
BOARD_PENALTIES = (0.0, 30.0, 45.0)   # 4th+ boardings disallowed (negligible in data)

# Per-line-haul perceived-IVT factors and excluded mode ranges (TransitAssign.job
# token_modefac / token_skipmodes).  Mode buckets: 10-79 local bus, 80-99 express,
# 100-109 ferry, 110-119 light rail, 120-129 heavy rail, 130-139 commuter rail.
RUN_COST: dict[str, dict] = {
    "com": {"skip": [],
            "fac": [(10, 79, 1.5), (80, 99, 1.2), (100, 109, 1.1), (110, 119, 1.1),
                    (120, 129, 1.1), (130, 139, 1.0)]},
    "hvy": {"skip": [(130, 139)],
            "fac": [(10, 79, 1.5), (80, 99, 1.2), (100, 109, 1.1), (110, 119, 1.1),
                    (120, 129, 1.0)]},
    "exp": {"skip": [(130, 139), (120, 129)],
            "fac": [(10, 79, 1.5), (80, 99, 1.0), (100, 109, 1.5), (110, 119, 1.5)]},
    "lrf": {"skip": [(130, 139), (120, 129), (80, 99)],
            "fac": [(10, 79, 1.5), (100, 109, 1.0), (110, 119, 1.0)]},
    "loc": {"skip": [(130, 139), (120, 129), (80, 99), (100, 119)],
            "fac": [(10, 79, 1.0)]},
}


@dataclass
class TransitParams:
    """Perceived-cost parameters (minutes), matched to ``TransitAssign.job``."""

    wait_perceive: float = 2.8            # iwaitfac / xwaitfac
    walk_factor: float = 2.0              # perceived-time factor on walk links
    board_penalties: tuple = BOARD_PENALTIES   # escalating boardpen (layered graph)
    linehaul: str | None = None           # key into RUN_COST for modefac/skipmodes
    inveh_factor: dict = field(default_factory=dict)  # extra {mode: factor} overrides


@dataclass
class TransitGraph:
    """Layered SF transit graph ready for :class:`HyperpathGenerating`."""

    edges: pd.DataFrame                 # columns a_node, b_node, trav_time, freq
    n_vertices: int
    centroid_vertex: dict               # zone id -> vertex id (O/D vertices)
    board_rows: dict                    # line name -> np.ndarray of boarding-edge rows


def build_transit_graph(
    links: pd.DataFrame,
    headways: dict,
    params: TransitParams | None = None,
    *,
    walk_modes: tuple = WALK_MODES,
    n_zones: int = 1475,
) -> TransitGraph:
    """Build the layered Spiess-Florian graph from a Cube-style transit link table.

    *links* has one row per directional link (``A, B, time, mode, stopA, stopB,
    name``); transit links have ``mode >= 10`` and a line ``name``, walk links carry
    ``mode`` in *walk_modes*.  *headways* maps line name -> headway (minutes).
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

    cost = RUN_COST.get(params.linehaul or "", {"skip": [], "fac": []})
    mode = transit["mode"].to_numpy()
    if cost["skip"]:
        drop = np.zeros(len(transit), dtype=bool)
        for lo, hi in cost["skip"]:
            drop |= (mode >= lo) & (mode <= hi)
        transit = transit[~drop]
        mode = transit["mode"].to_numpy()
    ivf = np.ones(len(transit))
    for lo, hi, fac in cost["fac"]:
        ivf[(mode >= lo) & (mode <= hi)] = fac
    for m, fac in params.inveh_factor.items():
        ivf[mode == int(m)] = fac

    walk = links[links["mode"].isin(walk_modes)]

    # one boarding point per (line, stop) -- see module docstring
    sa = transit.loc[transit["stopA"] == 1, ["name", "A", "hw"]].rename(columns={"A": "node"})
    sb = transit.loc[transit["stopB"] == 1, ["name", "B", "hw"]].rename(columns={"B": "node"})
    stops = pd.concat([sa, sb]).drop_duplicates(["name", "node"]).reset_index(drop=True)

    # ---- vertex ids: centroids, stop(node, layer), onboard(line-node, layer 1..L-1)
    all_nodes = pd.concat([links["A"], links["B"]])
    centroids = sorted({int(x) for x in all_nodes if x <= n_zones})
    cidx = {c: i for i, c in enumerate(centroids)}
    pnodes = sorted({int(x) for x in all_nodes if x > n_zones})
    pidx = {n: i for i, n in enumerate(pnodes)}
    obk = pd.unique(pd.concat([transit["name"] + "|" + transit["A"].astype(str),
                               transit["name"] + "|" + transit["B"].astype(str)]))
    obidx = {k: i for i, k in enumerate(obk)}
    s0 = len(cidx)
    o0 = s0 + len(pidx) * n_layers
    n_vertices = o0 + len(obidx) * (n_layers - 1)

    def cv(nodes):
        return np.array([cidx[int(n)] for n in nodes])

    def sv(nodes, k):
        return s0 + np.array([pidx[int(n)] for n in nodes]) * n_layers + k

    def ov(names, nodes, j):
        return o0 + np.array([obidx[f"{a}|{int(b)}"] for a, b in zip(names, nodes)]) \
            * (n_layers - 1) + (j - 1)

    frames: list[pd.DataFrame] = []

    def add(a, b, t, f):
        frames.append(pd.DataFrame({"a_node": a, "b_node": b, "trav_time": t, "freq": f}))

    # walk: access -> layer 0; egress/transfer replicated per layer (layer-preserving)
    wa, wb = walk["A"].to_numpy(), walk["B"].to_numpy()
    wt = walk["time"].to_numpy() * params.walk_factor
    is_c_a = wa <= n_zones
    is_c_b = wb <= n_zones
    acc = is_c_a & ~is_c_b
    egr = ~is_c_a & is_c_b
    xfr = ~is_c_a & ~is_c_b
    if acc.any():
        add(cv(wa[acc]), sv(wb[acc], 0), wt[acc], INF_FREQ)
    for k in range(n_layers):
        if egr.any():
            add(sv(wa[egr], k), cv(wb[egr]), wt[egr], INF_FREQ)
        if xfr.any():
            add(sv(wa[xfr], k), sv(wb[xfr], k), wt[xfr], INF_FREQ)

    # ride: onboard chains per layer 1..L-1
    tn = transit["name"].to_numpy()
    ta, tb = transit["A"].to_numpy(), transit["B"].to_numpy()
    tt = transit["time"].to_numpy() * ivf
    for j in range(1, n_layers):
        add(ov(tn, ta, j), ov(tn, tb, j), tt, INF_FREQ)

    # board layer k -> onboard layer k+1 (pens[k]); alight onboard j -> stop layer j
    freq_scale = 2.0 / params.wait_perceive     # SF wait 1/freq == perceived half-headway
    s_name = stops["name"].to_numpy()
    s_node = stops["node"].to_numpy()
    s_hw = stops["hw"].to_numpy()
    board_line_rows: dict[str, list] = {}
    for k in range(n_layers - 1):
        start = sum(len(f) for f in frames)
        add(sv(s_node, k), ov(s_name, s_node, k + 1),
            np.full(len(stops), pens[k]), freq_scale / s_hw)
        for i, ln in enumerate(s_name):
            board_line_rows.setdefault(ln, []).append(start + i)
    for j in range(1, n_layers):
        add(ov(s_name, s_node, j), sv(s_node, j), np.zeros(len(stops)), INF_FREQ)

    edges = pd.concat(frames, ignore_index=True)
    board_rows = {k: np.array(v) for k, v in board_line_rows.items()}
    centroid_vertex = {c: cidx[c] for c in centroids}
    return TransitGraph(edges=edges, n_vertices=n_vertices,
                        centroid_vertex=centroid_vertex, board_rows=board_rows)


def assign_transit(graph: TransitGraph, demand: np.ndarray, *,
                   threads: int | None = None) -> np.ndarray:
    """Run the Spiess-Florian hyperpath assignment; return per-edge volume."""
    o, d = np.nonzero(demand)
    vol = demand[o, d]
    cvert = graph.centroid_vertex
    ov = np.array([cvert.get(int(x + 1), -1) for x in o])
    dv = np.array([cvert.get(int(x + 1), -1) for x in d])
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
    return hp._edges["volume"].values


def boardings_by_line(volume: np.ndarray, graph: TransitGraph) -> pd.Series:
    """Total boardings per line = sum of volume over that line's boarding edges."""
    return pd.Series({ln: float(volume[rows].sum()) for ln, rows in graph.board_rows.items()})
