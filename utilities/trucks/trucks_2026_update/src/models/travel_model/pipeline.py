"""The scenario pipeline, as plain functions read top to bottom.

Per scenario: extract the base zip, replace a few files, run the model ``.bat``,
then convert its ``.tpp`` matrices to ``.omx`` and its ``.net`` network to
shapefiles. Everything except the three CUBE steps (``.bat`` and the two
conversions) works on macOS; those raise a clear error off-Windows.

Run a quick offline smoke check with::

    python -m models.travel_model.pipeline
"""
from __future__ import annotations

from os import environ
import time
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import requests

from .config import RunConfig, Replacement, Scenario

# CUBE scripts shipped with this package (templates you fill in for real, see spec).
SCRIPTS_DIR = Path(__file__).parent / "cube_scripts"


def resolve_source(source: str) -> str:
    """Return a local path to copy, downloading the source first if it's on GitHub.

    Parameters
    ----------
    source : str
        A local file path, or a GitHub URL (``github.com`` /
        ``raw.githubusercontent.com``). Whatever URL you paste is fetched exactly
        — paste a permalink (with the commit hash) if you want it pinned.

    Returns
    -------
    str
        A local filesystem path: the downloaded temp file for a GitHub URL, or
        ``source`` unchanged for a local path.

    Raises
    ------
    requests.HTTPError
        If a GitHub URL can't be fetched (e.g. 404).
    """
    if "github.com" not in source and "raw.githubusercontent.com" not in source:
        return source

    raw_url = source.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    response = requests.get(raw_url)
    response.raise_for_status()
    downloaded = Path(tempfile.mkdtemp()) / Path(raw_url).name
    downloaded.write_bytes(response.content)
    return str(downloaded)


