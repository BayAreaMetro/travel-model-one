# ruff: noqa: S603, S607
# ^ subprocess calls to java/taskkill use PATH resolution intentionally.
"""Simulate step: run CTRAMP (Java CT-RAMP demand model).

Launches the legacy Java model with configurable RunModel.* flags.
Properties are patched in-place before each run.

Architecture
------------
CTRAMP runs as multiple Java processes communicating via RMI:

    ┌─────────────┐   ┌───────────────────┐   ┌──────────────────┐
    │ JPPF Driver │──▶│ JPPF Node (worker) │──▶│ MatrixDataServer │
    └─────────────┘   └───────────────────┘   └──────────────────┘
                              ▲                          │
                              │                    VoyagerFileAccess.dll
    ┌────────────────────┐    │                    (reads .tpp skims)
    │ MtcTourBasedModel  │────┘
    │  (main process)    │
    └────────────────────┘
            ▲
    ┌───────────────────┐
    │ HouseholdDataMgr  │
    └───────────────────┘

License constraint (Bentley/Cube):
    VoyagerFileAccess.dll requires the Bentley license pipe which is ONLY
    accessible from the interactive Windows desktop session.  SSH and VS Code
    Remote sessions cannot reach it.  When running remotely, all Java
    processes are launched in the interactive session via Windows Task
    Scheduler (schtasks /it) and monitored via log file tailing.

Execution modes:
    - Interactive session: direct subprocess.Popen (fast, simple)
    - SSH/remote session:  schtasks launcher bat → interactive session
      Python stays in SSH, monitors logs/sentinel for progress/completion.

Requires:
    - Java 8 (JDK 1.8.x) with JPPF and MTC jars on classpath
    - Cube Voyager 6.5+ installed (VoyagerFileAccess.dll + tppdlibx.dll)
    - Bentley CONNECTION Client signed in (for license)
    - Pre-built skims (.tpp) and accessibility files
    - Population synthesis outputs (popsyn/hhFile.csv, personFile.csv)

Usage in scenario_config.yaml::

    simulate_ctramp:
      project_dir: "E:/Projects/2023_TM161_IPA_35_testrun"
      host_ip: "123.123.123.123"  # IP address of the machine running CTRAMP
      iteration: 3
      sample_rate: 0.5
      components:
        UsualWorkAndSchoolLocationChoice: true
        AutoOwnership: true
        ...
"""

import contextlib
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

from tm1.config import step_config

log = logging.getLogger(__name__)

# Execution order of CTRAMP model components (matches mtcTourBased.properties).
COMPONENTS: list[str] = [
    # Usual work/school location
    "UsualWorkAndSchoolLocationChoice",
    # Auto ownership
    "AutoOwnership",
    # Free Parking
    "FreeParking",
    "CoordinatedDailyActivityPattern",
    # Mandatory Tours
    "IndividualMandatoryTourFrequency",
    "MandatoryTourDepartureTimeAndDuration",
    "MandatoryTourModeChoice",
    # Joint tours
    "JointTourFrequency",
    "JointTourLocationChoice",
    "JointTourDepartureTimeAndDuration",
    "JointTourModeChoice",
    # Individual non-mandatory tours must run after joint tours to see their updated
    "IndividualNonMandatoryTourFrequency",
    "IndividualNonMandatoryTourLocationChoice",
    "IndividualNonMandatoryTourDepartureTimeAndDuration",
    "IndividualNonMandatoryTourModeChoice",
    # At-work subtours
    "AtWorkSubTourFrequency",
    "AtWorkSubTourLocationChoice",
    "AtWorkSubTourDepartureTimeAndDuration",
    "AtWorkSubTourModeChoice",
    # Stop frequency/location (must be last to see all upstream tour info):
    "StopFrequency",
    "StopLocation",
]

# Components with additional sub-flags that must match the parent.
_SUB_FLAGS: dict[str, list[str]] = {
    "UsualWorkAndSchoolLocationChoice": [
        "UsualWorkAndSchoolLocationChoice.RunFlag.Work",
        "UsualWorkAndSchoolLocationChoice.RunFlag.University",
        "UsualWorkAndSchoolLocationChoice.RunFlag.School",
    ],
}


# ---------------------------------------------------------------------------
# Configuration patching
# ---------------------------------------------------------------------------


def components_to_flags(components: dict[str, bool]) -> dict[str, str]:
    """Convert a component on/off dict to the full set of properties flags."""
    flags: dict[str, str] = {}
    for name in COMPONENTS:
        val = "true" if components.get(name, False) else "false"
        flags[f"RunModel.{name}"] = val
        for sf in _SUB_FLAGS.get(name, []):
            flags[sf] = val
    return flags


