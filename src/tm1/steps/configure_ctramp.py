r"""Propagate ``INPUT/params.properties`` into CT-RAMP's config files.

Native replacement for the *pre-run* path of
``model-files/scripts/preprocess/RuntimeConfiguration.py`` (the invocation with
neither ``--iter`` nor ``--logsums``, ``RunModel.bat`` line 190).  The legacy
script ships templates full of ``xx.xx`` / ``set_by_RuntimeConfiguration.py``
placeholders and stamps the scenario's real values over them; nothing
downstream works until it has run.

Six pieces are ported, matching the legacy call order:

===========================  =========================================================
``check_tazdata``            land-use sanity gate; asserts only, no writes
``config_mobility_params``   ~45 keys -> ``mtcTourBased.properties``; also *writes*
                             ``taxi_tnc_occ_factors.csv``
``config_auto_opcost``       operating costs, AV PCE factors and toll/fare discounts ->
                             ``hwyParam.block``, ``trnParam.block``,
                             ``accessibilities.properties``, ``mtcTourBased.properties``
``config_uec``               ``costPerMile`` cells in three mode-choice workbooks
``config_freeparking``       the free-parking dummy in ``FreeParkingEligibility.xls``
``config_machine_size``      the two machine-size settings ``config_distribution``
                             picked by hostname, stated in the config instead
===========================  =========================================================

Deliberately **not** ported: ``config_project_dir``, ``config_popsyn_files``,
``config_host_ip``, ``config_shadowprice`` and ``config_distribution``'s JPPF
patching are already native in :mod:`tm1.steps.simulate_ctramp`
(``patch_properties`` + JPPF patching), which owns those keys;
``config_logsums`` is deferred with logsums.  This step and ``simulate_ctramp``
therefore patch *disjoint* key sets in the same ``mtcTourBased.properties``.

Faithfulness notes -- these reproduce legacy behaviour deliberately, do not
"fix" them without re-verifying against the reference run:

- Property names are **not** regex-escaped, so ``.`` is a wildcard; matching is
  case-insensitive; and the leading ``\\n`` means a key on the file's very first
  line would never match.
- Zero substitutions for any key is a fatal error.  More than one is accepted
  silently (all matches are patched), as in the legacy script.
- The per-key format strings (``%.2f`` / ``%.3f`` / ``%d`` / raw) are
  load-bearing: they are what makes the output text-comparable to a legacy run.

The one deliberate deviation: the legacy moves each target to ``*.original``
before patching.  Those backups are skipped -- ``copy_inputs`` stages the
sources and git holds their history.  (In the reference run the ``.original``
files are *not* pristine: the script ran more than once, so each backup is
itself already patched.)

Config::

    configure_ctramp:
      proj_dir: "{proj_dir}"
      params: "{proj_dir}/INPUT/params.properties"
      acc_threads: 48
      intrastep_processes: 48

``model_year`` comes from the scenario unless a step key overrides it; both
machine-size keys are optional and skipped when absent.

.. warning:: CT-RAMP-ERA STEP -- DELETE WHOLE, DO NOT PORT.

    Unlike the ``build/`` steps, nothing here survives CT-RAMP: every target is
    a Java-model config file or a UEC workbook.  When ``simulate_ctramp`` goes,
    this module and the ``ctramp`` dependency extra go with it, in one commit.
    ActivitySim's equivalent settings live in its own YAML configs and are not
    derived from ``params.properties``.
"""

import logging
import re
import shutil
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

#: Workbook cell markers: (filename, marker column, marker text, value column, alignment).
#: xlrd/xlwt address cells 0-based, exactly as the legacy script did.
_UEC_COST_PER_MILE = ("ModeChoice.xls", "TripModeChoice.xls", "accessibility_utility.xls")
_COST_MARKER_COL, _COST_VALUE_COL = 1, 4
_FREE_PARKING_BOOK = "FreeParkingEligibility.xls"
_FREE_PARKING_MARKER = "Free parking eligibility OnOff dummy"
_FREE_PARKING_MARKER_COL, _FREE_PARKING_VALUE_COL = 2, 6

