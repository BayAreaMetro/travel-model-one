# ruff: noqa: S603, S607  (schtasks/runtpp are trusted system commands)
"""Run Cube Voyager ``.job`` scripts from Python, including over SSH/VS Code.

Cube's licensing (Bentley pipe) is only reachable from the **interactive Windows
desktop session**.  A direct ``subprocess`` call to ``runtpp`` from an SSH or
VS Code Remote session access-violates at startup because it can't reach the
license pipe.  The workaround (mirrored from :mod:`tm1.steps.simulate_ctramp`):

- **Interactive session** -> call ``runtpp`` directly (fast, simple).
- **Remote session** -> launch the job in the interactive session via Windows
  Task Scheduler (``schtasks /it``); Python stays remote and polls a sentinel
  file for the exit code, tailing the job log for progress.

Public API: :func:`run_cube_job`, :func:`is_interactive_session`.
"""

import logging
import os
import subprocess
import textwrap
import time
from pathlib import Path

log = logging.getLogger(__name__)

# Cube install dirs (from CTRAMP/runtime/SetPath.bat TPP_PATH). Prepended to PATH
# so runtpp and the Voyager engine + DLLs resolve.
_CUBE_DIRS = (
    r"C:\Program Files\Citilabs\CubeVoyager",
    r"C:\Program Files\Citilabs\VoyagerFileAPI",
    r"C:\Program Files\Bentley\OpenPaths\CubeVoyager",
)
_RUNTPP = r"C:\Program Files\Citilabs\CubeVoyager\runtpp.exe"
_CUBE_PATH = ";".join(d for d in _CUBE_DIRS if Path(d).is_dir())


class CubeJobError(RuntimeError):
    """A Cube ``.job`` exited non-zero or failed to run."""


def is_interactive_session() -> bool:
    """True if this process can reach the Bentley license pipe directly.

    The pipe is only available in the interactive desktop session; SSH
    (``SSH_CONNECTION``) and VS Code Remote (``VSCODE_AGENT_FOLDER``) cannot
    reach it, so Cube must be launched via :func:`run_cube_job`'s schtasks path.
    """
    return not (os.environ.get("SSH_CONNECTION") or os.environ.get("VSCODE_AGENT_FOLDER"))


def recover_license() -> None:
    """Clear a stuck Cube license lease (mirrors ``simulate_ctramp._recover_license``).

    A ``runtpp`` that hung on ``MatReaderOpen`` — e.g. launched a moment before
    Bentley was signed in — leaves a stuck lease in the Bentley/FlexNet license
    agents, so every later job hangs too.  Killing the lease-holding agents
    (which respawn on demand for the next license request) clears it.  The
    Bentley CONNECT client is deliberately left running so the user's sign-in
    is preserved.
    """
    for image in (
        "runtpp.exe", "VOYAGER.EXE", "voyager.exe",
        "Bentley.Licensing.Service.exe", "FNPLicensingService.exe",
    ):
        subprocess.run(["taskkill", "/f", "/im", image], capture_output=True, check=False)
    time.sleep(8)
    log.info("Recovered Cube license: killed stuck runtpp/Voyager + license agents")


def _env_lines(env_extra: dict[str, object] | None) -> str:
    if not env_extra:
        return ""
    return "\n".join(f"set {k}={v}" for k, v in env_extra.items()) + "\n"


def _write_job_bat(
    job: Path, cwd: Path, sentinel: Path, logfile: Path, env_extra: dict[str, object] | None
) -> Path:
    """Write the launcher .bat run by the scheduled task (interactive session)."""
    bat = textwrap.dedent(f"""\
        @echo off
        cd /d "{cwd}"
        set PATH={_CUBE_PATH};%PATH%
        {_env_lines(env_extra)}del /f "{sentinel}" 2>nul
        "{_RUNTPP}" "{job}" > "{logfile}" 2>&1
        echo %ERRORLEVEL% > "{sentinel}"
    """)
    bat_path = cwd / f"_cube_{job.stem}.bat"
    bat_path.write_text(bat, encoding="utf-8")
    return bat_path