# Default sample rates per global iteration, matching legacy RunModel.bat.
DEFAULT_SAMPLE_RATES: dict[int, float] = {1: 0.15, 2: 0.30, 3: 0.50}


#: Shadow-price passes per global round, as ``RuntimeConfiguration.py`` sets them.
#: A scenario overrides either key through ``shadow_price_passes:``; leaving it out
#: reproduces the legacy ladder exactly.
DEFAULT_SHADOW_PRICE_PASSES: dict[str, int] = {"first": 4, "subsequent": 2}


def _passes_for(iteration: int, passes: dict | None) -> int:
    """How many shadow-price passes this round runs.

    ``first`` and ``subsequent`` because that is the whole shape of the ladder:
    round 1 starts from zero prices and needs several passes to reach the right
    range; later rounds inherit prices that are already close and only top them up.
    """
    declared = passes or {}
    unknown = set(declared) - set(DEFAULT_SHADOW_PRICE_PASSES)
    if unknown:
        msg = (
            f"shadow_price_passes: unknown key(s) {', '.join(sorted(unknown))}. "
            f"Use {' and '.join(DEFAULT_SHADOW_PRICE_PASSES)} -- round 1 starts from "
            f"zero prices, every later round tops up the previous round's."
        )
        raise ValueError(msg)

    spec = {**DEFAULT_SHADOW_PRICE_PASSES, **declared}
    return int(spec["first"] if iteration == 1 else spec["subsequent"])


def shadow_pricing_flags(
    iteration: int,
    *,
    shadow_pricing: bool = True,
    passes: dict | None = None,
) -> dict[str, str]:
    """Return properties flags for shadow pricing at a given iteration.

    Matches the logic from legacy RuntimeConfiguration.py::

        Iteration 1:  no input file,                    MaximumIterations = 4
        Iteration 2:  input = main/ShadowPricing_3.csv, MaximumIterations = 2
        Iteration n:  input = main/ShadowPricing_{2n-1}.csv, MaxIter = 2

    A stock three-round run therefore performs 4 + 2 + 2 = **eight** passes, but
    the chain that survives is **seven**: round 2 restarts from
    ``ShadowPricing_3``, so round 1's fourth pass is computed and discarded.
    (Round 3 reading ``_5`` is what shows the numbering continues rather than
    restarting.)  Iteration 1 also starts from nothing, so a ``ShadowPricing_*.csv``
    staged into ``main/`` beforehand is never read.

    When *shadow_pricing* is False, forces MaximumIterations = 1 and comments
    out the input file (effectively disabling shadow pricing).

    *passes* overrides how many passes each round runs -- ``{"first": n,
    "subsequent": m}``, defaulting to :data:`DEFAULT_SHADOW_PRICE_PASSES`.  It is
    what a **convergence run** turns up: seven chained passes are known not to be
    enough.  See :func:`shadow_price_run_notes`.

    The input-file chain is deliberately not configurable -- it is derived from what
    the previous round wrote, so a free-hand value would name a file that does not
    exist.
    """
    prefix = "UsualWorkAndSchoolLocationChoice"
    flags: dict[str, str] = {}

    if not shadow_pricing:
        flags[f"{prefix}.ShadowPricing.MaximumIterations"] = "1"
        flags[f"{prefix}.ShadowPrice.Input.File"] = ""
        return flags

    flags[f"{prefix}.ShadowPricing.MaximumIterations"] = str(
        _passes_for(iteration, passes)
    )
    if iteration == 1:
        flags[f"{prefix}.ShadowPrice.Input.File"] = ""
    else:
        sp_input = 2 * iteration - 1
        flags[f"{prefix}.ShadowPrice.Input.File"] = f"main/ShadowPricing_{sp_input}.csv"

    return flags


def shadow_price_run_notes() -> str:
    """How to run shadow pricing to convergence, and why it is a separate run.

    Shadow prices adjust destination attractiveness until modeled employment and
    enrolment match the size terms.  The stock ladder gives them seven iterations
    across a full run, which is known to be insufficient -- the tell is the spread
    of modeled-to-target fill ratios, which stays wide instead of settling flat.

    Converging them is a *scenario*, not a step, because three things have to
    change together::

        simulate_ctramp:
          sample_rate: 1.0                 # at 0.15 the per-zone counts are noise
          shadow_price_passes:
            first: 30                      # instead of the ladder's 4
            subsequent: 30                 # ... and 2
          components:
            UsualWorkAndSchoolLocationChoice: true
            # every other component false -- location choice is the only model
            # shadow pricing touches, so the tour, trip and assignment stack is
            # dead weight here

    That combination is what makes it affordable: one component, one global
    iteration, no assignment.

    The product is a converged ``main/ShadowPricing_{N}.csv``.  Using it as a warm
    start needs one further change, because the ladder above clears the input file
    at iteration 1 -- a seeded run has to keep it.

    Converging shadow prices changes results, so it re-baselines whatever it
    touches.  It is deliberately not part of a parity run.
    """
    return shadow_price_run_notes.__doc__ or ""


