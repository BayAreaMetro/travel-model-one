"""PopulationSim runner for TM1a.

Orchestrates the full pipeline: seed creation → control prep → synthesis →
final CSV output. Can be run standalone or as a Prefect task via run_model.py.

All paths are explicit arguments to run(). Callers are responsible for
resolving them — see __main__ block (local dev) and run_model.py (Prefect).
"""

import argparse
import logging
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from travel_model_application.config import load_scenario_config, resolve_path

logger = logging.getLogger(__name__)

_PKG_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = _PKG_DIR / "configs"


def _derive_person_fields(per: pd.DataFrame, seed_cfg: dict, soc_map: dict) -> pd.DataFrame:
    """Derive employment status, student status, person type, and occupation.

    All thresholds and encoding values come from pums_encoding.yaml
    to avoid magic numbers in the code.
    """
    pe = seed_cfg["pemploy"]
    ps = seed_cfg["pstudent"]
    pt = seed_cfg["ptype"]

    # Employment status
    ft_wkw = seed_cfg["fulltime_wkw_codes"]
    ft_hrs = seed_cfg["fulltime_min_wkhp"]
    per["pemploy"] = np.select(
        [per.ESR == seed_cfg["esr_under_16"],
         per.ESR.isin(seed_cfg["unemployed_esr_codes"]),
         per.employed.astype(bool) & per.WKW.isin(ft_wkw) & (per.WKHP >= ft_hrs),
         per.employed.astype(bool)],
        [pe["child"], pe["not_employed"], pe["full_time"], pe["part_time"]],
        default=pe["not_employed"],
    ).astype(np.int16)

    # Student status
    gs_lo, gs_hi = seed_cfg["grade_school_schg"]
    uni_codes = seed_cfg["university_schg"]
    per["pstudent"] = np.select(
        [per.SCHG.between(gs_lo, gs_hi), per.SCHG.isin(uni_codes)],
        [ps["grade_or_high"], ps["university"]],
        default=ps["not_student"],
    ).astype(np.uint8)

    # Person type
    max_pre = seed_cfg["preschool_max_age"] + 1
    max_sch = seed_cfg["school_max_age"]
    min_uni = seed_cfg["university_adult_min_age"]
    min_ret = seed_cfg["retiree_min_age"]
    per["ptype"] = np.select(
        [(per.AGEP < max_pre) & (per.pstudent == ps["not_student"]),
         per.AGEP <= max_sch,
         per.pemploy == pe["full_time"],
         (per.pstudent == ps["university"])
         | ((per.AGEP >= min_uni) & (per.pstudent == ps["grade_or_high"])),
         per.pstudent == ps["grade_or_high"],
         per.pemploy == pe["part_time"],
         per.AGEP < min_ret,
         per.AGEP >= min_ret],
        [pt["preschool"], pt["school_age_child"], pt["full_time_worker"],
         pt["university_student"], pt["driving_age_student"], pt["part_time_worker"],
         pt["non_working_adult"], pt["retired"]],
        default=pt["retired"],
    ).astype(np.uint8)

    # Occupation from SOC code
    per["soc"] = per.SOCP.str[:2]
    per["occupation"] = per.soc.map(soc_map).fillna(0).astype(np.uint8)

    return per


