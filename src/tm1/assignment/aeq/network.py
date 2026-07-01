"""Import a Cube Travel Model One highway network into an AequilibraE graph.

The link attributes come from Cube's ``net2csv_avgload5period.job`` export (one row per
directional link with ``a, b, distance, lanes, ft, at, ffs, fft, cap`` and the per-class
operating-cost fields ``autoopc/smtropc/lrtropc``).  Cube link records are already
directional, so every link is one-way (``direction = 1``) in the graph.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from aequilibrae.paths import Graph

from tm1.assignment.aeq.vdf import CRITSPD


@dataclass
class LinkAttrs:
    """Per-link arrays (in ``link_id`` order) needed by the VDF + generalized cost."""

    link_id: np.ndarray
    ft: np.ndarray            # facility type
    distance: np.ndarray      # miles
    ffs: np.ndarray           # free-flow speed (mph)
    t0: np.ndarray            # free-flow time (minutes)
    critspd: np.ndarray       # critical speed by capacity class (mph)
    capacity: np.ndarray      # period link capacity (veh), = cap/lane * lanes * capfac
    opcost: dict[str, np.ndarray]  # operating cost (2000 cents/mi) by field name


def _clean_t0(fft: np.ndarray, ffs: np.ndarray, distance: np.ndarray) -> np.ndarray:
    """Free-flow time, floored positive (Cube uses OT for fixed links, dropped in export)."""
    fallback = np.where(ffs > 0, distance / np.maximum(ffs, 1.0) * 60.0, 0.05)
    return np.where(fft > 0, fft, fallback).clip(min=0.01)


def build_cube_graph(
    links: pd.DataFrame,
    n_zones: int,
    *,
    capfac: float,
    opcost_fields: tuple[str, ...] = ("autoopc", "smtropc", "lrtropc"),
) -> tuple[Graph, LinkAttrs]:
    """Build an AequilibraE graph + link attributes from a Cube link export.

    Parameters
    ----------
    links
        One row per directional link (Cube ``net2csv`` columns).
    n_zones
        Centroid count (zones ``1..n_zones``).
    capfac
        Capacity factor = hours represented in the period (EA 3, AM 4, MD 5, PM 4, EV 8).
    """
    n = len(links)
    ft = links["ft"].to_numpy()
    at = links["at"].to_numpy()
    distance = links["distance"].astype(float).to_numpy()
    ffs = links["ffs"].astype(float).clip(lower=1.0).to_numpy()
    t0 = _clean_t0(links["fft"].astype(float).to_numpy(), ffs, distance)
    capclass = np.minimum(at * 10 + ft, 62).astype(int)
    critspd = np.array([CRITSPD.get(int(c), 47.087) for c in capclass], dtype=float)
    lanes = links["lanes"].astype(float).clip(lower=0).to_numpy()
    cap_per_lane = links["cap"].astype(float).to_numpy()
    capacity = cap_per_lane * lanes * capfac
    capacity = np.where(capacity <= 0, 1e6, capacity)  # zero-lane/connector: uncapacitated
    opcost = {f: links[f].astype(float).to_numpy() for f in opcost_fields if f in links}

    link_id = np.arange(1, n + 1, dtype=np.int64)
    net = pd.DataFrame({
        "link_id": link_id,
        "a_node": links["a"].astype(np.int64).to_numpy(),
        "b_node": links["b"].astype(np.int64).to_numpy(),
        "direction": 1,
        "id": link_id,
        "cost": t0,  # placeholder; the assignment overwrites this each iteration
    })
    g = Graph()
    g.network = net
    g.prepare_graph(np.arange(1, n_zones + 1, dtype=np.int64))
    g.set_graph("cost")
    g.set_blocked_centroid_flows(True)

    attrs = LinkAttrs(link_id, ft, distance, ffs, t0, critspd, capacity, opcost)
    return g, attrs
