"""A project: the model to run, and the runs to make of it.

A project is a directory holding two files:

- ``config.yaml`` -- the full model with real default values (:mod:`tm1.project.config`)
- ``cases.yaml``  -- named variations on it (:mod:`tm1.project.cases`), each a set of
  overrides addressed into the config (:mod:`tm1.project.overrides`)

Reading only. Nothing here runs a step or touches a run directory, so a project can
be listed and checked -- ``tm1 cases`` -- on a machine that could not run the model.
"""