#: ``(target key, source property, format)`` for mtcTourBased.properties.
#: Order follows RuntimeConfiguration.config_mobility_params.
_MOBILITY_KEYS: tuple[tuple[str, str, str], ...] = (
    ("Bike_Infra_C_IVT_Multiplier", "Bike_Infra_C_IVT_Multiplier", ".2f"),
    ("Work_Transit_Hesitance", "Work_Transit_Hesitance", ".2f"),
    ("NonWork_Transit_Hesitance", "NonWork_Transit_Hesitance", ".2f"),
    ("Rail_Transit_Hesitance", "Rail_Transit_Hesitance", ".2f"),
    ("Means_Based_Tolling_Q1Factor", "Means_Based_Tolling_Q1Factor", ".2f"),
    ("Means_Based_Tolling_Q2Factor", "Means_Based_Tolling_Q2Factor", ".2f"),
    ("Means_Based_Cordon_Tolling_Q1Factor", "Means_Based_Cordon_Tolling_Q1Factor", ".2f"),
    ("Means_Based_Cordon_Tolling_Q2Factor", "Means_Based_Cordon_Tolling_Q2Factor", ".2f"),
    ("Means_Based_Fare_PctOfPoverty_Threshold",
     "Means_Based_Fare_PctOfPoverty_Threshold", "d"),
    ("Means_Based_Fare_Factor", "Means_Based_Fare_Factor", ".2f"),
    ("Means_Based_Cordon_Fare_Factor", "Means_Based_Cordon_Fare_Factor", ".2f"),
    ("CDAP.WFH.CalibrationConstant", "WFH_Calibration_constant", ".3f"),
    ("CDAP.WFH.Calibration.eastbay_SF", "WFH_Calibration_eastbay_SF", ".3f"),
    ("Adjust_TNCsingle_TourMode", "Adjust_TNCsingle_TourMode", ".2f"),
    ("Adjust_TNCshared_TourMode", "Adjust_TNCshared_TourMode", ".2f"),
    ("Adjust_TNCsingle_TripMode", "Adjust_TNCsingle_TripMode", ".2f"),
    ("Adjust_TNCshared_TripMode", "Adjust_TNCshared_TripMode", ".2f"),
    ("Mobility.AV.Share", "Mobility.AV.Share", ".2f"),
    ("Mobility.AV.ProbabilityBoost.AutosLTDrivers",
     "Mobility.AV.ProbabilityBoost.AutosLTDrivers", ".2f"),
    ("Mobility.AV.ProbabilityBoost.AutosGEDrivers",
     "Mobility.AV.ProbabilityBoost.AutosGEDrivers", ".2f"),
    ("Mobility.AV.IVTFactor", "Mobility.AV.IVTFactor", ".2f"),
    ("Mobility.AV.ParkingCostFactor", "Mobility.AV.ParkingCostFactor", ".2f"),
    ("Mobility.AV.CostPerMileFactor", "Mobility.AV.CostPerMileFactor", ".2f"),
    ("Mobility.AV.TerminalTimeFactor", "Mobility.AV.TerminalTimeFactor", ".2f"),
    ("Mobility.TNC.shared.IVTFactor", "Mobility.TNC.shared.IVTFactor", ".2f"),
    ("taxi.baseFare", "taxi.baseFare", ".2f"),
    ("taxi.costPerMile", "taxi.costPerMile", ".2f"),
    ("taxi.costPerMinute", "taxi.costPerMinute", ".2f"),
    ("TNC.single.baseFare", "TNC.single.baseFare", ".2f"),
    ("TNC.single.costPerMile", "TNC.single.costPerMile", ".2f"),
    ("TNC.single.costPerMinute", "TNC.single.costPerMinute", ".2f"),
    ("TNC.single.costMinimum", "TNC.single.costMinimum", ".2f"),
    ("TNC.shared.baseFare", "TNC.shared.baseFare", ".2f"),
    ("TNC.shared.costPerMile", "TNC.shared.costPerMile", ".2f"),
    ("TNC.shared.costPerMinute", "TNC.shared.costPerMinute", ".2f"),
    ("TNC.shared.costMinimum", "TNC.shared.costMinimum", ".2f"),
    # Wait times are copied through as written -- no float reformatting.
    ("TNC.single.waitTime.mean", "TNC.single.waitTime.mean", ""),
    ("TNC.single.waitTime.sd", "TNC.single.waitTime.sd", ""),
    ("TNC.shared.waitTime.mean", "TNC.shared.waitTime.mean", ""),
    ("TNC.shared.waitTime.sd", "TNC.shared.waitTime.sd", ""),
    ("Taxi.waitTime.mean", "Taxi.waitTime.mean", ""),
    ("Taxi.waitTime.sd", "Taxi.waitTime.sd", ""),
)

