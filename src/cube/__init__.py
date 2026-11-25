"""Cube Voyager: driving the program, and reading what it wrote.

Everything this repo knows about Cube lives here, and nothing here knows about
TM1 -- no projects, no cases, no run directories. Functions take paths and
parameters, which is what lets both the runner and ``tm1 status`` use them
without either importing the other.

- :mod:`cube.job` -- run a ``.job`` script: the Cube Cluster, the Bentley
  licence, and the interactive-session launch that SSH sessions need.
- :mod:`cube.process` -- read-only: are this run's Cube processes working, or
  wedged?

Submodules are imported directly (``from cube.job import run_cube_job``) so that
using one never drags in the other's dependencies.
"""
