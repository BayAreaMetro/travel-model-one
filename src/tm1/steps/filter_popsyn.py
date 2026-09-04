"""Filter unconnected-zone households out of the synthetic population.

Native replacement for two legacy pieces that ran back-to-back under the
``ITER==1`` guard in ``RunModel.bat``:

- ``model-files/scripts/skims/FindNoAccessZones.job`` — a Cube ``MATRIX`` pass
  flagging zones whose ``TOLLDISTDA`` skim row is entirely 500000 (Cube's
  no-path value), written to ``skims/unconnected_zones.csv``.
- ``model-files/scripts/preprocess/filterUnconnectedHouseholds.py`` (popsyn
  mode) — read that CSV, dropped households (and their persons) whose home TAZ
  is unconnected, or byte-copied the files through when nothing was flagged.

Here the zone scan happens in memory via :func:`cubeio.read_tpp` and no
handoff CSV is written.  A demand model asked to route a household out of a
zone with no path either crashes or produces garbage, so this runs before the
demand model ever sees the population; unconnected zones are a network coding
error and normally number zero, making the copy branch the production path.

Outputs use the canonical names ``hhFile.csv`` / ``personFile.csv`` that
``simulate_ctramp`` points CT-RAMP's properties at.  The legacy flow instead
kept the versioned input name (``hhFile.2023_v12.csv``) and had
``RuntimeConfiguration.py`` discover it; fixing the name at this seam keeps
the version tag where it belongs, on the ``INPUT/`` side.

Config::

    filter_popsyn:
      from: "{reference_run}/INPUT/popsyn"   # dir holding hhFile.* + personFile.*
      to: "{proj_dir}/popsyn"
      skim: "{proj_dir}/skims/HWYSKMAM.tpp"
      max_internal_zone: 1454                # zones above this are externals
"""

import logging
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from cubeio import read_tpp
from tm1.project.config import step_config
from tm1.status.slack import notify

log = logging.getLogger(__name__)

#: Cube's no-path cost.  FindNoAccessZones.job tests ``ROWMIN(TOLLDISTDA) == 500000``:
#: a zone is unconnected only when *every* destination, intrazonal included, is
#: unreachable by a tolled drive-alone path.
NO_PATH = 500_000.0

#: The skim table scanned for connectivity.
_TABLE = "TOLLDISTDA"

#: Source glob -> canonical output name.  Exactly one file must match each glob.
_FILES: dict[str, str] = {
    "hhFile.*": "hhFile.csv",
    "personFile.*": "personFile.csv",
}

_REQUIRED_KEYS = ("from", "to", "skim", "max_internal_zone")


def find_unconnected_zones(skim: Path, max_internal_zone: int) -> list[int]:
    """Zone numbers (1-based) with no tolled-DA path to any destination.

    Faithful to FindNoAccessZones.job's condition, with the external-zone
    exclusion filterUnconnectedHouseholds.py applied afterwards folded in:
    external zones (> *max_internal_zone*) hold no households, so their
    connectivity is not this step's problem.
    """
    mats = read_tpp(skim)
    if _TABLE not in mats["data"]:
        msg = f"{skim} has no {_TABLE} table; found {mats['tables']}"
        raise KeyError(msg)
    row_min = mats["data"][_TABLE].min(axis=1)
    flagged = (np.flatnonzero(row_min == NO_PATH) + 1).tolist()
    internal = [z for z in flagged if z <= max_internal_zone]
    log.info(
        "Unconnected zones in %s: %d flagged, %d internal (<= %d)",
        skim.name, len(flagged), len(internal), max_internal_zone,
    )
    return internal


def _single_match(src_dir: Path, pattern: str) -> Path:
    """The one file matching *pattern*, erroring on zero or several candidates."""
    matches = sorted(p for p in src_dir.glob(pattern) if p.is_file())
    if len(matches) != 1:
        found = ", ".join(p.name for p in matches) or "none"
        msg = f"Expected exactly one {pattern} in {src_dir}; found: {found}"
        raise FileNotFoundError(msg)
    return matches[0]


def _id_column(df: pd.DataFrame, path: Path) -> str:
    """The household-ID column name — legacy files spell it HHID or hh_id."""
    for col in ("HHID", "hh_id"):
        if col in df.columns:
            return col
    msg = f"{path} has neither an HHID nor an hh_id column"
    raise KeyError(msg)


def _filter_files(
    sources: dict[str, Path], out_dir: Path, unconnected: list[int]
) -> None:
    """Drop households home-based in *unconnected* zones from both popsyn files.

    The IDs to drop come from the household file's TAZ column — the person file
    carries no TAZ, only the household ID linking it back.
    """
    hh_path = sources["hhFile.*"]
    hh = pd.read_csv(hh_path)
    if "TAZ" not in hh.columns:
        msg = f"{hh_path} has no TAZ column; cannot locate households"
        raise KeyError(msg)
    drop_ids = hh.loc[hh["TAZ"].isin(unconnected), _id_column(hh, hh_path)].unique()

    msg = (
        f"filter_popsyn: dropping {len(drop_ids)} household(s) in "
        f"{len(unconnected)} unconnected zone(s): {unconnected}"
    )
    log.warning(msg)
    notify(f":warning: {msg}")

    for pattern, out_name in _FILES.items():
        df = pd.read_csv(sources[pattern])
        kept = df.loc[~df[_id_column(df, sources[pattern])].isin(drop_ids)]
        kept.to_csv(out_dir / out_name, index=False)
        log.info(
            "  %s: kept %d of %d rows -> %s",
            sources[pattern].name, len(kept), len(df), out_name,
        )


def run(
    config_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """Stage the synthetic population, filtered against network connectivity."""
    step_cfg = step_config(cfg, "filter_popsyn", kwargs)
    missing = [k for k in _REQUIRED_KEYS if k not in step_cfg]
    if missing:
        msg = f"filter_popsyn config is missing keys: {', '.join(missing)}"
        raise KeyError(msg)

    src_dir = Path(step_cfg["from"])
    out_dir = Path(step_cfg["to"])
    skim = Path(step_cfg["skim"])
    max_internal_zone = int(step_cfg["max_internal_zone"])

    if not kwargs.get("force", False) and all(
        (out_dir / name).exists() for name in _FILES.values()
    ):
        log.info("Popsyn files already staged in %s", out_dir)
        return "skipped"

    sources = {pattern: _single_match(src_dir, pattern) for pattern in _FILES}
    unconnected = find_unconnected_zones(skim, max_internal_zone)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not unconnected:
        # Byte-copy, not a pandas round-trip: with nothing to filter the staged
        # files stay identical to INPUT's, keeping them directly diffable.
        log.info("No unconnected zones -- copying popsyn files through unchanged")
        for pattern, out_name in _FILES.items():
            shutil.copy2(sources[pattern], out_dir / out_name)
    else:
        _filter_files(sources, out_dir, unconnected)
    return None
