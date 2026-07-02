"""AequilibraE-native highway assignment iteration (open-source Cube replacement).

One call runs, for all five periods: assemble demand (ActivitySim personal trips +
frozen non-residential), build the 13 assignment classes, solve user equilibrium with
Cube's facility-type VDF, skim the converged network, and write the refreshed highway
level-of-service into ``skims.omx`` for the next ActivitySim run.

Transit skims are preserved from the existing ``skims.omx`` (the transit assignment +
skimming is wired separately); only the highway matrices are refreshed here, so the
first closed loop exercises the skim -> demand -> assign -> skim cycle on the highway
side while transit stays frozen.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import openmatrix as omx
import pandas as pd

from tm1.assignment.aeq.classes import build_vehicle_classes
from tm1.assignment.aeq.demand import assemble_demand
from tm1.assignment.aeq.highway import equilibrium_assignment
from tm1.assignment.aeq.network import build_cube_graph
from tm1.assignment.aeq.skim import highway_skims
from tm1.assignment.aeq.vdf import congested_time

log = logging.getLogger(__name__)

PERIODS: tuple[str, ...] = ("EA", "AM", "MD", "PM", "EV")
# capacity factor = hours represented in each period (HwyAssign capfac)
CAPFAC: dict[str, float] = {"EA": 3.0, "AM": 4.0, "MD": 5.0, "PM": 4.0, "EV": 8.0}
N_ZONES = 1475


def _msa_average(
    state: dict,
    period: str,
    total_pce: np.ndarray,
    iteration: int,
) -> np.ndarray:
    """MSA-average this iteration's combined PCE volume against the running average.

    Replicates the legacy ``AverageNetworkVolumes.job`` ramp: iteration N blends
    ``1/N`` of the fresh volumes with ``1 - 1/N`` of the previous average.  The
    running average is kept in *state* (persisted across iterations by the caller).
    """
    wgt = 1.0 / max(1, iteration)
    prev = state.get(period)
    avg = total_pce if prev is None else wgt * total_pce + (1.0 - wgt) * prev
    state[period] = avg
    return avg


def _load_msa_state(path: Path) -> dict:
    if not path.exists():
        return {}
    with np.load(path) as z:
        return {k: z[k] for k in z.files}


def _save_msa_state(path: Path, state: dict) -> None:
    np.savez_compressed(path, **state)


def _write_skims_omx(
    skims_omx_path: Path,
    highway: dict[str, np.ndarray],
    n_zones: int,
) -> None:
    """Write refreshed highway matrices into ``skims.omx``, preserving other keys.

    Any existing (transit / non-motorised) matrices and the zone mapping are copied
    across; the highway keys in *highway* replace their previous values.
    """
    skims_omx_path = Path(skims_omx_path)
    preserved: dict[str, np.ndarray] = {}
    mapping = None
    mapping_name = None
    if skims_omx_path.exists():
        with omx.open_file(str(skims_omx_path), "r") as f:
            maps = f.list_mappings()
            if maps:
                mapping_name = maps[0]
                mapping = list(f.mapping(mapping_name).keys())
            for key in f.list_matrices():
                if key not in highway:
                    preserved[key] = np.asarray(f[key], dtype=np.float64)

    tmp = skims_omx_path.with_suffix(".omx.tmp")
    if tmp.exists():
        tmp.unlink()
    with omx.open_file(str(tmp), "w") as f:
        for key, mat in {**preserved, **highway}.items():
            f[key] = np.asarray(mat, dtype=np.float64)
        if mapping is None:
            mapping = list(range(1, n_zones + 1))
            mapping_name = "taz"
        f.create_mapping(mapping_name, np.asarray(mapping, dtype=np.int32))

    skims_omx_path.unlink(missing_ok=True)
    tmp.rename(skims_omx_path)
    log.info("Wrote %s (%d highway + %d preserved matrices)",
             skims_omx_path.name, len(highway), len(preserved))


def run_assignment_iteration(
    asim_output_dir: str | Path,
    network_csv: str | Path,
    nonres_dir: str | Path,
    skims_omx_path: str | Path,
    *,
    iteration: int,
    periods: tuple[str, ...] = PERIODS,
    n_zones: int = N_ZONES,
    max_iter: int = 100,
    gap_target: float = 1e-4,
    av_pce: float = 1.0,
    cores: int | None = None,
) -> dict[str, float]:
    """Run one AequilibraE highway assignment + skim iteration for all periods.

    Returns a per-period ``{period: VMT}`` summary (also logged).
    """
    network_csv = Path(network_csv)
    links = pd.read_csv(network_csv)
    log.info("aeq iteration %d: %d links, %d periods", iteration, len(links), len(periods))

    # running MSA volume average, persisted next to the skims across iterations
    msa_path = Path(skims_omx_path).with_name("aeq_msa_volumes.npz")
    msa_state = _load_msa_state(msa_path) if iteration > 1 else {}

    all_skims: dict[str, np.ndarray] = {}
    vmt: dict[str, float] = {}
    for period in periods:
        g, attrs = build_cube_graph(links, n_zones, capfac=CAPFAC[period])
        demand = assemble_demand(asim_output_dir, nonres_dir, period, n_zones)
        classes = build_vehicle_classes(demand, links, period, av_pce=av_pce)

        res = equilibrium_assignment(
            g, attrs, classes, n_zones, max_iter=max_iter, gap_target=gap_target,
            cores=cores,
        )
        vmt[period] = float((res.total_pce * attrs.distance).sum())
        log.info("aeq %s: gap %.2e in %d iters, VMT %.0f",
                 period, res.gap, res.iterations, vmt[period])

        # MSA volume averaging across global iterations (legacy AverageNetworkVolumes):
        # skim times come from the 1/N-averaged network, not the raw equilibrium --
        # this is also what Cube's reference skims are built on.
        avg_pce = _msa_average(msa_state, period, res.total_pce, iteration)
        skim_time = congested_time(avg_pce / attrs.capacity, attrs.ft, attrs.t0,
                                   attrs.distance, attrs.ffs, attrs.critspd)

        skims = highway_skims(g, attrs, classes, skim_time, links, period, n_zones,
                              cores=cores)
        for key, mat in skims.items():
            all_skims[f"{key}__{period}"] = mat

    _save_msa_state(msa_path, msa_state)
    _write_skims_omx(Path(skims_omx_path), all_skims, n_zones)
    return vmt
