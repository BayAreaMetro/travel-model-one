"""Transit fare model for the Cube-free skim path.

Cube's ``fare = xfare + modefare + faremat`` decomposes into:

* **xfare** -- ``XFARE[from_mode][to_mode]`` (``xfare.far``, 1-indexed 139x139): the
  boarding fare when ``from`` is a walk mode (1-9) and the transfer fare when ``from``
  is a transit mode.  This is where per-mode boarding fares live (there is no separate
  ``modefare`` table; ``XFARE[1][mode]`` is the walk-access boarding fare).
* **farelinks** -- per-``(mode, a, b)`` surcharges (``farelinks.far``), e.g. transbay
  or express add-ons.
* **faremat** -- station-to-station OD fares for rail (``BART.far``, ``Caltrain.far``).
  These are a *minimum + sublinear-distance* structure, NOT additive along links, so
  per-link embedding fails (+300% error).  BART/Caltrain fares are, however, a decent
  linear function of inter-station network distance (BART r~0.72, Caltrain r~0.95 at
  the station level; ~0.85-0.89 at OD level on pure-rail trips), so we model them as a
  per-band linear **distance curve** ``fare = a + b * key_mode_distance`` fitted from
  the fare matrix, applied to the accumulable key-mode in-vehicle distance skim.

Bus/light-rail fares (loc/exp/lrf) are boarding ``XFARE`` + ``farelinks`` (accumulated
on the graph); heavy/commuter rail (hvy/com) add the distance curve.  Everything is
derived from the ``.far`` inputs + link distances -- no Cube.
"""

import itertools
import re
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

# rail fare modelled by a per-line-haul distance curve fitted from the OD fare files of
# ALL systems in that line-haul's fare band: linehaul -> ([.far files], fare mode band).
# The fare band is the DISTANCE-fare modes only: for lrf that is ferry (100-109), NOT the
# light-rail 110-119 (flat, priced by boarding XFARE); com blends the four commuter rails.
RAIL_FARE = {
    "hvy": (["BART.far"], (120, 129)),
    "lrf": (["Ferry.far"], (100, 109)),
    "com": (["Caltrain.far", "Amtrak.far", "ACE.far", "SMART.far"], (130, 139)),
}

_XFARE_RE = re.compile(r"\s*XFARE\[(\d+)\]\s*=\s*(.+)", re.IGNORECASE)
_FARELINK_RE = re.compile(
    r"\s*FARELINKS\s+FARE\s*=\s*(-?\d+)\s*,\s*L\s*=\s*(\d+)\s*-\s*(\d+)"
    r"\s+MODES\s*=\s*(\d+)\s+ONEWAY\s*=\s*(\w)", re.IGNORECASE)
_FAR_ROW_RE = re.compile(r"\s*(\d+)\s+(\d+)\s+(-?\d+)")


def parse_xfare(path: str | Path) -> np.ndarray:
    """Parse ``xfare.far`` into a 140x140 array indexed ``[from_mode][to_mode]`` (cents).

    Modes are 1-indexed (1-139); row/col 0 are unused padding so callers index by the
    raw mode number.
    """
    xf = np.zeros((140, 140), dtype=float)
    for ln in Path(path).read_text(encoding="latin-1").splitlines():
        m = _XFARE_RE.match(ln)
        if not m:
            continue
        frm = int(m.group(1))
        vals = [int(x) for x in m.group(2).split(",") if x.strip().lstrip("-").isdigit()]
        xf[frm, 1:1 + len(vals)] = vals
    return xf


def parse_farelinks(path: str | Path) -> dict:
    """Parse ``farelinks.far`` into ``{(mode, a, b): cents}``, both ways if ``ONEWAY=N``."""
    out: dict = {}
    for ln in Path(path).read_text(encoding="latin-1").splitlines():
        m = _FARELINK_RE.match(ln)
        if not m:
            continue
        fare, a, b, mode, oneway = m.groups()
        fare, a, b, mode = int(fare), int(a), int(b), int(mode)
        out[(mode, a, b)] = fare
        if oneway.upper() == "N":
            out[(mode, b, a)] = fare
    return out


def _parse_far_matrix(path: str | Path) -> dict:
    """Parse a station-to-station ``.far`` file into ``{(board, alight): fare_cents}``."""
    out: dict = {}
    for ln in Path(path).read_text(encoding="latin-1").splitlines():
        m = _FAR_ROW_RE.match(ln)
        if m:
            out[(int(m.group(1)), int(m.group(2)))] = int(m.group(3))
    return out


