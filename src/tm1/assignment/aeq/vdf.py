"""Cube Travel Model One volume-delay function, re-implemented for AequilibraE.

MTC's Cube assignment (``SpeedFlowCurve.block``) uses a *facility-type-segmented* VDF:

- Freeways (FT 1, 2, 8, 9): a BPR variant
  ``TC = T0 * (1 + 0.20 * ((V/C) / 0.75) ** 6)``  (= BPR with alpha 1.124, beta 6).
- Arterials etc. (FT 3, 4, 5, 7, 10): the Akcelik time-dependent curve
  ``TC = 60 * (DIST/FFS + 0.25 * ((x-1) + sqrt((x-1)^2 + 16*Ja*x*DIST^2)))``, ``x = V/C``,
  where ``Ja = (1/CritSpd - 1/FFS) ** 2`` (``CritSpd`` from ``FreeFlowSpeed.block`` by
  capacity class, ``capclass = areatype*10 + facilitytype``).
- Connectors/dummy (FT 6): fixed time ``T0``.

Validated against the reference loaded network (2023_TM161_IPA_35): VDF(V/C) reproduces
Cube's congested time with correlation 0.9925 over 22,551 congestable links — freeways
bit-exact (~0.0015 min), arterials within ~0.03 min on average.
"""

import numpy as np

from tm1.assignment.aeq.params import Vdf


def capclass(areatype: np.ndarray, facilitytype: np.ndarray, vdf: Vdf) -> np.ndarray:
    """MTC capacity class = areatype*10 + facilitytype (capped at the special code)."""
    return np.minimum(areatype * 10 + facilitytype, vdf.max_capclass).astype(int)


def crit_speed(capclass_arr: np.ndarray, vdf: Vdf) -> np.ndarray:
    """Critical speed (mph) per capacity class (FreeFlowSpeed.block via aeq_params)."""
    return np.array([vdf.critspd_by_capclass.get(int(c), vdf.default_critspd)
                     for c in capclass_arr], dtype=float)


def akcelik_ja(critspd: np.ndarray, ffs: np.ndarray) -> np.ndarray:
    """Akcelik delay parameter ``Ja = (1/CritSpd - 1/FFS)^2`` (matches Cube's Ja10000/10000)."""
    return (1.0 / critspd - 1.0 / np.maximum(ffs, 1e-6)) ** 2


def congested_time(
    vc: np.ndarray,
    facilitytype: np.ndarray,
    t0: np.ndarray,
    distance: np.ndarray,
    ffs: np.ndarray,
    critspd: np.ndarray,
    vdf: Vdf,
) -> np.ndarray:
    """Cube congested link time (minutes) as a function of V/C, per facility type.

    Parameters are per-link arrays; ``t0`` is the free-flow time (minutes), ``ffs`` the
    free-flow speed (mph), ``critspd`` the critical speed for the link's capacity
    class; curve constants come from ``vdf`` (aeq_params.yaml).
    """
    x = np.asarray(vc, dtype=float)
    ft = np.asarray(facilitytype)
    ja = akcelik_ja(critspd, ffs)
    akcelik = 60.0 * (
        distance / np.maximum(ffs, 1e-6)
        + vdf.akcelik_quarter * ((x - 1) + np.sqrt((x - 1) ** 2
                                                   + vdf.akcelik_j_scale * ja * x
                                                   * distance ** 2))
    )
    bpr = t0 * (1 + vdf.bpr_coef * (x / vdf.bpr_vc_norm) ** vdf.bpr_power)
    return np.where(np.isin(ft, vdf.freeway_ft), bpr,
                    np.where(np.isin(ft, vdf.fixed_ft), t0, akcelik))
