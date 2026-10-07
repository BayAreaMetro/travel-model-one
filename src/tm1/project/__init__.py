"""A project: the model to run, and the runs to make of it.

A project is a directory holding ``steps.yaml`` (optional) plus one or more
``scen_*.yaml`` files: the scenarios it runs, each a set of overrides
(:mod:`tm1.project.overrides`) on the shared pipeline in ``default-configs/``
(:mod:`tm1.project.config`), addressed and enumerated by
:mod:`tm1.project.scenarios`.

Reading only. Nothing here runs a step or touches a run directory, so a project can
be listed and checked -- ``tm1 scenarios`` -- on a machine that could not run the model.
"""
