"""Assemble the 13 highway vehicle-trip tables for one period.

This is the AequilibraE-native equivalent of the demand side of ``HwyAssign.job``'s
``pathload vol[]`` expressions (which the faithful Cube loop leaves to the Cube job).
Personal-travel tables come from this iteration's ActivitySim ``trips_{period}.omx``;
the non-residential tables (internal-external, truck, air-passenger, high-speed-rail)
are frozen from a reference ``nonres/`` directory.

Person-trip -> vehicle-trip conversion (shared-ride occupancy) and the
non-residential merge happen here, matching Cube's ``vol[]`` definitions:

    da      = DA + ix.DA + air.DA
    sr2     = SHARED2FREE / 2    + ix.SR2 + air.SR2
    sr3     = SHARED3FREE / 3.25 + ix.SR3 + air.SR3
    sml     = trk.(VSTRUCK + STRUCK + MTRUCK)
    lrg     = trk.CTRUCK
    ...toll variants analogously (sr2toll also picks up hsr.taxi_veh)
    daav/s2av/s3av = 0   (this ActivitySim config folds TNC/AV into DA/SR)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import openmatrix as omx

from cubeio import read_tpp
from tm1.assignment.aeq.classes import CLASS_ORDER

# ActivitySim OMX personal-trip table base name -> internal key used below
_ASIM_MAIN = {
    "DRIVEALONEFREE": "da",
    "DRIVEALONEPAY": "datoll",
    "SHARED2FREE": "sr2",
    "SHARED2PAY": "sr2toll",
    "SHARED3FREE": "sr3",
    "SHARED3PAY": "sr3toll",
}

SR2_OCC = 2.0      # shared-ride-2 person->vehicle divisor
SR3_OCC = 3.25     # shared-ride-3+ person->vehicle divisor (avg occupancy)


def _pad(m: np.ndarray, n_zones: int) -> np.ndarray:
    """Place a (possibly internal-only) matrix into the full ``n_zones`` system."""
    if m.shape[0] == n_zones:
        return m
    full = np.zeros((n_zones, n_zones), dtype=np.float64)
    full[: m.shape[0], : m.shape[1]] = m
    return full


def _read_main(asim_output_dir: Path, period: str, n_zones: int) -> dict[str, np.ndarray]:
    """Read personal DA/SR tables from ActivitySim ``trips_{period}.omx``."""
    omx_path = asim_output_dir / f"trips_{period.lower()}.omx"
    if not omx_path.exists():
        msg = f"ActivitySim trip matrix not found: {omx_path}"
        raise FileNotFoundError(msg)
    out: dict[str, np.ndarray] = {}
    with omx.open_file(str(omx_path), "r") as f:
        avail = set(f.list_matrices())
        zones = f.shape()[0]
        for asim_name, key in _ASIM_MAIN.items():
            tbl = f"{asim_name}_{period.upper()}"
            if tbl in avail:
                out[key] = _pad(np.asarray(f[tbl], dtype=np.float64), n_zones)
            else:
                out[key] = np.zeros((n_zones, n_zones), dtype=np.float64)
    _ = zones
    return out


def _read_nonres(nonres_dir: Path, period: str, n_zones: int) -> dict[str, dict]:
    """Read frozen non-residential demand TPPs for the period."""
    per = period.upper()
    files = {
        "ix": nonres_dir / f"tripsIX{per}.tpp",
        "trk": nonres_dir / f"tripstrk{per}.tpp",
        "air": nonres_dir / f"tripsAirPax{per}.tpp",
        "hsr": nonres_dir / f"tripsHsr{per}.tpp",
    }
    data: dict[str, dict] = {}
    for key, path in files.items():
        if path.exists():
            tables = read_tpp(str(path))["data"]
            data[key] = {name: _pad(m, n_zones) for name, m in tables.items()}
        else:
            data[key] = {}
    return data


def assemble_demand(
    asim_output_dir: str | Path,
    nonres_dir: str | Path,
    period: str,
    n_zones: int,
) -> dict[str, np.ndarray]:
    """Assemble the 13 vehicle-trip tables (keys :data:`CLASS_ORDER`) for a period."""
    asim_output_dir = Path(asim_output_dir)
    nonres_dir = Path(nonres_dir)
    m = _read_main(asim_output_dir, period, n_zones)
    nr = _read_nonres(nonres_dir, period, n_zones)
    z = np.zeros((n_zones, n_zones), dtype=np.float64)

    def nz(src: str, name: str) -> np.ndarray:
        return nr.get(src, {}).get(name, z)

    demand = {
        "da":      m["da"]              + nz("ix", "DA")      + nz("air", "DA"),
        "sr2":     m["sr2"] / SR2_OCC    + nz("ix", "SR2")     + nz("air", "SR2"),
        "sr3":     m["sr3"] / SR3_OCC    + nz("ix", "SR3")     + nz("air", "SR3"),
        "sml":     nz("trk", "VSTRUCK") + nz("trk", "STRUCK") + nz("trk", "MTRUCK"),
        "lrg":     nz("trk", "CTRUCK"),
        "datoll":  m["datoll"]           + nz("ix", "DATOLL")  + nz("air", "DATOLL"),
        "sr2toll": m["sr2toll"] / SR2_OCC + nz("ix", "SR2TOLL") + nz("air", "SR2TOLL")
        + nz("hsr", "taxi_veh"),
        "sr3toll": m["sr3toll"] / SR3_OCC + nz("ix", "SR3TOLL") + nz("air", "SR3TOLL"),
        "smltoll": nz("trk", "VSTRUCKTOLL") + nz("trk", "STRUCKTOLL") + nz("trk", "MTRUCKTOLL"),
        "lrgtoll": nz("trk", "CTRUCKTOLL"),
        "daav":    z.copy(),
        "s2av":    z.copy(),
        "s3av":    z.copy(),
    }
    # guarantee every class present and in canonical order
    return {name: demand[name] for name in CLASS_ORDER}
