"""Highway/transit assignment backends.

- :mod:`tm1.assignment.cube` -- the faithful legacy Cube Voyager pipeline, run
  as-is through ``runtpp``.

Entry points are imported from their modules directly rather than re-exported
here, so that using one backend never imports another's dependencies.
"""
