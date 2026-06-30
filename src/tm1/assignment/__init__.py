"""Highway/transit assignment backends.

Two interchangeable backends produce loaded networks + skims from demand:

- :mod:`tm1.assignment.cube` — the faithful legacy Cube Voyager pipeline (Task 1).
- :mod:`tm1.assignment.aeq` — the AequilibraE open-source equivalent (Task 2).

The Cube loop entry points are re-exported here for convenience.
"""

from tm1.assignment.cube.highway import build_trip_matrices, run_assignment_iteration

__all__ = ["build_trip_matrices", "run_assignment_iteration"]
