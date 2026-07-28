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
import re
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
_CLUSTER = r"C:\Program Files\Citilabs\CubeVoyager\Cluster.exe"
_CUBE_PATH = ";".join(d for d in _CUBE_DIRS if Path(d).is_dir())

# Windows STATUS_ACCESS_VIOLATION (0xC0000005) — runtpp emits this when it cannot
# reach the Bentley license pipe at startup (signed and unsigned process-exit forms).
_ACCESS_VIOLATION = -1073741819
_ACCESS_VIOLATION_U = 3221225477

# Cube engine ReturnCode convention: 0 = ok, 1 = warnings, 2+ = fatal. MTC jobs
# tolerate warnings (``if ERRORLEVEL 2 goto done``), so only >= this is a failure.
_RC_FATAL = 2


class CubeJobError(RuntimeError):
    """A Cube ``.job`` exited non-zero or failed to run."""


def is_interactive_session() -> bool:
    """True if this process can reach the Bentley license pipe directly.

    The pipe is only available in the interactive desktop session; SSH
    (``SSH_CONNECTION``) and VS Code Remote (``VSCODE_AGENT_FOLDER``) cannot
    reach it, so Cube must be launched via :func:`run_cube_job`'s schtasks path.
    """
    return not (os.environ.get("SSH_CONNECTION") or os.environ.get("VSCODE_AGENT_FOLDER"))


def recover_license(*, hard: bool = False) -> None:
    """Clear stuck Cube processes; optionally restart the Bentley license agents.

    **Soft** (default): kill only orphaned Cube processes (``runtpp``/``Voyager``/
    ``Cluster``).  This clears stuck cluster nodes and their license leases without
    touching the Bentley CONNECT licensing chain — safe to call repeatedly.

    **Hard** (``hard=True``): additionally kill ``Bentley.Licensing.Service`` /
    ``FNPLicensingService`` so they respawn fresh on the next request.  This is a
    blunt instrument: killing the Bentley license agents repeatedly can leave the
    license entitlement itself broken (every later ``runtpp`` then access-violates
    at startup, requiring a manual CONNECTION Client restart / re-sign-in).  Use
    only as a deliberate last resort, never in an automatic retry loop.  The
    ``Bentley.Connect.Client`` is always left running to preserve sign-in.
    """
    images = ["runtpp.exe", "VOYAGER.EXE", "voyager.exe", "Cluster.exe"]
    if hard:
        images += ["Bentley.Licensing.Service.exe", "FNPLicensingService.exe"]
    for image in images:
        subprocess.run(["taskkill", "/f", "/im", image], capture_output=True, check=False)
    time.sleep(8)
    log.info("Cube recovery (%s): killed %s", "hard" if hard else "soft", ", ".join(images))


def _engine_returncode(log_text: str) -> int | None:
    """Authoritative Cube result parsed from the run log.

    ``runtpp.exe``'s *process* exit code can be a spurious .NET error
    (e.g. 0x80131509) even when the Voyager engine succeeded — notably when it
    reads a cubeio-written TPP.  The ``MATRIX/VOYAGER ReturnCode = N`` lines are
    the real result.  Returns the worst (max) ReturnCode found, or ``None`` if
    none are present (caller falls back to the process exit code).
    """
    codes = [int(m) for m in re.findall(r"ReturnCode\s*=\s*(\d+)", log_text)]
    return max(codes) if codes else None


def _env_lines(env_extra: dict[str, object] | None) -> str:
    if not env_extra:
        return ""
    return "\n".join(f"set {k}={v}" for k, v in env_extra.items()) + "\n"


def _cluster_lines(
    cluster_nodes: int | None, commpath: Path | None, *, opening: bool
) -> str:
    r"""Cube Cluster start/close lines for jobs that use ``DistributeMultistep``.

    MTC's assignment/skim/feedback jobs distribute their period (or class) steps
    across local Cube Cluster nodes and block on ``Wait4Files CTRAMP*.script.end``;
    without a running cluster they hang forever.  We faithfully reproduce
    ``RunModel.bat``'s ``Cluster "%COMMPATH%\\CTRAMP" 1-N Starthide Exit`` / ``…
    Close Exit`` bracketing, but self-contained per job so no node state has to
    survive across separately-scheduled tasks.
    """
    if not cluster_nodes or commpath is None:
        return ""
    base = f'"{commpath}\\CTRAMP" 1-{cluster_nodes}'
    if opening:
        # Defensive close clears any stale nodes from a prior aborted run.
        return (
            f'set COMMPATH={commpath}\n'
            f'"{_CLUSTER}" {base} Close Exit\n'
            f'"{_CLUSTER}" {base} Starthide Exit\n'
        )
    return f'"{_CLUSTER}" {base} Close Exit\n'


