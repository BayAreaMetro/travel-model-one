"""Calibration summaries for travel model submodels."""

import logging
from pathlib import Path
from types import ModuleType

import polars as pl

from .bundle import ModelBundle
from .compare import build_comparison, write_comparison_csvs
from .config import parse_config
from .io import load_bundle
from .report import write_report
from .submodels import auto_ownership, daily_activity_pattern, work_school_location

log = logging.getLogger(__name__)

# Maps submodel name → (module, required bundle fields)
SUBMODELS: dict[str, ModuleType] = {
    "work_school_location": work_school_location,
    "auto_ownership": auto_ownership,
    "daily_activity_pattern": daily_activity_pattern,
}


def _bundle_has_inputs(bundle: ModelBundle, submodel: ModuleType) -> bool:
    """Check whether *bundle* has the fields required by *submodel*."""
    for field_name in submodel.REQUIRED_FIELDS:
        if getattr(bundle, field_name, None) is None:
            return False
    return True


def _run_submodel(
    submodel: ModuleType,
    bundle: ModelBundle,
) -> dict[str, pl.DataFrame]:
    """Invoke a submodel's ``summarize()`` with the right arguments."""
    if submodel is work_school_location:
        wsloc = bundle.wsloc_results.collect()
        # If bundle has person weights from a separate persons table, join them
        needs_weight_join = (
            bundle.weight_col
            and bundle.persons is not None
            and bundle.weight_col not in wsloc.columns
        )
        if needs_weight_join:
            persons = bundle.persons.select(
                "hh_id", "person_id", bundle.weight_col,
            ).collect()
            wsloc = wsloc.join(
                persons,
                on=["hh_id", "person_id"],
                how="left",
            ).with_columns(pl.col(bundle.weight_col).fill_null(0.0))
        return submodel.summarize(
            wsloc=wsloc,
            taz_data=bundle.taz_data.collect(),
            dist_skim=bundle.dist_skim.collect(),
            weight_col=bundle.weight_col,
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
            weight_col=bundle.weight_col,
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


def run(
    scenario_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,  # noqa: ARG001
) -> None:
    """Produce calibration summaries by loading data bundles and running pure submodel functions."""
    run_cfg = parse_config(cfg)

    if not run_cfg.datasets:
        log.warning("No datasets configured — nothing to do")
        return
    if not run_cfg.submodels:
        log.warning("No submodels configured — nothing to do")
        return

    # {label: {submodel_name: {table_name: DataFrame}}}
    all_results: dict[str, dict[str, dict[str, pl.DataFrame]]] = {}

    for ds_cfg in run_cfg.datasets:
        log.info("Loading dataset: %s", ds_cfg.label)
        bundle = load_bundle(ds_cfg)
        all_results[bundle.label] = {}

        for submodel_name in run_cfg.submodels:
            mod = SUBMODELS.get(submodel_name)
            if mod is None:
                log.warning("Unknown submodel: %s — skipping", submodel_name)
                continue

            if not _bundle_has_inputs(bundle, mod):
                log.info(
                    "Skipping %s for %s (missing inputs)",
                    submodel_name,
                    bundle.label,
                )
                continue

            log.info("Running %s for %s", submodel_name, bundle.label)
            tables = _run_submodel(mod, bundle)
            all_results[bundle.label][submodel_name] = tables
            if run_cfg.write_csv:
                _write_csvs(tables, run_cfg.output_dir, bundle.label, submodel_name)

    # Comparison across datasets
    if len(run_cfg.datasets) > 1:
        log.info("Building comparison across datasets")
        comparisons = build_comparison(all_results)
        if run_cfg.write_csv:
            write_comparison_csvs(comparisons, run_cfg.output_dir)

    # HTML calibration report
    report_path = write_report(all_results, run_cfg.output_dir)
    log.info("Wrote calibration report: %s", report_path)