#: ``(target key, source property, format)`` for hwyParam.block.
_HWY_PARAM_KEYS: tuple[tuple[str, str, str], ...] = (
    ("AUTOOPC", "AutoOpCost", ".2f"),
    ("min_vtoll", "min_vtoll", ".2f"),
    # Truck/bus costs and the LOS blend are copied through unformatted.
    ("SMTROPC", "SmTruckOpCost", ""),
    ("LRTROPC", "LrTruckOpCost", ""),
    ("BUSOPC", "BusOpCost", ""),
    ("TRUCK_DISTRIB_LOS_TOLL_PART", "TRUCK_DISTRIB_LOS_TOLL_PART", ""),
    *(
        (f"AV_PCE_FT{n:02d}", f"AV_PCE_FAC_FT{n:02d}", ".2f")
        for n in range(1, 11)
    ),
    ("OwnedAV_ZPV_factor", "OwnedAV_ZPV_fac", ".2f"),
    ("TNC_ZPV_factor", "TNC_ZPV_fac", ".2f"),
    ("Means_Based_Tolling_Q1Factor", "Means_Based_Tolling_Q1Factor", ".2f"),
    ("Means_Based_Tolling_Q2Factor", "Means_Based_Tolling_Q2Factor", ".2f"),
    ("Means_Based_Cordon_Tolling_Q1Factor", "Means_Based_Cordon_Tolling_Q1Factor", ".2f"),
    ("Means_Based_Cordon_Tolling_Q2Factor", "Means_Based_Cordon_Tolling_Q2Factor", ".2f"),
)

#: ``(target key, source property, format)`` for trnParam.block.
_TRN_PARAM_KEYS: tuple[tuple[str, str, str], ...] = (
    ("Means_Based_Fare_PctOfPoverty_Threshold",
     "Means_Based_Fare_PctOfPoverty_Threshold", "d"),
    ("Means_Based_Fare_Factor", "Means_Based_Fare_Factor", ".2f"),
    ("Means_Based_Cordon_Fare_Factor", "Means_Based_Cordon_Fare_Factor", ".2f"),
    ("HSR_Interregional_Disable", "HSR_Interregional_Disable", "d"),
)

#: Occupancy shares written to taxi_tnc_occ_factors.csv, one row per occupancy.
_OCC_ROWS: tuple[tuple[int, tuple[str, str, str]], ...] = (
    (1, ("Taxi.da.share", "TNC.single.da.share", "TNC.shared.da.share")),
    (2, ("Taxi.s2.share", "TNC.single.s2.share", "TNC.shared.s2.share")),
    (3, ("Taxi.s3.share", "TNC.single.s3.share", "TNC.shared.s3.share")),
)

#: tolls.csv stores cordon tolls in dollars, tazData.csv in cents.
_CENTS_PER_DOLLAR = 100.0

_REQUIRED_KEYS = ("proj_dir", "params", "model_year")


class ConfigurationError(RuntimeError):
    """A property could not be read, or a substitution did not apply."""


def get_property(contents: str, name: str) -> str:
    """Value of *name* in Java-properties *contents*.

    Faithful to ``RuntimeConfiguration.get_property``: *name* is interpolated
    into the pattern unescaped, and the leading newline means a property on the
    file's first line is invisible.  A missing property is fatal -- silently
    defaulting one would change model results.
    """
    match = re.search(rf"\n{name}[ \t]*=[ \t]*(\S*)[ \t]*", contents)
    if match is None:
        msg = f"Property {name!r} not found in params file"
        raise ConfigurationError(msg)
    return match.group(1)


def _format(raw: str, spec: str) -> str:
    """Render a property value with the legacy per-key format."""
    if spec == "":
        return raw
    if spec == "d":
        return f"{int(raw):d}"
    return f"{float(raw):{spec}}"


def _substitutions(
    contents: str, keys: tuple[tuple[str, str, str], ...]
) -> dict[str, str]:
    """Build ``{target key: formatted value}`` by reading each source property."""
    return {target: _format(get_property(contents, source), spec)
            for target, source, spec in keys}


def patch_keys(path: Path, values: dict[str, str]) -> None:
    """Rewrite ``key = value`` lines in a properties/block file.

    Matching is case-insensitive and the key is not escaped, reproducing
    ``RuntimeConfiguration.replace_in_file``.  A key that matches nothing is
    fatal; several matches are all replaced, as in the legacy script.
    """
    if not path.exists():
        msg = f"configure_ctramp target missing: {path}"
        raise FileNotFoundError(msg)

    text = path.read_text(encoding="utf-8")
    for key, value in values.items():
        text, n = re.subn(
            rf"(\n{key}[ \t]*=[ \t]*)(\S*)", rf"\g<1>{value}", text,
            flags=re.IGNORECASE,
        )
        if n < 1:
            msg = f"{path.name}: no line matched {key!r} -- substitution not made"
            raise ConfigurationError(msg)
        if n > 1:
            log.warning("%s: %r matched %d lines; all replaced", path.name, key, n)
    path.write_text(text, encoding="utf-8")
    log.info("Patched %d keys in %s", len(values), path.name)


