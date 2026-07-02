"""Build per-run transit assignment networks from source inputs — no Cube required.

Replaces the dependency on Cube-built ``trnlink{run}.csv`` working files with:

* **transitLines.lin** (master TRNBUILD line file, ASCII): line name, per-period
  headways ``FREQ[1..5]``, MODE, ONEWAY, optional RUNTIME, and the stop/node sequence
  (negative node = served but not a stop).
* **support links** (one-time converted parquet, see ``scripts/build_aeq_inputs.py``):
  the walk/drive access, egress, transfer and station-funnel links (modes 1-9) per
  run type.  These are static network geometry/policy, not per-iteration outputs.
* **link distances** (one-time converted parquet): directional link distances for
  distributing rail RUNTIME and reporting.
* **highway congested times** for the period being built -- bus (mode < 100) in-vehicle
  times follow the congested street network (Cube's ``useruntime = n``).

Times: buses take the congested highway time of each (a, b) street link; rail/ferry
lines distribute their ``RUNTIME`` over links proportional to distance (falling back
to the converted reference link times where RUNTIME is absent).
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

_LINE_RE = re.compile(r"LINE\s+(NAME=.*?)(?=LINE\s+NAME=|\Z)", re.S | re.I)
_ATTR_RE = re.compile(r"(\w+(?:\[\d\])?)\s*=\s*(\"[^\"]*\"|[^,\s]+)")

# bus in-vehicle delay (min/mile) by area type, applied off-freeway (PrepHwyNet.job);
# freeways/expressways (FT 1, 2, 3, 8) get no bus delay.
_BUS_DELAY_BY_AT = {0: 2.46, 1: 2.46, 2: 1.74, 3: 1.74, 4: 1.14, 5: 0.08}
_MIN_SPEED, _MIN_SPEED_FWY = 3.0, 6.0     # congested-speed floors (mph)


def bus_time_table(links: pd.DataFrame, period: str) -> dict:
    """Port of PrepHwyNet.job's BUS_TIME: ``(a, b) -> bus in-vehicle minutes``.

    ``links`` is the highway link export (needs ``a, b, distance, ft, at, brt,
    fft, ctim{P}``).  Congested time gets Cube's slow-speed floors, then buses
    pay an area-type delay per mile (except freeways and BRT variants).
    """
    per = period.upper()
    dist = links["distance"].to_numpy(float)
    ft = links["ft"].to_numpy(int)
    at = links["at"].to_numpy(int)
    brt = links["brt"].to_numpy(int) if "brt" in links else np.zeros(len(links), int)
    fft = links["fft"].to_numpy(float)
    ctim = links[f"ctim{per}"].to_numpy(float).copy()

    # slow-speed floors (avoid TRNBUILD-hostile crawl speeds)
    with np.errstate(divide="ignore", invalid="ignore"):
        cspd = np.where(ctim > 0, dist / (ctim / 60.0), np.inf)
    fwy = (ft <= 4) | (ft == 8)
    ctim = np.where(fwy & (cspd < _MIN_SPEED_FWY), dist / (_MIN_SPEED_FWY / 60.0), ctim)
    ctim = np.where(~fwy & (cspd < _MIN_SPEED), dist / (_MIN_SPEED / 60.0), ctim)

    delay = np.where(np.isin(ft, (1, 2, 3, 8)), 0.0,
                     np.vectorize(lambda x: _BUS_DELAY_BY_AT.get(int(x), 0.0))(at))
    bus = np.select(
        [brt == 1, brt == 2, brt == 3],
        [fft + delay * dist * 0.5,
         ctim + delay * dist * 0.5,
         np.minimum(ctim, dist / (35.0 / 60.0))],
        default=ctim + delay * dist,
    )
    a = links["a"].to_numpy(int)
    b = links["b"].to_numpy(int)
    return {(int(x), int(y)): float(t) for x, y, t in zip(a, b, bus)}


def parse_lin(path: str | Path) -> pd.DataFrame:
    """Parse a TRNBUILD .lin file into one row per line.

    Returns columns: ``name, mode, owner, oneway, runtime, freq1..freq5, nodes``
    where ``nodes`` is the signed node list (negative = pass, positive = stop).
    """
    text = Path(path).read_text(encoding="latin-1")
    text = re.sub(r";[^\n]*", "", text)          # strip comments
    rows = []
    for m in _LINE_RE.finditer(text):
        body = m.group(1)
        # attributes may appear before OR interleaved within the node list
        nsplit = re.search(r"\bN\s*=", body)
        attrs = {k.upper(): v.strip('"') for k, v in _ATTR_RE.findall(body)
                 if k.upper() != "N"}
        nodes = []
        if nsplit:
            node_txt = body[nsplit.end():]
            # attributes (RUNTIME=, ACCESS=, N=...) may be interleaved within the
            # node list; strip every attr=value pair so their values are not read
            # as node numbers (a further N= continues the node list).
            node_txt = re.sub(r"\b(?!N\b)\w+(?:\[\d\])?\s*=\s*(\"[^\"]*\"|[^,\s]+)",
                              "", node_txt)
            node_txt = re.sub(r"\bN\s*=", "", node_txt)
            for tok in re.findall(r"-?\d+", node_txt):
                nodes.append(int(tok))
        freqs = [float(attrs.get(f"FREQ[{i}]", 0) or 0) for i in range(1, 6)]
        rows.append({
            # TRNBUILD/Wrangler uppercase line names in built networks
            "name": attrs.get("NAME", "").upper(),
            "mode": int(float(attrs.get("MODE", 0))),
            "owner": attrs.get("OWNER", ""),
            "oneway": str(attrs.get("ONEWAY", "T")).upper() in ("T", "Y", "TRUE"),
            "runtime": float(attrs["RUNTIME"]) if "RUNTIME" in attrs else np.nan,
            "freq1": freqs[0], "freq2": freqs[1], "freq3": freqs[2],
            "freq4": freqs[3], "freq5": freqs[4],
            "nodes": nodes,
        })
    return pd.DataFrame(rows)


PERIOD_FREQ = {"EA": "freq1", "AM": "freq2", "MD": "freq3", "PM": "freq4", "EV": "freq5"}


def build_ride_links(
    lines: pd.DataFrame,
    period: str,
    street_time: dict,
    link_dist: dict,
    ref_time: dict | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Build directional transit ride links for one period.

    Parameters
    ----------
    lines
        Output of :func:`parse_lin`.
    street_time
        ``(a, b) -> congested minutes`` for street links (bus in-vehicle times).
    link_dist
        ``(a, b) -> miles`` (for distributing rail RUNTIME).
    ref_time
        Optional ``(a, b, line-mode-bucket) -> minutes`` fallback for rail links
        of lines without RUNTIME (from the one-time converted reference).

    Returns
    -------
    (links, headways): links has ``A, B, time, mode, stopA, stopB, name``;
    headways maps line name -> headway for lines running this period.
    """
    fcol = PERIOD_FREQ[period.upper()]
    out = []
    headways: dict[str, float] = {}
    for ln in lines.itertuples(index=False):
        hw = getattr(ln, fcol)
        if not hw or hw <= 0 or len(ln.nodes) < 2:
            continue
        # two-way lines are split into two directional lines; the reverse direction
        # carries the Wrangler/TRNBUILD naming convention of a trailing '-'. Node
        # SIGNS (negative = served-not-a-stop) belong to the node, not the
        # direction, so the reversed sequence keeps each node's sign.
        seqs = [(ln.name, ln.nodes)] if ln.oneway else [
            (ln.name, ln.nodes), (f"{ln.name}-", ln.nodes[::-1])]
        for dname, nodes in seqs:
            headways[dname] = hw
            a = np.abs(np.array(nodes[:-1])); b = np.abs(np.array(nodes[1:]))
            stop_a = (np.array(nodes[:-1]) > 0).astype(int)
            stop_b = (np.array(nodes[1:]) > 0).astype(int)
            dist = np.array([link_dist.get((x, y), np.nan) for x, y in zip(a, b)])
            if ln.mode < 100:                       # street-running: congested times
                t = np.array([street_time.get((x, y), np.nan) for x, y in zip(a, b)])
            elif np.isfinite(ln.runtime):           # rail/ferry with line RUNTIME
                w = np.where(np.isfinite(dist), dist, np.nanmean(dist) if np.isfinite(dist).any() else 1.0)
                t = ln.runtime * w / w.sum()
            else:
                t = np.array([(ref_time or {}).get((x, y), np.nan) for x, y in zip(a, b)])
            out.append(pd.DataFrame({
                "A": a, "B": b, "time": t, "mode": ln.mode,
                "stopA": stop_a, "stopB": stop_b, "distance": dist, "name": dname,
            }))
    links = pd.concat(out, ignore_index=True)
    # time fallbacks: links absent from the highway export (express-only ramps,
    # transit-only rights-of-way) take the converted reference ride time, then a
    # 20 mph distance-based estimate. NaN times must never reach the solver.
    miss = links["time"].isna()
    if miss.any() and ref_time:
        links.loc[miss, "time"] = [ref_time.get((a, b), np.nan)
                                   for a, b in zip(links.loc[miss, "A"], links.loc[miss, "B"])]
        miss = links["time"].isna()
    if miss.any():
        links.loc[miss, "time"] = links.loc[miss, "distance"].fillna(0.25) / (20.0 / 60.0)
    return links, headways


def assemble_run_network(
    ride_links: pd.DataFrame,
    support_links: pd.DataFrame,
) -> pd.DataFrame:
    """Concatenate ride + support links into the table build_transit_graph expects."""
    sup = support_links.rename(columns=str.strip)
    cols = ["A", "B", "time", "mode", "stopA", "stopB", "distance", "name"]
    sup = sup.assign(stopA=0, stopB=0, name=None)[[c for c in cols if c in sup.columns or c in ("stopA", "stopB", "name")]]
    for c in cols:
        if c not in sup.columns:
            sup[c] = np.nan
    return pd.concat([ride_links[cols], sup[cols]], ignore_index=True)
