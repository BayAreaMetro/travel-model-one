"""Gamma parameter calibration via Nelder-Mead optimization.

The optimizer minimizes a weighted loss between the modeled TLFD and the
observed TLFD, with an optional average-trip-length (ATL) penalty term.

Loss function::

    loss = weighted_SSE + atl_penalty_weight * ATL_penalty

    weighted_SSE = sum_k [ observed_share_k * (modeled_share_k - observed_share_k)^2 ]
    ATL_penalty  = ((modeled_ATL - observed_ATL) / observed_ATL)^2

``weighted_SSE`` uses the observed bin shares as weights so that
well-populated short-trip bins matter more than the sparse long-distance tail.

``ATL_penalty`` penalizes mismatch in average trip length.  Set
``atl_penalty_weight = 0.0`` in ``model_settings`` to disable it entirely and
optimize on TLFD shape only.

Optimizer
---------
``scipy.optimize.minimize`` is called with the method declared in
``model_settings.optimizer_method`` (default ``"Nelder-Mead"``).  Bounds from
``gamma_b_bounds`` and ``gamma_c_bounds`` are passed directly to scipy.
scipy >= 1.7 enforces Nelder-Mead bounds via a soft-penalty transform; an
explicit large-loss return is also applied inside the objective as a safety net
for any method that ignores bounds.

The optimizer is deterministic given fixed starting values (``b0``, ``c0``).
No random seed is needed — identical YAML + inputs always produce identical
calibrated parameters.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import scipy.optimize

from src.models.trip_distribution.config import ModelSettings
from src.models.trip_distribution.friction import build_ff_matrix
from src.models.trip_distribution.gravity import run_gravity


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CalibrationResult:
    """Output of a single gamma parameter calibration.

    Parameters
    ----------
    b : float
        Calibrated gamma ``b`` (exponent) parameter.
    c : float
        Calibrated gamma ``c`` (exponential decay) parameter.
    converged : bool
        True if the optimizer reported successful convergence within the
        allotted function evaluations.
    n_iters : int
        Number of objective function evaluations performed by the optimizer.
        Reported as "evals" in log messages.
    final_loss : float
        Optimizer loss value at termination (lower is better).
    loss_history : list[float]
        Loss value sampled every 10 objective evaluations, for convergence
        plots.  Empty when calibration finishes in fewer than 10 evals.
    """

    b: float
    c: float
    converged: bool
    n_iters: int
    final_loss: float
    loss_history: list[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# TLFD computation
# ---------------------------------------------------------------------------

def compute_tlfd(
    trips: np.ndarray,
    skim: np.ndarray,
    tlfd_bins: pd.DataFrame,
) -> np.ndarray:
    """Compute the modeled trip length frequency distribution.

    Assigns every trip in ``trips`` to a time bin based on the corresponding
    travel time in ``skim``.  Returns the share of total trips falling in
    each bin.

    Bin assignment rules:

    - Bins 0 … N-2: ``bin_start ≤ time < bin_end`` (half-open, exclusive right)
    - Bin N-1 (last): ``time ≥ bin_start`` (open-ended, captures all long trips)

    The last-bin rule ensures that trips beyond the observed TLFD's right edge
    are always captured rather than silently dropped.

    Parameters
    ----------
    trips : np.ndarray
        Modeled trip matrix, shape (n_zones, n_zones), dtype float64.
        0-based zone indexing.  All values must be ≥ 0.
    skim : np.ndarray
        Travel time matrix, shape (n_zones, n_zones), dtype float64.
        Minutes.  Must have the same shape as ``trips``.
    tlfd_bins : pd.DataFrame
        Observed TLFD bin structure.  Must contain columns ``bin_start``
        (float, inclusive left edge) and ``bin_end`` (float, exclusive right
        edge), one row per bin, sorted ascending.  Typically the DataFrame
        returned by ``io.load_tlfd``.

    Returns
    -------
    np.ndarray
        Modeled share per bin, shape (n_bins,), dtype float64.  Sums to 1.0
        when ``trips.sum() > 0``.  Returns an all-zero array when the total
        trip count is zero.

    Notes
    -----
    Intrazonal trips (where ``skim[i, i] = 0``) land in the first bin if
    its ``bin_start = 0``.  In practice they contribute zero trips because
    :func:`friction.gamma_ff` returns 0 for ``t = 0``.
    """
    trips_flat = trips.ravel()
    times_flat = skim.ravel()

    total = float(trips_flat.sum())
    n_bins = len(tlfd_bins)
    mod_shares = np.zeros(n_bins, dtype=np.float64)

    if total <= 0.0:
        return mod_shares

    bin_starts = tlfd_bins["bin_start"].to_numpy(dtype=np.float64)
    bin_ends = tlfd_bins["bin_end"].to_numpy(dtype=np.float64)

    for k in range(n_bins):
        if k < n_bins - 1:
            # Half-open interval [bin_start, bin_end)
            mask = (times_flat >= bin_starts[k]) & (times_flat < bin_ends[k])
        else:
            # Last bin: open-ended to capture all remaining trips
            mask = times_flat >= bin_starts[k]

        mod_shares[k] = float(trips_flat[mask].sum()) / total

    return mod_shares


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------

def calibrate_trip_distribution(
    P: np.ndarray,
    A: np.ndarray,
    skim: np.ndarray,
    observed_tlfd: pd.DataFrame,
    b0: float,
    c0: float,
    model_settings: ModelSettings,
) -> CalibrationResult:
    """Calibrate gamma friction factor parameters for one truck type.

    Uses ``scipy.optimize.minimize`` (default method: Nelder-Mead) to find
    ``b`` and ``c`` that minimize the weighted TLFD loss plus ATL penalty.
    Each optimizer evaluation runs the full doubly-constrained gravity model
    internally.

    The loss function is::

        loss = weighted_SSE + atl_penalty_weight * ATL_penalty

    See the module docstring for the full formula.

    Parameters
    ----------
    P : np.ndarray
        Production vector, shape (n_zones,), dtype float64.
        Daily vehicle trips per origin zone.
    A : np.ndarray
        Attraction vector, shape (n_zones,), dtype float64.
        Daily vehicle trips per destination zone.
    skim : np.ndarray
        Travel time matrix, shape (n_zones, n_zones), dtype float64.
        Minutes.  Used both to build the friction matrix and to bin trips
        into TLFD bins during each evaluation.
    observed_tlfd : pd.DataFrame
        Validated TLFD with columns ``bin_start``, ``bin_end``, ``share``.
        Returned by :func:`io.load_tlfd`.
    b0 : float
        Initial value for the ``b`` parameter passed to the optimizer.
        Should be negative (e.g. ``-0.5``).
    c0 : float
        Initial value for the ``c`` parameter passed to the optimizer.
        Should be negative (e.g. ``-0.05``).
    model_settings : ModelSettings
        Algorithm settings drawn from the YAML ``model_settings`` block:

        - ``optimizer_method`` — scipy minimize method (default ``"Nelder-Mead"``)
        - ``optimizer_max_iters`` — max function evaluations
        - ``gamma_b_bounds`` — ``(lo, hi)`` search bounds for ``b``
        - ``gamma_c_bounds`` — ``(lo, hi)`` search bounds for ``c``
        - ``atl_penalty_weight`` — weight of ATL penalty term
        - ``gravity_max_iters`` — forwarded to :func:`gravity.run_gravity`
        - ``gravity_max_rmse`` — forwarded to :func:`gravity.run_gravity`

    Returns
    -------
    CalibrationResult
        Calibrated ``b``, ``c`` and optimizer diagnostics.

    Notes
    -----
    **Determinism:** Nelder-Mead is deterministic given fixed ``b0``, ``c0``.
    Identical YAML and input files always produce identical calibrated parameters.

    **Boundary hits:** if ``b`` or ``c`` converge at a bound, a WARNING is
    emitted by :func:`run._check_boundary_warnings` after this function returns.
    The calibration itself does not warn — it just returns the best parameters
    it found.

    **Gravity convergence inside the optimizer:** non-convergence of the inner
    gravity model during calibration is silently accepted — the optimizer sees
    the loss for the current (slightly off) trip table and adjusts accordingly.
    Only the *final* gravity run (in ``run.py``) emits a warning on
    non-convergence.
    """
    logger = logging.getLogger("trip_distribution")

    P = np.asarray(P, dtype=np.float64)
    A = np.asarray(A, dtype=np.float64)
    skim = np.asarray(skim, dtype=np.float64)

    # Pre-compute observed quantities used in every loss evaluation
    obs_shares = observed_tlfd["share"].to_numpy(dtype=np.float64)
    midpoints = (
        (observed_tlfd["bin_start"] + observed_tlfd["bin_end"]) / 2.0
    ).to_numpy(dtype=np.float64)
    obs_atl = float((midpoints * obs_shares).sum())

    b_lo, b_hi = model_settings.gamma_b_bounds
    c_lo, c_hi = model_settings.gamma_c_bounds
    atl_weight = float(model_settings.atl_penalty_weight)

    # Mutable state shared with the closure
    eval_count = [0]
    loss_history: list[float] = []

    # ── Objective function ────────────────────────────────────────────────────
    def _objective(params: np.ndarray) -> float:
        b = float(params[0])
        c = float(params[1])
        eval_count[0] += 1

        # Hard boundary guard: Nelder-Mead may explore outside bounds even
        # with scipy's soft-penalty transform; return a large loss to push it back.
        if not (b_lo <= b <= b_hi) or not (c_lo <= c <= c_hi):
            return 1e9

        # ── Inner gravity model ───────────────────────────────────────────
        F = build_ff_matrix(skim, b, c)
        grav = run_gravity(
            P, A, F,
            max_iters=model_settings.gravity_max_iters,
            max_rmse=model_settings.gravity_max_rmse,
        )

        # ── Modeled TLFD ──────────────────────────────────────────────────
        mod_shares = compute_tlfd(grav.trips, skim, observed_tlfd)

        # ── Loss components ───────────────────────────────────────────────
        # Weighted SSE: observed shares act as per-bin weights
        weighted_sse = float(np.sum(obs_shares * (mod_shares - obs_shares) ** 2))

        # ATL penalty: relative squared error of average trip length
        mod_atl = float((midpoints * mod_shares).sum())
        atl_penalty = ((mod_atl - obs_atl) / obs_atl) ** 2 if obs_atl > 0.0 else 0.0

        loss = weighted_sse + atl_weight * atl_penalty

        # DEBUG log + loss history every 10 evaluations
        n = eval_count[0]
        if n % 10 == 0:
            loss_history.append(loss)
            logger.debug(
                f"[trip_distribution]   Optimizer iter {n}: "
                f"loss={loss:.6f}, b={b:.4f}, c={c:.4f}"
            )

        return loss

    # ── Run the optimizer ─────────────────────────────────────────────────────
    bounds = [(b_lo, b_hi), (c_lo, c_hi)]

    opt_result = scipy.optimize.minimize(
        _objective,
        x0=np.array([b0, c0], dtype=np.float64),
        method=model_settings.optimizer_method,
        bounds=bounds,
        options={
            "maxiter": model_settings.optimizer_max_iters,
            "maxfev": model_settings.optimizer_max_iters,
            "xatol": 1e-6,
            "fatol": 1e-6,
        },
    )

    return CalibrationResult(
        b=float(opt_result.x[0]),
        c=float(opt_result.x[1]),
        converged=bool(opt_result.success),
        n_iters=int(opt_result.nfev),
        final_loss=float(opt_result.fun),
        loss_history=loss_history,
    )
