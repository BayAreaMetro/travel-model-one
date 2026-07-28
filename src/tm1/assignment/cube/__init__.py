"""Faithful Cube Voyager assignment backend (run as-is via ``runtpp``).

- :mod:`~tm1.assignment.cube.runner` — run Cube ``.job`` scripts over SSH/schtasks,
  including the local Cube Cluster.
- :mod:`~tm1.assignment.cube.highway` — ActivitySim trips -> Cube demand, HwyAssign,
  feedback, skims, and the per-iteration loop driver.
- :mod:`~tm1.assignment.cube.transit` — transit network prep, assignment and skims.
"""

from tm1.assignment.cube.highway import (
    build_trip_matrices,
    run_assignment_iteration,
    run_highway_assignment,
    run_highway_feedback,
    run_highway_skims,
)
from tm1.assignment.cube.runner import CubeJobError, run_cube_job
from tm1.assignment.cube.transit import run_transit

__all__ = [
    "CubeJobError",
    "build_trip_matrices",
    "run_assignment_iteration",
    "run_cube_job",
    "run_highway_assignment",
    "run_highway_feedback",
    "run_highway_skims",
    "run_transit",
]