def create_seed_population(hh_file: Path, per_file: Path, working_dir: Path) -> None:
    """Read raw PUMS CSVs and write seed_households/persons.csv.

    Performs cross-table derivations that cannot be expressed as
    PopulationSim annotation CSVs (person->household aggregations,
    GQ weight transfers, filtering).

    Row-level derivations (employment status, student status, person type,
    occupation, income deflation) are also done here for now; see
    DEVELOPMENT_PLAN.md for migration path to annotation CSVs.
    """
    with (CONFIGS_DIR / "pums_encoding.yaml").open() as f:
        enc = yaml.safe_load(f)
    soc_df = pd.read_csv(CONFIGS_DIR / "soc_to_occupation.csv", dtype={"soc": str})
    soc_map = dict(zip(soc_df.soc, soc_df.occupation, strict=True))
    gq = enc["gqtype"]
    gq_inst, gq_noninst = enc["gq_institutional"], enc["gq_non_institutional"]

    hu = pd.read_csv(hh_file)
    per = pd.read_csv(per_file)
    logger.info("Read %s housing, %s person records", f"{len(hu):,}", f"{len(per):,}")

    # Filter to Bay Area PUMAs via geo crosswalk (inner join drops non-Bay-Area records)
    xwalk = pd.read_csv(CONFIGS_DIR / "geo_cross_walk.csv")[["PUMA", "COUNTY"]].drop_duplicates()
    hu = hu.merge(xwalk, on="PUMA", how="inner")
    per = per.merge(xwalk, on="PUMA", how="inner")
    logger.info("After PUMA filter: %s HH, %s persons", f"{len(hu):,}", f"{len(per):,}")

    # --- Cross-table: workers per household from person ESR ---
    employed_codes = enc["employed_esr_codes"]
    per["ESR"] = per.ESR.fillna(0).astype(np.uint8)
    per["employed"] = per.ESR.isin(employed_codes).astype(np.uint8)

    hh_workers = (
        per[["SERIALNO", "employed"]].groupby("SERIALNO").sum()
        .rename(columns={"employed": "num_workers"})
    )
    hu = hu.merge(hh_workers, left_on="SERIALNO", right_index=True, how="left")
    hu["num_workers"] = hu.num_workers.fillna(0).astype(np.uint8)

    # --- Row-level person derivations (config-driven) ---
    per = _derive_person_fields(per, enc, soc_map)

    # --- Cross-table: transfer PINCP->HINCP for GQ records ---
    pers_inc = per[["SERIALNO", "PINCP"]].dropna(subset=["PINCP"]).drop_duplicates("SERIALNO")
    hu = hu.merge(pers_inc, on="SERIALNO", how="left", suffixes=("", "_per"))
    hu.loc[hu.HINCP.isna(), "HINCP"] = hu["PINCP"]
    hu = hu.drop(columns=["PINCP"], errors="ignore")

    # Income deflation
    deflator = enc["income_deflator_2021_to_2000"]
    adjinc_scale = enc["adjinc_scale"]
    hu["hh_income_2021"] = (hu.ADJINC / adjinc_scale) * hu.HINCP
    hu["income"] = hu.hh_income_2021 * deflator

    # --- Filtering ---
    hu = hu.loc[hu.NP > 0]  # remove vacant units
    per = per.merge(hu[["SERIALNO", "TYPEHUGQ"]], on="SERIALNO", how="left")
    hu = hu.loc[hu.TYPEHUGQ != gq_inst]
    per = per.loc[per.TYPEHUGQ != gq_inst]
    logger.info("After filtering: %s HH, %s persons", f"{len(hu):,}", f"{len(per):,}")

    # Unique household ID
    hu = hu.reset_index(drop=True)
    hu["household_id"] = hu.index + 1
    per = per.merge(hu[["SERIALNO", "WGTP", "household_id"]], on="SERIALNO", how="left",
                    suffixes=("", "_hu"))

    # --- Cross-table: GQ type + weight transfer ---
    gq_col_schg = enc["gq_college_schg"]
    gq_mil = enc["gq_military_mil"]
    per["gqtype"] = np.select(
        [(per.TYPEHUGQ == gq_noninst) & (per.MIL == gq_mil),
         (per.TYPEHUGQ == gq_noninst) & per.SCHG.isin(gq_col_schg),
         per.TYPEHUGQ == gq_noninst],
        [gq["military"], gq["college"], gq["other"]],
        default=gq["not_gq"],
    ).astype(np.uint8)

    gq_wt = per[["SERIALNO", "PWGTP", "gqtype"]].drop_duplicates("SERIALNO")
    hu = hu.merge(gq_wt, on="SERIALNO", how="left")
    hu.loc[hu.TYPEHUGQ == gq_noninst, "WGTP"] = hu.PWGTP
    hu = hu.drop(columns=["PWGTP"])
    hu = hu.rename(columns={"gqtype": "hhgqtype"})

    # Write
    working_dir.mkdir(parents=True, exist_ok=True)
    hu.to_csv(working_dir / "seed_households.csv", index=False)
    per.to_csv(working_dir / "seed_persons.csv", index=False)
    logger.info("Wrote seed files to %s", working_dir)



