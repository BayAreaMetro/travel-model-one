"""Highway level-of-service skims from a converged AequilibraE assignment.

For each skim class Cube produces (drive-alone, shared-2, shared-3, and their toll
variants), we skim four link attributes along that class's minimum-generalized-cost
path: congested time, distance, bridge toll and value toll.  The path a class takes
is exactly the one it was assigned on, so the skim reuses the same generalized cost
(and the same HOV / value-toll link exclusions) built for assignment.

Output keys match the ActivitySim skim OMX (see :mod:`tm1.steps.convert_skims`):
``{SOV,HOV2,HOV3}[TOLL]_{TIME,DIST,BTOLL,VTOLL}`` (VTOLL only for toll classes).
"""

import logging

import numpy as np
import pandas as pd
from aequilibrae.paths import Graph
from aequilibrae.paths.network_skimming import NetworkSkimming

from tm1.assignment.aeq.highway import _EXCLUDED_COST, VehicleClass, _graph_order
from tm1.assignment.aeq.params import Highway

log = logging.getLogger(__name__)

def highway_skims(
    g: Graph,
    attrs,
    classes: list[VehicleClass],
    congested_time: np.ndarray,
    links: pd.DataFrame,
    period: str,
    n_zones: int,
    hw: Highway,
    cores: int | None = None,
) -> dict[str, np.ndarray]:
    """Skim TIME/DIST/BTOLL/VTOLL for each highway class off the converged network.

    Parameters
    ----------
    g, attrs
        The graph and link attributes from :func:`build_cube_graph`.
    classes
        The assigned :class:`VehicleClass` list (for per-class cost + exclusions).
    congested_time
        Final congested link time (minutes), ``link_id`` order.
    links
        Cube link export (needs ``tollclass`` to split bridge vs value toll).
    period
        Two-letter period (used only for logging).
    n_zones
        Centroid count; output matrices are ``(n_zones, n_zones)``.
    hw
        :class:`tm1.assignment.aeq.params.Highway` (skim classes + tollclass split).
    """
    by_name = {c.name: c for c in classes}
    order = _graph_order(g, attrs.link_id)
    gidx = g.graph.index[order]
    tollclass = links["tollclass"].to_numpy(float)
    is_value = tollclass >= hw.first_value_tollclass

    def gencost(cls: VehicleClass) -> np.ndarray:
        toll = cls.toll if cls.toll is not None else 0.0
        gc = congested_time + (0.6 / cls.vot) * (attrs.distance * attrs.opcost[cls.opcost] + toll)
        if cls.exclude is not None:
            gc = np.where(cls.exclude, _EXCLUDED_COST, gc)
        return gc

    skims: dict[str, np.ndarray] = {}
    for cls_name, prefix, is_toll in hw.skim_classes:
        cls = by_name[cls_name]
        cls_toll = cls.toll if cls.toll is not None else np.zeros_like(attrs.distance)
        btoll = np.where(is_value, 0.0, cls_toll)
        vtoll = np.where(is_value, cls_toll, 0.0)

        # place cost + skim accumulators on the (compacted) graph
        g.graph.loc[gidx, "cost"] = gencost(cls)
        g.graph.loc[gidx, "s_time"] = congested_time
        g.graph.loc[gidx, "s_dist"] = attrs.distance
        g.graph.loc[gidx, "s_btoll"] = btoll
        g.graph.loc[gidx, "s_vtoll"] = vtoll
        g.set_graph("cost")
        g.set_skimming(["s_time", "s_dist", "s_btoll", "s_vtoll"])
        g.set_blocked_centroid_flows(True)

        skm = NetworkSkimming(g)
        if cores:
            skm.set_cores(cores)
        skm.execute()
        res = skm.results.skims

        def _mat(field: str, res=res) -> np.ndarray:  # bind: called within this iteration
            m = np.asarray(res.get_matrix(field), dtype=np.float64)[:n_zones, :n_zones]
            return np.nan_to_num(m, nan=0.0, posinf=0.0, neginf=0.0)

        skims[f"{prefix}_TIME"] = _mat("s_time")
        skims[f"{prefix}_DIST"] = _mat("s_dist")
        skims[f"{prefix}_BTOLL"] = _mat("s_btoll")
        if is_toll:
            skims[f"{prefix}_VTOLL"] = _mat("s_vtoll")

        log.info("skim %s %s: mean TIME %.2f min, mean DIST %.2f mi",
                 period, prefix, float(skims[f"{prefix}_TIME"].mean()),
                 float(skims[f"{prefix}_DIST"].mean()))

    return skims
