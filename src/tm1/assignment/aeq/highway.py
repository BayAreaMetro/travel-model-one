"""Multi-class highway equilibrium assignment in AequilibraE with Cube's exact VDF.

AequilibraE's native assignment applies a single global VDF, but Cube uses a
facility-type-segmented VDF (BPR for freeways, Akcelik for arterials). To stay faithful
we drive our own MSA equilibrium: AequilibraE's fast multithreaded all-or-nothing does
the routing each iteration, and :mod:`tm1.assignment.aeq.vdf` supplies the exact
congested times from the combined (PCE-weighted) link volumes.

Each class routes on its own generalized cost ``time + (0.6/VOT)·(dist·opcost + toll)``;
all classes share the congested ``time`` implied by the combined volume-to-capacity ratio.
"""

import logging
from dataclasses import dataclass, field

import numpy as np
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths import Graph, allOrNothing
from aequilibrae.paths.results import AssignmentResults

from tm1.assignment.aeq.network import LinkAttrs
from tm1.assignment.aeq.vdf import congested_time

log = logging.getLogger(__name__)

_LOG_FIRST = 5   # log every iteration up to this, then...
_LOG_EVERY = 10  # ...every Nth


@dataclass
class VehicleClass:
    """One assignment class: demand + generalized-cost parameters."""

    name: str
    demand: np.ndarray            # (n_zones, n_zones) full trip table
    vot: float                    # value of time, $2000/hr
    opcost: str = "autoopc"       # key into LinkAttrs.opcost (2000 cents/mile)
    pce: float = 1.0              # passenger-car equivalent
    toll: np.ndarray | None = None  # per-link toll (2000 cents); None = untolled


@dataclass
class AssignmentResult:
    """Per-class link flows + the converged network state."""

    flows: dict[str, np.ndarray]      # class name -> link flow (link_id order)
    total_pce: np.ndarray             # combined PCE volume per link
    congested_time: np.ndarray        # minutes per link
    vc: np.ndarray                    # volume/capacity per link
    gap: float
    iterations: int
    meta: dict = field(default_factory=dict)


def _graph_order(g: Graph, link_id: np.ndarray) -> np.ndarray:
    """Map link_id order (0..n-1) -> row index in ``g.graph``."""
    lid_to_row = {int(v): i for i, v in enumerate(g.graph["link_id"].to_numpy())}
    return np.array([lid_to_row[int(v)] for v in link_id])


def _matrix(demand: np.ndarray, n_zones: int, name: str) -> AequilibraeMatrix:
    m = AequilibraeMatrix()
    m.create_empty(zones=n_zones, matrix_names=[name], memory_only=True)
    m.index[:] = np.arange(1, n_zones + 1)
    m.matrix[name][:] = demand
    m.computational_view([name])
    return m


def _aon(g: Graph, matrix: AequilibraeMatrix, name: str, link_id: np.ndarray) -> np.ndarray:
    """All-or-nothing link loads for one class, in link_id order."""
    res = AssignmentResults()
    res.prepare(g, matrix)
    allOrNothing(name, matrix, g, res).execute()
    ld = res.get_load_results()
    abcol = next(c for c in ld.columns if c.endswith("_ab"))
    return ld[abcol].reindex(link_id).fillna(0.0).to_numpy()


def equilibrium_assignment(
    g: Graph,
    attrs: LinkAttrs,
    classes: list[VehicleClass],
    n_zones: int,
    *,
    max_iter: int = 100,
    gap_target: float = 1e-4,
) -> AssignmentResult:
    """MSA user-equilibrium with Cube's exact facility-type VDF (see module docstring)."""
    order = _graph_order(g, attrs.link_id)
    gidx = g.graph.index[order]
    mats = {c.name: _matrix(c.demand, n_zones, c.name) for c in classes}

    def gencost(cls: VehicleClass, tc: np.ndarray) -> np.ndarray:
        toll = cls.toll if cls.toll is not None else 0.0
        return tc + (0.6 / cls.vot) * (attrs.distance * attrs.opcost[cls.opcost] + toll)

    flows = {c.name: None for c in classes}
    tc = congested_time(np.zeros_like(attrs.distance), attrs.ft, attrs.t0,
                        attrs.distance, attrs.ffs, attrs.critspd)
    gap = np.nan
    it = 0
    for it in range(1, max_iter + 1):
        num = den = 0.0
        for c in classes:
            gc = gencost(c, tc)
            g.graph.loc[gidx, "cost"] = gc
            g.set_graph("cost")
            g.set_blocked_centroid_flows(True)
            aux = _aon(g, mats[c.name], c.name, attrs.link_id)
            cur = flows[c.name]
            if cur is not None:
                num += float(((cur - aux) * gc).sum())
                den += float((aux * gc).sum())
            flows[c.name] = aux if cur is None else cur + (aux - cur) / it
        gap = num / den if den else np.nan
        total_pce = sum(c.pce * flows[c.name] for c in classes)
        vc = total_pce / attrs.capacity
        tc = congested_time(vc, attrs.ft, attrs.t0, attrs.distance, attrs.ffs, attrs.critspd)
        if it <= _LOG_FIRST or it % _LOG_EVERY == 0:
            log.info("aeq assign it %d: gap %.3e  VMT %.0f  maxV/C %.2f",
                     it, gap, float((total_pce * attrs.distance).sum()), vc.max())
        if np.isfinite(gap) and abs(gap) < gap_target:
            break

    return AssignmentResult(
        flows=dict(flows),
        total_pce=total_pce, congested_time=tc, vc=vc, gap=float(gap), iterations=it,
    )