def fit_rail_curve(far_paths, lines: pd.DataFrame, link_dist: dict,
                   mode_band: tuple) -> tuple[float, float]:
    """Fit ``fare = a + b * network_distance`` from one or more rail fare matrices.

    Station adjacency comes from the band's rail line node sequences (``lines`` =
    parse_lin output); the per-station-pair network distance is the shortest path over
    the consecutive-station links.  When several systems share a band (e.g. commuter
    rail = Caltrain + Amtrak + ACE + SMART) their fare files are pooled into one blended
    curve.  Returns ``(a, b)`` in cents / cents-per-mile.
    """
    if isinstance(far_paths, (str, Path)):
        far_paths = [far_paths]
    lo, hi = mode_band
    rail = lines[(lines["mode"] >= lo) & (lines["mode"] <= hi)]
    g = nx.Graph()
    for nodes in rail["nodes"]:
        seq = [abs(int(n)) for n in nodes]
        for a, b in itertools.pairwise(seq):
            d = link_dist.get((a, b), link_dist.get((b, a)))
            if d:
                g.add_edge(a, b, d=d)
    dist, fare = [], []
    for far_path in far_paths:
        for (a, b), f in _parse_far_matrix(far_path).items():
            if a in g and b in g and nx.has_path(g, a, b):
                dist.append(nx.shortest_path_length(g, a, b, weight="d"))
                fare.append(f)
    if len(dist) < 5:
        return 0.0, 0.0
    b_coef, a_coef = np.polyfit(np.array(dist), np.array(fare), 1)
    return float(a_coef), float(b_coef)


@dataclass
class TransitFares:
    """Loaded fare inputs + fitted rail distance curves."""

    xfare: np.ndarray                       # [from_mode][to_mode] cents
    farelinks: dict                         # (mode, a, b) -> cents
    rail_curve: dict = field(default_factory=dict)   # linehaul -> (a, b) cents, c/mi
    rail_band: dict = field(default_factory=dict)    # linehaul -> (lo, hi) fare modes
    faremat: dict = field(default_factory=dict)      # linehaul -> {(from_node,to_node): cents}
    # per line-haul, the exact station-to-station OD fare (Cube FAREMATI .far files).  Fare
    # station ids ARE the network rail stop node ids, so board/alight nodes look up directly.

    def boarding_fare(self, access_mode: int, line_mode: int) -> float:
        """Walk/transfer boarding fare into ``line_mode`` from ``access_mode``."""
        return float(self.xfare[access_mode, line_mode])

    def station_fare(self, linehaul: str | None, board_node: int, alight_node: int) -> float:
        """Exact FAREMAT OD fare (cents) for a rail board->alight station pair; 0 if absent.

        Falls back to the distance curve only when the exact pair is missing from the .far
        (rare -- e.g. a station pair with no coded fare).
        """
        fm = self.faremat.get(linehaul or "")
        if fm is not None:
            f = fm.get((int(board_node), int(alight_node)))
            if f is not None:
                return f
        return 0.0

    def rail_fare(self, linehaul: str | None, key_distance: np.ndarray) -> np.ndarray:
        """Distance-curve OD fare (cents) for a rail run's key-mode distance array."""
        if linehaul not in self.rail_curve:
            return np.zeros_like(key_distance)
        a, b = self.rail_curve[linehaul]
        return np.where(key_distance > 0, a + b * key_distance, 0.0)


def load_fares(fares_dir: str | Path, link_dist: dict,
               lines: pd.DataFrame | None = None) -> TransitFares:
    """Load ``xfare.far`` + ``farelinks.far`` and fit rail distance curves.

    ``link_dist`` is ``{(a, b): miles}`` (from the converted ``link_distance.parquet``);
    ``lines`` is :func:`parse_lin` output (needed for the rail station adjacency).  If
    ``lines`` is None the rail curves are skipped (bus-only fares).
    """
    fares_dir = Path(fares_dir)
    xfare = parse_xfare(fares_dir / "xfare.far")
    farelinks = parse_farelinks(fares_dir / "farelinks.far")
    curves: dict = {}
    bands: dict = {}
    faremat: dict = {}
    if lines is not None:
        for lh, (far_names, band) in RAIL_FARE.items():
            paths = [fares_dir / n for n in far_names if (fares_dir / n).exists()]
            if paths:
                curves[lh] = fit_rail_curve(paths, lines, link_dist, band)
                bands[lh] = band
                # exact station-to-station fare (pooled across the band's operators); node
                # ids match the network rail stop nodes, so this is a direct board->alight lookup.
                fm: dict = {}
                for p in paths:
                    for (a, b), f in _parse_far_matrix(p).items():
                        fm[(int(a), int(b))] = f
                        fm.setdefault((int(b), int(a)), f)   # .far lists ONE direction; fares
                        # are symmetric (B->A == A->B), so add the reverse if not already given
                faremat[lh] = fm
    return TransitFares(xfare=xfare, farelinks=farelinks, rail_curve=curves,
                        rail_band=bands, faremat=faremat)
