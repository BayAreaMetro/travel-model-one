"""Doubly-constrained gravity model using iterative proportional fitting (IPF).

Algorithm
---------
The gravity model distributes productions P_i to attractions A_j using::

    T_ij = a_i * P_i * b_j * A_j * F_ij * K_ij

where ``a_i`` and ``b_j`` are internal balancing factors (not user-visible)
that are updated each IPF iteration.

To avoid tracking a_i and b_j as separate arrays the implementation uses
"effective" row and column factors that fold in the P and A vectors::

    row_factors[i] = a_i * P_i   →  T.sum(axis=1)[i] == P[i]
    col_factors[j] = b_j * A_j   →  T.sum(axis=0)[j] == A[j]

Each iteration alternates:
  1. Row step  → ``row_factors = P / (FK @ col_factors)``
                 guarantees row sums = P (exact, by construction)
  2. Convergence check on column RMSE before the column step
  3. Column step → ``col_factors = A / (FK.T @ row_factors)``
                   resets column sums = A for the next row step

Convergence is declared when the RMSE of column sums vs A (checked after
the row step but before the column step) is ≤ ``max_rmse``.  At that point
the returned matrix already has exact row sums = P and column sums within
``max_rmse`` of A.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class GravityResult:
    """Output of a single gravity model run.

    Parameters
    ----------
    trips : np.ndarray
        Modeled zone-to-zone trip matrix, shape (n_zones, n_zones), dtype float64.
        0-based zone indexing. Row sums = P (exact); column sums ≈ A (within
        ``final_rmse`` vehicle trips of the target when ``converged`` is True).
    converged : bool
        True if IPF converged within ``max_iters`` and ``max_rmse``.
    n_iters : int
        Number of full IPF iterations (row step + column step) completed.
        The final row step that triggered convergence is counted.
    final_rmse : float
        RMSE of column sums vs target attractions at termination, in vehicle trips.
        Should be ≤ ``max_rmse`` when ``converged`` is True.
    """

    trips: np.ndarray
    converged: bool
    n_iters: int
    final_rmse: float


def run_gravity(
    P: np.ndarray,
    A: np.ndarray,
    F: np.ndarray,
    K: np.ndarray | None = None,
    max_iters: int = 99,
    max_rmse: float = 10.0,
    truck_type: str = "",
) -> GravityResult:
    """Apply the doubly-constrained gravity model via IPF.

    Distributes productions ``P`` at origin zones to attractions ``A`` at
    destination zones using friction factors ``F`` (and optional K-factors).
    Iterates until column sums equal ``A`` within ``max_rmse`` vehicle trips,
    or ``max_iters`` is reached.

    Parameters
    ----------
    P : np.ndarray
        Production vector, shape (n_zones,), dtype float64. Daily vehicle trips.
        Row sums of the returned trip table equal P exactly.
    A : np.ndarray
        Attraction vector, shape (n_zones,), dtype float64. Daily vehicle trips.
        Column sums of the returned trip table converge toward A.
    F : np.ndarray
        Friction factor matrix, shape (n_zones, n_zones), dtype float64.
        Typically built by ``friction.build_ff_matrix``.  Zero cells suppress
        trips between the corresponding zone pair (e.g. intrazonal cells).
    K : np.ndarray or None, optional
        K-factor adjustment matrix, shape (n_zones, n_zones), dtype float64.
        Applied as element-wise multiplier on ``F``.  ``None`` (default)
        is equivalent to a matrix of ones — no K-factor adjustment.
    max_iters : int, optional
        Maximum number of IPF iterations.  Default 99.
    max_rmse : float, optional
        Convergence threshold — RMSE of column sums vs ``A`` in vehicle trips.
        Default 10.0.
    truck_type : str, optional
        Run name included in ``ValueError`` messages for easier debugging.
        Not used in the computation.  Default empty string.

    Returns
    -------
    GravityResult
        Modeled trip matrix and convergence diagnostics.  See :class:`GravityResult`.

    Raises
    ------
    ValueError
        If any input shape is inconsistent: ``A`` or ``F`` don't match ``len(P)``,
        ``F`` is not square, or ``K`` (when provided) has a different shape from ``F``.

    Notes
    -----
    **Balanced vs unbalanced P/A:** when ``P.sum() != A.sum()`` (unbalanced),
    IPF will still run but may not converge within ``max_iters``.  A warning
    is emitted upstream (in ``run.py``) when the imbalance exceeds 5%.  The
    returned matrix has exact row sums = P regardless of convergence.

    **Zero-friction cells:** zones connected only through zero-friction cells
    (e.g. isolated zones with no skim coverage) will send or receive zero
    trips.  Their balancing factors are set to 0 to avoid division by zero.

    **K-factors:** reserved for a future phase. Pass ``None`` (default) to
    skip K-factor adjustment entirely.

    Examples
    --------
    Spec test — uniform friction, balanced P/A:

    >>> import numpy as np
    >>> n = 5
    >>> P = np.array([100, 80, 60, 90, 70], dtype=float)
    >>> A = np.array([80, 70, 90, 100, 60], dtype=float)
    >>> F = np.ones((n, n))
    >>> result = run_gravity(P, A, F)
    >>> assert result.converged
    >>> assert np.allclose(result.trips.sum(axis=1), P, atol=1.0), "Row sums must equal P"
    >>> assert np.allclose(result.trips.sum(axis=0), A, atol=1.0), "Col sums must equal A"
    """
    # ── Input coercion ────────────────────────────────────────────────────────
    P = np.asarray(P, dtype=np.float64)
    A = np.asarray(A, dtype=np.float64)
    F = np.asarray(F, dtype=np.float64)

    n = len(P)
    tag = f" [{truck_type}]" if truck_type else ""

    # ── Shape validation ──────────────────────────────────────────────────────
    if P.ndim != 1:
        raise ValueError(f"run_gravity{tag}: P must be 1-D; got shape {P.shape}.")
    if A.shape != (n,):
        raise ValueError(
            f"run_gravity{tag}: A shape {A.shape} must match len(P)={n}."
        )
    if F.shape != (n, n):
        raise ValueError(
            f"run_gravity{tag}: F shape {F.shape} must be ({n}, {n})."
        )

    # ── Combined friction × K matrix ──────────────────────────────────────────
    if K is not None:
        K = np.asarray(K, dtype=np.float64)
        if K.shape != (n, n):
            raise ValueError(
                f"run_gravity{tag}: K shape {K.shape} must be ({n}, {n})."
            )
        FK = F * K
    else:
        FK = F

    # ── IPF ───────────────────────────────────────────────────────────────────
    # "Effective" column factors absorb the b_j * A_j product.
    # Initialise with b_j = 1 → col_factors = A.
    col_factors = A.copy()

    T = np.zeros((n, n), dtype=np.float64)
    converged = False
    final_rmse = np.inf
    n_iters = 0

    for iteration in range(max_iters):

        # ── Row step ──────────────────────────────────────────────────────
        # row_factors[i] = P_i / sum_j( FK_ij * col_factors_j )
        # Guarantees: T.sum(axis=1)[i] = P[i]  (exact when denom > 0)
        #
        # errstate: with extreme friction parameters (explored during calibration),
        # FK values can span ~18 orders of magnitude.  Zones connected only through
        # long-distance arcs get near-zero denominators → large balancing factors →
        # potential overflow in the matmul or divide.  The np.where and np.isfinite
        # guards below handle these cases correctly; errstate silences the expected
        # intermediate warnings that numpy would otherwise emit.
        with np.errstate(divide='ignore', over='ignore', invalid='ignore'):
            denom_row = FK @ col_factors          # shape (n,)
            _raw_row = np.where(denom_row > 0.0, P / denom_row, 0.0)
        row_factors = np.where(np.isfinite(_raw_row), _raw_row, 0.0)

        # Trip matrix after row step
        T = row_factors[:, np.newaxis] * FK * col_factors[np.newaxis, :]

        # ── Convergence check ─────────────────────────────────────────────
        # Check column sums (the unsatisfied constraint after the row step)
        col_sums = T.sum(axis=0)
        rmse = float(np.sqrt(np.mean((col_sums - A) ** 2)))
        final_rmse = rmse
        n_iters = iteration + 1

        if rmse <= max_rmse:
            converged = True
            break

        # ── Column step ───────────────────────────────────────────────────
        # col_factors[j] = A_j / sum_i( FK_ij * row_factors_i )
        # Guarantees: T.sum(axis=0)[j] = A[j] for next iteration's row step
        with np.errstate(divide='ignore', over='ignore', invalid='ignore'):
            denom_col = FK.T @ row_factors        # shape (n,)
            _raw_col = np.where(denom_col > 0.0, A / denom_col, 0.0)
        # isfinite guard: if A / tiny_denom overflowed to inf, zero it out so
        # the value doesn't propagate into the next iteration's matmul.
        col_factors = np.where(np.isfinite(_raw_col), _raw_col, 0.0)

    return GravityResult(
        trips=T,
        converged=converged,
        n_iters=n_iters,
        final_rmse=final_rmse,
    )
