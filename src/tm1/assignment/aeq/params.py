"""Typed loader for the AequilibraE assignment/skim model parameters.

All model policy ported from the legacy Cube job files lives in
``default-configs/assignment/aeq_params.yaml`` (provenance documented there), NOT in the
engine modules.  Entry points call :func:`load_aeq_params` once (optionally with a
scenario-supplied alternate path) and pass the object down.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

DEFAULT_PARAMS_PATH = (Path(__file__).resolve().parents[4]
                       / "default-configs" / "assignment" / "aeq_params.yaml")


@dataclass(frozen=True)
class LinehaulCost:
    """One line-haul path's cost policy (token_skipmodes / token_modefac / key band)."""

    skip: tuple                 # ((lo, hi), ...) excluded mode ranges
    fac: tuple                  # ((lo, hi, factor), ...) perceived-IVT factors
    key_band: tuple | None      # premier mode band; None = no premier filter
    spread_window: float | None  # overrides transit_cost.spread_window
    wait_pool: bool             # COMBINE the boarded lines' headways (Cube MAXDIFF)


@dataclass(frozen=True)
class TransitCost:
    """Perceived-cost policy for transit assignment + skimming."""

    assign_wait_perceive: float
    skim_wait_perceive: float
    walk_factor: float
    assign_board_penalties: tuple
    walk_board_penalties: tuple
    drive_board_penalties: tuple
    skim_max_perceived_min: float
    skim_max_path_min: float
    spread_window: float | None
    iwaitmax_min: float
    iwaitmax_modes: tuple
    ferry_band: tuple
    wait_combine: str           # "line" | "service" | "node" (COMBINE pooling rule)
    linehauls: dict             # name -> LinehaulCost


@dataclass(frozen=True)
class SkimOutput:
    """Run-type structure + ActivitySim OMX publishing conventions."""

    access_egress: tuple        # ((access, egress, access_mode, egress_mode), ...)
    linehauls: tuple            # LOS-skimmed line-hauls (includes trn)
    fare_linehauls: tuple       # exact fare pass subset
    token_scale: dict
    token_name: dict
    linehaul_tokens: dict
    drive_tokens: tuple


@dataclass(frozen=True)
class BusTime:
    """PrepHwyNet.job BUS_TIME policy (bus in-vehicle times from congested links)."""

    delay_by_at: dict
    min_speed: float
    min_speed_fwy: float
    brt3_speed_cap: float
    fallback_speed: float
    fallback_dist: float


@dataclass(frozen=True)
class Periods:
    """Model periods, capacity factors, and TRNBUILD headway fields."""

    names: tuple
    capfac: dict
    freq_field: dict


@dataclass(frozen=True)
class Vdf:
    """Volume-delay functions (SpeedFlowCurve.block / FreeFlowSpeed.block)."""

    bpr_coef: float
    bpr_vc_norm: float
    bpr_power: float
    akcelik_quarter: float
    akcelik_j_scale: float
    freeway_ft: tuple
    fixed_ft: tuple
    max_capclass: int
    default_critspd: float
    critspd_by_capclass: dict


@dataclass(frozen=True)
class RideHail:
    """Ride-hail (TNC/taxi) person->vehicle folding (PrepAssign.job steps 3-5)."""

    zpv_factor: float           # zero-passenger (deadhead) empty-vehicle factor
    tables: dict                # {"taxi": "TAXI", "single": "TNC_SINGLE", "shared": "TNC_SHARED"}
    shares: dict                # {mode: {"da":.., "s2":.., "s3":..}} occupancy-bin split


@dataclass(frozen=True)
class Highway:
    """Highway assignment policy (hwyParam.block / HwyAssign.job)."""

    vot: float
    truck_vot: float
    sr2_toll_share: float
    sr3_toll_share: float
    truck_pce: float
    first_value_tollclass: int
    occupancy: dict             # {"sr2": ..., "sr3": ...} person->vehicle divisors
    asim_tables: dict           # ActivitySim OMX table -> assignment class
    ridehail: RideHail          # TNC/taxi folding constants
    skim_classes: tuple         # ((class, OMX prefix, is_toll), ...)
    vdf: Vdf


@dataclass(frozen=True)
class AeqParams:
    """Everything the aeq assignment/skim engine reads from aeq_params.yaml."""

    n_taz: int
    periods: Periods
    transit_cost: TransitCost
    skim_output: SkimOutput
    bus_time: BusTime
    rail_fare: dict             # linehaul -> {"far_files": [...], "band": (lo, hi)}
    highway: Highway


def _tuples(rows: list) -> tuple:
    return tuple(tuple(r) for r in rows)


