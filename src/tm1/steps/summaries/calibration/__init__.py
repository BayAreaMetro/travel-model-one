"""Calibration summaries for travel model submodels."""

import logging
import time
from pathlib import Path
from types import ModuleType

import polars as pl

from .bundle import ModelBundle
from .compare import build_comparison, write_comparison_csvs
from .config import parse_config
from .io import load_bundle
from .report import write_report
from .submodels import (
    auto_ownership,
    daily_activity_pattern,
    nonwork_dest_choice,
    tour_mode_choice,
    trip_mode_choice,
    work_school_location,
)

log = logging.getLogger(__name__)

# Maps submodel name → (module, required bundle fields)
SUBMODELS: dict[str, ModuleType] = {
    "work_school_location": work_school_location,
    "auto_ownership": auto_ownership,
    "daily_activity_pattern": daily_activity_pattern,
    "nonwork_dest_choice": nonwork_dest_choice,
    "tour_mode_choice": tour_mode_choice,
    "trip_mode_choice": trip_mode_choice,
}


def _check_bundle_inputs(bundle: ModelBundle, submodel: ModuleType, submodel_name: str) -> list[str]:
    """Return missing field names. Logs a loud WARNING if any are missing."""
    missing = [
        f for f in submodel.REQUIRED_FIELDS
        if getattr(bundle, f, None) is None
    ]
    if missing:
        log.warning(
            "MISSING INPUTS: %s for '%s' — fields %s are None. "
            "Check dataset paths/config. This dataset will be OMITTED from "
            "the %s comparison.",
            submodel_name, bundle.label, missing, submodel_name,
        )
    return missing


def _run_submodel(
    submodel: ModuleType,
    bundle: ModelBundle,
) -> dict[str, pl.DataFrame]:
    """Invoke a submodel's ``summarize()`` with the right arguments."""
    if submodel is work_school_location:
        wc = bundle.get_weight_col("wsloc_results")
        wsloc = bundle.wsloc_results.collect()
        # If bundle has person weights from a separate persons table, join them
        needs_weight_join = (
            wc
            and bundle.persons is not None
            and wc not in wsloc.columns
        )
        if needs_weight_join:
            persons = bundle.persons.select(
                "hh_id", "person_id", wc,
            ).collect()
            wsloc = wsloc.join(
                persons,
                on=["hh_id", "person_id"],
                how="left",
            ).with_columns(pl.col(wc).fill_null(0.0))
        return submodel.summarize(
            wsloc=wsloc,
            taz_data=bundle.taz_data.collect(),
            dist_skim=bundle.dist_skim.collect(),
            weight_col=wc,
            sampleshare=bundle.sampleshare,
        )
    if submodel is auto_ownership:
        return submodel.summarize(
            households=bundle.households.collect(),
            ao_results=bundle.ao_results.collect(),
            taz_data=bundle.taz_data.collect(),
            sampleshare=bundle.sampleshare,
        )
    if submodel is daily_activity_pattern:
        return submodel.summarize(
            cdap_results=bundle.cdap_results.collect(),
            weight_col=bundle.get_weight_col("cdap_results"),
            sampleshare=bundle.sampleshare,
        )
    if submodel is nonwork_dest_choice:
        return submodel.summarize(
            indiv_tour_data=bundle.indiv_tour_data.collect(),
            dist_skim=bundle.dist_skim.collect(),
            joint_tour_data=(
                bundle.joint_tour_data.collect()
                if bundle.joint_tour_data is not None
                else None
            ),
            weight_col=bundle.get_weight_col("indiv_tour_data"),
            sampleshare=bundle.sampleshare,
        )
    if submodel is tour_mode_choice:
        return submodel.summarize(
            indiv_tour_data=bundle.indiv_tour_data.collect(),
            ao_results=bundle.ao_results.collect(),
            households=bundle.households.collect(),
            joint_tour_data=(
                bundle.joint_tour_data.collect()
                if bundle.joint_tour_data is not None
                else None
            ),
            weight_col=bundle.get_weight_col("indiv_tour_data"),
            sampleshare=bundle.sampleshare,
        )
    if submodel is trip_mode_choice:
        return submodel.summarize(
            indiv_trip_data=bundle.indiv_trip_data.collect(),
            joint_trip_data=(
                bundle.joint_trip_data.collect()
                if bundle.joint_trip_data is not None
                else None
            ),
            weight_col=bundle.get_weight_col("indiv_trip_data"),
            sampleshare=bundle.sampleshare,
        )
    msg = f"Unknown submodel module: {submodel}"
    raise ValueError(msg)


