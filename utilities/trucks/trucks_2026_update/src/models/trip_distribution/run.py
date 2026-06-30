"""
Truck Trip Distribution Model
==============================

Calibrates and applies a doubly-constrained gravity model for truck trip
distribution. For each configured run (truck type), the model:

  1. Loads productions and attractions from the PA table
  2. Loads travel time skims from an OMX file
  3. Calibrates gamma friction factor parameters (b, c) by fitting the
     modeled trip length frequency distribution (TLFD) to an observed one
  4. Applies the calibrated gravity model to produce a zone-to-zone trip table
  5. Writes a validation report (Excel + plots) and the modeled trip matrices

Usage
-----
CLI::

    python -m src.models.trip_distribution.run \\
        --config configs/trip_distribution.yaml

Notebook::

    from src.models.trip_distribution.run import run
    run(config_path="configs/trip_distribution.yaml")

Configuration
-------------
All inputs, run parameters, and output location are declared in a single
YAML file. See the design specification (TRIP_DISTRIBUTION_SPEC.md) for the
full YAML template and field descriptions.

Inputs
------
PA table (parquet)
    One row per zone. Index is 1-based integer zone IDs. Must contain
    productions and attractions columns for each configured run, plus any
    zone attribute columns listed in geo_agg_cols.

    Required columns (per run, names declared in YAML):
        {run_name}_productions  : float, daily vehicle trip productions
        {run_name}_attractions  : float, daily vehicle trip attractions

    Optional columns:
        Any zone attribute (e.g. county_id, district_id) listed in
        geo_agg_cols will be used for geographic aggregation in outputs.

Skim file (OMX)
    Pre-processed OMX file containing one travel time matrix per truck type.
    Matrix names must match skim_column values declared in the YAML.
    Units: minutes. 0-based internal indexing (zone ID z = row/col z-1).
    Must cover at least all zones in the PA table index.

    Preprocessing note: any blending of time periods (e.g. 1/3 AM + 2/3 MD)
    must be done before calling this model. This package expects a single
    ready-to-use impedance matrix per truck type.

TLFD files (CSV, one per run)
    Observed trip length frequency distribution. Required columns:
        bin_start : float, left edge of time bin (minutes, inclusive)
        bin_end   : float, right edge of time bin (minutes, exclusive)
        share     : float, fraction of trips in this bin (must sum to ~1.0)

    Bins may be irregular. Additional columns are allowed and ignored.

Target OD matrix (parquet, optional, one per run)
    Observed or reference OD trip table for model validation.
    Required columns:
        origin      : int, 1-based zone ID
        destination : int, 1-based zone ID
        trips       : float, daily vehicle trips

    If provided, the model produces OD scatter plots and summary statistics
    comparing modeled flows to observed. Not used in calibration.

Outputs
-------
All outputs written to output_dir declared in model_settings of the YAML.

    summary.xlsx          Calibration results, PA diagnostics, and TLFD
                          comparison tables. One tab per run per table type.
                          See design spec Section 7.1 for full tab structure.

    plots/                PNG figures for visual validation.
        tlfd_comparison.png          Observed vs modeled TLFD per run
        friction_curves.png          Gamma F(t) curves per run
        calibration_loss.png         Optimizer convergence per run
        pa_residuals_{sn}_{geo}.png  PA residuals by geography (if geo_agg_cols set)
        od_scatter_{sn}.png          Observed vs modeled OD scatter (if target OD set)
        od_residuals_{sn}_{geo}.png  OD residuals by geography (if both set)

    matrices/
        modeled_trips.parquet   Long format: origin, destination, {run_name}...
        modeled_trips.omx       Wide format for Cube/TP+ compatibility

    run.log               Full log of the run including warnings and timing

Zone Index Convention
---------------------
PA parquet uses 1-based zone IDs as the index (zones 1...N).
OMX skims use 0-based array indexing internally (rows/columns 0...N-1).
Zone ID z in the parquet corresponds to row/column z-1 in the OMX array.
This mapping is applied automatically at load time. If the skim file
contains more zones than the PA table (e.g. gateway zones), the skim is
filtered to match the PA zone list before any computation.
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.models.trip_distribution.calibration import CalibrationResult, calibrate_trip_distribution
from src.models.trip_distribution.config import TripDistributionConfig
from src.models.trip_distribution.friction import build_ff_matrix
from src.models.trip_distribution.gravity import GravityResult, run_gravity
from src.models.trip_distribution.io import load_od, load_pa, load_skims, load_tlfd, write_trips_omx, write_trips_parquet
from src.models.trip_distribution.validation import build_report_data, render_excel, render_plots


def _setup_logging(verbosity: str, output_dir: Path) -> None:
    """Configure the root logger to write to stdout and output_dir/run.log.

    Parameters
    ----------
    verbosity : str
        Logging level string: ``"DEBUG"``, ``"INFO"``, or ``"WARNING"``.
    output_dir : Path
        Directory where ``run.log`` will be created (must already exist).
    """
    level = getattr(logging, verbosity.upper(), logging.INFO)
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.FileHandler(output_dir / "run.log", mode="w"),
    ]
    logging.basicConfig(level=level, format="%(message)s", handlers=handlers, force=True)


def _check_boundary_warnings(
    run_name: str,
    cal_result: CalibrationResult,
    b_bounds: tuple[float, float],
    c_bounds: tuple[float, float],
    logger: logging.Logger,
) -> None:
    """Emit a WARNING if the optimizer settled at a parameter boundary.

    A boundary hit indicates the model may be misspecified for this truck
    type — the true optimum likely lies outside the search space.

    Parameters
    ----------
    run_name : str
        Run name used in the warning message.
    cal_result : CalibrationResult
        Calibration output containing the final ``b`` and ``c`` values.
    b_bounds : tuple[float, float]
        ``(lo, hi)`` search bounds for ``b``.
    c_bounds : tuple[float, float]
        ``(lo, hi)`` search bounds for ``c``.
    logger : logging.Logger
        Logger instance to write warnings to.
    """
    tol = 1e-6
    b_lo, b_hi = b_bounds
    c_lo, c_hi = c_bounds
    if abs(cal_result.b - b_lo) < tol or abs(cal_result.b - b_hi) < tol:
        logger.warning(
            f"[trip_distribution] WARNING: {run_name} — parameter b at bound "
            f"({cal_result.b:.4f}). Check initial values or TLFD data quality."
        )
    if abs(cal_result.c - c_lo) < tol or abs(cal_result.c - c_hi) < tol:
        logger.warning(
            f"[trip_distribution] WARNING: {run_name} — parameter c at bound "
            f"({cal_result.c:.4f}). Check initial values or TLFD data quality."
        )


def run(config_path: str | Path = "configs/trip_distribution.yaml") -> None:
    """Run the full truck trip distribution pipeline.

    Follows the initialization order required by the spec:
      1. Parse YAML → TripDistributionConfig
      2. Create output directories on disk
      3. Initialize logging
      4. Load shared inputs (PA table, skims)
      5. Iterate over runs (calibrate → gravity → collect results)
      6. Write matrix outputs
      7. Build report data
      8. Render Excel and plots

    Runs are independent — a failure in one run is caught, logged at ERROR
    level, and marked as FAILED in the report. All other runs continue.

    Parameters
    ----------
    config_path : str or Path
        Path to the YAML configuration file.
        Default: ``"configs/trip_distribution.yaml"``.
    """
    config_path = Path(config_path)

    config = TripDistributionConfig.from_yaml(config_path)

    ms = config.model_settings
    output_dir = ms.output_dir
    plots_dir = output_dir / "plots"
    matrices_dir = output_dir / "matrices"

    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(exist_ok=True)
    matrices_dir.mkdir(exist_ok=True)

    # Initialize logging
    _setup_logging(ms.verbosity, output_dir)
    logger = logging.getLogger("trip_distribution")

    start_time = time.time()
    n_runs = len(config.runs)
    logger.info(f"[trip_distribution] Starting — {n_runs} run(s) configured")

    # Load shared inputs
    logger.info("[trip_distribution] Loading inputs...")
    pa = load_pa(config.inputs.pa_path)
    skims = load_skims(config.inputs.skim_path, pa_zone_ids=pa.index.to_numpy())

    n_zones = len(pa)
    n_skims = len(skims)
    skim_names = ", ".join(skims.keys())
    logger.info(f"[trip_distribution]   PA table loaded: {n_zones} zones")
    logger.info(f"[trip_distribution]   Skims loaded: {n_skims} matrices ({skim_names})")
    logger.info("[trip_distribution]   Zone alignment validated: PA index matches skim dimensions")

    # Iterate over runs
    all_trips: dict[str, np.ndarray] = {}
    run_results: list[dict] = []

    for i, run_cfg in enumerate(config.runs, 1):
        logger.info(f"[trip_distribution] Run {i}/{n_runs}: {run_cfg.name}")

        skim: np.ndarray | None = None  # set inside try; kept here so except can reference it

        try:
            # Load TLFD
            tlfd = load_tlfd(run_cfg.tlfd_path)
            n_bins = len(tlfd)
            midpoints = (tlfd["bin_start"] + tlfd["bin_end"]) / 2.0
            obs_atl = float((midpoints * tlfd["share"]).sum())
            logger.info(
                f"[trip_distribution]   TLFD loaded: {n_bins} bins, "
                f"observed mean={obs_atl:.1f} min"
            )

            # Load target OD (optional)
            target_od: pd.DataFrame | None = None
            if run_cfg.target_od_path is not None:
                target_od = load_od(run_cfg.target_od_path, pa_zone_ids=pa.index.to_numpy())

            # Extract P/A arrays for this run
            productions = pa[run_cfg.productions_column].to_numpy(dtype=float)
            attractions = pa[run_cfg.attractions_column].to_numpy(dtype=float)
            skim = skims[run_cfg.skim_column]

            # TODO: Add check in a different func _WARN_PA_BALANCE
            # Warn if P/A totals are unbalanced (>5%)
            p_total = float(productions.sum())
            a_total = float(attractions.sum())
            if p_total > 0:
                diff_pct = abs(p_total - a_total) / p_total * 100.0
                if diff_pct > 5.0:
                    logger.warning(
                        f"[trip_distribution] WARNING: {run_cfg.name} — "
                        f"P total ({p_total:.0f}) and A total ({a_total:.0f}) "
                        f"differ by {diff_pct:.1f}%"
                    )

            # Calibrate gamma parameters
            logger.info("[trip_distribution]   Calibrating gamma parameters...")
            cal_result = calibrate_trip_distribution(
                P=productions,
                A=attractions,
                skim=skim,
                observed_tlfd=tlfd,
                b0=run_cfg.gamma_b0,
                c0=run_cfg.gamma_c0,
                model_settings=ms,
            )
            conv_str = "converged" if cal_result.converged else "not converged"
            logger.info(
                f"[trip_distribution]   Calibration complete: "
                f"b={cal_result.b:.4f}, c={cal_result.c:.4f} "
                f"({cal_result.n_iters} evals, {conv_str})"
            )
            _check_boundary_warnings(
                run_cfg.name, cal_result, ms.gamma_b_bounds, ms.gamma_c_bounds, logger
            )

            # Build friction matrix and apply gravity model
            logger.info("[trip_distribution]   Applying gravity model...")
            F = build_ff_matrix(skim, cal_result.b, cal_result.c)
            grav_result = run_gravity(
                P=productions,
                A=attractions,
                F=F,
                max_iters=ms.gravity_max_iters,
                max_rmse=ms.gravity_max_rmse,
                truck_type=run_cfg.name, # TODO: Change arg name to "name". "truck_type" is too specific
            )

            if grav_result.converged:
                logger.info(
                    f"[trip_distribution]   Gravity converged: "
                    f"{grav_result.n_iters} iterations, "
                    f"RMSE={grav_result.final_rmse:.1f}"
                )
            else:
                logger.warning(
                    f"[trip_distribution] WARNING: {run_cfg.name} — "
                    f"gravity did not converge after {grav_result.n_iters} iterations. "
                    f"Final RMSE={grav_result.final_rmse:.1f}"
                )

            all_trips[run_cfg.name] = grav_result.trips

            run_results.append(
                {
                    "run_cfg": run_cfg,
                    "cal_result": cal_result,
                    "grav_result": grav_result,
                    "tlfd": tlfd,
                    "target_od": target_od,
                    "pa": pa,
                    "skim": skim,
                    "status": "OK",
                    "error_message": None,
                }
            )

        except Exception as exc:
            logger.error(
                f"[trip_distribution] Run {run_cfg.name} FAILED: {exc}", exc_info=True
            )
            run_results.append(
                {
                    "run_cfg": run_cfg,
                    "cal_result": None,
                    "grav_result": None,
                    "tlfd": None,
                    "target_od": None,
                    "pa": pa,
                    "skim": skim,          # None if error occurred before skim extraction
                    "status": "FAILED",
                    "error_message": str(exc),
                }
            )

    # Write matrix outputs for all successful runs
    successful_trips = {
        r["run_cfg"].name: all_trips[r["run_cfg"].name]
        for r in run_results
        if r["status"] == "OK"
    }
    if successful_trips:
        zone_ids = pa.index.to_numpy()
        write_trips_parquet(successful_trips, zone_ids, matrices_dir)
        write_trips_omx(successful_trips, matrices_dir)

    # Build report data
    report = build_report_data(run_results=run_results, config=config)

    # Render outputs
    render_excel(report, output_dir)
    render_plots(report, plots_dir)
    logger.info("[trip_distribution]   Validation outputs written")

    elapsed = time.time() - start_time
    logger.info(f"[trip_distribution] All runs complete — outputs written to: {output_dir}")
    logger.info(f"[trip_distribution] Total elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Truck Trip Distribution Model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        default="configs/trip_distribution.yaml",
        help="Path to the YAML configuration file (default: configs/trip_distribution.yaml)",
    )
    args = parser.parse_args()
    run(config_path=args.config)
