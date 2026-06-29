"""PopulationSim step: synthesize a population from PUMS and control totals.

Reads ``cfg["steps"]["populationsim"]`` for:
  - ``pums.household`` / ``pums.person``: paths to raw PUMS CSVs
  - ``controls.taz`` / ``controls.county`` / ``controls.region``: control totals
  - ``working_dir``: intermediate files (seed CSVs, preprocessed controls)
  - ``output_dir``: final households.csv / persons.csv for ActivitySim

Idempotent: skips each sub-step if its outputs already exist.

Architecture:
  This module handles only the cross-table operations that require code:
    - ``num_workers``: person ESR → household aggregation
    - ``income``: ADJINC * HINCP deflation, PINCP→HINCP backfill for GQ
    - GQ type classification and person→household weight transfer
    - PUMA filtering via geo_cross_walk.csv

  Person-level model fields (``pemploy``, ``pstudent``, ``ptype``) are derived
  at ActivitySim runtime by ``annotate_persons_pums.csv``, NOT here.
  Raw PUMS columns (ESR, WKW, WKHP, SCHG, AGEP) are passed through on the
  seed persons table so they're available after PopulationSim expansion.
"""

import argparse
import logging
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

log = logging.getLogger(__name__)

_CONFIGS_DIR = Path(__file__).resolve().parents[3] / "base-models" / "population" / "configs"


def _resolve_config(filename: str, config_dirs: list[Path]) -> Path:
    """Resolve a config file across the config-dir chain (first match wins).

    Falls back to the base-models configs dir if not found in the chain. This
    lets a scenario override ``geo_cross_walk.csv`` / ``pums_encoding.yaml`` by
    placing its own copy earlier in the chain (e.g. for a different PUMA vintage).
    """
    for d in config_dirs:
        p = d / filename
        if p.exists():
            return p
    return _CONFIGS_DIR / filename


# ---------------------------------------------------------------------------
# Seed population creation (cross-table operations)
# ---------------------------------------------------------------------------