@lru_cache(maxsize=4)
def load_aeq_params(path: str | Path | None = None) -> AeqParams:
    """Load (and cache) the model parameters; ``path`` overrides the default file."""
    path = Path(path) if path else DEFAULT_PARAMS_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    tc = raw["transit_cost"]
    linehauls = {
        name: LinehaulCost(
            skip=_tuples(lh["skip"]), fac=_tuples(lh["fac"]),
            key_band=tuple(lh["key_band"]) if lh["key_band"] else None,
            spread_window=lh.get("spread_window", tc["spread_window"]),
            wait_pool=bool(lh.get("wait_pool", True)))
        for name, lh in tc["linehauls"].items()
    }
    transit_cost = TransitCost(
        assign_wait_perceive=float(tc["assign_wait_perceive"]),
        skim_wait_perceive=float(tc["skim_wait_perceive"]),
        walk_factor=float(tc["walk_factor"]),
        assign_board_penalties=tuple(tc["assign_board_penalties"]),
        walk_board_penalties=tuple(tc["walk_board_penalties"]),
        drive_board_penalties=tuple(tc["drive_board_penalties"]),
        skim_max_perceived_min=float(tc["skim_max_perceived_min"]),
        skim_max_path_min=float(tc["skim_max_path_min"]),
        spread_window=tc["spread_window"],
        iwaitmax_min=float(tc["iwaitmax"]["max_min"]),
        iwaitmax_modes=tuple(tc["iwaitmax"]["modes"]),
        ferry_band=tuple(tc["ferry_band"]),
        wait_combine=str(tc.get("wait_combine", "line")),
        linehauls=linehauls,
    )

    so = raw["skim_output"]
    skim_output = SkimOutput(
        access_egress=_tuples(so["access_egress"]),
        linehauls=tuple(so["linehauls"]),
        fare_linehauls=tuple(so["fare_linehauls"]),
        token_scale={k: float(v) for k, v in so["token_scale"].items()},
        token_name=dict(so["token_name"]),
        linehaul_tokens={k: tuple(v) for k, v in so["linehaul_tokens"].items()},
        drive_tokens=tuple(so["drive_tokens"]),
    )

    bt = raw["bus_time"]
    bus_time = BusTime(
        delay_by_at={int(k): float(v) for k, v in bt["delay_by_at"].items()},
        min_speed=float(bt["min_speed"]), min_speed_fwy=float(bt["min_speed_fwy"]),
        brt3_speed_cap=float(bt["brt3_speed_cap"]),
        fallback_speed=float(bt["fallback_speed"]),
        fallback_dist=float(bt["fallback_dist"]),
    )

    per = raw["periods"]
    periods = Periods(names=tuple(per["names"]), capfac=dict(per["capfac"]),
                      freq_field=dict(per["freq_field"]))

    rail_fare = {name: {"far_files": tuple(v["far_files"]), "band": tuple(v["band"])}
                 for name, v in raw["rail_fare"].items()}

    hw = raw["highway"]
    vdf = Vdf(
        bpr_coef=float(hw["vdf"]["bpr"]["coef"]),
        bpr_vc_norm=float(hw["vdf"]["bpr"]["vc_norm"]),
        bpr_power=float(hw["vdf"]["bpr"]["power"]),
        akcelik_quarter=float(hw["vdf"]["akcelik"]["quarter"]),
        akcelik_j_scale=float(hw["vdf"]["akcelik"]["j_scale"]),
        freeway_ft=tuple(hw["vdf"]["freeway_ft"]),
        fixed_ft=tuple(hw["vdf"]["fixed_ft"]),
        max_capclass=int(hw["vdf"]["max_capclass"]),
        default_critspd=float(hw["vdf"]["default_critspd"]),
        critspd_by_capclass={int(k): float(v)
                             for k, v in hw["vdf"]["critspd_by_capclass"].items()},
    )
    rh = hw["ridehail"]
    ridehail = RideHail(
        zpv_factor=float(rh["zpv_factor"]),
        tables=dict(rh["tables"]),
        shares={mode: {k: float(v) for k, v in sh.items()}
                for mode, sh in rh["shares"].items()},
    )
    highway = Highway(
        vot=float(hw["vot"]), truck_vot=float(hw["truck_vot"]),
        sr2_toll_share=float(hw["sr2_toll_share"]),
        sr3_toll_share=float(hw["sr3_toll_share"]),
        truck_pce=float(hw["truck_pce"]),
        first_value_tollclass=int(hw["first_value_tollclass"]),
        occupancy={k: float(v) for k, v in hw["occupancy"].items()},
        asim_tables=dict(hw["asim_tables"]),
        ridehail=ridehail,
        skim_classes=_tuples(hw["skim_classes"]),
        vdf=vdf,
    )

    return AeqParams(n_taz=int(raw["zones"]["n_taz"]), periods=periods,
                     transit_cost=transit_cost, skim_output=skim_output,
                     bus_time=bus_time, rail_fare=rail_fare, highway=highway)
