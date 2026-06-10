"""
gravity.py
----------
Doubly-constrained gravity model via iterative proportional fitting (IPF).

Given:
    P_i  : productions at origin zone i
    A_j  : attractions at destination zone j
    F_ij : friction factor matrix
    K_ij : optional K-factor matrix (defaults to all ones)

The model finds T_ij such that:
    sum_j T_ij = P_i  for all i   (row constraint)
    sum_i T_ij = A_j  for all j   (column constraint)

using the formulation:
    T_ij = Ai * Pi * Bj * Aj * Fij * Kij

where Ai and Bj are balancing factors updated each iteration.

Convergence criterion: RMSE between modeled column sums and target A.
"""

import numpy as np
from typing import Optional, Dict
from dataclasses import dataclass

from .config import GRAVITY_MAX_ITERS, GRAVITY_MAX_RMSE, TRUCK_TYPES
from .friction import GammaParams, build_ff_matrix


@dataclass
class GravityResult:
    """Output of one gravity model run."""
    truck_type: str
    trips: np.ndarray          # (n_zones, n_zones) trip matrix
    n_iterations: int
    final_rmse: float
    converged: bool

    @property
    def total_trips(self) -> float:
        return float(self.trips.sum())

    @property
    def avg_trip_length(self) -> float:
        """Requires skim — computed externally in validation."""
        raise NotImplementedError("Use validation.avg_trip_length(result, skim)")


def run_gravity(
    P: np.ndarray,
    A: np.ndarray,
    F: np.ndarray,
    K: Optional[np.ndarray] = None,
    max_iters: int = GRAVITY_MAX_ITERS,
    max_rmse: float = GRAVITY_MAX_RMSE,
    truck_type: str = "",
) -> GravityResult:
    """
    Run a doubly-constrained gravity model.

    Parameters
    ----------
    P        : (n,) productions
    A        : (n,) attractions
    F        : (n,n) friction factor matrix
    K        : (n,n) K-factor matrix, optional. Defaults to ones.
    max_iters: maximum number of IPF iterations
    max_rmse : convergence threshold (RMSE of column sums vs target A)
    truck_type: label for logging only

    Returns
    -------
    GravityResult
    """
    n = len(P)
    assert F.shape == (n, n), f"F shape {F.shape} doesn't match n_zones={n}"
    assert len(A) == n, f"A length {len(A)} doesn't match n_zones={n}"

    if K is None:
        K = np.ones((n, n), dtype=np.float64)
    else:
        assert K.shape == (n, n), f"K shape {K.shape} doesn't match n_zones={n}"

    # Base matrix: Aj * Fij * Kij  — fixed throughout iterations
    # Shape: (n, n),  base[i,j] = A[j] * F[i,j] * K[i,j]
    base = A[np.newaxis, :] * F * K   # broadcast A across rows

    # Initialize destination balancing factors
    B_j = np.ones(n, dtype=np.float64)

    final_rmse = np.inf
    n_iter = 0

    for iteration in range(max_iters):
        # ── Step 1: solve for A_i (origin balancing factors) ──────────────────
        # A_i = P_i / sum_j(B_j * base[i,j])
        row_denom = (B_j[np.newaxis, :] * base).sum(axis=1)  # (n,)
        # Avoid division by zero for zones with zero production denominator
        A_i = np.where(row_denom > 1e-10, P / row_denom, 0.0)

        # ── Step 2: compute T_ij ───────────────────────────────────────────────
        # T_ij = A_i[i] * P[i] * B_j[j] * base[i,j]
        T = (A_i * P)[:, np.newaxis] * B_j[np.newaxis, :] * base

        # ── Step 3: solve for B_j (destination balancing factors) ─────────────
        # B_j = A_j / sum_i(A_i * P_i * base[i,j])
        col_sums = T.sum(axis=0)  # (n,)  current attraction totals
        B_j = np.where(col_sums > 1e-10, A / col_sums * B_j, 0.0)

        # ── Step 4: recompute T with updated B_j ──────────────────────────────
        T = (A_i * P)[:, np.newaxis] * B_j[np.newaxis, :] * base

        # ── Convergence check ─────────────────────────────────────────────────
        col_sums_final = T.sum(axis=0)
        rmse = float(np.sqrt(np.mean((col_sums_final - A) ** 2)))
        n_iter = iteration + 1

        if rmse < max_rmse:
            final_rmse = rmse
            break

        final_rmse = rmse

    converged = final_rmse < max_rmse
    label = f"[{truck_type}]" if truck_type else ""

    if converged:
        print(f"  Gravity {label} converged in {n_iter} iterations, "
              f"RMSE={final_rmse:.2f}")
    else:
        print(f"  WARNING: Gravity {label} did NOT converge after {n_iter} "
              f"iterations. Final RMSE={final_rmse:.2f} > threshold={max_rmse}")

    return GravityResult(
        truck_type=truck_type,
        trips=T,
        n_iterations=n_iter,
        final_rmse=final_rmse,
        converged=converged,
    )


def run_all_gravity(
    pa_data: Dict[str, Dict[str, np.ndarray]],
    skims: Dict[str, np.ndarray],
    gamma_params: Dict[str, "GammaParams"],
    k_factors: Optional[Dict[str, np.ndarray]] = None,
) -> Dict[str, GravityResult]:
    """
    Run gravity model for all truck types.

    Parameters
    ----------
    pa_data      : {truck_type: {"P": ..., "A": ...}}
    skims        : {truck_type: blended_skim_matrix}
    gamma_params : {truck_type: GammaParams}
    k_factors    : {truck_type: K_matrix}, optional

    Returns
    -------
    results : {truck_type: GravityResult}
    """
    results = {}
    for tt in TRUCK_TYPES:
        print(f"\nRunning gravity model: {tt}")
        P = pa_data[tt]["P"]
        A = pa_data[tt]["A"]
        F = build_ff_matrix(skims[tt], gamma_params[tt].b, gamma_params[tt].c)
        K = k_factors[tt] if k_factors and tt in k_factors else None

        results[tt] = run_gravity(P, A, F, K=K, truck_type=tt)

    return results