def _popsyn_files(project_dir: Path) -> tuple[str, str]:
    """The synthetic-population filenames, found rather than assumed.

    ``RuntimeConfiguration.config_popsyn_files``: the files carry a version in
    the name (``hhFile.2023_v12.csv``), so the properties must state what is
    actually there.  Globbed in ``INPUT/popsyn`` because that is the shipped
    input; ``filterUnconnectedHouseholds.py`` copies the same names into
    ``popsyn/``, which is the path prefix CT-RAMP reads.  Hard-coding
    ``popsyn/hhFile.csv`` here is a FileNotFoundException three processes deep
    in the Java model.
    """
    found: list[str] = []
    for stem in ("hhFile", "personFile"):
        matches = sorted((project_dir / "INPUT" / "popsyn").glob(f"{stem}.*"))
        if len(matches) != 1:
            names = ", ".join(m.name for m in matches) or "none"
            msg = (
                f"Expected exactly one INPUT/popsyn/{stem}.* "
                f"(the legacy RuntimeConfiguration asserts this too); found: {names}"
            )
            raise FileNotFoundError(msg)
        found.append(f"popsyn/{matches[0].name}")
    return found[0], found[1]


def patch_properties(props_path: Path, flags: dict[str, str]) -> None:
    """Patch mtcTourBased.properties in-place. Backs up on first call.

    If a flag value is the empty string, the property line is commented out.
    """
    backup = props_path.with_suffix(".properties.backup")
    if not backup.exists():
        shutil.copy2(props_path, backup)

    content = props_path.read_text(encoding="utf-8")
    for key, value in flags.items():
        if value == "":
            # Comment out the property (whether already commented or not)
            pattern = rf"(^)(#?)\s*({re.escape(key)}\s*=\s*)(\S*)"
            content, n = re.subn(
                pattern, r"#\g<3>\g<4>", content, flags=re.MULTILINE,
            )
        else:
            pattern = rf"(^)(#?\s*)({re.escape(key)}\s*=\s*)(\S*)"
            content, n = re.subn(
                pattern, rf"\g<3>{value}", content, flags=re.MULTILINE,
            )
        if n == 0:
            if value == "":
                content += f"\n#{key} =\n"
            else:
                content += f"\n{key} = {value}\n"
            log.warning("Property %s not found — appending", key)

    props_path.write_text(content, encoding="utf-8")
    log.info("Patched %d flags in %s", len(flags), props_path.name)


def patch_jppf_configs(
    config_dir: Path, host_ip: str, *, threads: int = 24,
) -> None:
    """Patch JPPF config files with the correct host IP and thread count."""
    # Derive driver name from IP (e.g. "localhost" -> "driverlocalhost")
    last_part = host_ip.rsplit(".", maxsplit=1)[-1] if "." in host_ip else host_ip
    driver = f"driver{last_part}"

    # Patch driver name and server host in client properties
    client_files = ["jppf-clientDistributed.properties", "jppf-clientLocal.properties"]
    for filename in client_files:
        fpath = config_dir / filename
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8")
        content = re.sub(r"(\njppf\.drivers\s*=\s*)(\S*)", rf"\g<1>{driver}", content)
        content = re.sub(r"(\n)(driver[0-9a-z]+\.)", rf"\1{driver}.", content)
        content = re.sub(r"(jppf\.server\.host\s*=\s*)(\S*)", rf"\g<1>{host_ip}", content)
        content = re.sub(r"(jppf\.management\.host\s*=\s*)(\S*)", rf"\g<1>{host_ip}", content)
        fpath.write_text(content, encoding="utf-8")

    # Patch server host and thread count in driver and node properties
    other_files = ["jppf-driver.properties"]
    for i in range(5):
        other_files.append(f"jppf-node{i}.properties")
    for filename in other_files:
        fpath = config_dir / filename
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8")
        content = re.sub(r"(jppf\.server\.host\s*=\s*)(\S*)", rf"\g<1>{host_ip}", content)
        content = re.sub(
            r"(processing\.threads\s*=\s*)(\d+)", rf"\g<1>{threads}", content,
        )
        # Ensure jna.library.path is set for node child JVMs (DLL loading)
        if "node" in filename:
            jna_path = str(config_dir.parent).replace("\\", "/")
            # Remove any existing jna.library.path
            content = re.sub(r"\s+-Djna\.library\.path=\S+", "", content)
            # Append to active other.jvm.options line
            content = re.sub(
                r"(^other\.jvm\.options\s*=\s*.+)",
                rf"\1 -Djna.library.path={jna_path}",
                content,
                flags=re.MULTILINE,
            )
        fpath.write_text(content, encoding="utf-8")

    log.info(
        "Patched JPPF configs in %s (host=%s, driver=%s, threads=%d)",
        config_dir, host_ip, driver, threads,
    )


