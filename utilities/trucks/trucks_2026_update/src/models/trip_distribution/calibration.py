"""
calibration.py
--------------
Estimates gamma parameters (b, c) per truck type by minimizing the difference
between the modeled TLFD and the observed TLFD.

Algorithm
---------
For each truck type:
1. Fix P, A, skim (from inputs)
2. Run gravity model with F(t) = t^b * exp(c*t)
3. Compute modeled TLFD from output T_ij
4. Compute loss = weighted SSE between modeled and observed TLFD
5. Use Nelder-Mead to find (b, c) that minimizes loss
6. Report final parameters + diagnostics

The objective also tracks average trip length as a secondary diagnostic.
"""

import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from scipy.optimize import minimize, OptimizeResult

from .config import (
    TRUCK_TYPES,
    GAMMA_INITIAL_PARAMS,
    GAMMA_BOUNDS,
    TLFD_BINS,
)
from .friction import GammaParams, gamma_ff
from .gravity import run_gravity


# ── TLFD utilities ─────────────────────────────────────────────────────────────

def compute_tlfd(
    T_ij: np.ndarray,
    t_ij: np.ndarray,
    bins: np.ndarray = TLFD_BINS,
) -> np.ndarray:
    """
    Compute the trip length frequency distribution from a trip matrix and skim.

    Parameters
    ----------
    T_ij : (n, n) trip matrix
    t_ij : (n, n) travel time matrix
    bins : bin edges in minutes

    Returns
    -------
    shares : (len(bins)-1,) array of trip shares per bin, sums to 1
    """
    n_bins = len(bins) - 1
    tlfd = np.zeros(n_bins, dtype=np.float64)

    for k in range(n_bins):
        mask = (t_ij >= bins[k]) & (t_ij < bins[k + 1])
        tlfd[k] = T_ij[mask].sum()

    total = tlfd.sum()
    if total > 0:
        tlfd /= total
    return tlfd


def avg_trip_length(T_ij: np.ndarray, t_ij: np.ndarray) -> float:
    """Weighted average travel time across all OD pairs."""
    total = T_ij.sum()
    if total < 1e-9:
        return 0.0
    return float((T_ij * t_ij).sum() / total)


def tlfd_avg_from_shares(shares: np.ndarray, bins: np.ndarray = TLFD_BINS) -> float:
    """Compute approximate mean travel time from TLFD shares and bin midpoints."""
    bin_mids = 0.5 * (bins[:-1] + bins[1:])
    return float(np.dot(shares, bin_mids))


# ── Calibration result ─────────────────────────────────────────────────────────

@dataclass
class CalibrationResult:
    """Stores calibration outcome for one truck type."""
    truck_type: str
    b: float
    c: float
    converged: bool
    n_function_evals: int
    final_loss: float
    observed_avg_tl: float           # average trip length from observed TLFD
    modeled_avg_tl: float            # average trip length from calibrated model
    observed_tlfd: np.ndarray
    modeled_tlfd: np.ndarray
    loss_history: List[float] = field(default_factory=list)

    @property
    def params(self) -> GammaParams:
        return GammaParams(truck_type=self.truck_type, b=self.b, c=self.c)

    def summary(self) -> str:
        status = "✓ converged" if self.converged else "✗ did not converge"
        return (
            f"{self.truck_type} [{status}]\n"
            f"  b={self.b:.4f}, c={self.c:.4f}\n"
            f"  Avg trip length: observed={self.observed_avg_tl:.1f} min, "
            f"modeled={self.modeled_avg_tl:.1f} min\n"
            f"  Final loss={self.final_loss:.6f}, "
            f"fn evals={self.n_function_evals}"
        )


# ── Objective function ─────────────────────────────────────────────────────────

def _make_objective(
    P: np.ndarray,
    A: np.ndarray,
    skim: np.ndarray,
    observed_tlfd: np.ndarray,
    loss_history: List[float],
    verbose: bool = False,
) -> callable:
    """
    Build the objective function for one truck type.

    Loss = weighted SSE between modeled and observed TLFD
         + penalty term for average trip length mismatch

    The observed shares are used as weights so that well-populated
    time bins matter more than the sparse tail.
    """
    obs_avg_tl = tlfd_avg_from_shares(observed_tlfd)

    def objective(params: np.ndarray) -> float:
        b, c = params

        # Hard constraints: b and c must be negative
        if b >= 0 or c >= 0:
            return 1e10

        # Compute friction factor matrix
        F = gamma_ff(skim, b, c)

        # Run gravity model (tight tolerance during calibration is overkill;
        # use a looser rmse to keep calibration fast)
        result = run_gravity(P, A, F, max_iters=50, max_rmse=50.0)
        T_mod = result.trips

        # Compute modeled TLFD
        mod_tlfd = compute_tlfd(T_mod, skim)

        # Primary loss: observed-weighted SSE on TLFD shares
        weights = observed_tlfd  # upweight bins with more trips
        tlfd_loss = float(np.sum(weights * (mod_tlfd - observed_tlfd) ** 2))

        # Secondary penalty: average trip length mismatch
        mod_avg_tl = avg_trip_length(T_mod, skim)
        atl_penalty = 0.1 * ((mod_avg_tl - obs_avg_tl) / (obs_avg_tl + 1e-9)) ** 2

        loss = tlfd_loss + atl_penalty

        loss_history.append(loss)
        if verbose and len(loss_history) % 10 == 0:
            print(f"    iter {len(loss_history):3d}: b={b:.4f}, c={c:.4f}, "
                  f"loss={loss:.6f}, avg_tl={mod_avg_tl:.1f}")

        return loss

    return objective


