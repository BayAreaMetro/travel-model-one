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



## Python Runtime Harness — Quickstart

A Python CLI (`tm1`) that runs the model in place of the `.bat` script chain. **The model
itself is unchanged** — this is the same Java CT-RAMP demand model reading the same inputs
and producing the same results; only the orchestration is different.

This is phase 1 of a longer migration. See [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md) for the
full phase plan and current status of each piece.

### What Changed

| Legacy                        | New                                     |
|-------------------------------|-----------------------------------------|
| `RunModel.bat`                | `tm1 run --scenario base_2023_ctramp`   |
| Hand-edited properties files  | `scenario_config.yaml` per scenario     |
| Paths edited in-place per run | Templated (`{proj_dir}`, `{reference_run}`) |

### Scope

Runs a full global iteration: CT-RAMP demand, then Cube assignment, feedback and skims —
`RunModel.bat` and `RunIteration.bat` replaced end to end. Every Cube `.job` script is the
stock one, run unmodified; only the orchestration around them is new.

Requires Cube Voyager and a licence, as before.

### Repository Layout

```
scenarios/{name}/     # Scenario config (base_2023_ctramp)
src/tm1/              # Python package: CLI, step orchestrator, model steps
scripts/              # Launch/utility entrypoints
default-configs/      # Shared model configs — scaffolded, populated in phase 4
model-files/, core/   # Legacy CT-RAMP/Cube assets, unchanged, still in production
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

# a single step
tm1 run --scenario base_2023_ctramp --step simulate_ctramp
```

### Creating a New Scenario

1. Copy `scenarios/base_2023_ctramp/scenario_config.yaml` to `scenarios/<name>/`
2. Update `reference_run` and `proj_dir` for your environment
3. Adjust the `steps:` block — iterations, sample rate, threads, model components
4. Run with `tm1 run --scenario <name>`