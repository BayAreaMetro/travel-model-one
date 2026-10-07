# Plan Bay Area 2050+ Final Blueprint

| File | Holds |
|---|---|
| [`steps.yaml`](steps.yaml) | this project's own pipeline additions |
| [`scen_2023.yaml`](scen_2023.yaml) | 2023 baseline |
| [`scen_2035_NoProject.yaml`](scen_2035_NoProject.yaml) | 2035 no-project |
| [`scen_2035_Plan.yaml`](scen_2035_Plan.yaml) | 2035 Final Blueprint |
| [`scen_2050_NoProject.yaml`](scen_2050_NoProject.yaml) | 2050 no-project |
| [`scen_2050_Plan.yaml`](scen_2050_Plan.yaml) | 2050 Final Blueprint |
| [`ladder.yaml`](ladder.yaml), [`matrix.yaml`](matrix.yaml) | placeholders -- this project uses neither pathway yet |

`tm1 scenarios PBA50+_FBP` merges every `scen_*.yaml` in this directory before checking
any of them, so an ID collision between two files is caught just the same as one inside
a single file.

This project's own pipeline additions (appended once, for every scenario alike) are in
`steps.yaml`, not repeated per scenario.

Inside a `scen_*.yaml` file, each key under a scenario ID is an **address**: a dotted
path to the value it overrides in the shared model file
(`default-configs/ctramp-cube-model.yaml`), however deep that value sits:

```
model_year: 2035                                  a top-level key
env.MODEL_YEAR: 2035                              inside a top-level mapping
env.EN7: ENABLED                                  ... and its siblings survive
copy_inputs.input_landuse.from: "M:/.../landuse"  inside a step
iterate.count: 1                                  the loop's own key
iterate.hwy_assign.cluster_nodes: 24              a step, whatever iteration it runs in
```

The address must already exist in the shared model file, values replace rather than
merge, and `steps` itself is not addressable -- a scenario varies values, it never
changes the pipeline.

Two other pathways, each in its own glob-matched file, for when a group of scenarios
grows past one-entry-per-run -- see the placeholder `ladder.yaml` and `matrix.yaml` for
what one looks like:

| File | Pathway |
|---|---|
| `scen_*.yaml` | one entry per run, written out |
| `ladder*.yaml` | cumulative -- rung k applies rungs 1..k, so the diff between adjacent rungs isolates the one intervention that was added |
| `matrix*.yaml` | the cross product of named axes, minus `exclude:` combinations |

`tm1 scenarios PBA50+_FBP` prints what every `scen_*.yaml` here expands to and checks
every address against the shared model file.

IDs are `YEAR_MODELVERSION_SERIES_SCENARIO_VERSION` (e.g. `2050_TM161_FBP_Plan_16`) and
stable forever: the ID names the run directory, so renaming a scenario makes it an unrun
one. Case is preserved (camelCase is fine for a multi-part last segment), but two IDs
differing only by case collide -- they would name the same run directory on a
case-insensitive filesystem.
