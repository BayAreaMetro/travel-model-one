"""Where a run got to, and how to pick it up.

``tm1 status`` answers three questions that need three different sources: what the
config says will run (:mod:`tm1.run.iterations`), what the log says happened
(:mod:`tm1.status.read`), and whether Cube is working right now
(:mod:`cube.process`).

Read-only, and a separate process from the run it reports on. **Nothing here
imports** :mod:`tm1.run.model`: watching a run must not depend on the code that
runs one, or every change to the runner risks breaking the thing you use to find
out what the runner did.
"""

from pathlib import Path

from tm1.run import directory as run_directory
from tm1.run.prepare import latest_run
from tm1.status.grid import Sections, render, sections
from tm1.status.read import RunLog, harness_alive, read_logs

__all__ = ["RunLog", "Sections", "render", "sections", "status"]

def status(config_dir: Path, case: str | None = None) -> str:
    """Render the newest run's status, or say why there is nothing to show.

    Read-only in every sense: :func:`tm1.project.config.latest_run` finds the newest
    existing run rather than allocating one, so asking about a project cannot
    bring a run directory into being.
    """
    config_dir = Path(config_dir).resolve()
    prepared = latest_run(config_dir, case)
    if prepared is None:
        return f"\n  {config_dir.name}: nothing run yet.\n"

    cfg = prepared.cfg
    run_dir = prepared.run_dir
    label = f"{config_dir.name}:{run_dir.name}"

    state = read_logs(run_dir)
    if state is None:
        return f"\n  {label}: no run logs in {run_dir / 'logs'}.\n"

    # Said out loud rather than left for someone to notice: the newest run for
    # this case was produced by a different config than the one on disk now.
    stale = "" if prepared.state == run_directory.RESUME else (
        "\n  NOTE: config.yaml or cases.yaml has changed since this run.\n"
    )
    return stale + render(
        label,
        sections(cfg.get("steps") or []),
        state,
        run_dir,
        harness_alive(state),
    )
