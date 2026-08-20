"""Tests for the Cube liveness probe behind ``tm1 status``.

The probe answers one question file mtimes cannot: is Cube *computing*, or is it
holding 48 processes open and burning nothing?  Cube buffers its ``.PRN`` output
to the end of a run, so a healthy 27-minute assignment and a job wedged on a
licence look identical on disk and completely different on the CPU clock.

Real processes are not started here.  ``psutil.Process`` is replaced with a stub
whose CPU numbers and argv the test dictates, which is what lets a *wedged* run
be tested at all -- there is no way to ask a real Cube job to hang on cue.
"""

from __future__ import annotations

from collections import namedtuple
from pathlib import Path

import psutil
import pytest

from tm1.status import CubeProbe, _commpath_of, _cube_lines, _owns, probe_cube

#: Only the two fields the probe sums; psutil's own tuple is platform-shaped.
CpuTimes = namedtuple("CpuTimes", "user system")  # noqa: PYI024

PROJ = Path("E:/Tests/base_2023_ctramp")
NODE = r"E:\Tests\base_2023_ctramp\commpath\CTRAMP7.script"
MASTER = r"E:\Tests\base_2023_ctramp\CTRAMP\scripts\assign\HwyAssign.job"


class FakeProc:
    """A psutil.Process stand-in: fixed argv, CPU time that advances on read."""

    def __init__(self, name: str, args: list[str], cpu_step: float = 0.0) -> None:
        """Accrue ``cpu_step`` CPU-seconds on every ``cpu_times`` read."""
        self._name, self._args, self._step = name, args, cpu_step
        self._cpu = 0.0

    def name(self) -> str:
        """The process image name, as psutil reports it."""
        return self._name

    def cmdline(self) -> list[str]:
        """The process argv."""
        return self._args

    def cpu_times(self) -> CpuTimes:
        """CPU time so far, advanced by one step per read."""
        self._cpu += self._step
        return CpuTimes(self._cpu, 0.0)


class DeniedProc(FakeProc):
    """Another user's process: readable by name, denied on argv."""

    def cmdline(self) -> list[str]:
        """Denied, as psutil does for a process this user does not own."""
        raise psutil.AccessDenied(1)


def _cluster(cpu_step: float, nodes: int = 3) -> list[FakeProc]:
    master = FakeProc("RUNTPP.EXE", [r"C:\...\runtpp.exe", MASTER], cpu_step)
    workers = [
        FakeProc("Voyager.exe", [r"C:\...\Voyager.exe", NODE.replace("7", str(n)), "/wait"],
                 cpu_step)
        for n in range(1, nodes + 1)
    ]
    return [master, *workers]


# --- which processes belong to this run -------------------------------------


@pytest.mark.parametrize("arg", [MASTER, NODE, "e:/tests/base_2023_ctramp/x.job"])
def test_owns_matches_across_separator_and_case(arg: str) -> None:
    """The config writes forward slashes; Windows hands back backslashes."""
    assert _owns([arg], PROJ)


@pytest.mark.parametrize(
    "arg",
    [
        r"E:\Tests\other_project\CTRAMP\scripts\assign\HwyAssign.job",
        r"E:\Tests\base_2023_ctramp_v2\commpath\CTRAMP1.script",
    ],
)
def test_owns_rejects_another_run(arg: str) -> None:
    """A second project on the same machine must never be counted or acted on."""
    assert not _owns([arg], PROJ)


def test_commpath_comes_from_the_node_argv() -> None:
    """Read from argv, not assumed -- a step may set `commpath:` itself."""
    assert _commpath_of([r"C:\...\Voyager.exe", NODE]) == Path(
        r"E:\Tests\base_2023_ctramp\commpath"
    )
    assert _commpath_of([r"C:\...\runtpp.exe", MASTER]) is None


# --- the probe --------------------------------------------------------------


def test_probe_counts_master_and_nodes_separately() -> None:
    """The master is the one process with no ``.script`` in its argv."""
    probe = probe_cube(PROJ, procs=_cluster(cpu_step=0.0), sample=0.0)

    assert probe is not None
    assert (probe.master, probe.nodes) == (1, 3)


def test_probe_reports_no_cpu_for_a_wedged_cluster() -> None:
    """Today's hang: every process up, nothing computing."""
    probe = probe_cube(PROJ, procs=_cluster(cpu_step=0.0), sample=0.0)

    assert probe is not None
    assert probe.cpu_delta == 0.0


def test_probe_reports_cpu_for_a_working_cluster() -> None:
    """The healthy case: every process accruing CPU between the two samples."""
    probe = probe_cube(PROJ, procs=_cluster(cpu_step=5.0), sample=0.0)

    assert probe is not None
    assert probe.cpu_delta == pytest.approx(20.0)  # 4 processes x 5s


def test_probe_is_none_when_no_cube_is_running() -> None:
    """A Java or Python step prints nothing rather than an alarming zero."""
    java = FakeProc("java.exe", ["java", "-jar", "ctramp.jar", str(PROJ)])

    assert probe_cube(PROJ, procs=[java], sample=0.0) is None


def test_probe_ignores_another_users_processes() -> None:
    """A denied argv means *cannot tell*, which must not read as evidence."""
    denied = DeniedProc("Voyager.exe", [r"C:\...\Voyager.exe", NODE])

    assert probe_cube(PROJ, procs=[denied], sample=0.0) is None


def test_probe_survives_a_process_exiting_mid_sample() -> None:
    """The cluster shutting down under the probe is normal, not an error."""

    class Vanishing(FakeProc):
        def cpu_times(self) -> CpuTimes:
            raise psutil.NoSuchProcess(1)

    procs = [*_cluster(cpu_step=1.0), Vanishing("Voyager.exe", [r"C:\v.exe", NODE])]
    probe = probe_cube(PROJ, procs=procs, sample=0.0)

    assert probe is not None
    assert probe.cpu_delta == pytest.approx(4.0)


# --- rendering --------------------------------------------------------------


def test_lines_report_facts_without_a_verdict() -> None:
    """No 'stalled', no 'working' -- naming a healthy run stalled is the costly error."""
    lines = _cube_lines(CubeProbe(1, 48, 0.0, 2.0, 0))

    assert lines == [
        "          cube     1 master + 48 nodes, +0.0 CPU-s over 2s",
        "          commpath 0 files",
    ]
    assert not any(w in " ".join(lines).lower() for w in ("stall", "hung", "dead", "idle"))


def test_lines_omit_commpath_for_a_clusterless_job() -> None:
    """A job like PrepHwyNet has no cluster, so there is no commpath to count."""
    lines = _cube_lines(CubeProbe(1, 0, 3.2, 2.0, None))

    assert lines == ["          cube     1 master + 0 nodes, +3.2 CPU-s over 2s"]


def test_nothing_is_printed_without_a_probe() -> None:
    """No Cube processes means no lines at all -- not a line saying zero."""
    assert _cube_lines(None) == []
