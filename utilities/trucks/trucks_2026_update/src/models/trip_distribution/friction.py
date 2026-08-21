"""Gamma friction factor functions for the doubly-constrained gravity model.

The gamma function family used here is::

    F(t) = t^b * exp(c * t)

where both ``b`` and ``c`` are negative, giving a monotonically decreasing
friction factor.  The parameter ``a`` (overall scale) is fixed at 1.0 because
it cancels in the doubly-constrained denominator and has no effect on the
calibrated trip table.

Zero-time cells (intrazonal impedances of 0) are assigned F = 0.0.  This
suppresses intrazonal trips, consistent with the convention used in the
observed TLFD data which also excludes intrazonal movements.

Calibration note
----------------
``b`` and ``c`` are calibrated by ``calibration.calibrate_trip_distribution``
using Nelder-Mead optimisation.  Typical search bounds:
  b ∈ [−3.0, −0.01]
  c ∈ [−0.5, −0.001]
"""

from __future__ import annotations

import numpy as np


def gamma_ff(t: np.ndarray, b: float, c: float) -> np.ndarray:
    """Compute the gamma friction factor F(t) = t^b * exp(c * t).

    Both ``b`` and ``c`` must be negative so that F(t) is monotonically
    decreasing — longer trips receive lower friction weights.
    The ``a`` coefficient is fixed at 1.0 (it cancels in the gravity denominator).

    Zero-time cells receive F = 0.0.  This suppresses intrazonal trips and
    avoids ``0 ** b = inf`` when ``b`` is negative.

    Parameters
    ----------
    t : np.ndarray
        Travel time values in minutes.  Scalar or any shape.  Values of 0
        are treated as intrazonal and receive F = 0.0.
    b : float
        Exponent parameter.  Must be negative.
    c : float
        Exponential decay parameter.  Must be negative.

    Returns
    -------
    np.ndarray
        Friction factor values, same shape as ``t``.  dtype float64.
        All values ≥ 0.
    """
    t = np.asarray(t, dtype=np.float64)

    # Replace 0s with a safe placeholder before computing to avoid
    # 0**negative = inf.  The second np.where zeroes those cells back out.
    safe_t = np.where(t > 0.0, t, 1.0)
    ff = safe_t**b * np.exp(c * safe_t)

    return np.where(t > 0.0, ff, 0.0)


def build_ff_matrix(skim: np.ndarray, b: float, c: float) -> np.ndarray:
    """Build a full friction factor matrix from a travel time skim.

    Applies :func:`gamma_ff` element-wise to the entire skim array.
    Intrazonal cells (zero travel time) receive F = 0.0, which effectively
    removes them from the gravity model denominator.

    Parameters
    ----------
    skim : np.ndarray
        Travel time matrix, shape (n_zones, n_zones), dtype float64.
        Values are in minutes, 0-based zone indexing.
    b : float
        Gamma exponent parameter.  Must be negative.
    c : float
        Gamma exponential decay parameter.  Must be negative.

    Returns
    -------
    np.ndarray
        Friction factor matrix, shape (n_zones, n_zones), dtype float64.

    Raises
    ------
    ValueError
        If ``skim`` is not a 2-D square array.
    """
    skim = np.asarray(skim, dtype=np.float64)

    if skim.ndim != 2 or skim.shape[0] != skim.shape[1]:
        raise ValueError(
            f"skim must be a square 2-D array; got shape {skim.shape}."
        )

    return gamma_ff(skim, b, c)