def _write_job_bat(
    job: Path,
    cwd: Path,
    sentinel: Path,
    logfile: Path,
    env_extra: dict[str, object] | None,
    *,
    cluster_nodes: int | None = None,
    commpath: Path | None = None,
) -> Path:
    """Write the launcher .bat run by the scheduled task (interactive session).

    When ``cluster_nodes`` is set the job is bracketed by Cube Cluster start/close;
    ``runtpp``'s exit code is captured into ``RC`` *before* the cluster close (which
    would otherwise clobber ``%ERRORLEVEL%``) and is what lands in the sentinel.
    """
    bat = textwrap.dedent(f"""\
        @echo off
        cd /d "{cwd}"
        set PATH={_CUBE_PATH};%PATH%
        {_env_lines(env_extra)}del /f "{sentinel}" 2>nul
        {_cluster_lines(cluster_nodes, commpath, opening=True)}\
        "{_RUNTPP}" "{job}" > "{logfile}" 2>&1
        set RC=%ERRORLEVEL%
        {_cluster_lines(cluster_nodes, commpath, opening=False)}\
        echo %RC% > "{sentinel}"
    """)
    bat_path = cwd / f"_cube_{job.stem}.bat"
    bat_path.write_text(bat, encoding="utf-8")
    return bat_path


def _progress_mtime(cwd: Path, logfile: Path, commpath: Path | None = None) -> float:
    """Latest mtime across the artifacts a *working* Cube job keeps touching.

    Cube writes its real output to ``TPPL*.PRN`` print files and, under a cluster,
    to per-node coordination files in ``commpath`` and the node working/print files
    — NOT to runtpp's redirected stdout, which can stay empty for the whole run.

    A long multi-period *highway assignment* in particular keeps its churn in the
    cluster's ``commpath`` and node scratch, touching nothing in ``cwd`` for minutes
    at a time, so watching only ``cwd`` falsely reads as "hung" (this is what
    false-killed a healthy 48-node run and cascaded into a broken license).  We
    therefore take the newest mtime across cwd's Cube artifacts *and* the entire
    ``commpath`` tree; a job genuinely hung on the license touches none of these.
    """
    latest = 0.0
    for pat in ("TPPL*.PRN", "TPPL*.prn", "ctramp*.script", "*.script*", logfile.name):
        for f in cwd.glob(pat):
            try:
                latest = max(latest, f.stat().st_mtime)
            except OSError:
                continue
    if commpath is not None and commpath.is_dir():
        for f in commpath.rglob("*"):
            try:
                latest = max(latest, f.stat().st_mtime)
            except OSError:
                continue
    return latest


