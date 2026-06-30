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



## ActivitySim Migration — Quickstart

This branch (`activitysim_revival`) replaces the Java-based CTRAMP demand model with [ActivitySim](https://activitysim.github.io/). The network assignment and skimming steps remain unchanged.

### What Changed from Legacy

| Legacy (CTRAMP)            | New (ActivitySim)                         |
|----------------------------|-------------------------------------------|
| Java + Cube scripts        | Python (`uv` managed)                     |
| UEC workbooks (`.xls`)     | CSV specs + YAML configs                  |
| Properties files           | `settings.yaml` + `constants.yaml`        |
| `model-files/RunModel.bat` | `tm1 run --scenario base_2023_activitysim`            |

### Repository Layout

```
base-models/activity/configs/    # Canonical ActivitySim configs (specs, coefficients, YAML)
scenarios/{name}/activitysim/    # Scenario overrides ONLY (inherits from base-models)
scenarios/{name}/populationsim/  # PopulationSim overrides
src/tm1/                         # Python package (CLI, runner)
src/cubeio/                      # Cube skim/matrix I/O
scripts/                         # Utility and launch scripts
model-files/                     # Legacy CTRAMP batch files (retained for reference)
```

### Key Concept: Config Inheritance

ActivitySim resolves configs in directory order. The scenario `settings.yaml` sets `inherit_settings: True`, so only files you **override** need to exist in the scenario folder. Everything else falls through to `base-models/activity/configs/`.

- **YAMLs merge** — you only specify the keys that differ.
- **CSVs replace** — you must copy the entire file and modify it in place.

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
tm1 run --scenario base_2023_activitysim
```

### Creating a New Scenario

1. Create `scenarios/<name>/activitysim/settings.yaml` with `inherit_settings: True`
2. Add only the config files that *differ* from the base
3. Point input tables at your land-use / skims data
4. Run with `tm1 run --scenario <name>`