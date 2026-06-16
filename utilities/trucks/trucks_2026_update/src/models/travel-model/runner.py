"""
ModelRunner: Windows-only .bat execution wrapper. See §7 and §2.

Raises a hard, explicit error if invoked on a non-Windows platform (§2).
Streams stdout/stderr and captures exit code (§5.5).
"""
from __future__ import annotations

from pathlib import Path

from .config import Scenario


DEFAULT_BAT_RELATIVE_PATH = "CTRAMP/RunIteration.bat"
"""Fixed internal path to the bat file within an extracted scenario. See §4.3.1."""


class ModelRunner:
    """
    Wraps subprocess invocation of a scenario's .bat file. See §7.

    Platform guard: raises immediately on non-Windows OS (§2).
    Success is defined as exit code 0 only (§5.5). No timeout is implemented (§5.5, §9).
    """

    def __init__(self, scenario: Scenario, scenario_root: Path) -> None:
        """Bind scenario and scenario_root; derive bat path from §4.3.1 or scenario override."""
        raise NotImplementedError("ModelRunner.__init__ not yet implemented")

    @property
    def bat_path(self) -> Path:
        """Return the full path to the .bat file to run. See §4.3.1."""
        raise NotImplementedError("ModelRunner.bat_path not yet implemented")

    def run(self) -> int:
        """
        Execute the .bat file, streaming output. Returns the exit code. See §5.5.

        Raises RuntimeError immediately if called on a non-Windows platform (§2).
        """
        raise NotImplementedError("ModelRunner.run not yet implemented")