def _create_seed_population(
    hh_file: Path,
    per_file: Path,
    working_dir: Path,
    enc_path: Path,
    xwalk_path: Path,
) -> None:
    """Read raw PUMS CSVs and write seed_households/persons.csv.

    Performs cross-table derivations that cannot be expressed as
    PopulationSim annotation CSVs (person->household aggregations,
    GQ weight transfers, filtering).

    ``enc_path`` (pums_encoding.yaml) and ``xwalk_path`` (geo_cross_walk.csv)
    are resolved from the scenario config chain so scenarios can override the
    PUMS encoding / PUMA vintage.

    Person-level model fields (pemploy, pstudent, ptype) are NOT derived here.
    They are computed at ActivitySim runtime by annotate_persons_pums.csv.
    """
    with enc_path.open() as f:
        enc = yaml.safe_load(f)
    gq = enc["gqtype"]
    gq_inst, gq_noninst = enc["gq_institutional"], enc["gq_non_institutional"]

    hu = pd.read_csv(hh_file)
    per = pd.read_csv(per_file)
    log.info("Read %s housing, %s person records", f"{len(hu):,}", f"{len(per):,}")

    # Bay-Area pre-filtered PUMS files carry their own COUNTY (FIPS code) and
    # County_Name columns. Drop them so the crosswalk's MTC COUNTY (1-9) is
    # authoritative after the merge below (raw statewide PUMS lack these columns,
    # so this is a harmless no-op there).
    hu = hu.drop(columns=["COUNTY", "County_Name"], errors="ignore")
    per = per.drop(columns=["COUNTY", "County_Name"], errors="ignore")

    # Normalize weeks-worked across PUMS vintages: 2017-21 PUMS has the
    # categorical WKW (1-6); the 2019-23 5-year PUMS replaced it with numeric
    # WKWN (weeks worked, 0-52). Derive WKW from WKWN when WKW is absent so the
    # synthetic_persons output and annotate_persons_pums can rely on one column.
    # ACS WKW categories: 1=50-52wks 2=48-49 3=40-47 4=27-39 5=14-26 6=1-13.
    if "WKW" not in per.columns and "WKWN" in per.columns:
        wkwn = per.WKWN.fillna(0).clip(0, 52)
        per["WKW"] = (
            pd.cut(wkwn, [-1, 0, 13, 26, 39, 47, 49, 52], labels=[0, 6, 5, 4, 3, 2, 1])
            .astype(int)
        )
        log.info("Derived categorical WKW from numeric WKWN (2019-23 PUMS vintage)")

    # Filter to Bay Area PUMAs via geo crosswalk
    xwalk = pd.read_csv(xwalk_path)[["PUMA", "COUNTY"]].drop_duplicates()
    hu = hu.merge(xwalk, on="PUMA", how="inner")
    per = per.merge(xwalk, on="PUMA", how="inner")
    log.info("After PUMA filter: %s HH, %s persons", f"{len(hu):,}", f"{len(per):,}")

    # --- Cross-table: workers per household from person ESR ---
    employed_codes = enc["employed_esr_codes"]
    per["ESR"] = per.ESR.fillna(0).astype(np.uint8)
    per["employed"] = per.ESR.isin(employed_codes).astype(np.uint8)

    hh_workers = (
        per[["SERIALNO", "employed"]]
        .groupby("SERIALNO")
        .sum()
        .rename(columns={"employed": "num_workers"})
    )
    hu = hu.merge(hh_workers, left_on="SERIALNO", right_index=True, how="left")
    hu["num_workers"] = hu.num_workers.fillna(0).astype(np.uint8)

    # --- Cross-table: transfer PINCP->HINCP for GQ records ---
    pers_inc = per[["SERIALNO", "PINCP"]].dropna(subset=["PINCP"]).drop_duplicates("SERIALNO")
    hu = hu.merge(pers_inc, on="SERIALNO", how="left", suffixes=("", "_per"))
    hu.loc[hu.HINCP.isna(), "HINCP"] = hu["PINCP"]
    hu = hu.drop(columns=["PINCP"], errors="ignore")

    # Income deflation
    deflator = enc["income_deflator_to_2000"]
    adjinc_scale = enc["adjinc_scale"]
    hu["income"] = (hu.ADJINC / adjinc_scale) * hu.HINCP * deflator

    # --- Filtering ---
    hu = hu.loc[hu.NP > 0]  # remove vacant units
    per = per.merge(hu[["SERIALNO", "TYPEHUGQ"]], on="SERIALNO", how="left")
    hu = hu.loc[hu.TYPEHUGQ != gq_inst]
    per = per.loc[per.TYPEHUGQ != gq_inst]
    log.info("After filtering: %s HH, %s persons", f"{len(hu):,}", f"{len(per):,}")

    # Unique household ID
    hu = hu.reset_index(drop=True)
    hu["household_id"] = hu.index + 1
    per = per.merge(
        hu[["SERIALNO", "WGTP", "household_id"]], on="SERIALNO", how="left", suffixes=("", "_hu")
    )

    # --- Cross-table: GQ type + weight transfer ---
    gq_col_schg = enc["gq_college_schg"]
    gq_mil = enc["gq_military_mil"]
    per["gqtype"] = np.select(
        [
            (per.TYPEHUGQ == gq_noninst) & (per.MIL == gq_mil),
            (per.TYPEHUGQ == gq_noninst) & per.SCHG.isin(gq_col_schg),
            per.TYPEHUGQ == gq_noninst,
        ],
        [gq["military"], gq["college"], gq["other"]],
        default=gq["not_gq"],
    ).astype(np.uint8)

    gq_wt = per[["SERIALNO", "PWGTP", "gqtype"]].drop_duplicates("SERIALNO")
    hu = hu.merge(gq_wt, on="SERIALNO", how="left")
    hu.loc[hu.TYPEHUGQ == gq_noninst, "WGTP"] = hu.PWGTP
    hu = hu.drop(columns=["PWGTP"])
    hu = hu.rename(columns={"gqtype": "hhgqtype"})

    # Write seed files
    working_dir.mkdir(parents=True, exist_ok=True)
    hu.to_csv(working_dir / "seed_households.csv", index=False)
    per.to_csv(working_dir / "seed_persons.csv", index=False)
    log.info("Wrote seed files to %s", working_dir)


# ---------------------------------------------------------------------------
# Control totals preprocessing
# ---------------------------------------------------------------------------


def _prepare_controls(controls: dict[str, str | Path], working_dir: Path) -> None:
    """Fetch and preprocess control totals into working_dir."""
    working_dir.mkdir(parents=True, exist_ok=True)

    if not (working_dir / "taz_summaries_hhgq.csv").exists():
        taz = pd.read_csv(controls["taz"])
        taz["numhh_gq"] = taz.TOTHH + taz.gq_tot_pop
        taz["hh_size_1_gq"] = taz.hh_size_1 + taz.gq_tot_pop
        taz.to_csv(working_dir / "taz_summaries_hhgq.csv", index=False)
        log.info("Wrote TAZ controls (%d rows)", len(taz))

    if not (working_dir / "county_controls.csv").exists():
        pd.read_csv(controls["county"]).to_csv(working_dir / "county_controls.csv", index=False)
        log.info("Wrote county controls")

    if not (working_dir / "region_controls.csv").exists():
        pd.read_csv(controls["region"]).to_csv(working_dir / "region_controls.csv", index=False)
        log.info("Wrote region controls")


# ---------------------------------------------------------------------------
# PopulationSim synthesis invocation
# ---------------------------------------------------------------------------


