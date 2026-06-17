"""Windows-only ``.tpp`` → ``.omx`` matrix conversion wrapper. See §3a, §7.

``MatrixConverter`` runs a fixed CUBE ``.s`` script (a sequence of
``CONVERTMAT`` statements) inside a scenario directory to convert CUBE's binary
``.tpp`` matrix outputs into Python-readable ``.omx`` files written alongside
them. It is structurally parallel to :class:`~models.travel_model.runner.ModelRunner`
— same Windows-only guard, subprocess invocation, and exit-code capture — but is
a separate class because it is a conceptually distinct post-run step with its own
success/failure outcome (§8).

The ``.s`` script is run directly through CUBE's CLI (``runtpp`` / ``voyager.exe``),
not via a ``.bat`` wrapper (§3a). The converter itself is unconditional: the
"don't convert if the model run failed" rule (§8) lives in the caller
(``ScenarioManager``), not here.
"""
from __future__ import annotations

from pathlib import Path

from .runner import ensure_windows, stream_subprocess

# Fixed conversion script shipped with this package (§10, cube_scripts/).
DEFAULT_CONVERSION_SCRIPT = Path(__file__).parent / "cube_scripts" / "tpp_to_omx.s"
"""Path to the package-owned ``.tpp`` → ``.omx`` CUBE script. See §3a, §10."""

CUBE_SCRIPT_RUNNER = "runtpp"
"""CUBE CLI program that runs a ``.s`` script directly (no ``.bat``). See §3a."""


class MatrixConverter:
    """Wraps subprocess invocation of the ``.tpp`` → ``.omx`` CUBE script. See §3a, §7.

    Parameters
    ----------
    scenario_root : Path
        The extracted scenario directory. Used as the working directory so the
        script's relative paths (``data\\interim\\...`` etc.) resolve correctly.
    script_path : Path | None, optional
        The ``.s`` conversion script to run. Defaults to the package-owned
        :data:`DEFAULT_CONVERSION_SCRIPT`; overridable for tests (a trivial
        placeholder script) or a future real script.
    """

    def __init__(self, scenario_root: Path, script_path: Path | None = None) -> None:
        """Bind the scenario root and conversion script path.

        Parameters
        ----------
        scenario_root : Path
            The extracted scenario directory (also the working directory).
        script_path : Path | None, optional
            The ``.s`` script to run; defaults to the packaged conversion script.
        """
        self._scenario_root = Path(scenario_root)
        self._script_path = (
            DEFAULT_CONVERSION_SCRIPT if script_path is None else Path(script_path)
        )

    @property
    def script_path(self) -> Path:
        """Return the ``.s`` conversion script path to execute. See §3a.

        Returns
        -------
        Path
            The resolved conversion script path.
        """
        return self._script_path

    def run(self) -> int:
        """Run the conversion script via CUBE's CLI and return its exit code. See §3a, §5.5.

        Runs unconditionally; the caller decides whether conversion should be
        attempted at all (§8). The working directory is the scenario root so the
        script's relative paths resolve correctly (§3a).

        Returns
        -------
        int
            The process exit code. ``0`` means success (§5.5, §8).

        Raises
        ------
        RuntimeError
            If invoked on a non-Windows platform (§2). Expected and correct
            off-Windows — not a bug.
        FileNotFoundError
            If the conversion script does not exist.
        """
        ensure_windows("matrix conversion (.tpp -> .omx)")
        if not self.script_path.is_file():
            raise FileNotFoundError(f"conversion script not found: {self.script_path}")
        return stream_subprocess(
            [CUBE_SCRIPT_RUNNER, str(self.script_path)], cwd=self._scenario_root
        )