def _write_csvs(
    tables: dict[str, pl.DataFrame],
    output_dir: Path,
    label: str,
    submodel_name: str,
) -> None:
    """Write each DataFrame as ``{output_dir}/{label}/{submodel}_{table}.csv``."""
    out = output_dir / label
    out.mkdir(parents=True, exist_ok=True)
    for table_name, df in tables.items():
        if df is not None:
            path = out / f"{submodel_name}_{table_name}.csv"
            df.write_csv(path)
            log.info("Wrote %s", path)


def run(  # noqa: C901, PLR0912
    scenario_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,  # noqa: ARG001
) -> None:
    """Produce calibration summaries by loading data bundles and running pure submodel functions."""
    # Ensure root logger has a timestamp format
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    else:
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S",
        )
        for h in root.handlers:
            h.setFormatter(fmt)

    run_cfg = parse_config(cfg)

    if not run_cfg.datasets:
        log.warning("No datasets configured — nothing to do")
        return
    if not run_cfg.submodels:
        log.warning("No submodels configured — nothing to do")
        return

    # {label: {submodel_name: {table_name: DataFrame}}}
    all_results: dict[str, dict[str, dict[str, pl.DataFrame]]] = {}

    t_total = time.perf_counter()

    # --- Load all bundles up front ---
    bundles: list[ModelBundle] = []
    for ds_cfg in run_cfg.datasets:
        t_ds = time.perf_counter()
        bundle = load_bundle(ds_cfg)
        log.info("Loaded %s (%.1fs)", ds_cfg.label, time.perf_counter() - t_ds)
        bundles.append(bundle)
        all_results[bundle.label] = {}

    # --- Run submodels across all bundles ---
    for submodel_name in run_cfg.submodels:
        mod = SUBMODELS.get(submodel_name)
        if mod is None:
            log.warning("Unknown submodel: %s — skipping", submodel_name)
            continue

        for bundle in bundles:
            missing = _check_bundle_inputs(bundle, mod, submodel_name)
            if missing:
                continue

            t_sub = time.perf_counter()
            tables = _run_submodel(mod, bundle)
            log.info(
                "%s / %s (%.1fs)",
                submodel_name, bundle.label, time.perf_counter() - t_sub,
            )
            all_results[bundle.label][submodel_name] = tables
            if run_cfg.write_csv:
                _write_csvs(tables, run_cfg.output_dir, bundle.label, submodel_name)

    # Comparison across datasets
    if len(run_cfg.datasets) > 1:
        log.info("Building comparison across datasets")
        comparisons = build_comparison(all_results)
        if run_cfg.write_csv:
            write_comparison_csvs(comparisons, run_cfg.output_dir)

    # Identify survey datasets (those using per-record weights, not sampleshare)
    survey_labels = {
        ds_cfg.label for ds_cfg in run_cfg.datasets if ds_cfg.weight_cols
    }

    # HTML calibration report
    t_rpt = time.perf_counter()
    report_path = write_report(
        all_results, run_cfg.output_dir, survey_labels=survey_labels,
    )
    log.info("Wrote calibration report: %s (%.1fs)", report_path, time.perf_counter() - t_rpt)
    log.info("Calibration complete (%.1fs total)", time.perf_counter() - t_total)

