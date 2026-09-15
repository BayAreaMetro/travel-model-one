"""Pure computation layer for the validation report.

Builds ``ReportData`` from calibration results, gravity results, and observed
data. No rendering dependencies — never imports openpyxl or matplotlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from src.models.trip_distribution.calibration import compute_tlfd


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RunReport:
    """Validation data for a single truck type run.

    Parameters
    ----------
    run_name : str
        Full run name (matches ``RunConfig.name``).
    short_name : str
        Short label (matches ``RunConfig.short_name``), used as Excel tab prefix.
    status : str
        ``"OK"`` if the run completed successfully, ``"FAILED"`` otherwise.
    error_message : str or None
        Exception message for failed runs; None for successful runs.
    b_initial : float
        Initial ``b`` value passed to the optimizer.
    c_initial : float
        Initial ``c`` value passed to the optimizer.
    b_final : float or None
        Calibrated ``b`` value; None for failed runs.
    c_final : float or None
        Calibrated ``c`` value; None for failed runs.
    converged : bool or None
        Whether the optimizer converged; None for failed runs.
    n_iters : int or None
        Number of optimizer evaluations; None for failed runs.
    final_loss : float or None
        Optimizer loss at termination; None for failed runs.
    tlfd_table : pd.DataFrame or None
        Columns: ``bin_start``, ``bin_end``, ``observed_share``, ``modeled_share``,
        ``abs_diff``, ``pct_diff``. None for failed runs.
    pa_stats : pd.DataFrame or None
        Columns: ``metric``, ``productions``, ``attractions``. None for failed runs.
    pa_zones : pd.DataFrame or None
        Per-zone residuals. Columns: ``zone_id``, ``target_P``, ``modeled_P``,
        ``P_diff``, ``P_pct_diff``, ``P_abs_diff_rank``, ``target_A``,
        ``modeled_A``, ``A_diff``, ``A_pct_diff``, ``A_abs_diff_rank``.
        None for failed runs.
    pa_geo : dict[str, pd.DataFrame]
        Keyed by geo column name. Each DataFrame has columns: ``{geo_col}``,
        ``target_P``, ``modeled_P``, ``P_diff``, ``P_pct_diff``, ``target_A``,
        ``modeled_A``, ``A_diff``, ``A_pct_diff``. Empty dict for failed runs
        or when no geo columns are configured.
    od_stats : pd.DataFrame or None
        Summary statistics comparing modeled vs observed OD. None if no
        ``target_od_path`` was set or the run failed.
    r2_log : float or None
        R² on log-log scatter of modeled vs observed OD pairs. None if no OD.
    slope_log : float or None
        Slope of the fitted line on the log-log OD scatter. None if no OD.
    intercept_log : float or None
        Intercept of the log-log linear fit (in log-space). Used by
        ``plots.py`` to draw the trend line. None if no OD.
    loss_history : list[float]
        Optimizer loss sampled every 10 evaluations.  Used by ``plots.py``
        for the calibration loss convergence chart.  Empty when calibration
        finished in fewer than 10 evaluations.
    od_pairs : pd.DataFrame or None
        Full joined OD table with columns ``origin``, ``destination``,
        ``observed_trips``, ``modeled_trips`` (1-based zone IDs).  Used by
        ``plots.py`` for the log-log scatter.  None if no target OD.
    od_geo : dict[str, pd.DataFrame]
        Pivot tables of OD relative residuals aggregated to each geography
        level, keyed by ``geo_col``.  Index = origin geography value,
        columns = destination geography value, values = (mod−obs)/obs×100 %.
        Used by ``plots.py`` for the OD residual heatmap.  Empty when no
        target OD or no ``geo_agg_cols``.
    """

    run_name: str
    short_name: str
    status: str
    error_message: str | None
    b_initial: float
    c_initial: float
    b_final: float | None
    c_final: float | None
    converged: bool | None
    n_iters: int | None
    final_loss: float | None
    tlfd_table: pd.DataFrame | None
    pa_stats: pd.DataFrame | None
    pa_zones: pd.DataFrame | None
    pa_geo: dict[str, pd.DataFrame] = field(default_factory=dict)
    od_stats: pd.DataFrame | None = None
    r2_log: float | None = None
    slope_log: float | None = None
    intercept_log: float | None = None
    loss_history: list[float] = field(default_factory=list)
    od_pairs: pd.DataFrame | None = None
    od_geo: dict[str, pd.DataFrame] = field(default_factory=dict)


@dataclass
class ReportData:
    """Aggregated validation data for all runs.

    Parameters
    ----------
    runs : list[RunReport]
        One entry per configured run (including failed ones).
    has_od : bool
        True if at least one run has a ``target_od_path`` set.
    has_geo : bool
        True if ``geo_agg_cols`` is non-empty in the config.
    """

    runs: list[RunReport]
    has_od: bool
    has_geo: bool


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _pct_within(
    actual: np.ndarray,
    target: np.ndarray,
    threshold: float,
) -> float:
    """% of zones where ``|actual − target| / target ≤ threshold``.

    Zones with ``target == 0`` are excluded.  Returns ``nan`` when no valid
    zones exist.
    """
    valid = target > 0.0
    if valid.sum() == 0:
        return float("nan")
    ratio = np.abs(actual[valid] - target[valid]) / target[valid]
    return float((ratio <= threshold).mean() * 100.0)


def _pa_stats_df(
    modeled_P: np.ndarray,
    target_P: np.ndarray,
    modeled_A: np.ndarray,
    target_A: np.ndarray,
) -> pd.DataFrame:
    """Build the PA summary statistics table (MAE, RMSE, …)."""
    P_diff = modeled_P - target_P
    A_diff = modeled_A - target_A

    return pd.DataFrame({
        "metric": [
            "MAE",
            "RMSE",
            "max_abs_error",
            "pct_zones_within_5pct",
            "pct_zones_within_10pct",
        ],
        "productions": [
            float(np.mean(np.abs(P_diff))),
            float(np.sqrt(np.mean(P_diff ** 2))),
            float(np.max(np.abs(P_diff))),
            _pct_within(modeled_P, target_P, 0.05),
            _pct_within(modeled_P, target_P, 0.10),
        ],
        "attractions": [
            float(np.mean(np.abs(A_diff))),
            float(np.sqrt(np.mean(A_diff ** 2))),
            float(np.max(np.abs(A_diff))),
            _pct_within(modeled_A, target_A, 0.05),
            _pct_within(modeled_A, target_A, 0.10),
        ],
    })


def _pa_zones_df(
    zone_ids: np.ndarray,
    target_P: np.ndarray,
    modeled_P: np.ndarray,
    target_A: np.ndarray,
    modeled_A: np.ndarray,
) -> pd.DataFrame:
    """Per-zone PA residuals, sorted worst-attraction-fit first (rank 1 = largest error)."""
    P_diff = modeled_P - target_P
    A_diff = modeled_A - target_A

    P_pct_diff = np.where(target_P > 0.0, P_diff / target_P * 100.0, np.nan)
    A_pct_diff = np.where(target_A > 0.0, A_diff / target_A * 100.0, np.nan)

    # Rank 1 = largest absolute difference (worst-fit zone)
    P_rank = (
        pd.Series(np.abs(P_diff))
        .rank(method="min", ascending=False)
        .to_numpy(dtype=np.int64)
    )
    A_rank = (
        pd.Series(np.abs(A_diff))
        .rank(method="min", ascending=False)
        .to_numpy(dtype=np.int64)
    )

    return (
        pd.DataFrame({
            "zone_id": zone_ids,
            "target_P": target_P,
            "modeled_P": modeled_P,
            "P_diff": P_diff,
            "P_pct_diff": P_pct_diff,
            "P_abs_diff_rank": P_rank,
            "target_A": target_A,
            "modeled_A": modeled_A,
            "A_diff": A_diff,
            "A_pct_diff": A_pct_diff,
            "A_abs_diff_rank": A_rank,
        })
        .sort_values("A_abs_diff_rank")
        .reset_index(drop=True)
    )


def _pa_geo_dict(
    pa: pd.DataFrame,
    geo_agg_cols: list[str],
    target_P: np.ndarray,
    modeled_P: np.ndarray,
    target_A: np.ndarray,
    modeled_A: np.ndarray,
) -> dict[str, pd.DataFrame]:
    """One aggregated DataFrame per geographic column."""
    base = pd.DataFrame(
        {col: pa[col].to_numpy() for col in geo_agg_cols},
        index=pa.index,
    )
    base["target_P"] = target_P
    base["modeled_P"] = modeled_P
    base["target_A"] = target_A
    base["modeled_A"] = modeled_A

    result: dict[str, pd.DataFrame] = {}
    for geo_col in geo_agg_cols:
        agg = (
            base
            .groupby(geo_col)[["target_P", "modeled_P", "target_A", "modeled_A"]]
            .sum()
            .reset_index()
        )
        agg["P_diff"] = agg["modeled_P"] - agg["target_P"]
        agg["P_pct_diff"] = np.where(
            agg["target_P"] > 0.0,
            agg["P_diff"] / agg["target_P"] * 100.0,
            np.nan,
        )
        agg["A_diff"] = agg["modeled_A"] - agg["target_A"]
        agg["A_pct_diff"] = np.where(
            agg["target_A"] > 0.0,
            agg["A_diff"] / agg["target_A"] * 100.0,
            np.nan,
        )
        result[geo_col] = agg[[
            geo_col,
            "target_P", "modeled_P", "P_diff", "P_pct_diff",
            "target_A", "modeled_A", "A_diff", "A_pct_diff",
        ]]

    return result


def _od_tables(
    grav_trips: np.ndarray,
    zone_ids: np.ndarray,
    target_od: pd.DataFrame,
) -> tuple[pd.DataFrame, float | None, float | None, float | None, pd.DataFrame]:
    """Compute OD statistics table, log-log regression metrics, and raw OD pairs.

    Parameters
    ----------
    grav_trips : np.ndarray
        Modeled zone-to-zone matrix, shape (n, n), 0-based indexing.
    zone_ids : np.ndarray
        1-based zone IDs for rows/columns of ``grav_trips``.
    target_od : pd.DataFrame
        Columns ``origin``, ``destination``, ``trips`` (1-based zone IDs).

    Returns
    -------
    od_stats : pd.DataFrame
        Summary stats with columns ``metric`` and ``value``.
    r2_log : float or None
        R² of log-log scatter; None when fewer than 2 positive pairs exist.
    slope_log : float or None
        Slope of the log-log linear fit; None under the same condition.
    intercept_log : float or None
        Intercept of the log-log linear fit (log-space); None under the same
        condition.  Needed by ``plots.py`` to draw the trend line.
    od_pairs : pd.DataFrame
        All observed OD pairs joined with their modelled counterparts.
        Columns: ``origin``, ``destination``, ``observed_trips``,
        ``modeled_trips``.  Used by ``plots.py`` for the scatter plot and
        OD residual heatmap.
    """
    n = len(zone_ids)

    # Expand modelled matrix to long format using 1-based zone IDs
    orig_ids = np.repeat(zone_ids, n).astype(np.int64)
    dest_ids = np.tile(zone_ids, n).astype(np.int64)
    modeled_od = pd.DataFrame({
        "origin": orig_ids,
        "destination": dest_ids,
        "modeled_trips": grav_trips.ravel(),
    })

    # Left join keeps every observed OD pair; unmatched pairs get 0 modelled trips
    od_joined = pd.merge(
        target_od.rename(columns={"trips": "observed_trips"}),
        modeled_od,
        on=["origin", "destination"],
        how="left",
    )
    od_joined["modeled_trips"] = od_joined["modeled_trips"].fillna(0.0)

    obs = od_joined["observed_trips"].to_numpy(dtype=np.float64)
    mod = od_joined["modeled_trips"].to_numpy(dtype=np.float64)

    # Log-log linear regression on pairs where both values are strictly positive
    both_pos = (obs > 0.0) & (mod > 0.0)
    r2_log: float | None = None
    slope_log: float | None = None
    intercept_log: float | None = None

    if both_pos.sum() >= 2:
        log_obs = np.log(obs[both_pos])
        log_mod = np.log(mod[both_pos])
        lr = stats.linregress(log_obs, log_mod)
        r2_log = float(lr.rvalue ** 2)
        slope_log = float(lr.slope)
        intercept_log = float(lr.intercept)

    # Residual percentages for observed pairs (obs > 0 by convention in target_od)
    valid = obs > 0.0
    if valid.any():
        abs_resid_pct = np.abs(mod[valid] - obs[valid]) / obs[valid] * 100.0
        mean_resid_pct = float(abs_resid_pct.mean())
        median_resid_pct = float(np.median(abs_resid_pct))
        pct_within_10 = float((abs_resid_pct <= 10.0).mean() * 100.0)
        pct_within_25 = float((abs_resid_pct <= 25.0).mean() * 100.0)
    else:
        mean_resid_pct = median_resid_pct = pct_within_10 = pct_within_25 = float("nan")

    obs_total = float(obs.sum())
    mod_total = float(mod.sum())
    trips_err_pct = (
        (mod_total - obs_total) / obs_total * 100.0
        if obs_total > 0.0
        else float("nan")
    )

    od_stats = pd.DataFrame({
        "metric": [
            "R² (log scale)",
            "slope of fitted line (log-log)",
            "mean absolute residual %",
            "median absolute residual %",
            "% OD pairs within 10%",
            "% OD pairs within 25%",
            "total observed trips",
            "total modeled trips",
            "total trips error %",
        ],
        "value": [
            r2_log if r2_log is not None else float("nan"),
            slope_log if slope_log is not None else float("nan"),
            mean_resid_pct,
            median_resid_pct,
            pct_within_10,
            pct_within_25,
            obs_total,
            mod_total,
            trips_err_pct,
        ],
    })

    # Compact OD pairs table used for scatter plots and geo heatmaps
    od_pairs = od_joined[
        ["origin", "destination", "observed_trips", "modeled_trips"]
    ].copy()

    return od_stats, r2_log, slope_log, intercept_log, od_pairs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_report_data(
    run_results: list[dict],
    config: object,
) -> ReportData:
    """Build a ReportData object from raw pipeline results.

    Computes all derived statistics (TLFD comparison, PA residuals, zone
    rankings, geographic aggregations, OD stats) from calibration and gravity
    outputs. Pure computation — no rendering I/O, no openpyxl, no matplotlib.

    Parameters
    ----------
    run_results : list[dict]
        One dict per run, as assembled in ``run.py``. Expected keys per dict:
        ``run_cfg``, ``cal_result``, ``grav_result``, ``tlfd``,
        ``target_od``, ``pa``, ``skim``, ``status``, ``error_message``.
    config : TripDistributionConfig
        Full configuration object (provides ``geo_agg_cols`` and run metadata).

    Returns
    -------
    ReportData
        Fully populated report object ready for rendering.
    """
    geo_agg_cols: list[str] = config.inputs.geo_agg_cols
    has_geo = len(geo_agg_cols) > 0
    has_od = any(r["run_cfg"].target_od_path is not None for r in run_results)

    runs: list[RunReport] = []

    for result in run_results:
        run_cfg = result["run_cfg"]
        status: str = result["status"]
        error_message: str | None = result["error_message"]
        cal_result = result.get("cal_result")
        grav_result = result.get("grav_result")
        tlfd = result.get("tlfd")
        target_od = result.get("target_od")
        pa: pd.DataFrame = result["pa"]
        skim: np.ndarray | None = result.get("skim")

        if status != "OK" or grav_result is None or skim is None or tlfd is None:
            # Failed run — all computed fields are None / empty
            runs.append(RunReport(
                run_name=run_cfg.name,
                short_name=run_cfg.short_name,
                status="FAILED",
                error_message=error_message,
                b_initial=float(run_cfg.gamma_b0),
                c_initial=float(run_cfg.gamma_c0),
                b_final=None,
                c_final=None,
                converged=None,
                n_iters=None,
                final_loss=None,
                tlfd_table=None,
                pa_stats=None,
                pa_zones=None,
                pa_geo={},
                od_stats=None,
                r2_log=None,
                slope_log=None,
            ))
            continue

        # ── P/A vectors ───────────────────────────────────────────────────
        zone_ids = pa.index.to_numpy()
        target_P = pa[run_cfg.productions_column].to_numpy(dtype=np.float64)
        target_A = pa[run_cfg.attractions_column].to_numpy(dtype=np.float64)
        modeled_P = grav_result.trips.sum(axis=1)
        modeled_A = grav_result.trips.sum(axis=0)

        # ── TLFD comparison ───────────────────────────────────────────────
        mod_shares = compute_tlfd(grav_result.trips, skim, tlfd)
        obs_shares = tlfd["share"].to_numpy(dtype=np.float64)

        pct_diff = np.where(
            obs_shares > 0.0,
            (mod_shares - obs_shares) / obs_shares * 100.0,
            np.nan,
        )
        tlfd_table = pd.DataFrame({
            "bin_start": tlfd["bin_start"].to_numpy(),
            "bin_end": tlfd["bin_end"].to_numpy(),
            "observed_share": obs_shares,
            "modeled_share": mod_shares,
            "abs_diff": np.abs(mod_shares - obs_shares),
            "pct_diff": pct_diff,
        })

        # ── PA tables ─────────────────────────────────────────────────────
        pa_stats = _pa_stats_df(modeled_P, target_P, modeled_A, target_A)
        pa_zones = _pa_zones_df(zone_ids, target_P, modeled_P, target_A, modeled_A)

        pa_geo: dict[str, pd.DataFrame] = {}
        if geo_agg_cols:
            pa_geo = _pa_geo_dict(
                pa, geo_agg_cols, target_P, modeled_P, target_A, modeled_A
            )

        # ── OD statistics (optional) ──────────────────────────────────────
        od_stats: pd.DataFrame | None = None
        r2_log: float | None = None
        slope_log: float | None = None
        intercept_log: float | None = None
        od_pairs_df: pd.DataFrame | None = None
        od_geo_dict: dict[str, pd.DataFrame] = {}

        if target_od is not None:
            od_stats, r2_log, slope_log, intercept_log, od_pairs_df = _od_tables(
                grav_result.trips, zone_ids, target_od
            )

            # Geographic OD aggregations for residual heatmap plots
            if geo_agg_cols and od_pairs_df is not None:
                for geo_col in geo_agg_cols:
                    zone_geo = pa[geo_col]          # Series indexed by zone_id (1-based)
                    og_col = f"origin_{geo_col}"
                    dg_col = f"dest_{geo_col}"

                    geo_df = od_pairs_df.copy()
                    geo_df[og_col] = geo_df["origin"].map(zone_geo)
                    geo_df[dg_col] = geo_df["destination"].map(zone_geo)
                    geo_df = geo_df.dropna(subset=[og_col, dg_col])

                    agg = (
                        geo_df
                        .groupby([og_col, dg_col], sort=True)
                        [["observed_trips", "modeled_trips"]]
                        .sum()
                        .reset_index()
                    )
                    agg["rel_residual_pct"] = np.where(
                        agg["observed_trips"] > 0.0,
                        (agg["modeled_trips"] - agg["observed_trips"])
                        / agg["observed_trips"] * 100.0,
                        np.nan,
                    )
                    od_geo_dict[geo_col] = agg.pivot(
                        index=og_col, columns=dg_col, values="rel_residual_pct"
                    )

        runs.append(RunReport(
            run_name=run_cfg.name,
            short_name=run_cfg.short_name,
            status="OK",
            error_message=None,
            b_initial=float(run_cfg.gamma_b0),
            c_initial=float(run_cfg.gamma_c0),
            b_final=float(cal_result.b),
            c_final=float(cal_result.c),
            converged=cal_result.converged,
            n_iters=cal_result.n_iters,
            final_loss=float(cal_result.final_loss),
            tlfd_table=tlfd_table,
            pa_stats=pa_stats,
            pa_zones=pa_zones,
            pa_geo=pa_geo,
            od_stats=od_stats,
            r2_log=r2_log,
            slope_log=slope_log,
            intercept_log=intercept_log,
            loss_history=list(cal_result.loss_history),
            od_pairs=od_pairs_df,
            od_geo=od_geo_dict,
        ))

    return ReportData(runs=runs, has_od=has_od, has_geo=has_geo)
