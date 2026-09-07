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
from tm1.assignment.params import Vdf
from tm1.assignment.aeq.vdf import congested_time

log = logging.getLogger(__name__)

_LOG_FIRST = 5   # log every iteration up to this, then...
_LOG_EVERY = 10  # ...every Nth
_EXCLUDED_COST = 1.0e9  # generalized cost for links a class may not use


@dataclass
class VehicleClass:
    """One assignment class: demand + generalized-cost parameters."""

    name: str
    demand: np.ndarray            # (n_zones, n_zones) full trip table
    vot: float                    # value of time, $2000/hr
    opcost: str = "autoopc"       # key into LinkAttrs.opcost (2000 cents/mile)
    pce: float = 1.0              # passenger-car equivalent
    toll: np.ndarray | None = None  # per-link toll (2000 cents); None = untolled
    exclude: np.ndarray | None = None  # per-link bool mask (link_id order); True = forbidden


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


def _aon(g: Graph, matrix: AequilibraeMatrix, name: str, link_id: np.ndarray,
         cores: int | None = None) -> np.ndarray:
    """All-or-nothing link loads for one class, in link_id order."""
    res = AssignmentResults()
    if cores:
        res.set_cores(cores)  # before prepare(): avoids the post-alloc __redim bug
    res.prepare(g, matrix)
    allOrNothing(name, matrix, g, res).execute()
    ld = res.get_load_results()
    abcol = next(c for c in ld.columns if c.endswith("_ab"))
    return ld[abcol].reindex(link_id).fillna(0.0).to_numpy()


def _fw_step(
    total_pce: np.ndarray,
    aux_pce: np.ndarray,
    attrs: LinkAttrs,
    vdf: Vdf,
) -> float:
    """Exact Frank-Wolfe line search: the Beckmann-minimising step in [0, 1].

    Minimises the network's Beckmann objective along the descent direction
    ``d = aux_pce - total_pce`` by finding the root of
    ``sigma(l) = sum_a time_a(V + l*d) * d_a`` (the objective's derivative in
    ``l``).  ``time_a`` is Cube's congested-time VDF of the combined PCE flow, so
    the step is chosen against the *same* congestion function Cube's Frank-Wolfe
    uses; class-specific tolls/opcosts enter through the shortest paths (``aux``).
    ``sigma`` is monotone increasing in ``l`` (time rises with flow), so a plain
    bisection converges.
    """
    d = aux_pce - total_pce

    def sigma(lam: float) -> float:
        vc = (total_pce + lam * d) / attrs.capacity
        t = congested_time(vc, attrs.ft, attrs.t0, attrs.distance, attrs.ffs,
                           attrs.critspd, vdf)
        return float((t * d).sum())

    if sigma(0.0) >= 0.0:      # direction is not descending -> no move
        return 0.0
    if sigma(1.0) <= 0.0:      # full step still descending -> take it
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(40):        # ~1e-12 precision on lambda
        mid = 0.5 * (lo + hi)
        if sigma(mid) > 0.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def equilibrium_assignment(
    g: Graph,
    attrs: LinkAttrs,
    classes: list[VehicleClass],
    n_zones: int,
    vdf: Vdf,
    *,
    max_iter: int = 100,
    gap_target: float = 1e-4,
    algorithm: str = "fw",
    cores: int | None = None,
) -> AssignmentResult:
    """User-equilibrium assignment with Cube's exact facility-type VDF.

    ``algorithm``: ``"fw"`` (Frank-Wolfe with an exact Beckmann line search, the
    default -- matches Cube's ``combine = equi``) or ``"msa"`` (method of
    successive averages, ``1/it`` steps).  Frank-Wolfe converges to a tighter
    equilibrium in far fewer iterations.
    """
    order = _graph_order(g, attrs.link_id)
    gidx = g.graph.index[order]
    mats = {c.name: _matrix(c.demand, n_zones, c.name) for c in classes}

    def gencost(cls: VehicleClass, tc: np.ndarray) -> np.ndarray:
        toll = cls.toll if cls.toll is not None else 0.0
        return tc + (0.6 / cls.vot) * (attrs.distance * attrs.opcost[cls.opcost] + toll)

    flows = {c.name: None for c in classes}
    total_pce = np.zeros_like(attrs.distance)
    tc = congested_time(np.zeros_like(attrs.distance), attrs.ft, attrs.t0,
                        attrs.distance, attrs.ffs, attrs.critspd, vdf)
    vc = np.zeros_like(attrs.distance)
    gap = np.nan
    it = 0
    for it in range(1, max_iter + 1):
        # all-or-nothing for every class at the current congested cost
        num = den = 0.0
        aux = {}
        for c in classes:
            gc = gencost(c, tc)
            if c.exclude is not None:
                # forbid excluded links (HOV/value-toll/no-truck) by pricing them
                # out of every path -- replicates Cube's pathload ``excludegrp``
                gc = np.where(c.exclude, _EXCLUDED_COST, gc)
            g.graph.loc[gidx, "cost"] = gc
            g.set_graph("cost")
            g.set_blocked_centroid_flows(True)
            aux[c.name] = _aon(g, mats[c.name], c.name, attrs.link_id, cores=cores)
            cur = flows[c.name]
            if cur is not None:
                num += float(((cur - aux[c.name]) * gc).sum())
                den += float((aux[c.name] * gc).sum())
        gap = num / den if den else np.nan

        # step: FW line search on the combined-PCE flow, or MSA 1/it
        if flows[classes[0].name] is None:
            step = 1.0
        elif algorithm == "msa":
            step = 1.0 / it
        else:
            aux_pce = sum(c.pce * aux[c.name] for c in classes)
            step = _fw_step(total_pce, aux_pce, attrs, vdf)

        for c in classes:
            cur = flows[c.name]
            flows[c.name] = aux[c.name] if cur is None else cur + step * (aux[c.name] - cur)

        total_pce = sum(c.pce * flows[c.name] for c in classes)
        vc = total_pce / attrs.capacity
        tc = congested_time(vc, attrs.ft, attrs.t0, attrs.distance, attrs.ffs,
                            attrs.critspd, vdf)
        if it <= _LOG_FIRST or it % _LOG_EVERY == 0:
            log.info("aeq assign it %d: gap %.3e  step %.4f  VMT %.0f  maxV/C %.2f",
                     it, gap, step, float((total_pce * attrs.distance).sum()), vc.max())
        if np.isfinite(gap) and abs(gap) < gap_target:
            break

    return AssignmentResult(
        flows=dict(flows),
        total_pce=total_pce, congested_time=tc, vc=vc, gap=float(gap), iterations=it,
    )