def _run_via_schtasks(  # noqa: C901
    job: Path,
    cwd: Path,
    *,
    env_extra: dict[str, object] | None,
    timeout: float,
    cluster_nodes: int | None = None,
    commpath: Path | None = None,
) -> tuple[int, Path]:
    """Run ``runtpp <job>`` in the interactive session via schtasks; block.

    Returns the engine exit code and the path of the log it wrote (unique per
    run, so the caller never reads a previous run's output).
    """
    sentinel = cwd / f"_cube_{job.stem}.sentinel"
    # Unique per run.  A job killed mid-write (e.g. by license recovery) can leave
    # a handle on its log that outlives the process, making the path unwritable;
    # a fresh name sidesteps that instead of failing the next run.
    logfile = cwd / f"_cube_{job.stem}_{os.getpid()}_{int(time.time())}.log"
    bat = _write_job_bat(
        job, cwd, sentinel, logfile, env_extra,
        cluster_nodes=cluster_nodes, commpath=commpath,
    )
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
    # A stuck-license hang shows no Cube output progress; a healthy job keeps touching
    # its PRN/script/commpath files. A multi-period highway assignment can compute for
    # many minutes between cwd/commpath touches, so use a generous stall window for
    # cluster jobs — false-killing a healthy assignment then "recovering" the license
    # is far worse than waiting out a real hang.
    no_progress_grace = 1800 if cluster_nodes else 300
    last_progress = start
    last_sig = 0.0
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
            sig = _progress_mtime(cwd, logfile, commpath)
            if sig > last_sig:
                last_sig = sig
                last_progress = time.time()
            if running and time.time() - last_progress > no_progress_grace:
                # No Cube output progress for the whole window -> hung on
                # MatReaderOpen (a stuck Bentley license lease). Kill runtpp +
                # cluster nodes; caller recovers the license and retries once.
                for image in ("runtpp.exe", "Cluster.exe", "VOYAGER.EXE"):
                    subprocess.run(
                        ["taskkill", "/f", "/im", image], capture_output=True, check=False
                    )
                msg = (
                    f"Cube job {job.name} appears hung on the license "
                    f"(no output progress for {no_progress_grace:.0f}s)"
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

    if not logfile.exists():
        msg = (
            f"Cube job {job.name} wrote a sentinel but no log ({logfile.name}); "
            f"the output redirect never landed."
        )
        raise CubeJobError(msg)

    return int(sentinel.read_text().strip() or "1"), logfile


def run_cube_job(
    job: str | Path,
    cwd: str | Path,
    *,
    env_extra: dict[str, object] | None = None,
    timeout: float = 7200,
    cluster_nodes: int | None = None,
    commpath: str | Path | None = None,
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
    cluster_nodes
        If set, start a local Cube Cluster of this many nodes around the job
        (required by jobs using ``DistributeMultistep``/``Wait4Files`` — i.e. the
        assignment, skim and feedback jobs).  Must be >= the highest ``processNum``
        the job distributes (5 for the period-looped jobs).
    commpath
        Cluster communication directory (defaults to ``<cwd>/commpath``).  The job's
        ``%COMMPATH%`` token resolves to this.
    """
    job = Path(job).resolve()
    cwd = Path(cwd).resolve()
    if not job.exists():
        msg = f"Cube job not found: {job}"
        raise FileNotFoundError(msg)
    cwd.mkdir(parents=True, exist_ok=True)

    cpath: Path | None = None
    if cluster_nodes:
        cpath = Path(commpath).resolve() if commpath else cwd / "commpath"
        cpath.mkdir(parents=True, exist_ok=True)

    if is_interactive_session():
        env = os.environ.copy()
        env["PATH"] = _CUBE_PATH + ";" + env.get("PATH", "")
        if cpath is not None:
            env["COMMPATH"] = str(cpath)
        if env_extra:
            env.update({k: str(v) for k, v in env_extra.items()})
        log.info("Running Cube job %s (interactive)", job.name)
        if cluster_nodes:
            # Reuse the bat path so the cluster bracketing is identical to remote.
            sentinel = cwd / f"_cube_{job.stem}.sentinel"
            logfile = cwd / f"_cube_{job.stem}.log"
            sentinel.unlink(missing_ok=True)
            bat = _write_job_bat(
                job, cwd, sentinel, logfile, env_extra,
                cluster_nodes=cluster_nodes, commpath=cpath,
            )
            subprocess.run(
                ["cmd", "/c", str(bat)], cwd=str(cwd), env=env,
                capture_output=True, text=True, timeout=timeout, check=False,
            )
            rc = int(sentinel.read_text().strip() or "1") if sentinel.exists() else 1
            log_text = logfile.read_text(errors="replace") if logfile.exists() else ""
        else:
            proc = subprocess.run(
                [_RUNTPP, str(job)], cwd=str(cwd), env=env,
                capture_output=True, text=True, timeout=timeout, check=False,
            )
            rc, log_text = proc.returncode, proc.stdout or ""
    else:
        try:
            rc, logfile = _run_via_schtasks(
                job, cwd, env_extra=env_extra, timeout=timeout,
                cluster_nodes=cluster_nodes, commpath=cpath,
            )
        except (CubeJobError, TimeoutError) as exc:
            # A genuine hang leaves orphaned Cube processes/leases — a *soft*
            # recovery (kill stuck runtpp/Voyager/Cluster only) + one retry is the
            # safe fix.  We deliberately do NOT touch the Bentley license agents
            # here: killing them in a retry loop is what breaks the license.
            log.warning("Cube job %s failed (%s) — soft recover, retry once", job.name, exc)
            recover_license()
            rc, logfile = _run_via_schtasks(
                job, cwd, env_extra=env_extra, timeout=timeout,
                cluster_nodes=cluster_nodes, commpath=cpath,
            )
        log_text = logfile.read_text(errors="replace") if logfile.exists() else ""

    # A startup access-violation (0xC0000005 / -1073741819) means runtpp could not
    # reach the Bentley license pipe — a broken license entitlement, not a stuck
    # lease.  Retrying or killing license agents cannot fix it and only makes it
    # worse; fail fast with the manual remedy.
    if rc in (_ACCESS_VIOLATION, _ACCESS_VIOLATION_U) and _engine_returncode(log_text) is None:
        msg = (
            f"Cube job {job.name} access-violated at startup (exit={rc}): runtpp could "
            f"not reach the Bentley license. Restart the CONNECTION Client and "
            f"re-sign-in in the interactive session, then retry. (cwd={cwd})"
        )
        raise CubeJobError(msg)

    # The Voyager engine ReturnCode is authoritative; runtpp's process exit code
    # can be a spurious .NET error on an otherwise-successful run.  Cube's convention
    # is 0 = ok, 1 = warnings, 2 = fatal; every MTC job tolerates warnings
    # (``if ERRORLEVEL 2 goto done``), e.g. TRNBUILD emits ReturnCode 1 for benign
    # "zone access link does not connect to stop node" warnings — so accept rc < 2.
    engine_rc = _engine_returncode(log_text)
    ok = engine_rc < _RC_FATAL if engine_rc is not None else rc == 0
    if not ok:
        msg = (
            f"Cube job {job.name} failed (exit={rc}, engine ReturnCode={engine_rc}, "
            f"cwd={cwd})\n{log_text[-1500:]}"
        )
        raise CubeJobError(msg)
    log.info("Cube job %s OK (engine ReturnCode=%s, exit=%s)", job.name, engine_rc, rc)
    return 0
