"""
friction.py
-----------
Gamma friction factor computation.

The gamma function is:
    F(t) = t^b * exp(c * t)

where:
    t  = travel time in minutes (scalar or array)
    b  = power parameter (should be negative)
    c  = exponential decay parameter (should be negative)
    a  = scaling constant, fixed at 1.0 (cancels in gravity denominator)

Both b and c negative → F(t) is monotonically decreasing for t > 0,
which is required for a well-behaved gravity model.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict

from .config import TRUCK_TYPES, GAMMA_INITIAL_PARAMS


@dataclass
class GammaParams:
    """Gamma function parameters for one truck type."""
    truck_type: str
    b: float
    c: float

    def __post_init__(self):
        if self.b >= 0:
            raise ValueError(f"[{self.truck_type}] b must be negative, got {self.b}")
        if self.c >= 0:
            raise ValueError(f"[{self.truck_type}] c must be negative, got {self.c}")

    def __repr__(self):
        return f"GammaParams({self.truck_type}: b={self.b:.4f}, c={self.c:.4f})"


def gamma_ff(t: np.ndarray, b: float, c: float) -> np.ndarray:
    """
    Evaluate the gamma friction factor for a travel time matrix or vector.

    F(t) = t^b * exp(c * t)

    Parameters
    ----------
    t : array-like, travel times in minutes. Zeros/negatives are clipped to 0.1
        to avoid numerical issues with t^b when b < 0.
    b : power parameter (negative)
    c : exponential parameter (negative)

    Returns
    -------
    F : same shape as t, float64
    """
    t = np.asarray(t, dtype=np.float64)
    t_safe = np.maximum(t, 0.1)  # avoid 0^(negative) = inf
    return np.power(t_safe, b) * np.exp(c * t_safe)


def build_ff_matrix(
    skim: np.ndarray,
    b: float,
    c: float,
) -> np.ndarray:
    """
    Build a full (n_zones x n_zones) friction factor matrix from a skim.

    Parameters
    ----------
    skim : (n_zones, n_zones) blended travel time matrix
    b, c : gamma parameters

    Returns
    -------
    F : (n_zones, n_zones) friction factor matrix
    """
    return gamma_ff(skim, b, c)


def build_all_ff_matrices(
    skims: Dict[str, np.ndarray],
    params: Dict[str, GammaParams],
) -> Dict[str, np.ndarray]:
    """
    Build FF matrices for all truck types given calibrated parameters.

    Parameters
    ----------
    skims  : {truck_type: blended_skim_matrix}
    params : {truck_type: GammaParams}

    Returns
    -------
    ff_matrices : {truck_type: ff_matrix}
    """
    return {
        tt: build_ff_matrix(skims[tt], params[tt].b, params[tt].c)
        for tt in TRUCK_TYPES
    }


def initial_params() -> Dict[str, GammaParams]:
    """Return NCHRP 365-based starting parameters for all truck types."""
    return {
        tt: GammaParams(truck_type=tt, b=b0, c=c0)
        for tt, (b0, c0) in GAMMA_INITIAL_PARAMS.items()
    }


def evaluate_ff_curve(
    b: float,
    c: float,
    t_max: float = 120.0,
    n_points: int = 120,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Evaluate F(t) over a range of travel times — useful for plotting the curve.

    Returns
    -------
    t_values : (n_points,) array of travel times
    f_values : (n_points,) array of friction factors
    """
    t_values = np.linspace(1.0, t_max, n_points)
    f_values = gamma_ff(t_values, b, c)
    return t_values, f_values


def is_monotone_decreasing(b: float, c: float, t_max: float = 120.0) -> bool:
    """
    Check that F(t) is monotonically decreasing over [1, t_max].
    Both b < 0 and c < 0 guarantees this, but useful as a runtime check.
    """
    t = np.linspace(1.0, t_max, 500)
    f = gamma_ff(t, b, c)
    return bool(np.all(np.diff(f) <= 0))
