"""AequilibraE-native highway assignment iteration (open-source Cube replacement).

One call runs, for all five periods: assemble demand (ActivitySim personal trips +
frozen non-residential), build the 13 assignment classes, solve user equilibrium with
Cube's facility-type VDF, skim the converged network, and write the refreshed highway
level-of-service into ``skims.omx`` for the next ActivitySim run.

When ``transit_inputs_dir`` is given, transit level-of-service skims are refreshed too:
the Spiess-Florian component skims (:mod:`tm1.assignment.aeq.transit_skims`) are built
from the source transit network with bus in-vehicle times taken from this iteration's
congested highway times, and merged into ``skims.omx`` alongside the highway matrices --
a fully Cube-free closed loop.  Without it, existing transit matrices are preserved.
"""

import logging
from pathlib import Path

import numpy as np
import openmatrix as omx
import pandas as pd

from tm1.assignment.aeq.classes import build_vehicle_classes
from tm1.assignment.aeq.demand import assemble_demand
from tm1.assignment.aeq.fares import load_fares
from tm1.assignment.aeq.highway import equilibrium_assignment
from tm1.assignment.aeq.network import build_cube_graph
from tm1.assignment.params import AeqParams, load_aeq_params
from tm1.assignment.aeq.skim import highway_skims
from tm1.assignment.aeq.transit_network import build_ride_links, bus_time_table, parse_lin
from tm1.assignment.aeq.transit_skims import skim_all_runs
from tm1.assignment.aeq.vdf import congested_time

log = logging.getLogger(__name__)


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


def _load_fare_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    with np.load(path) as z:
        return {k: z[k] for k in z.files}


def _save_fare_cache(path: Path, cache: dict) -> None:
    np.savez_compressed(path, **cache)