def check_tazdata(landuse_csv: Path, tolls_csv: Path) -> None:
    """Assert cordon tolls agree between tazData.csv and tolls.csv.

    ``RuntimeConfiguration.check_tazdata``: every cordon toll class in
    ``tolls.csv`` must have an AM drive-alone toll equal to the mean
    ``CORDONCOST`` of the zones carrying that cordon, converted from cents.  A
    mismatch means the pricing scenario is internally inconsistent.
    """
    tazdata = pd.read_csv(landuse_csv)
    for col in ("CORDON", "CORDONCOST"):
        if col not in tazdata.columns:
            msg = f"{landuse_csv} is missing the {col} column"
            raise ConfigurationError(msg)

    tolls = pd.read_csv(tolls_csv)
    cordons = sorted(set(tolls.loc[tolls["tolltype"] == "cordon", "tollclass"]))
    if not cordons:
        log.info("No cordon toll classes in %s; nothing to cross-check", tolls_csv.name)
        return

    for tollclass in cordons:
        toll = float(tolls.loc[tolls["tollclass"] == tollclass, "tollam_da"].iloc[0])
        zones = tazdata.loc[tazdata["CORDON"] == tollclass, "CORDONCOST"]
        cost = float(zones.mean()) / _CENTS_PER_DOLLAR if len(zones) else None
        if cost is None or toll != cost:
            msg = (
                f"tollclass {tollclass}: tolls.csv tollam_da={toll} does not match "
                f"tazData.csv CORDONCOST/100={cost}"
            )
            raise ConfigurationError(msg)
    log.info("Cordon tolls agree for %d toll class(es)", len(cordons))


def write_occupancy_factors(contents: str, path: Path) -> None:
    """Write ``taxi_tnc_occ_factors.csv`` -- taxi/TNC occupancy shares for PrepAssign.

    Three rows (occupancy 1/2/3) of taxi, TNC-single and TNC-shared shares, in
    the legacy's ``%5.2f`` fixed width.  Text mode is deliberate: the reference
    run's copy has CRLF endings, which is what Cube read.
    """
    with path.open("w", encoding="ascii") as f:
        for occ, props in _OCC_ROWS:
            shares = (float(get_property(contents, p)) for p in props)
            f.write(f"{occ}," + ",".join(f"{s:5.2f}" for s in shares) + "\n")
    log.info("Wrote %s", path)


def _patch_workbook(
    path: Path, marker_col: int, marker: str, value_col: int, value: float, align: str
) -> int:
    """Write *value* wherever *marker* appears, preserving formatting.

    ``xlutils.copy`` round-trips the workbook through ``xlwt``, which is the
    only way to edit a BIFF ``.xls`` in place without Excel.  Imported here so
    the ``ctramp`` extra is needed only by the step that uses it.
    """
    import xlrd  # noqa: PLC0415
    import xlutils.copy  # noqa: PLC0415
    import xlwt  # noqa: PLC0415

    book = xlrd.open_workbook(str(path), formatting_info=True, on_demand=True)
    try:
        out = xlutils.copy.copy(book)
        style = xlwt.easyxf(align)
        hits = 0
        for index in range(book.nsheets):
            sheet = book.get_sheet(index)
            for row in range(sheet.nrows):
                if sheet.cell(row, marker_col).value == marker:
                    out.get_sheet(index).write(row, value_col, value, style)
                    hits += 1
    finally:
        # on_demand keeps the .xls open for lazy sheet loads; Windows refuses to
        # reopen it for writing until released.  (The legacy script sidestepped
        # this by renaming the original out of the way first.)
        book.release_resources()
    if hits == 0:
        msg = f"{path.name}: no cell in column {marker_col} holds {marker!r}"
        raise ConfigurationError(msg)
    out.save(str(path))
    log.info("Patched %d %r cell(s) in %s", hits, marker, path.name)
    return hits


def config_uec(model_dir: Path, auto_op_cost: float) -> None:
    """Stamp the auto operating cost into the mode-choice UEC workbooks."""
    for book in _UEC_COST_PER_MILE:
        _patch_workbook(
            model_dir / book, _COST_MARKER_COL, "costPerMile", _COST_VALUE_COL,
            auto_op_cost, "align: horiz left",
        )


