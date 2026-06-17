"""Pipeline smoke test — proves how far the pipeline actually runs. See §12.0.

Unlike the unit tests, this script exercises the real call chain one layer at a
time. Each layer either runs for real or raises
``NotImplementedError("ClassName.method — Phase N")``; the script walks the
layers in order, stops at the first not-yet-implemented one, and reports it as
the current implementation frontier.

What you can inspect
--------------------
Layers that produce files write them into ``.smoke_artifacts/`` at the repo root
(wiped fresh on every run, git-ignored). After running, open that folder to see
exactly what the pipeline created — extracted scenario trees, replaced files, the
provenance manifest, and a run summary. Each layer also prints a one-line summary.

Run it after any change to answer "is everything wired together so far?":

    python tests/models/travel_model/smoke_test.py

Layers (all implemented):
- Phase 2: validate config                          (no files)
- Phase 3: resolve a local source                   -> .smoke_artifacts/phase3_resolve/
- Phase 4: ScenarioWorkspace extract + replace      -> .smoke_artifacts/phase4_workspace/
- Phase 5: ModelRunner (Windows guard off-Windows)  (no files off-Windows)
- Phase 6: MatrixConverter (Windows guard)          (no files off-Windows)
- Phase 7: ScenarioManager.run() — full chain       -> .smoke_artifacts/phase7_manager/

Off-Windows, the Phase 5/6/7 model + conversion steps correctly hit the Windows
platform guard (§2); the smoke test reports that as the expected outcome.
"""
from __future__ import annotations

import shutil
import sys
from collections.abc import Callable
from pathlib import Path

import yaml

# Make `models.travel_model` importable when run as a plain script (not via -m).
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from models.travel_model import resolvers  # noqa: E402
from models.travel_model.config import LocalSource, RunConfig  # noqa: E402
from models.travel_model.converter import MatrixConverter  # noqa: E402
from models.travel_model.manager import ScenarioManager  # noqa: E402
from models.travel_model.runner import ModelRunner  # noqa: E402
from models.travel_model.workspace import ScenarioWorkspace  # noqa: E402

# The smoke test runs against the fake fixture config (local zip + local sources),
# not the user-facing configs/travel_model_scenarios.yaml, so it works on macOS.
CONFIG_PATH = Path(__file__).resolve().parent / "fixtures" / "scenarios.yaml"

# Durable, inspectable output. Wiped and recreated at the start of every run.
ARTIFACTS_DIR = REPO_ROOT / ".smoke_artifacts"


def _fixture_config(output_root: Path) -> RunConfig:
    """Load the fixture config, redirecting output into the artifacts dir."""
    config = RunConfig.model_validate(yaml.safe_load(CONFIG_PATH.read_text()))
    return config.model_copy(update={"output_root": str(output_root)})


def layer_phase2_validate_config() -> str:
    """Phase 2: validate the config YAML (no files produced)."""
    config = RunConfig.model_validate(yaml.safe_load(CONFIG_PATH.read_text()))
    names = ", ".join(s.name for s in config.scenarios)
    total = sum(len(s.replacements) for s in config.scenarios)
    return f"validated {len(config.scenarios)} scenario(s) [{names}], {total} replacement(s)"


def layer_phase3_resolve_local() -> str:
    """Phase 3: resolve a local source for real, leaving the copied file behind."""
    config = RunConfig.model_validate(yaml.safe_load(CONFIG_PATH.read_text()))
    repl = next(
        r
        for s in config.scenarios
        for r in s.replacements
        if isinstance(r.file_source, LocalSource)
    )
    destination = ARTIFACTS_DIR / "phase3_resolve" / repl.destination
    resolvers.resolve_source(repl.file_source, destination)
    matches = destination.read_bytes() == Path(repl.file_source.path).read_bytes()
    return (
        f"copied local source -> {destination.relative_to(REPO_ROOT)} "
        f"({destination.stat().st_size} bytes; identical to source: {matches})"
    )