def _transit_skims(
    transit_dir: Path,
    street_time_by_period: dict,
    p: AeqParams,
    cores: int | None,
    fare_cache_path: Path,
) -> dict[str, np.ndarray]:
    """Build the ActivitySim transit skim matrices from the source network.

    Ride (in-vehicle bus) times come from this iteration's congested highway times
    (``street_time_by_period`` = ``period -> {(a, b): bus minutes}``); the exact
    operator-graph fare is computed once and cached to ``fare_cache_path`` (fares are
    static, so later iterations reuse it).
    """
    lines = parse_lin(transit_dir / "transitLines.lin")
    ld = pd.read_parquet(transit_dir / "link_distance.parquet")
    link_dist = {(int(a), int(b)): float(x)
                 for a, b, x in zip(ld.A, ld.B, ld.distance, strict=False)}
    rtd = pd.read_parquet(transit_dir / "ref_ride_time.parquet")
    ref_time = {(int(a), int(b)): float(t)
                for a, b, t in zip(rtd.A, rtd.B, rtd.time, strict=False)}
    sl = pd.read_parquet(transit_dir / "support_links.parquet")
    support_by_runtype = {rt: sl[sl["run_type"] == rt] for rt in sl["run_type"].unique()}
    fares = load_fares(transit_dir / "fares", link_dist, lines, rail_fare=p.rail_fare)

    ride_by_period: dict = {}
    hw_by_period: dict = {}
    for period, street_time in street_time_by_period.items():
        ride, hw = build_ride_links(lines, period, street_time, link_dist, ref_time,
                                    bus_cfg=p.bus_time, freq_field=p.periods.freq_field)
        ride_by_period[period] = ride
        hw_by_period[period] = hw

    fare_cache = _load_fare_cache(fare_cache_path)
    # Both passes scale via worker concurrency (small sparse graphs): the 75 LOS skims
    # ~1.9x at ~6 workers x 8 threads, the 15 one-time fare skims ~3x at 4 workers x 12
    # threads (~7 min on TM2-B).  Split cores accordingly; small boxes run sequentially.
    if cores and cores >= 16:
        workers = min(6, cores // 8)
        threads = max(4, cores // workers)
        fare_workers = min(4, cores // 12)
        fare_threads = max(8, cores // fare_workers)
    else:
        workers, threads = 1, cores
        fare_workers, fare_threads = 1, cores
    mats = skim_all_runs(ride_by_period, support_by_runtype, hw_by_period, fares,
                         params=p, threads=threads, fare_cache=fare_cache,
                         workers=workers, fare_threads=fare_threads,
                         fare_workers=fare_workers)
    _save_fare_cache(fare_cache_path, fare_cache)
    log.info("transit skims: %d matrices (%d run types cached fare)",
             len(mats), len(fare_cache))
    return mats


def run_assignment_iteration(
    asim_output_dir: str | Path,
    network_csv: str | Path,
    nonres_dir: str | Path,
    skims_omx_path: str | Path,
    *,
    iteration: int,
    periods: tuple[str, ...] | None = None,
    n_zones: int | None = None,
    max_iter: int = 100,
    gap_target: float = 1e-4,
    av_pce: float = 1.0,
    cores: int | None = None,
    transit_inputs_dir: str | Path | None = None,
    params_path: str | Path | None = None,
) -> dict[str, float]:
    """Run one AequilibraE highway assignment + skim iteration for all periods.

    Model policy (periods/capfac, zones, transit cost, bus times, fares) comes from
    ``params.yaml``; ``params_path`` selects an alternate copy.  Returns a
    per-period ``{period: VMT}`` summary (also logged).
    """
    p = load_aeq_params(params_path)
    periods = tuple(periods) if periods else p.periods.names
    n_zones = n_zones or p.n_taz
    network_csv = Path(network_csv)
    links = pd.read_csv(network_csv)
    log.info("aeq iteration %d: %d links, %d periods", iteration, len(links), len(periods))

    # running MSA volume average, persisted next to the skims across iterations
    msa_path = Path(skims_omx_path).with_name("aeq_msa_volumes.npz")
    msa_state = _load_msa_state(msa_path) if iteration > 1 else {}

    all_skims: dict[str, np.ndarray] = {}
    vmt: dict[str, float] = {}
    street_time_by_period: dict[str, dict] = {}
    for period in periods:
        g, attrs = build_cube_graph(links, n_zones, capfac=p.periods.capfac[period],
                                    vdf=p.highway.vdf)
        demand = assemble_demand(asim_output_dir, nonres_dir, period, n_zones, p.highway)
        classes = build_vehicle_classes(demand, links, period, p.highway, av_pce=av_pce)

        res = equilibrium_assignment(
            g, attrs, classes, n_zones, p.highway.vdf, max_iter=max_iter,
            gap_target=gap_target, cores=cores,
        )
        vmt[period] = float((res.total_pce * attrs.distance).sum())
        log.info("aeq %s: gap %.2e in %d iters, VMT %.0f",
                 period, res.gap, res.iterations, vmt[period])

        # MSA volume averaging across global iterations (legacy AverageNetworkVolumes):
        # skim times come from the 1/N-averaged network, not the raw equilibrium --
        # this is also what Cube's reference skims are built on.
        avg_pce = _msa_average(msa_state, period, res.total_pce, iteration)
        skim_time = congested_time(avg_pce / attrs.capacity, attrs.ft, attrs.t0,
                                   attrs.distance, attrs.ffs, attrs.critspd,
                                   p.highway.vdf)

        skims = highway_skims(g, attrs, classes, skim_time, links, period, n_zones,
                              p.highway, cores=cores)
        for key, mat in skims.items():
            all_skims[f"{key}__{period}"] = mat

        # transit bus in-vehicle times follow the congested street network (Cube
        # useruntime=n): area-type delay applied to this iteration's congested times.
        if transit_inputs_dir is not None:
            links_ct = links.copy()
            links_ct[f"ctim{period}"] = skim_time
            street_time_by_period[period] = bus_time_table(links_ct, period, p.bus_time)

    if transit_inputs_dir is not None:
        fare_cache_path = Path(skims_omx_path).with_name("aeq_transit_fare_cache.npz")
        all_skims.update(_transit_skims(Path(transit_inputs_dir), street_time_by_period,
                                        p, cores, fare_cache_path))

    _save_msa_state(msa_path, msa_state)
    _write_skims_omx(Path(skims_omx_path), all_skims, n_zones)
    return vmt
