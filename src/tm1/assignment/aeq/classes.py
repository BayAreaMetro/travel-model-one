"""Build Cube's 13 highway assignment classes for AequilibraE.

Replicates ``HwyAssign.job``'s ``pathload`` class definitions: the per-class
generalized-cost parameters (value of time, operating-cost field, PCE), the toll
paid (SR tolls divided by the occupancy cost-share), and the link-exclusion groups
(HOV / HOV3+ / no-big-truck / value-toll-eligibility) that Cube enforces via
``excludegrp``.

The 13 classes, in Cube's vehicle order:

    da sr2 sr3 sml lrg datoll sr2toll sr3toll smltoll lrgtoll daav s2av s3av

``build_vehicle_classes`` takes the assembled 13 demand tables plus the Cube link
export (``net2csv_avgload5period`` columns, incl. per-period ``toll{P}_*``,
``use{P}`` and ``tollclass``) and returns the :class:`VehicleClass` list ready for
:func:`tm1.assignment.aeq.highway.equilibrium_assignment`.
"""

import numpy as np
import pandas as pd

from tm1.assignment.aeq.highway import VehicleClass
from tm1.assignment.params import Highway

# The 13 classes in Cube's canonical order (structural: demand/skim/highway contract).
CLASS_ORDER = (
    "da", "sr2", "sr3", "sml", "lrg",
    "datoll", "sr2toll", "sr3toll", "smltoll", "lrgtoll",
    "daav", "s2av", "s3av",
)


def _class_spec(hw: Highway) -> dict:
    """Per-class (value-of-time, operating-cost field, toll column, PCE, toll share).

    toll_col is the suffix in ``toll{PERIOD}_{col}``; share divides the toll (SR
    occupancy cost share).  Scalars come from params.yaml (hwyParam.block).
    """
    return {
        "da":      (hw.vot,       "autoopc", "da",  1.0,          1.0),
        "sr2":     (hw.vot,       "autoopc", "s2",  1.0,          hw.sr2_toll_share),
        "sr3":     (hw.vot,       "autoopc", "s3",  1.0,          hw.sr3_toll_share),
        "sml":     (hw.truck_vot, "smtropc", "sml", 1.0,          1.0),
        "lrg":     (hw.truck_vot, "lrtropc", "lrg", hw.truck_pce, 1.0),
        "datoll":  (hw.vot,       "autoopc", "da",  1.0,          1.0),
        "sr2toll": (hw.vot,       "autoopc", "s2",  1.0,          hw.sr2_toll_share),
        "sr3toll": (hw.vot,       "autoopc", "s3",  1.0,          hw.sr3_toll_share),
        "smltoll": (hw.truck_vot, "smtropc", "sml", 1.0,          1.0),
        "lrgtoll": (hw.truck_vot, "lrtropc", "lrg", hw.truck_pce, 1.0),
        "daav":    (hw.vot,       "autoopc", "da",  None,         1.0),  # PCE from av_pce
        "s2av":    (hw.vot,       "autoopc", "s2",  None,         hw.sr2_toll_share),
        "s3av":    (hw.vot,       "autoopc", "s3",  None,         hw.sr3_toll_share),
    }


def build_vehicle_classes(
    demand: dict[str, np.ndarray],
    links: pd.DataFrame,
    period: str,
    hw: Highway,
    *,
    av_pce: float = 1.0,
) -> list[VehicleClass]:
    """Construct the 13 :class:`VehicleClass` objects for one period.

    Parameters
    ----------
    demand
        The 13 assembled vehicle-trip tables keyed by :data:`CLASS_ORDER` name.
    links
        Cube link export; must have ``toll{P}_{da,s2,s3,sml,lrg}``, ``use{P}``
        and ``tollclass`` for the given ``period``.
    period
        Two-letter period (``EA``/``AM``/``MD``/``PM``/``EV``).
    hw
        :class:`tm1.assignment.params.Highway` policy (params.yaml).
    av_pce
        Passenger-car-equivalent for the AV classes (1.0 in the no-AV base).
    """
    per = period.upper()
    toll = {c: links[f"toll{per}_{c}"].to_numpy(float) for c in ("da", "s2", "s3", "sml", "lrg")}
    use = links[f"use{per}"].to_numpy(int)
    tollclass = links["tollclass"].to_numpy(float)

    # link-exclusion groups (HwyAssign pathload excludegrp)
    hov = np.isin(use, [2, 3])          # any HOV-restricted link
    hov3 = use == 3                     # HOV3+-only link
    notruck = np.isin(use, [2, 3, 4])   # no-big-truck link
    value_toll = tollclass >= hw.first_value_tollclass

    # value-toll-eligibility: a class may not use a value-toll link it isn't priced on
    vt_excl = {
        "da":  value_toll & (toll["da"] > 0),
        "s2":  value_toll & (toll["s2"] > 0),
        "s3":  value_toll & (toll["s3"] > 0),
        "sml": value_toll & (toll["sml"] > 0),
        "lrg": value_toll & (toll["lrg"] > 0),
    }

    # exclusion mask per class (None = no exclusions)
    exclude = {
        "da":      vt_excl["da"] | hov,
        "sr2":     vt_excl["s2"] | hov3,
        "sr3":     vt_excl["s3"],
        "sml":     vt_excl["sml"] | hov,
        "lrg":     vt_excl["lrg"] | hov | notruck,
        "datoll":  hov,
        "sr2toll": hov3,
        "sr3toll": None,
        "smltoll": hov,
        "lrgtoll": hov | notruck,
        "daav":    hov,
        "s2av":    hov3,
        "s3av":    None,
    }

    classes: list[VehicleClass] = []
    spec = _class_spec(hw)
    for name in CLASS_ORDER:
        vot, opcost, toll_col, pce, share = spec[name]
        classes.append(
            VehicleClass(
                name=name,
                demand=demand[name],
                vot=vot,
                opcost=opcost,
                pce=av_pce if pce is None else pce,
                toll=toll[toll_col] / share,
                exclude=exclude[name],
            )
        )
    return classes
