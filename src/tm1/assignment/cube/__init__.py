"""Faithful Cube Voyager assignment backend (run as-is via ``runtpp``).

- :mod:`cube.job` -- run Cube ``.job`` scripts over
  SSH/schtasks, including the local Cube Cluster.
- :mod:`~tm1.assignment.cube.highway` -- HwyAssign, the feedback block, and
  highway skims.
- :mod:`~tm1.assignment.cube.transit` -- transit network prep, assignment and
  skims.
- :mod:`~tm1.assignment.cube.ctramp` -- sequences the above into one CT-RAMP
  global iteration.
"""

from cube.job import CubeJobError, run_cube_job

__all__ = ["CubeJobError", "run_cube_job"]