def run_populationsim(
    *,
    working_dir: Path,
    output_dir: Path,
    pums: dict[str, Path | str],
    controls: dict[str, Path | str],
    skip_seed: bool = False,
    skip_synthesis: bool = False,
) -> Path:
    """Run the full PopulationSim pipeline. Returns the output directory.

    Args:
        working_dir: Working directory for intermediate files.
        output_dir: Where to write final results.
        pums: {"household": path/url, "person": path/url} to raw PUMS CSVs.
        controls: {"taz": ..., "county": ..., "region": ...} control totals.
        skip_seed: Skip seed population creation.
        skip_synthesis: Skip the PopulationSim synthesis step.
    """
    working_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1 — Seed population from PUMS
    if not skip_seed and not (working_dir / "seed_households.csv").exists():
        create_seed_population(pums["household"], pums["person"], working_dir) # pyright: ignore[reportArgumentType]

    # 2 — Fetch/preprocess control totals
    if not (working_dir / "taz_summaries_hhgq.csv").exists():
        taz = pd.read_csv(controls["taz"])
        taz["numhh_gq"] = taz.TOTHH + taz.gq_tot_pop
        taz["hh_size_1_gq"] = taz.hh_size_1 + taz.gq_tot_pop
        taz.to_csv(working_dir / "taz_summaries_hhgq.csv", index=False)
        logger.info("Wrote TAZ controls (%d rows) to %s", len(taz), working_dir)

    if not (working_dir / "county_controls.csv").exists():
        pd.read_csv(controls["county"]).to_csv(working_dir / "county_controls.csv", index=False)
        logger.info("Wrote county controls to %s", working_dir)

    if not (working_dir / "region_controls.csv").exists():
        pd.read_csv(controls["region"]).to_csv(working_dir / "region_controls.csv", index=False)
        logger.info("Wrote region controls to %s", working_dir)

    # 3 — Run PopulationSim synthesis
    if not skip_synthesis and not (working_dir / "pipeline" / "synthetic_households.csv").exists():
        xwalk = working_dir / "geo_cross_walk.csv"
        if not xwalk.exists():
            shutil.copy2(CONFIGS_DIR / "geo_cross_walk.csv", xwalk)

        popsim_output = working_dir / "pipeline"
        popsim_output.mkdir(parents=True, exist_ok=True)

        configs_mp = CONFIGS_DIR.parent / "configs_mp"
        config_dirs = [str(configs_mp), str(CONFIGS_DIR)] if configs_mp.is_dir() else [str(CONFIGS_DIR)]  # noqa: E501

        from populationsim import run as _popsim_run
        from populationsim.run import add_run_args as _popsim_add_run_args

        cli_args = [x for d in config_dirs for x in ("-c", d)]
        cli_args += ["-d", str(working_dir), "-o", str(popsim_output)]
        if configs_mp.is_dir():
            cli_args += ["-m"]

        parser = argparse.ArgumentParser()
        _popsim_add_run_args(parser)
        args = parser.parse_args(cli_args)

        logger.info(
            "Running PopulationSim: configs=%s, data=%s, output=%s",
            config_dirs,
            working_dir,
            popsim_output,
        )
        _popsim_run(args)

    # 4 — Copy final CSVs to output_dir (add person_id, fill HHT NaN)
    popsim_output = working_dir / "pipeline"
    if not (output_dir / "households.csv").exists():
        hh = pd.read_csv(popsim_output / "synthetic_households.csv")
        per = pd.read_csv(popsim_output / "synthetic_persons.csv")
        hh.loc[hh.HHT.isna(), "HHT"] = 0
        per["person_id"] = per.index + 1
        hh.to_csv(output_dir / "households.csv", index=False)
        per.to_csv(output_dir / "persons.csv", index=False)
        logger.info("Wrote households.csv and persons.csv to %s", output_dir)

    return output_dir


def kwargs_from_config(
    scenario: str,
    scenarios_dir: Path,
    netpaths: dict[str, str] | None = None,
) -> dict:
    """Build run() keyword arguments from scenarios/<scenario>.yaml."""
    cfg, project_dir = load_scenario_config(scenario, scenarios_dir, "populationsim", netpaths)
    return {
        "working_dir": project_dir / cfg.get("working_dir", ".cache"),
        "output_dir": project_dir / cfg.get("output_dir", ".cache/output"),
        "pums": {k: resolve_path(v, project_dir) for k, v in cfg["pums"].items()},
        "controls": {k: resolve_path(v, project_dir) for k, v in cfg["controls"].items()},
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    _SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"

    # Netpath mapping (for running on M: drive with different local structure)
    _NETPATHS = {
        "M:": r"\\models.ad.mtc.ca.gov\data\models",
    }

    parser = argparse.ArgumentParser(description="Run PopulationSim for a TM1a scenario.")
    parser.add_argument(
        "--scenario",
        required=True,
        help="Scenario name (must match a file in scenarios/)",
    )
    _args = parser.parse_args()

    run_populationsim(**kwargs_from_config(_args.scenario, _SCENARIOS_DIR, _NETPATHS))