# ---------------------------------------------------------------------------
# Java infrastructure management
# ---------------------------------------------------------------------------


def _classpath(runtime_dir: Path) -> str:
    # Match SetPath.bat: config dir, runtime dir itself, JPPF libs, and mtc.jar
    parts: list[str] = [
        str(runtime_dir / "config"),
        str(runtime_dir),
        str(runtime_dir / "config" / "jppf-2.4" / "jppf-2.4-admin-ui" / "lib" / "*"),
        str(runtime_dir / "mtc.jar"),
    ]
    return ";".join(parts)


def _lib_path(runtime_dir: Path) -> str:
    """Build java.library.path: runtime dir + Cube Voyager DLL location."""
    paths = [str(runtime_dir)]
    # Standard Cube Voyager install paths (contains tppdlibx.dll for .tpp IO)
    for candidate in [
        Path(r"C:\Program Files\Citilabs\CubeVoyager"),
        Path(r"C:\Program Files\Bentley\OpenPaths\CubeVoyager"),
        Path(r"C:\Program Files\Citilabs\VoyagerFileAPI"),
        # Repo-bundled DLLs (VoyagerFileAccess.dll, tppioNative.dll)
        Path(__file__).resolve().parents[3] / "core" / "cmf" / "common-base" / "bin",
    ]:
        if candidate.exists():
            paths.append(str(candidate))
    return ";".join(paths)


def _env(classpath: str, lib_path: str) -> dict[str, str]:
    env = os.environ.copy()
    env["CLASSPATH"] = classpath
    # JNA loads native libraries from PATH (not java.library.path).
    # Prepend Cube DLL dirs so child JVMs (e.g. JPPF node worker) inherit them.
    env["PATH"] = lib_path + ";" + env.get("PATH", "")
    return env


def _ensure_native_dlls(runtime_dir: Path) -> None:
    """Ensure VoyagerFileAccess.dll is in the runtime dir for JNA loading.

    JNA finds the DLL via jna.library.path (set to runtime_dir).
    The DLL's transitive dependency tppdlibx.dll is resolved via PATH
    which includes C:\\Program Files\\Citilabs\\CubeVoyager (set in _env).
    This matches the legacy SetPath.bat approach exactly.
    """
    # Remove win32-x86-64/ if it exists — JNA resource-path search would
    # find the DLL there first, isolated from its PATH-resolved dependencies.
    stale = runtime_dir / "win32-x86-64"
    if stale.exists():
        shutil.rmtree(stale, ignore_errors=True)

    target = runtime_dir / "VoyagerFileAccess.dll"
    if target.exists():
        return

    # Find the DLL source — prefer VoyagerFileAPI install (matches MODEL3-C)
    for candidate in [
        Path(r"C:\Program Files\Citilabs\VoyagerFileAPI") / "VoyagerFileAccess.dll",
        Path(__file__).resolve().parents[3] / "core" / "cmf" / "common-base" / "bin" / "VoyagerFileAccess.dll",
    ]:
        if candidate.exists():
            shutil.copy2(candidate, target)
            log.info("Placed VoyagerFileAccess.dll at %s", target)
            return

    msg = "VoyagerFileAccess.dll not found — cannot run CTRAMP"
    raise FileNotFoundError(msg)


# ---------------------------------------------------------------------------
# License / session detection
# ---------------------------------------------------------------------------


def _is_interactive_session() -> bool:
    """Return True if the current process runs in an interactive desktop session.

    The Bentley license pipe (net.pipe://localhost/bentleyconnect/client/
    licenseservice) is only accessible from the interactive Windows session.
    SSH sessions, VS Code Remote terminals, and service sessions cannot reach
    the pipe, causing VoyagerFileAccess.dll to hang indefinitely on
    MatReaderOpen.
    """
    # SSH_CONNECTION is set by OpenSSH server for remote sessions
    if os.environ.get("SSH_CONNECTION"):
        return False
    # VS Code Remote sets VSCODE_AGENT_FOLDER
    if os.environ.get("VSCODE_AGENT_FOLDER"):
        return False
    return True