def layer_phase4_workspace() -> str:
    """Phase 4: extract the base zip and apply replacements into an inspectable tree."""
    config = _fixture_config(ARTIFACTS_DIR / "phase4_workspace")
    workspace = ScenarioWorkspace(config.scenarios[0], config)
    workspace.prepare()
    records = workspace.apply_replacements()

    root = workspace.scenario_root
    n_files = sum(1 for p in root.rglob("*") if p.is_file())
    first = records[0]["destination"]
    return (
        f"extracted + replaced into {root.relative_to(REPO_ROOT)}/ "
        f"({n_files} files; {len(records)} replaced, e.g. {first})"
    )


def layer_phase5_runner() -> str:
    """Phase 5: invoke ModelRunner; off-Windows this correctly hits the platform guard."""
    config = _fixture_config(ARTIFACTS_DIR / "phase4_workspace")
    scenario = config.scenarios[0]
    root = ScenarioWorkspace(scenario, config).scenario_root
    runner = ModelRunner(scenario, root)
    try:
        code = runner.run()
        return f"ran {runner.bat_path.name} -> exit code {code}"
    except RuntimeError as exc:
        return f"platform guard correctly refused off-Windows ({exc})"


def layer_phase6_converter() -> str:
    """Phase 6: invoke MatrixConverter; off-Windows this correctly hits the platform guard."""
    config = _fixture_config(ARTIFACTS_DIR / "phase4_workspace")
    root = ScenarioWorkspace(config.scenarios[0], config).scenario_root
    converter = MatrixConverter(root)
    try:
        code = converter.run()
        return f"ran conversion script -> exit code {code}"
    except RuntimeError as exc:
        return f"platform guard correctly refused off-Windows ({exc})"


def layer_phase7_manager() -> str:
    """Phase 7: run the whole chain via ScenarioManager and leave the summary on disk."""
    output_root = ARTIFACTS_DIR / "phase7_manager"
    manager = ScenarioManager(_fixture_config(output_root))
    results = manager.run()
    (output_root / "RUN_SUMMARY.txt").write_text(manager.summary(results))
    parts = "; ".join(
        f"{r.name}: model={r.model.value}/conversion={r.conversion.value}" for r in results
    )
    return f"ScenarioManager.run() -> {parts} (see {output_root.relative_to(REPO_ROOT)}/)"


# Ordered deepest-allowed entry points; grows one entry per phase (§12.0).
LAYERS: list[tuple[str, Callable[[], str]]] = [
    ("Phase 2: RunConfig.model_validate", layer_phase2_validate_config),
    ("Phase 3: resolve_source (local)", layer_phase3_resolve_local),
    ("Phase 4: ScenarioWorkspace extract + replace", layer_phase4_workspace),
    ("Phase 5: ModelRunner", layer_phase5_runner),
    ("Phase 6: MatrixConverter", layer_phase6_converter),
    ("Phase 7: ScenarioManager.run()", layer_phase7_manager),
]


def main() -> int:
    """Walk the layers, report the frontier, and leave artifacts for inspection.

    Returns
    -------
    int
        ``0`` — reaching a ``NotImplementedError`` boundary is the expected,
        correct state before the pipeline is fully implemented; only an
        unexpected error (import error, wrong exception) is a real failure.
    """
    if ARTIFACTS_DIR.exists():
        shutil.rmtree(ARTIFACTS_DIR)
    ARTIFACTS_DIR.mkdir(parents=True)

    print(f"smoke test — config: {CONFIG_PATH.relative_to(REPO_ROOT)}")
    for label, fn in LAYERS:
        try:
            summary = fn()
        except NotImplementedError as exc:
            print(f"  x {label}")
            print(f"    frontier reached (expected): NotImplementedError: {exc}")
            break
        print(f"  ok {label}")
        print(f"     -> {summary}")
    else:
        print("  all wired layers passed")

    print(f"\ninspect what was created here: {ARTIFACTS_DIR.relative_to(REPO_ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