def _run_synthesis(
    working_dir: Path, config_dirs: list[Path], multiprocess: bool, xwalk_path: Path
) -> None:
    """Invoke PopulationSim with the given config chain."""
    popsim_output = working_dir / "pipeline"
    popsim_output.mkdir(parents=True, exist_ok=True)

    # Ensure geo_cross_walk is in data dir (resolved from the config chain)
    xwalk_dst = working_dir / "geo_cross_walk.csv"
    if not xwalk_dst.exists():
        shutil.copy2(xwalk_path, xwalk_dst)

    from populationsim import run as _popsim_run  # noqa: PLC0415
    from populationsim.run import add_run_args as _popsim_add_run_args  # noqa: PLC0415

    cli_args: list[str] = []
    for d in config_dirs:
        cli_args += ["-c", str(d)]
    cli_args += ["-d", str(working_dir), "-o", str(popsim_output)]
    if multiprocess:
        cli_args += ["-m"]

    parser = argparse.ArgumentParser()
    _popsim_add_run_args(parser)
    args = parser.parse_args(cli_args)

    log.info("Running PopulationSim: configs=%s, data=%s", config_dirs, working_dir)
    _popsim_run(args)


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------


def _postprocess(working_dir: Path, output_dir: Path) -> None:
    """Copy final CSVs to output_dir with post-processing (HHT fill, person_id)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    popsim_output = working_dir / "pipeline"

    hh = pd.read_csv(popsim_output / "synthetic_households.csv")
    per = pd.read_csv(popsim_output / "synthetic_persons.csv")
    hh.loc[hh.HHT.isna(), "HHT"] = 0
    per["person_id"] = per.index + 1
    hh.to_csv(output_dir / "households.csv", index=False)
    per.to_csv(output_dir / "persons.csv", index=False)
    log.info("Wrote households.csv (%d) and persons.csv (%d) to %s", len(hh), len(per), output_dir)


# ---------------------------------------------------------------------------
# Step entry point
# ---------------------------------------------------------------------------


def run(
    scenario_dir: Path,
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """Run PopulationSim synthesis pipeline.

    Config keys (under ``steps.populationsim``):
        pums.household: path to PUMS household CSV
        pums.person: path to PUMS person CSV
        controls.taz: path/URL to TAZ control totals
        controls.county: path/URL to county control totals
        controls.region: path/URL to region control totals
        working_dir: intermediate files directory
        output_dir: final output directory
        configs: list of config directories (optional, defaults to base-models)
    """
    step_cfg = cfg.get("steps", {}).get("populationsim", {})
    if not step_cfg:
        log.info("No populationsim config found — skipping")
        return "skipped"

    base_model_dir: Path = kwargs.get("base_model_dir", scenario_dir.parent.parent)  # pyright: ignore[reportAssignmentType]

    pums = step_cfg["pums"]
    controls = step_cfg["controls"]
    working_dir = Path(step_cfg.get("working_dir", str(scenario_dir / ".cache" / "popsim")))
    output_dir = Path(step_cfg.get("output_dir", str(scenario_dir / ".cache" / "data")))

    # Skip if final outputs already exist
    if (output_dir / "households.csv").exists() and (output_dir / "persons.csv").exists():
        if not kwargs.get("force", False):
            log.info("PopulationSim outputs already exist in %s — skipping", output_dir)
            return "skipped"

    # 1. Build config directory chain (used to resolve overridable config files)
    config_dirs: list[Path] = []
    raw_configs = step_cfg.get("configs", [])
    if raw_configs:
        for c in raw_configs:
            p = Path(c)
            if not p.is_absolute():
                p = base_model_dir / p
            config_dirs.append(p)
    else:
        # Default: configs_mp (if exists) + configs
        configs_mp = _CONFIGS_DIR.parent / "configs_mp"
        if configs_mp.is_dir():
            config_dirs.append(configs_mp)
        config_dirs.append(_CONFIGS_DIR)

    # Resolve scenario-overridable config files from the chain (first match wins)
    enc_path = _resolve_config("pums_encoding.yaml", config_dirs)
    xwalk_path = _resolve_config("geo_cross_walk.csv", config_dirs)
    log.info("Using pums_encoding=%s, geo_cross_walk=%s", enc_path, xwalk_path)

    # 2. Create seed population from PUMS
    if not (working_dir / "seed_households.csv").exists():
        _create_seed_population(
            Path(pums["household"]), Path(pums["person"]), working_dir, enc_path, xwalk_path
        )

    # 3. Prepare control totals
    _prepare_controls(controls, working_dir)

    multiprocess = any(
        (d / "settings.yaml").exists()
        and "multiprocess: True" in (d / "settings.yaml").read_text()
        for d in config_dirs
    )

    # 4. Run synthesis
    if not (working_dir / "pipeline" / "synthetic_households.csv").exists():
        _run_synthesis(working_dir, config_dirs, multiprocess, xwalk_path)

    # 5. Post-process to final output
    _postprocess(working_dir, output_dir)

    return None
