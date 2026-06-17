"""Full orchestration across all scenarios.

``ScenarioManager`` loads and validates the ``RunConfig``, holds the run lock
(§5.6) for the whole run, and iterates scenarios sequentially (single CUBE seat),
calling workspace → manifest → runner → converter per scenario. It records
per-scenario outcomes without letting one failure abort the rest (§8), tracking
the model run and the ``.tpp`` → ``.omx`` conversion as independent outcomes —
conversion is a three-way result (succeeded / failed / skipped because the model
run failed, §8) — and produces a final summary.

This is the only module that knows about the Windows-only constraints, via
``runner`` and ``converter`` (§10).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml

from .config import RunConfig, Scenario
from .converter import MatrixConverter
from .lock import RunLock
from .manifest import write_manifest
from .runner import ModelRunner
from .workspace import ScenarioWorkspace


class Status(str, Enum):
    """Outcome of a single pipeline step for one scenario. See §8."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ScenarioResult:
    """Outcome record for a single scenario run. See §8.

    Parameters
    ----------
    name : str
        The scenario name this result describes.
    model : Status
        Outcome of the model run: ``SUCCEEDED``, ``FAILED``, or ``SKIPPED``
        (``skip_if_exists`` left the scenario untouched, §5.3 / §3a).
    conversion : Status
        Outcome of the ``.tpp`` → ``.omx`` conversion: ``SUCCEEDED``, ``FAILED``,
        or ``SKIPPED`` (not attempted because the model run failed, §8).
    detail : str | None
        Optional human-readable note (e.g. the error that caused a failure).
    """

    name: str
    model: Status
    conversion: Status
    detail: str | None = None


class ScenarioManager:
    """Loads config, iterates scenarios, and aggregates results. See §7, §8.

    Parameters
    ----------
    config : RunConfig
        The validated run configuration to execute.
    """

    def __init__(self, config: RunConfig) -> None:
        """Bind the validated ``RunConfig``.

        Parameters
        ----------
        config : RunConfig
            The validated run configuration.
        """
        self._config = config

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> ScenarioManager:
        """Load and validate a ``RunConfig`` from YAML and return a manager.

        Parameters
        ----------
        yaml_path : Path
            Path to the scenarios YAML file.

        Returns
        -------
        ScenarioManager
            A manager bound to the validated config.

        Raises
        ------
        pydantic.ValidationError
            If the config fails validation (all errors are reported, §8).
        """
        raw = yaml.safe_load(Path(yaml_path).read_text())
        return cls(RunConfig.model_validate(raw))

    def run(self) -> list[ScenarioResult]:
        """Execute all scenarios sequentially under the run lock. See §5.6, §8.

        Returns
        -------
        list[ScenarioResult]
            One result per scenario, regardless of individual failures.

        Raises
        ------
        RuntimeError
            If the run lock is already held (an overlapping run, §5.6).
        """
        results: list[ScenarioResult] = []
        with RunLock(Path(self._config.output_root)):
            for scenario in self._config.scenarios:
                results.append(self._run_one(scenario))
        return results

    def _run_one(self, scenario: Scenario) -> ScenarioResult:
        """Run a single scenario, capturing failures rather than raising. See §3, §8.

        Sequence: prepare (extract/skip) → replace → manifest → model run →
        conversion. The conversion only runs when the model succeeded or was
        skipped via ``skip_if_exists``; it is skipped when the model failed (§8).

        Parameters
        ----------
        scenario : Scenario
            The scenario to run.

        Returns
        -------
        ScenarioResult
            The model and conversion outcomes (and a detail note on failure).
        """
        workspace = ScenarioWorkspace(scenario, self._config)
        root = workspace.scenario_root

        try:
            rebuilt = workspace.prepare()
        except Exception as exc:  # noqa: BLE001 — record, don't abort the run (§8)
            return ScenarioResult(scenario.name, Status.FAILED, Status.SKIPPED, f"prepare failed: {exc}")

        if rebuilt:
            try:
                records = workspace.apply_replacements()
            except Exception as exc:  # noqa: BLE001
                return ScenarioResult(scenario.name, Status.FAILED, Status.SKIPPED, f"replacement failed: {exc}")

            write_manifest(scenario, root, workspace.base_zip_path, records)

            try:
                exit_code = ModelRunner(scenario, root).run()
            except Exception as exc:  # noqa: BLE001 — e.g. platform guard off-Windows (§2)
                return ScenarioResult(scenario.name, Status.FAILED, Status.SKIPPED, str(exc))
            if exit_code != 0:
                return ScenarioResult(
                    scenario.name, Status.FAILED, Status.SKIPPED, f"model run exit code {exit_code}"
                )
            model_status = Status.SUCCEEDED
        else:
            # skip_if_exists: left untouched; the model run is skipped (§3a).
            model_status = Status.SKIPPED

        # Conversion runs when the model succeeded or was skipped (§3a, §8).
        try:
            conv_code = MatrixConverter(root).run()
        except Exception as exc:  # noqa: BLE001
            return ScenarioResult(scenario.name, model_status, Status.FAILED, str(exc))
        if conv_code != 0:
            return ScenarioResult(
                scenario.name, model_status, Status.FAILED, f"conversion exit code {conv_code}"
            )
        return ScenarioResult(scenario.name, model_status, Status.SUCCEEDED)

    def summary(self, results: list[ScenarioResult]) -> str:
        """Format a human-readable final summary. See §8.

        Parameters
        ----------
        results : list[ScenarioResult]
            The per-scenario outcomes from :meth:`run`.

        Returns
        -------
        str
            A summary listing, per scenario, the model and conversion outcomes
            (and any failure detail), plus a one-line tally.
        """
        lines = ["Scenario run summary", "===================="]
        for result in results:
            line = (
                f"  {result.name}: model={result.model.value}, "
                f"conversion={result.conversion.value}"
            )
            if result.detail:
                line += f"  ({result.detail})"
            lines.append(line)

        failed = sum(
            1
            for r in results
            if Status.FAILED in (r.model, r.conversion)
        )
        skipped = sum(1 for r in results if r.model is Status.SKIPPED)
        ok = len(results) - failed
        lines.append("")
        lines.append(
            f"{len(results)} scenario(s): {ok} ok, {failed} with failures, "
            f"{skipped} skipped model run(s)."
        )
        return "\n".join(lines)
