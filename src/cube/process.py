"""Are this run's Cube processes working, or wedged?

Cube buffers its ``.PRN`` output and can leave every file untouched for minutes
during a long assignment, so file mtimes cannot tell a working job from a hung
one.  CPU time can: two samples a couple of seconds apart separate *busy* from
*stopped*.

Processes are attributed to a run by their command line, so two runs on one
machine are never confused for each other.

Read-only.  Nothing here starts, stops or configures Cube -- that is
:mod:`cube.job`.
"""

import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import psutil

#: The two Cube images a running job owns: the master interpreter and its
#: cluster nodes.  Matched case-insensitively -- Windows reports both spellings
#: (``RUNTPP.EXE``, ``Voyager.exe``) depending on how the process was started.
_CUBE_IMAGES = frozenset({"runtpp.exe", "voyager.exe"})

#: Seconds between the two CPU samples.  Long enough that a working job is
#: unambiguous (a 48-node assignment accrues tens of CPU-seconds), short enough
#: that ``tm1 status`` still feels immediate.
_CPU_SAMPLE = 2.0


@dataclass
class CubeProbe:
    """What the Cube processes of one run are doing, right now.

    CPU time is the only signal that separates *working* from *wedged*: Cube
    buffers its ``.PRN`` output and can leave every file untouched for minutes
    while computing, so file mtimes answer a different question (see
    :func:`newest_write`).  A job hung waiting on a licence holds its processes
    open and burns nothing.

    This reports; it does not judge.  A reader who sees 48 nodes and no CPU
    knows what that means, and nothing here acts on the answer -- which is what
    keeps the probe free of the false-positive risk that a killing watchdog has.
    """

    master: int
    nodes: int
    #: CPU-seconds accrued across every matched process during the sample.
    cpu_delta: float
    window: float
    #: Files in the cluster's commpath, or ``None`` when the job has no cluster.
    commpath_files: int | None


def _cube_cmdline(proc: psutil.Process) -> list[str] | None:
    """A live process's argv, or ``None`` if it cannot be read as Cube's.

    Both lookups race the process exiting, and ``cmdline()`` is denied outright
    for another user's processes.  Every failure means *cannot tell*, which is
    not the same as *not running* -- so they all drop the process rather than
    letting it count as evidence either way.
    """
    try:
        if proc.name().lower() not in _CUBE_IMAGES:
            return None
        return proc.cmdline()
    except (psutil.Error, OSError):
        return None


def _owns(cmdline: Iterable[str], run_dir: Path) -> bool:
    r"""True if this Cube process is working for ``run_dir``.

    Every Cube process a run starts names the project directory in its argv --
    the master through the ``.job`` path, each node through its
    ``commpath\\CTRAMP<n>.script``.  That is what separates this run's processes
    from a second project's on the same machine, so the harness never reports
    on, and a caller never acts on, someone else's run.

    Compared with separators folded and case ignored: the config writes forward
    slashes, Windows hands back backslashes, and drive letters vary in case.
    The match must end on a path boundary -- a plain prefix test claims
    ``ctramp_2023_v2``'s processes as ``ctramp_2023``'s.
    """
    want = str(run_dir).replace("\\", "/").casefold().rstrip("/")
    for arg in cmdline:
        folded = arg.replace("\\", "/").casefold()
        if folded == want or folded.startswith(want + "/"):
            return True
    return False


def _commpath_of(cmdline: Iterable[str]) -> Path | None:
    """The cluster directory a node argv points at, if this is a node.

    Taken from the argv rather than assumed to be ``run_dir/commpath``: a step
    may set ``commpath:`` itself, and the transit jobs run from a subdirectory
    while still pointing their cluster at the project root.
    """
    for arg in cmdline:
        if arg.replace("\\", "/").casefold().endswith(".script"):
            return Path(arg).parent
    return None


def probe_cube(
    run_dir: Path,
    procs: Iterable[psutil.Process] | None = None,
    sample: float = _CPU_SAMPLE,
) -> CubeProbe | None:
    """Sample the Cube processes running for ``run_dir``, or ``None`` if none are.

    ``None`` covers both "this step is not a Cube job" -- CT-RAMP is Java, the
    ``command:`` steps are Python -- and "the Cube processes are gone".  The
    caller prints nothing in either case rather than guessing which it is; a
    line reading *no Cube processes* under a running Java step would be true and
    still read as an alarm.
    """
    found: list[tuple[psutil.Process, list[str]]] = []
    for proc in procs if procs is not None else psutil.process_iter():
        cmdline = _cube_cmdline(proc)
        if cmdline and _owns(cmdline, run_dir):
            found.append((proc, cmdline))
    if not found:
        return None

    before = _cpu_total(p for p, _ in found)
    time.sleep(sample)
    after = _cpu_total(p for p, _ in found)

    commpath = next(
        (c for _, cmdline in found if (c := _commpath_of(cmdline)) is not None), None
    )
    return CubeProbe(
        master=sum(1 for _, cmdline in found if _commpath_of(cmdline) is None),
        nodes=sum(1 for _, cmdline in found if _commpath_of(cmdline) is not None),
        cpu_delta=max(0.0, after - before),
        window=sample,
        commpath_files=_count_files(commpath) if commpath else None,
    )


def _cpu_total(procs: Iterable[psutil.Process]) -> float:
    """CPU-seconds accrued across processes, skipping any that have exited."""
    total = 0.0
    for proc in procs:
        try:
            times = proc.cpu_times()
        except (psutil.Error, OSError):
            continue
        total += times.user + times.system
    return total


def _count_files(commpath: Path) -> int | None:
    """Files in the cluster directory, or ``None`` if it cannot be read."""
    try:
        return sum(1 for _ in commpath.iterdir())
    except OSError:
        return None