# ── Single truck type calibration ─────────────────────────────────────────────

def calibrate_one(
    truck_type: str,
    P: np.ndarray,
    A: np.ndarray,
    skim: np.ndarray,
    observed_tlfd: np.ndarray,
    b0: Optional[float] = None,
    c0: Optional[float] = None,
    verbose: bool = True,
) -> CalibrationResult:
    """
    Calibrate gamma parameters for one truck type.

    Parameters
    ----------
    truck_type    : label
    P, A          : productions and attractions (n,)
    skim          : blended travel time matrix (n, n)
    observed_tlfd : target TLFD shares (n_bins,)
    b0, c0        : initial parameter values (defaults to NCHRP 365 values)
    verbose       : print progress every 10 function evaluations

    Returns
    -------
    CalibrationResult
    """
    if b0 is None or c0 is None:
        b0_default, c0_default = GAMMA_INITIAL_PARAMS[truck_type]
        b0 = b0 if b0 is not None else b0_default
        c0 = c0 if c0 is not None else c0_default

    print(f"\nCalibrating {truck_type}: starting at b={b0}, c={c0}")
    t_start = time.time()

    loss_history: List[float] = []
    objective = _make_objective(P, A, skim, observed_tlfd, loss_history, verbose)

    opt_result: OptimizeResult = minimize(
        objective,
        x0=np.array([b0, c0]),
        method="Nelder-Mead",
        options={
            "xatol": 1e-4,
            "fatol": 1e-6,
            "maxiter": 500,
            "adaptive": True,   # adaptive Nelder-Mead, better for 2D
        },
    )

    b_opt, c_opt = opt_result.x
    elapsed = time.time() - t_start

    # Final evaluation with tight gravity convergence
    F_final = gamma_ff(skim, b_opt, c_opt)
    final_result = run_gravity(P, A, F_final, truck_type=truck_type)
    T_final = final_result.trips

    mod_tlfd = compute_tlfd(T_final, skim)
    mod_avg_tl = avg_trip_length(T_final, skim)
    obs_avg_tl = tlfd_avg_from_shares(observed_tlfd)

    result = CalibrationResult(
        truck_type=truck_type,
        b=float(b_opt),
        c=float(c_opt),
        converged=bool(opt_result.success),
        n_function_evals=int(opt_result.nfev),
        final_loss=float(opt_result.fun),
        observed_avg_tl=obs_avg_tl,
        modeled_avg_tl=mod_avg_tl,
        observed_tlfd=observed_tlfd,
        modeled_tlfd=mod_tlfd,
        loss_history=loss_history,
    )

    print(f"  Done in {elapsed:.1f}s")
    print(result.summary())

    return result


# ── All truck types ────────────────────────────────────────────────────────────

def calibrate_all(
    pa_data: Dict[str, Dict[str, np.ndarray]],
    skims: Dict[str, np.ndarray],
    observed_tlfds: Dict[str, np.ndarray],
    verbose: bool = True,
) -> Dict[str, CalibrationResult]:
    """
    Calibrate gamma parameters for all truck types.

    Parameters
    ----------
    pa_data        : {truck_type: {"P": ..., "A": ...}}
    skims          : {truck_type: blended_skim_matrix}
    observed_tlfds : {truck_type: observed_tlfd_shares}
    verbose        : print progress during optimization

    Returns
    -------
    results : {truck_type: CalibrationResult}
    """
    results = {}
    for tt in TRUCK_TYPES:
        results[tt] = calibrate_one(
            truck_type=tt,
            P=pa_data[tt]["P"],
            A=pa_data[tt]["A"],
            skim=skims[tt],
            observed_tlfd=observed_tlfds[tt],
            verbose=verbose,
        )

    print("\n" + "=" * 60)
    print("CALIBRATION SUMMARY")
    print("=" * 60)
    for tt, r in results.items():
        print(r.summary())

    return results


def params_from_calibration(
    calibration_results: Dict[str, CalibrationResult],
) -> Dict[str, GammaParams]:
    """Extract GammaParams dict from calibration results — pass to gravity model."""
    return {tt: r.params for tt, r in calibration_results.items()}
