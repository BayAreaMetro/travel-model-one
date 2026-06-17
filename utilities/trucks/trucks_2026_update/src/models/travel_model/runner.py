"""Windows-only ``.bat`` execution wrapper.

``ModelRunner`` runs a scenario's ``.bat`` under the CUBE license. It guards
against non-Windows platforms with a hard, explicit error (§2), streams output,
and treats exit code ``0`` as the sole success criterion (§5.5). No timeout is
implemented in v1 (§5.5, §9).

The two small helpers :func:`ensure_windows` and :func:`stream_subprocess` are
shared with :mod:`models.travel_model.converter`, which is structurally parallel
(a Windows-only subprocess wrapper).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .config import Scenario


DEFAULT_BAT_RELATIVE_PATH = "CTRAMP/RunIteration.bat"
"""Fixed internal bat path within an extracted scenario tree. See §4.3.1."""


def ensure_windows(step: str) -> None:
    """Raise unless running on Windows. See §2.

    Parameters
    ----------
    step : str
        Human-readable name of the step being guarded, used in the error message.

    Raises
    ------
    RuntimeError
        If the current platform is not Windows. This is a hard, explicit error —
        the step must never silently no-op off-Windows (§2).
    """
    if sys.platform != "win32":
        raise RuntimeError(
            f"{step} requires Windows (CUBE is Windows-only); "
            f"current platform is {sys.platform!r}."
        )


def stream_subprocess(command: list[str], cwd: Path) -> int:
    """Run a subprocess, streaming its combined output, and return the exit code.

    Cross-platform and CUBE-agnostic: this is the generic subprocess plumbing
    shared by the runner and converter, so it can be exercised on any platform by
    pointing it at a trivial dummy script.

    Parameters
    ----------
    command : list[str]
        The command and arguments to execute.
    cwd : Path
        Working directory for the subprocess.

    Returns
    -------
    int
        The process exit code (``0`` means success, §5.5). No timeout is applied
        (§5.5, §9).
    """
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
    process.wait()
    return process.returncode


class ModelRunner:
    """Wraps subprocess invocation of a scenario's ``.bat`` file. See §7, §2, §5.5.

    Parameters
    ----------
    scenario : Scenario
        The scenario being run; consulted for a ``bat_file`` override (§4.3.1).
    scenario_root : Path
        The extracted scenario directory; the bat path is resolved relative to it,
        and it is the subprocess working directory.
    """

    def __init__(self, scenario: Scenario, scenario_root: Path) -> None:
        """Bind the scenario and root.

        Parameters
        ----------
        scenario : Scenario
            The scenario being run.
        scenario_root : Path
            The extracted scenario directory.
        """
        self._scenario = scenario
        self._scenario_root = Path(scenario_root)

    @property
    def bat_path(self) -> Path:
        """Return the full path to the ``.bat`` file to execute. See §4.3.1.

        Returns
        -------
        Path
            ``<scenario_root>/CTRAMP/RunIteration.bat`` unless the scenario
            overrides ``bat_file`` (resolved relative to the scenario root if the
            override is itself relative).
        """
        override = self._scenario.bat_file
        if override is None:
            return self._scenario_root / DEFAULT_BAT_RELATIVE_PATH
        override_path = Path(override)
        if override_path.is_absolute():
            return override_path
        return self._scenario_root / override_path

    def run(self) -> int:
        """Execute the ``.bat`` file, streaming output, and return its exit code. See §5.5.

        Returns
        -------
        int
            The process exit code. ``0`` means success (§5.5).

        Raises
        ------
        RuntimeError
            If invoked on a non-Windows platform (§2). Expected and correct
            off-Windows — not a bug.
        FileNotFoundError
            If the resolved bat path does not exist in the scenario tree.
        """
        ensure_windows("model run (RunIteration.bat)")
        if not self.bat_path.is_file():
            raise FileNotFoundError(f"bat file not found in scenario tree: {self.bat_path}")
        return stream_subprocess(["cmd", "/c", str(self.bat_path)], cwd=self._scenario_root)
