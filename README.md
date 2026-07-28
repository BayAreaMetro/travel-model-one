# travel-model-one
The Metropolitan Transportation Commission (MTC) maintains a simulation model of typical weekday travel to assist in regional planning activities.  MTC makes the software and scripts necessary to implement the model as well as detailed model results available to the public.  Users of the model and/or the model's results are entirely responsible for the outcomes, interpretations, and conclusions they reach from the information.  Users of the MTC model or model results shall in no way imply MTC's support or review of their findings or analyses.

## Model Versions
The following model versions are available in the repository:

1. Version 0.3 -- Maintained in branch [`v03`](https://github.com/BayAreaMetro/travel-model-one/tree/v03).
2. Version 0.4 -- Maintained in branch [`v04`](https://github.com/BayAreaMetro/travel-model-one/tree/v04).
3. Version 0.5 -- Maintained in branch [`v05`](https://github.com/BayAreaMetro/travel-model-one/tree/v05).
3. Version 0.6 -- Maintained in branch [`v06`](https://github.com/BayAreaMetro/travel-model-one/tree/v06).
4. Version 1.5 -- Maintained in branch [`TM1.5`](https://github.com/BayAreaMetro/travel-model-one/tree/TM1.5).
5. Version 1.6 -- Maintained in branch [`master`](https://github.com/BayAreaMetro/travel-model-one/tree/master).

Travel Model Two is also under development in a different repository: https://github.com/BayAreaMetro/travel-model-two

For additional details about the different versions, please see [here](https://github.com/BayAreaMetro/modeling-website/wiki/Development)
Any other branches are exploratory and not used in our planning work.

Please find a detailed User's Guide [here](https://github.com/BayAreaMetro/modeling-website/wiki/UsersGuide). 

Other documentation is available on the [Travel Model wiki](https://github.com/BayAreaMetro/modeling-website/wiki/TravelModel), including the [Travel Model User's Guide](https://github.com/BayAreaMetro/modeling-website/wiki/UsersGuide) and the page on [Setup and Configuration](https://github.com/BayAreaMetro/modeling-website/wiki/SetupConfiguration).



## Python Runtime Pipeline — Quickstart

This branch (`activitysim_revival`) replaces the `.bat`/Ant-launched runtime with a Python
CLI (`tm1`) that drives the *existing* CT-RAMP (Java) demand model and Cube Voyager
assignment/skimming — the model itself is unchanged, only how it's launched and orchestrated.
See [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md) for the full multi-phase migration this is part
of, including the (separate, not-yet-decided) work to eventually swap the demand model and/or
assignment engine themselves.

### What Changed from Legacy

| Legacy                              | New                                      |
|--------------------------------------|-------------------------------------------|
| `RunModel.bat` / `RunIteration.bat`   | `tm1 run --scenario base_2023_ctramp`     |
| Hand-edited properties files          | `scenario_config.yaml` + scenario overrides |
| Manual/scheduled Cube `.job` launches | `src/tm1/assignment/cube/` (Python-driven, same `.job` scripts) |

### Repository Layout

```
scenarios/{name}/           # Scenario config + overrides (e.g. base_2023_ctramp)
src/tm1/                    # Python package (CLI, runner, steps, Cube launcher)
src/cubeio/                 # Cube skim/matrix I/O (no Cube install required)
scripts/                    # Utility and launch scripts
model-files/, core/         # Legacy CT-RAMP/Cube assets, unchanged, still in production
```

### Setup

```bash
# Install uv (one-time)
pip install uv

# Install project in dev mode
uv sync

# Verify
tm1 --help
```

### Running a Scenario

```bash
tm1 run --scenario base_2023_ctramp
```