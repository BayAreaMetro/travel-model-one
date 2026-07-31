"""Assemble the 13 highway vehicle-trip tables for one period.

This is the AequilibraE-native equivalent of the demand side of ``HwyAssign.job``'s
``pathload vol[]`` expressions plus the ``PrepAssign.job`` trip-table build.  Personal
travel comes from this iteration's ActivitySim ``trips_{period}.omx``; the
non-residential tables (internal-external, truck, air-passenger, high-speed-rail) are
frozen from a reference ``nonres/`` directory.

Units: ActivitySim's ``write_trip_matrices`` already divides the shared-ride tables by
occupancy, so the OMX auto tables are **vehicle** trips (drive-alone is occ-1, undivided);
we do NOT divide them again.  The ride-hail tables (TAXI/TNC_SINGLE/TNC_SHARED) are exported
as **person** trips and folded to vehicles here, exactly as ``PrepAssign.job`` steps 3-5 do:

    da      = DRIVEALONEFREE + ix.DA + air.DA
    sr2     = SHARED2FREE     + ix.SR2 + air.SR2                 (OMX already /occ)
    sr3     = SHARED3FREE     + ix.SR3 + air.SR3
    sml     = trk.(VSTRUCK + STRUCK + MTRUCK)
    lrg     = trk.CTRUCK
    ...toll variants analogously; taxi folds into the toll classes by occupancy share,
       and sr2toll also picks up hsr.taxi_veh
    daav/s2av/s3av = TNC (single+shared) split across occupancy bins -> vehicles, plus the
       zero-passenger (deadhead) empty vehicles on the return leg (all occ-1).  Owned-AV is
       zero here (this ActivitySim config has no autonomous-vehicle mode).
"""

from pathlib import Path

import numpy as np
import openmatrix as omx

from cubeio import read_tpp
from tm1.assignment import expand_period
from tm1.assignment.aeq.classes import CLASS_ORDER
from tm1.assignment.params import Highway


def _pad(m: np.ndarray, n_zones: int) -> np.ndarray:
    """Place a (possibly internal-only) matrix into the full ``n_zones`` system."""
    if m.shape[0] == n_zones:
        return m
    full = np.zeros((n_zones, n_zones), dtype=np.float64)
    full[: m.shape[0], : m.shape[1]] = m
    return full


def _read_omx(omx_path: Path, names: dict, period: str, n_zones: int) -> dict[str, np.ndarray]:
    """Read ActivitySim OMX tables ``{omx_name}_{PERIOD}`` under the given keys.

    ``names`` maps the desired output key -> the ActivitySim table base name; a table
    absent from the file (e.g. ride-hail before the export config is refreshed) reads as
    zeros, so the loop degrades gracefully.
    """
    if not omx_path.exists():
        msg = f"ActivitySim trip matrix not found: {omx_path}"
        raise FileNotFoundError(msg)
    out: dict[str, np.ndarray] = {}
    with omx.open_file(str(omx_path), "r") as f:
        avail = set(f.list_matrices())
        for key, omx_name in names.items():
            tbl = f"{omx_name}_{period.upper()}"
            out[key] = (_pad(np.asarray(f[tbl], dtype=np.float64), n_zones)
                        if tbl in avail else np.zeros((n_zones, n_zones), dtype=np.float64))
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
    demand: str,
    nonres_dir: str | Path,
    period: str,
    n_zones: int,
    hw: Highway,
) -> dict[str, np.ndarray]:
    """Assemble the 13 vehicle-trip tables (keys :data:`CLASS_ORDER`) for a period.

    *demand* is the per-period path pattern declared by the assignment step's
    ``demand:`` key (``{period}`` -> ``ea``/``am``/...), read rather than
    reconstructed so the seam stays the single statement of where demand lives.

    Occupancy divisors, the ActivitySim table mapping, and the ride-hail folding
    constants come from ``hw`` (params.yaml ``highway:`` section).
    """
    nonres_dir = Path(nonres_dir)
    sr2_occ, sr3_occ = hw.occupancy["sr2"], hw.occupancy["sr3"]
    omx_path = Path(expand_period(demand, period))

    # auto tables are already vehicle trips (write_trip_matrices divided SR by occupancy);
    # ride-hail tables are person trips, folded to vehicles below.
    m = _read_omx(omx_path, {v: k for k, v in hw.asim_tables.items()}, period, n_zones)
    rh = _read_omx(omx_path, hw.ridehail.tables, period, n_zones)
    nr = _read_nonres(nonres_dir, period, n_zones)
    z = np.zeros((n_zones, n_zones), dtype=np.float64)

    def nz(src: str, name: str) -> np.ndarray:
        return nr.get(src, {}).get(name, z)

    # --- ride-hail person-trips -> vehicle trips (PrepAssign.job steps 3-5) ------------
    sh = hw.ridehail.shares
    taxi, single, shared = rh["taxi"], rh["single"], rh["shared"]

    # TNC (single + shared) split across occupancy bins, then person -> vehicle
    da_tnc = single * sh["single"]["da"] + shared * sh["shared"]["da"]        # occ 1
    s2_tnc = (single * sh["single"]["s2"] + shared * sh["shared"]["s2"]) / sr2_occ
    s3_tnc = (single * sh["single"]["s3"] + shared * sh["shared"]["s3"]) / sr3_occ
    # zero-passenger (deadhead) empty vehicles: return leg (transpose), all occ 1
    zpv = (da_tnc + s2_tnc + s3_tnc).T * hw.ridehail.zpv_factor

    # taxi folds into the toll classes by occupancy share, then person -> vehicle
    taxi_datoll = taxi * sh["taxi"]["da"]                    # occ 1
    taxi_sr2toll = taxi * sh["taxi"]["s2"] / sr2_occ
    taxi_sr3toll = taxi * sh["taxi"]["s3"] / sr3_occ

    demand = {
        "da":      m["da"]     + nz("ix", "DA")     + nz("air", "DA"),
        "sr2":     m["sr2"]    + nz("ix", "SR2")    + nz("air", "SR2"),
        "sr3":     m["sr3"]    + nz("ix", "SR3")    + nz("air", "SR3"),
        "sml":     nz("trk", "VSTRUCK") + nz("trk", "STRUCK") + nz("trk", "MTRUCK"),
        "lrg":     nz("trk", "CTRUCK"),
        "datoll":  m["datoll"] + taxi_datoll  + nz("ix", "DATOLL")  + nz("air", "DATOLL"),
        "sr2toll": m["sr2toll"] + taxi_sr2toll + nz("ix", "SR2TOLL") + nz("air", "SR2TOLL")
        + nz("hsr", "taxi_veh"),
        "sr3toll": m["sr3toll"] + taxi_sr3toll + nz("ix", "SR3TOLL") + nz("air", "SR3TOLL"),
        "smltoll": nz("trk", "VSTRUCKTOLL") + nz("trk", "STRUCKTOLL") + nz("trk", "MTRUCKTOLL"),
        "lrgtoll": nz("trk", "CTRUCKTOLL"),
        "daav":    da_tnc + zpv,
        "s2av":    s2_tnc,
        "s3av":    s3_tnc,
    }
    # guarantee every class present and in canonical order
    return {name: demand[name] for name in CLASS_ORDER}