def _preflight_license() -> bool:
    """Check whether the Bentley license is accessible from this session.

    Returns True if we can safely call the DLL directly (interactive session).
    Returns False if we need to use schtasks to run in the interactive session.
    Does NOT touch the DLL — that would deadlock on failure.
    """
    if _is_interactive_session():
        log.info("Preflight: interactive session — direct execution OK")
        return True

    log.warning(
        "Preflight: SSH/remote session detected — Bentley license pipe "
        "is not accessible from this session. Java processes that load "
        "VoyagerFileAccess.dll will be launched in the interactive session "
        "via schtasks."
    )
    return False


def _recover_license() -> None:
    """Kill hung processes and allow Bentley license service to recover.

    Called during teardown to prevent the license from getting stuck.
    Safe to call even when nothing is hung.
    """
    for image in ["java.exe", "Cluster.exe", "runtpp.exe", "VOYAGER.EXE"]:
        subprocess.run(
            ["taskkill", "/f", "/im", image],
            capture_output=True, check=False,
        )
    # Restart Bentley services so the pipe recovers
    for image in ["Bentley.Connect.Client.exe", "Bentley.Licensing.Service.exe"]:
        subprocess.run(
            ["taskkill", "/f", "/im", image],
            capture_output=True, check=False,
        )
    # Bentley services auto-restart; give them time
    time.sleep(5)
    log.info("License recovery: killed processes, Bentley services restarting")


# ---------------------------------------------------------------------------
# schtasks-based execution (for SSH/remote sessions)
# ---------------------------------------------------------------------------

_TASK_NAME = "CTRAMP_Python_Run"
_SENTINEL_FILE = "ctramp_sentinel.txt"


def _write_launcher_bat(
    project_dir: Path,
    runtime_dir: Path,
    host_ip: str,
    *,
    iteration: int,
    sample_rate: float,
    seed: int,
) -> Path:
    """Write a .bat that starts infrastructure + runs the model.

    This .bat is executed via schtasks in the interactive session where
    the Bentley license pipe is accessible.
    """
    cp = _classpath(runtime_dir)
    lib = _lib_path(runtime_dir)
    sentinel = project_dir / _SENTINEL_FILE

    bat_content = textwrap.dedent(f"""\
        @echo off
        cd /d "{project_dir}"
        set CLASSPATH={cp}
        set PATH={lib};%PATH%

        del /f "{sentinel}" 2>nul

        echo Starting JPPF Driver...
        start /b java -server -Xmx16m ^
            -Dlog4j.configuration=log4j-driver.properties ^
            -Djppf.config=jppf-driver.properties ^
            org.jppf.server.DriverLauncher

        echo Starting JPPF Node...
        start /b java -server -Xmx16m ^
            -Dlog4j.configuration=log4j-node0.xml ^
            -Djppf.config=jppf-node0.properties ^
            org.jppf.node.NodeLauncher

        echo Starting Household Data Manager...
        start /b java -Xms20000m -Xmx20000m ^
            -Dlog4j.configuration=log4j_hh.xml ^
            com.pb.mtc.ctramp.MtcHouseholdDataManager ^
            -hostname {host_ip}

        echo Starting Matrix Data Server...
        start /b java -Xms14000m -Xmx14000m ^
            -Dlog4j.configuration=log4j_mtx.xml ^
            -Djava.library.path="{lib}" ^
            com.pb.models.ctramp.MatrixDataServer ^
            -hostname {host_ip}

        echo Waiting 15s for infrastructure startup...
        timeout /t 15 /nobreak >nul

        echo Running CTRAMP model...
        java -showversion -Xmx6000m ^
            -cp "{cp}" ^
            -Dlog4j.configuration=log4j.xml ^
            -Djava.library.path="{lib}" ^
            -Djppf.config=jppf-clientDistributed.properties ^
            com.pb.mtc.ctramp.MtcTourBasedModel mtcTourBased ^
            -iteration {iteration} ^
            -sampleRate {sample_rate} ^
            -sampleSeed {seed} >> "logs\\event_main.log" 2>&1

        echo %ERRORLEVEL% > "{sentinel}"
        taskkill /f /im java.exe >nul 2>&1
    """)

    bat_path = project_dir / "_ctramp_launcher.bat"
    bat_path.write_text(bat_content, encoding="utf-8")
    log.info("Wrote launcher bat: %s", bat_path)
    return bat_path