def extract_scenario(base_zip: str, scenario_dir: Path) -> None:
    """Delete ``scenario_dir`` if present, extract ``base_zip``, strip any wrapper folder.

    Many zips made from a single folder put everything one level too deep. If the
    extract produced exactly one top-level entry and it's a directory, its
    contents are moved up into ``scenario_dir`` and the empty wrapper removed.
    Any other shape is left as-is.

    Parameters
    ----------
    base_zip : str
        Path to the zip to extract.
    scenario_dir : Path
        Folder to (re)create and extract into.
    """
    if scenario_dir.exists():
        shutil.rmtree(scenario_dir)
    scenario_dir.mkdir(parents=True)

    with zipfile.ZipFile(base_zip) as archive:
        archive.extractall(scenario_dir)

    entries = list(scenario_dir.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        wrapper = entries[0]
        for item in wrapper.iterdir():
            shutil.move(str(item), str(scenario_dir / item.name))
        wrapper.rmdir()


def apply_replacements(scenario_dir: Path, replacements: list[Replacement]) -> None:
    """Copy each replacement's resolved source over its destination.

    Checks that every destination already exists before copying anything, so a
    typo'd path fails loudly instead of partially applying.

    Parameters
    ----------
    scenario_dir : Path
        Root of the extracted scenario, used to resolve relative destinations.
    replacements : list[Replacement]
        Source/destination pairs to apply.

    Raises
    ------
    FileNotFoundError
        If one or more destinations don't already exist in ``scenario_dir``. The
        message lists every missing path, not just the first.
    """
    missing = [r.destination for r in replacements if not (scenario_dir / r.destination).exists()]
    if missing:
        raise FileNotFoundError("destination(s) not found in scenario: " + ", ".join(missing))

    for replacement in replacements:
        source_path = resolve_source(replacement.source)
        shutil.copyfile(source_path, scenario_dir / replacement.destination)


def _require_windows() -> None:
    """Raise unless running on Windows (the CUBE steps need it).

    Raises
    ------
    RuntimeError
        If the current platform is not Windows.
    """
    if sys.platform != "win32":
        raise RuntimeError(f"this step needs Windows (CUBE); you're on {sys.platform!r}")


def _run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> bool:
    """Run a command, stream its output, and return whether it exited 0.

    Parameters
    ----------
    command : list[str]
        Command and arguments.
    cwd : Path
        Working directory.

    Returns
    -------
    bool
        ``True`` if the process exited 0, else ``False``.
    """
    process = subprocess.Popen(
        command, 
        cwd=str(cwd), 
        env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    for line in process.stdout:
        print(line, end="")
    process.wait()
    return process.returncode == 0


def run_bat(scenario_dir: Path) -> bool:
    """Run ``<scenario_dir>/CTRAMP/RunIteration.bat`` and return whether it exited 0.

    Parameters
    ----------
    scenario_dir : Path
        The extracted scenario root.

    Returns
    -------
    bool
        ``True`` if the ``.bat`` exited 0.

    Raises
    ------
    RuntimeError
        If called on a non-Windows platform.
    """
    _require_windows()
    model_env = environ.copy()
    # Assume running iteration 1
    # Values taken from: 
    # https://github.com/BayAreaMetro/travel-model-one/blob/4c756c05260def2b572a19f6714841eecb66c932/model-files/RunModel.bat#L276-L279
    model_env["ITER"] = str(1)
    model_env["PREV_ITER"] = str(1)
    model_env["PREV_WGT"] = str(0.0)
    model_env["WGT"] = str(1.0)
    bat = scenario_dir / "CTRAMP" / "RunIteration.bat"
    return _run(["cmd", "/c", str(bat)], cwd=scenario_dir, env=model_env)


def run_conversion(scenario_dir: Path) -> bool:
    """Run the ``.tpp`` → ``.omx`` script (``runtpp``) and return whether it exited 0.

    Parameters
    ----------
    scenario_dir : Path
        The scenario root; used as the working directory so the script's relative
        paths resolve against it.

    Returns
    -------
    bool
        ``True`` if the conversion exited 0.

    Raises
    ------
    RuntimeError
        If called on a non-Windows platform.
    """
    _require_windows()
    return _run(["runtpp", str(SCRIPTS_DIR / "tpp_to_omx.s")], cwd=scenario_dir)


def run_net_conversion(scenario_dir: Path) -> bool:
    """Run the ``.net`` → shapefile script (``runtpp``) and return whether it exited 0.

    Parameters
    ----------
    scenario_dir : Path
        The scenario root; used as the working directory.

    Returns
    -------
    bool
        ``True`` if the conversion exited 0.

    Raises
    ------
    RuntimeError
        If called on a non-Windows platform.
    """
    _require_windows()
    source_script = SCRIPTS_DIR / "net_to_shp.s"
    local_script = scenario_dir / "net_to_shp.s"
    shutil.copyfile(source_script, local_script)
    return _run(["runtpp", local_script.name], cwd=scenario_dir)


def run_scenario(scenario: Scenario, base_zip: str, output_root: Path) -> None:
    """Run the full per-scenario pipeline, printing failures instead of raising.

    Extract → replace → ``.bat`` (skipped entirely if ``skip_if_exists`` and the
    folder already exists), then both conversions — which always run unless the
    ``.bat`` was just run in this call and failed.

    Parameters
    ----------
    scenario : Scenario
        The scenario to run.
    base_zip : str
        Shared base zip (used unless the scenario overrides it).
    output_root : Path
        Parent folder for scenario directories.
    """
    scenario_dir = output_root / scenario.name
    zip_to_use = scenario.base_zip or base_zip

    bat_failed = False
    if scenario.skip_if_exists and scenario_dir.exists():
        print(f"[{scenario.name}] folder exists + skip_if_exists — leaving model alone")
    else:
        print(f"[{scenario.name}] extracting base zip")
        extract_scenario(zip_to_use, scenario_dir)
        print(f"[{scenario.name}] applying {len(scenario.replacements)} replacement(s)")
        apply_replacements(scenario_dir, scenario.replacements)
        print(f"[{scenario.name}] running RunIteration.bat")
        if not run_bat(scenario_dir):
            bat_failed = True
            print(f"[{scenario.name}] .bat failed — skipping conversions")

    if not bat_failed:
        # print(f"[{scenario.name}] converting .tpp -> .omx")
        # if not run_conversion(scenario_dir):
        #     print(f"[{scenario.name}] .tpp -> .omx conversion exited non-zero")
        print(f"[{scenario.name}] converting .net -> shapefiles")
        if not run_net_conversion(scenario_dir):
            print(f"[{scenario.name}] .net -> shapefile conversion exited non-zero")


def run_all(config: RunConfig) -> None:
    """Run every scenario in order, one at a time.

    Parameters
    ----------
    config : RunConfig
        An already-validated config.
    """
    output_root = Path(config.output_root)
    timings = []
    for scenario in config.scenarios:
        start = time.perf_counter()
        run_scenario(scenario, config.base_zip, output_root)
        elapsed = time.perf_counter() - start
        timings.append((scenario.name, elapsed))

    
    print("\n===== Scenario Timing Summary =====")
    total_time = 0.0
    
    for name, seconds in timings:
        minutes = seconds / 60
        print(f"{name:30s}  {seconds:8.1f} sec  ({minutes:.2f} min)")
        total_time += seconds

    print("-----------------------------------")
    print(f"{'TOTAL':30s}  {total_time:8.1f} sec  ({total_time/60:.2f} min)")



if __name__ == "__main__":
    # Quick offline smoke check (no Windows, no network): extract the mock base
    # zip into a scratch folder and show what landed, then confirm resolve_source
    # passes a local path through unchanged.
    _mock_zip = "data/external/mtc/full_run_2026.zip"
    _scratch = Path(tempfile.mkdtemp()) / "demo"
    extract_scenario(_mock_zip, _scratch)
    print("extracted top-level:", sorted(p.name for p in _scratch.iterdir()))
    print("resolve_source(local):", resolve_source("README.md"))