def config_freeparking(model_dir: Path, contents: str) -> None:
    """Stamp the free-parking eligibility switch into its UEC workbook."""
    value = float(get_property(contents, "Free_Parking_Eligibility_OnOff"))
    _patch_workbook(
        model_dir / _FREE_PARKING_BOOK, _FREE_PARKING_MARKER_COL, _FREE_PARKING_MARKER,
        _FREE_PARKING_VALUE_COL, value, "align: horiz right",
    )


def config_machine_size(proj_dir: Path, step_cfg: dict) -> None:
    """How much of this machine the model may use.

    The legacy ``config_distribution`` chose these by ``socket.gethostname()`` from a
    hard-coded list, so a run on unlisted hardware raised outright.  They are stated
    here instead, which is the whole reason that whitelist existed:

    ``acc_threads``
        ``num.acc.threads`` in ``accessibilities.properties`` -- threads inside the
        accessibility calculator's single JVM.

    ``intrastep_processes``
        Selects ``HwyIntraStep_{n}.block``, which is *not* a count but a static map
        of Cube Cluster process numbers to time periods -- the congested AM and PM
        peaks get the widest slices.  It must agree with the ``cluster_nodes`` the
        assignment step starts, or ``HwyAssign`` distributes to processes that do
        not exist.

    The legacy's third setting, ``processing.threads`` in the JPPF node configs, is
    :mod:`tm1.steps.simulate_ctramp`'s (``threads:``) and is not touched here.
    """
    acc_threads = step_cfg.get("acc_threads")
    if acc_threads is not None:
        patch_keys(
            proj_dir / "CTRAMP" / "runtime" / "accessibilities.properties",
            {"num.acc.threads": f"{int(acc_threads):d}"},
        )

    processes = step_cfg.get("intrastep_processes")
    if processes is None:
        return
    block = proj_dir / "CTRAMP" / "scripts" / "block"
    source = block / f"HwyIntraStep_{int(processes)}.block"
    if not source.is_file():
        available = sorted(p.stem.split("_")[-1] for p in block.glob("HwyIntraStep_*.block"))
        msg = (
            f"configure_ctramp: no {source.name} for intrastep_processes="
            f"{processes}. Available allocations: {', '.join(available) or 'none'}. "
            f"These are hand-tuned process maps, not generated, so the value must "
            f"match one that ships."
        )
        raise FileNotFoundError(msg)
    shutil.copy2(source, block / "HwyIntraStep.block")
    log.info("Selected %s as HwyIntraStep.block", source.name)


def run(
    scenario_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,  # noqa: ARG001
) -> str | None:
    """Propagate params.properties into CT-RAMP's properties, blocks and UECs."""
    step_cfg = cfg.get("steps", {}).get("configure_ctramp", {}) or {}
    missing = [k for k in _REQUIRED_KEYS if k not in step_cfg and k not in cfg]
    if missing:
        msg = f"configure_ctramp config is missing keys: {', '.join(missing)}"
        raise KeyError(msg)

    proj_dir = Path(step_cfg.get("proj_dir") or cfg["proj_dir"])
    params = Path(step_cfg["params"])
    # Scenario-level by default -- the pre-process is not the only reader.
    model_year = int(step_cfg.get("model_year", cfg.get("model_year")))

    contents = params.read_text(encoding="utf-8")
    log.info("Read %d characters from %s", len(contents), params)

    runtime = proj_dir / "CTRAMP" / "runtime"
    block = proj_dir / "CTRAMP" / "scripts" / "block"
    model = proj_dir / "CTRAMP" / "model"

    check_tazdata(proj_dir / "landuse" / "tazData.csv", proj_dir / "hwy" / "tolls.csv")

    # mtcTourBased.properties: mobility parameters + the auto operating cost.
    auto_op_cost = float(get_property(contents, "AutoOpCost"))
    mobility = {"Model_Year": f"{model_year:d}"}
    mobility.update(_substitutions(contents, _MOBILITY_KEYS))
    mobility["Auto.Operating.Cost"] = f"{auto_op_cost:.2f}"
    patch_keys(runtime / "mtcTourBased.properties", mobility)

    patch_keys(
        runtime / "accessibilities.properties",
        {"Auto.Operating.Cost": f"{auto_op_cost:.2f}"},
    )
    patch_keys(block / "hwyParam.block", _substitutions(contents, _HWY_PARAM_KEYS))
    patch_keys(block / "trnParam.block", _substitutions(contents, _TRN_PARAM_KEYS))

    write_occupancy_factors(contents, proj_dir / "taxi_tnc_occ_factors.csv")

    config_uec(model, auto_op_cost)
    config_freeparking(model, contents)
    config_machine_size(proj_dir, step_cfg)
    return None