def _run_via_schtasks(
    project_dir: Path,
    runtime_dir: Path,
    host_ip: str,
    *,
    iteration: int,
    sample_rate: float,
    seed: int,
) -> None:
    """Launch the full CTRAMP run in the interactive session via schtasks.

    Monitors progress by tailing log files. Blocks until completion.
    """
    bat_path = _write_launcher_bat(
        project_dir, runtime_dir, host_ip,
        iteration=iteration, sample_rate=sample_rate, seed=seed,
    )
    sentinel = project_dir / _SENTINEL_FILE
    sentinel.unlink(missing_ok=True)

    # Create scheduled task that runs interactively (/it)
    subprocess.run(
        ["schtasks", "/create",
         "/tn", _TASK_NAME,
         "/tr", f'cmd /c "{bat_path}"',
         "/sc", "once",
         "/st", "00:00",
         "/f",  # force overwrite
         "/it",  # interactive only
         "/rl", "HIGHEST"],
        capture_output=True, check=True, text=True,
    )

    # Run it now
    subprocess.run(
        ["schtasks", "/run", "/tn", _TASK_NAME],
        capture_output=True, check=True, text=True,
    )
    log.info("Launched CTRAMP via schtasks (interactive session)")

    # Monitor via log file and sentinel
    logs_dir = project_dir / "logs"
    stop_event = threading.Event()
    monitor = threading.Thread(
        target=_monitor_logs, args=(logs_dir, stop_event), daemon=True,
    )
    monitor.start()

    try:
        # Poll for sentinel file (written when model completes)
        poll_interval = 10
        while not sentinel.exists():
            time.sleep(poll_interval)
            # Check if task is still running
            result = subprocess.run(
                ["schtasks", "/query", "/tn", _TASK_NAME, "/fo", "csv", "/nh"],
                capture_output=True, text=True, check=False,
            )
            if "Running" not in result.stdout and sentinel.exists():
                break
            if "Running" not in result.stdout and not sentinel.exists():
                # Task ended without sentinel — something crashed
                msg = (
                    "CTRAMP task ended without writing sentinel file. "
                    "Check logs in: " + str(logs_dir)
                )
                raise RuntimeError(msg)
    finally:
        stop_event.set()
        monitor.join(timeout=2)
        # Cleanup the scheduled task
        subprocess.run(
            ["schtasks", "/delete", "/tn", _TASK_NAME, "/f"],
            capture_output=True, check=False,
        )

    # Read exit code from sentinel
    exit_code_str = sentinel.read_text().strip()
    try:
        exit_code = int(exit_code_str)
    except ValueError:
        exit_code = -1

    if exit_code != 0:
        msg = f"CTRAMP exited with code {exit_code}"
        raise RuntimeError(msg)

    log.info("CTRAMP completed successfully (via schtasks)")


def start_infrastructure(
    runtime_dir: Path, project_dir: Path, host_ip: str,
) -> list[subprocess.Popen]:
    """Start JPPF driver, JPPF node, HH manager, and Matrix manager."""
    cp = _classpath(runtime_dir)
    lib = _lib_path(runtime_dir)
    java_env = _env(cp, lib)
    popen_kw: dict = {
        "cwd": str(project_dir),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "env": java_env,
    }

    procs = [
        # JPPF Driver
        subprocess.Popen(
            ["java", "-server", "-Xmx16m",
             "-Dlog4j.configuration=log4j-driver.properties",
             "-Djppf.config=jppf-driver.properties",
             "org.jppf.server.DriverLauncher"],
            **popen_kw,
        ),
        # JPPF Node (NodeLauncher forks a child JVM using other.jvm.options
        # from jppf-node0.properties; the child inherits our env/PATH which
        # includes Cube DLL dirs for JNA native library loading)
        subprocess.Popen(
            ["java", "-server", "-Xmx16m",
             "-Dlog4j.configuration=log4j-node0.xml",
             "-Djppf.config=jppf-node0.properties",
             "org.jppf.node.NodeLauncher"],
            **popen_kw,
        ),
        # Household Data Manager
        subprocess.Popen(
            ["java", "-Xms20000m", "-Xmx20000m",
             "-Dlog4j.configuration=log4j_hh.xml",
             "com.pb.mtc.ctramp.MtcHouseholdDataManager",
             "-hostname", host_ip],
            **popen_kw,
        ),
        # Matrix Data Server (must run as a separate process — the DLL is NOT
        # thread-safe; this serialises all matrix I/O via RMI).
        # Matches legacy: JavaOnly_runMain.cmd
        subprocess.Popen(
            ["java", "-Xms14000m", "-Xmx14000m",
             "-Dlog4j.configuration=log4j_mtx.xml",
             f"-Djava.library.path={lib}",
             "com.pb.models.ctramp.MatrixDataServer",
             "-hostname", host_ip],
            **popen_kw,
        ),
    ]
    log.info("Started Java infrastructure (5 processes); waiting 15s")
    time.sleep(15)
    return procs


def kill_infrastructure(procs: list[subprocess.Popen]) -> None:
    """Terminate Java infrastructure processes."""
    for p in procs:
        with contextlib.suppress(OSError):
            p.terminate()
    with contextlib.suppress(FileNotFoundError):
        subprocess.run(
            ["taskkill", "/f", "/im", "java.exe"],
            capture_output=True, check=False,
        )


