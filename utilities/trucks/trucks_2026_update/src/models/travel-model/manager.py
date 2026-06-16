"""
ScenarioManager: full orchestration across all scenarios. See §7 and §8.

Loads RunConfig, acquires the run lock (§5.6), iterates scenarios sequentially,
catches per-scenario failures without aborting the rest (§8), and produces a final summary.
"""
from __future__ import annotations

from pathlib import Path

from .config import RunConfig


class ScenarioResult:
    """Outcome record for a single scenario run."""

    def __init__(self, name: str) -> None:
        raise NotImplementedError("ScenarioResult.__init__ not yet implemented")


class ScenarioManager:
    """
    Loads RunConfig, iterates scenarios, and aggregates results. See §7.

    Scenarios run sequentially (single CUBE seat). One scenario's failure does not
    abort the rest (§8). Holds the run lock for the entire run (§5.6).
    """

    def __init__(self, config: RunConfig) -> None:
        """Bind the validated RunConfig."""
        raise NotImplementedError("ScenarioManager.__init__ not yet implemented")

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ScenarioManager":
        """Load and validate a RunConfig from a YAML file, then return a ScenarioManager."""
        raise NotImplementedError("ScenarioManager.from_yaml not yet implemented")

    def run(self) -> list[ScenarioResult]:
        """
        Execute all scenarios sequentially under the run lock. See §5.6, §8.

        Returns a list of ScenarioResult (one per scenario) regardless of individual failures.
        """
        raise NotImplementedError("ScenarioManager.run not yet implemented")

    def summary(self, results: list[ScenarioResult]) -> str:
        """Format a human-readable final summary (succeeded / skipped / failed). See §8."""
        raise NotImplementedError("ScenarioManager.summary not yet implemented")