def _run_via_schtasks(
    job: Path, cwd: Path, *, env_extra: dict[str, object] | None, timeout: float
) -> int:
    """Run ``runtpp <job>`` in the interactive session via schtasks; block."""
    sentinel = cwd / f"_cube_{job.stem}.sentinel"
    logfile = cwd / f"_cube_{job.stem}.log"
    bat = _write_job_bat(job, cwd, sentinel, logfile, env_extra)
    sentinel.unlink(missing_ok=True)
    task = f"tm1_cube_{job.stem}"

    subprocess.run(
        ["schtasks", "/create", "/tn", task, "/tr", f'cmd /c "{bat}"',
         "/sc", "once", "/st", "00:00", "/f", "/it", "/rl", "HIGHEST"],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(["schtasks", "/run", "/tn", task], check=True, capture_output=True, text=True)
    log.info("Launched Cube job %s via schtasks (interactive session)", job.name)

    start = time.time()
    deadline = start + timeout
    startup_grace = 120  # Cube startup can take ~60s+; let the task appear first
    hang_grace = 150  # a healthy runtpp writes its banner well within this
    seen_running = False
    try:
        while True:
            if sentinel.exists():
                break
            time.sleep(5)
            q = subprocess.run(
                ["schtasks", "/query", "/tn", task, "/fo", "csv", "/nh"],
                capture_output=True, text=True, check=False,
            )
            running = "Running" in q.stdout
            seen_running = seen_running or running
            if sentinel.exists():
                break
            empty_log = not logfile.exists() or logfile.stat().st_size == 0
            if running and empty_log and time.time() - start > hang_grace:
                # runtpp launched but produced zero output -> hung on MatReaderOpen
                # (a stuck Bentley license lease). Kill it; caller recovers + retries.
                subprocess.run(
                    ["taskkill", "/f", "/im", "runtpp.exe"], capture_output=True, check=False
                )
                msg = (
                    f"Cube job {job.name} appears hung on the license "
                    f"(no output after {hang_grace:.0f}s)"
                )
                raise CubeJobError(msg)
            if not running and seen_running:
                # Task ran then ended without writing the sentinel -> real failure.
                tail = logfile.read_text(errors="replace")[-2000:] if logfile.exists() else "(no log)"  # noqa: E501
                msg = f"Cube job {job.name} ended without a sentinel.\n{tail}"
                raise CubeJobError(msg)
            if not seen_running and time.time() - start > startup_grace:
                # Never started — usually means no interactive desktop session for /it.
                msg = (
                    f"Cube job {job.name} task never started within "
                    f"{startup_grace:.0f}s (schtasks /it needs an interactive "
                    f"desktop session). status: {q.stdout.strip()}"
                )
                raise CubeJobError(msg)
            if time.time() > deadline:
                msg = f"Cube job {job.name} timed out after {timeout:.0f}s"
                raise TimeoutError(msg)
    finally:
        subprocess.run(["schtasks", "/delete", "/tn", task, "/f"], capture_output=True, check=False)

    return int(sentinel.read_text().strip() or "1")


def run_cube_job(
    job: str | Path,
    cwd: str | Path,
    *,
    env_extra: dict[str, object] | None = None,
    timeout: float = 7200,
) -> int:
    """Run a Cube Voyager ``.job`` and return its exit code (raises on non-zero).

    Parameters
    ----------
    job
        Path to the ``.job`` script.
    cwd
        Working directory for the run (job-relative input/output paths resolve
        against this).
    env_extra
        Extra environment variables to set before running (e.g. iteration
        parameters ``ITER``/``WGT`` for assignment/feedback jobs).
    timeout
        Seconds to wait for completion (schtasks path).
    """
    job = Path(job).resolve()
    cwd = Path(cwd).resolve()
    if not job.exists():
        msg = f"Cube job not found: {job}"
        raise FileNotFoundError(msg)
    cwd.mkdir(parents=True, exist_ok=True)

    if is_interactive_session():
        env = os.environ.copy()
        env["PATH"] = _CUBE_PATH + ";" + env.get("PATH", "")
        if env_extra:
            env.update({k: str(v) for k, v in env_extra.items()})
        log.info("Running Cube job %s (interactive)", job.name)
        proc = subprocess.run(
            [_RUNTPP, str(job)], cwd=str(cwd), env=env,
            capture_output=True, text=True, timeout=timeout, check=False,
        )
        rc = proc.returncode
    else:
        try:
            rc = _run_via_schtasks(job, cwd, env_extra=env_extra, timeout=timeout)
        except (CubeJobError, TimeoutError) as exc:
            # Most failures here are a stuck license lease (hang) — recover and
            # retry once, which is the manual fix proven to work.
            log.warning("Cube job %s failed (%s) — recover license, retry once", job.name, exc)
            recover_license()
            rc = _run_via_schtasks(job, cwd, env_extra=env_extra, timeout=timeout)

    if rc != 0:
        msg = f"Cube job {job.name} exited {rc} (cwd={cwd})"
        raise CubeJobError(msg)
    log.info("Cube job %s OK", job.name)
    return rc