# ---------------------------------------------------------------------------
# Log monitoring
# ---------------------------------------------------------------------------


def _monitor_logs(logs_dir: Path, stop: threading.Event) -> None:
    """Background thread: tail log files and forward all lines to Python logging.

    Monitors both the JPPF node log (event-node0.log) and the main model
    stdout log (event_main.log) so progress is visible from the SSH session.
    """
    targets = {
        "node": (logs_dir / "event-node0.log", 0),
        "main": (logs_dir / "event_main.log", 0),
    }
    interval = 3  # seconds between polls

    while not stop.wait(timeout=interval):
        for label, (path, offset) in list(targets.items()):
            if not path.exists():
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size <= offset:
                continue
            try:
                with path.open("r", encoding="utf-8", errors="replace") as f:
                    f.seek(offset)
                    new_text = f.read()
                targets[label] = (path, size)
            except OSError:
                continue
            for raw_line in new_text.splitlines():
                line = raw_line.strip()
                if line:
                    log.info("[%s] %s", label, line)


# ---------------------------------------------------------------------------
# Direct execution (interactive session only)
# ---------------------------------------------------------------------------


def run_model(
    project_dir: Path,
    runtime_dir: Path,
    *,
    iteration: int = 3,
    sample_rate: float = 0.5,
    seed: int = 0,
) -> None:
    """Run the MtcTourBasedModel Java process."""
    cp = _classpath(runtime_dir)
    lib = _lib_path(runtime_dir)
    java_env = _env(cp, lib)

    # Preflight: verify VoyagerFileAccess.dll is findable (fail fast)
    dll_found = any(
        (Path(d) / "VoyagerFileAccess.dll").exists()
        for d in lib.split(";") if d
    )
    if not dll_found:
        msg = (
            "PREFLIGHT FAILED: VoyagerFileAccess.dll not found in any lib path.\n"
            f"Searched: {lib}"
        )
        raise RuntimeError(msg)
    log.info("Preflight OK: VoyagerFileAccess.dll found")

    cmd = [
        "java", "-showversion", "-Xmx6000m",
        "-cp", cp,
        "-Dlog4j.configuration=log4j.xml",
        f"-Djava.library.path={lib}",
        "-Djppf.config=jppf-clientDistributed.properties",
        "com.pb.mtc.ctramp.MtcTourBasedModel", "mtcTourBased",
        "-iteration", str(iteration),
        "-sampleRate", str(sample_rate),
        "-sampleSeed", str(seed),
    ]
    log.info("CTRAMP: iter=%d sample=%s seed=%d", iteration, sample_rate, seed)

    # Start background log monitor
    logs_dir = project_dir / "logs"
    stop_event = threading.Event()
    monitor = threading.Thread(
        target=_monitor_logs, args=(logs_dir, stop_event), daemon=True,
    )
    monitor.start()

    proc = subprocess.Popen(
        cmd, cwd=str(project_dir), env=java_env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    for line in proc.stdout:  # pyright: ignore[reportOptionalIterable]
        sys.stdout.write(line)

    stop_event.set()
    monitor.join(timeout=2)

    if proc.wait() != 0:
        msg = f"CTRAMP exited with code {proc.returncode}"
        raise RuntimeError(msg)


# ---------------------------------------------------------------------------
# Step entry point
# ---------------------------------------------------------------------------


def run(scenario_dir: Path, cfg: dict, **kwargs: object) -> None:  # noqa: ARG001
    """Run CTRAMP with the component flags specified in scenario config.

    Supports two modes:

    * **Single iteration** (``iteration: 3``): run just that iteration with
      the given ``sample_rate``.  Shadow pricing input is derived from the
      iteration number (see :func:`shadow_pricing_flags`).
    * **Multi-iteration loop** (``iterations: 3``): run iterations 1 through N,
      ramping the sample rate per :data:`DEFAULT_SAMPLE_RATES`.  Infrastructure
      is started once and kept alive across iterations.  A per-iteration
      ``sample_rate`` key can override the default ramp.

    Config structure::

        steps:
          simulate_ctramp:
            project_dir: "E:/Projects/..."
            host_ip: "localhost"
            iterations: 3              # loop 1..3 (or "iteration: 3" for single)
            sample_rate: 0.5           # override per-iter default
            shadow_pricing: true       # set false to disable
            seed: 0
            components:
              UsualWorkAndSchoolLocationChoice: true
              ...
    """
    step_cfg = step_config(cfg, "simulate_ctramp", kwargs)
    project_dir = Path(step_cfg["project_dir"])
    runtime_dir = Path(step_cfg.get("runtime_dir", str(project_dir / "CTRAMP" / "runtime")))
    host_ip = step_cfg.get("host_ip", "localhost")
    seed = step_cfg.get("seed", 0)
    do_shadow_pricing = step_cfg.get("shadow_pricing", True)

    # One call runs one iteration.  The global feedback loop belongs to the
    # runner (`iterations:` in the scenario config), because an iteration is
    # demand *plus* assignment -- exactly what RunIteration.bat runs, and what
    # this step alone cannot express.
    if "iterations" in step_cfg:
        msg = (
            "steps.simulate_ctramp.iterations has moved to a top-level block, so "
            "the loop can include assignment:\n\n"
            "    iterations:\n"
            "      count: 3\n"
            "      steps: [simulate_ctramp, assignment]\n\n"
            "Looping demand here only re-ran the demand model against unchanged "
            "skims, which is not feedback."
        )
        raise ValueError(msg)

    iteration = int(kwargs.get("iteration") or step_cfg.get("iteration") or 1)

    # Per-iteration sample rate: explicit value overrides the default ramp.
    explicit_rate = step_cfg.get("sample_rate")

    # The Java model treats "localhost" specially by starting an in-process
    # MatrixDataServer.  We always start the server externally (separate 14GB
    # process, matching legacy JavaOnly_runMain.cmd) so the model must see a
    # non-"localhost" address to trigger the RMI client path.
    if host_ip.lower() == "localhost":
        host_ip = socket.gethostbyname(socket.gethostname())
        log.info("Resolved host_ip to %s", host_ip)

    # Build flags from component dict (default: all on)
    components: dict[str, bool] = step_cfg.get(
        "components", dict.fromkeys(COMPONENTS, True)
    )
    flags = components_to_flags(components)

    # Patch runtime configuration (replaces what RuntimeConfiguration.py did).
    proj_dir_fwd = str(project_dir).replace("\\", "/").rstrip("/") + "/"
    flags["Project.Directory"] = proj_dir_fwd
    hh_file, person_file = _popsyn_files(project_dir)
    flags["PopulationSynthesizer.InputToCTRAMP.HouseholdFile"] = hh_file
    flags["PopulationSynthesizer.InputToCTRAMP.PersonFile"] = person_file
    flags["RunModel.MatrixServerAddress"] = host_ip
    flags["RunModel.HouseholdServerAddress"] = host_ip
    flags["Model.Random.Seed"] = str(seed)

    threads = step_cfg.get("threads", max(1, (os.cpu_count() or 4) - 2))

    props_path = runtime_dir / "mtcTourBased.properties"
    patch_properties(props_path, flags)
    patch_jppf_configs(runtime_dir / "config", host_ip, threads=threads)

    enabled = sum(1 for v in components.values() if v)
    log.info("Components enabled: %d/%d", enabled, len(COMPONENTS))
    log.info("Iteration %d  shadow_pricing=%s", iteration, do_shadow_pricing)

    # Kill any orphaned java from a previous aborted run
    kill_infrastructure([])

    _ensure_native_dlls(runtime_dir)

    # Preflight: determine if we can access the Bentley license from this
    # session, or if we need to launch via schtasks in the interactive session.
    # NOTE: we ALWAYS use schtasks for the single-iteration ablation case,
    # even from an interactive RDP session, because schtasks survives RDP
    # disconnect (Windows throttles direct subprocesses when the session
    # disconnects).  Direct subprocess is only used for multi-iteration runs
    # which require the looping infrastructure.
    interactive = _preflight_license()

    sample_rate = explicit_rate or DEFAULT_SAMPLE_RATES.get(iteration, 0.50)
    sp_flags = shadow_pricing_flags(
        iteration,
        shadow_pricing=do_shadow_pricing,
        passes=step_cfg.get("shadow_price_passes"),
    )
    patch_properties(props_path, sp_flags)
    log.info("CT-RAMP iteration %d  sample_rate=%.2f", iteration, sample_rate)

    if not interactive:
        # schtasks path — works from any session and survives RDP disconnect.
        # Every call is single-iteration -- the runner owns the loop -- so this
        # path handles multi-iteration runs one round at a time.
        try:
            _run_via_schtasks(
                project_dir, runtime_dir, host_ip,
                iteration=iteration, sample_rate=sample_rate, seed=seed,
            )
        finally:
            _recover_license()
    else:
        # Interactive session: direct subprocess execution.  The JPPF cluster and
        # matrix server are started and torn down per iteration, matching
        # RunIteration.bat, which calls javaOnly_runMain/runNode0 inside each one.
        procs = start_infrastructure(runtime_dir, project_dir, host_ip)
        try:
            run_model(
                project_dir, runtime_dir,
                iteration=iteration, sample_rate=sample_rate, seed=seed,
            )
        finally:
            kill_infrastructure(procs)
