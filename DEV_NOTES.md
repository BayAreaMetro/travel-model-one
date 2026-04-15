# Repo Layout Notes

## Existing

```text
travel-model-one/
|-- core/          legacy Java/Ant model code + bundled dependencies
|-- model-files/   runnable model assets, runtime configs, batch files
|-- utilities/     one-off analysis, calibration, GIS, data-prep scripts
```

## Proposed

```text
travel-model-one/
|-- base-model/    base configs, specs, lookup tables, default assets
|-- scenarios/     scenario overrides only
|-- scripts/       run/prep/export entrypoints
`-- src/           shared Python code used by scripts/tooling
```

## Diffs

- `core/` -> retire from day-to-day layout; use installable `activitysim` where possible
- `model-files/model/` -> `base-models/`
- `model-files/runtime/` -> split between `base-models/` and `scripts/`
- `model-files/scripts/` -> move into `scripts/` or `src/`
- `utilities/` -> cherry-pick only maintained pieces into `scripts/` or `src/`
- `utilities/RTP/config_RTP2025/` -> `scenarios/RTP2025/`

## Working principle

The general direction is to separate:

1. Base model assets.
2. Scenario deltas.
3. Operational scripts.
4. Shared code.

That should make the repo easier to reason about and highlight eventual file deletions.

## CTRAMP → ActivitySim migration plan

### Step 0: Cube ↔ OMX bridge (`src/tm1/matrices.py`)
- Bidirectional TPP ↔ OMX converter
- Skims: TPP→OMX so ActivitySim can read Cube highway skims
- Trips: OMX→TPP so Cube assignment can read ActivitySim demand
- Transitional; deprecate once a Python-native assignment tool is validated (AequilibraE is a candidate, needs evaluation)

### Step 1: Python orchestrator (`src/tm1/run_model.py`)
- Replaces RunModel.bat / RunIteration.bat
- Calls `runtpp` via subprocess for Cube jobs (skims, assignment, nonres)
- Calls ActivitySim in-process where CTRAMP Java used to be
- Iteration params (sample rate, seed, weights) are Python variables
- Start minimal: preprocess → skims → demand → assignment loop

### Step 2: Validation
- Run both pipelines on same inputs, compare trip matrices by mode/period
- Hard part: `.properties` → ActivitySim config mapping (~30 params)
- `scenario_config.yaml` becomes single source of truth for scenario params

### Step 3: Post-processing pythonification
- Replace EMFAC, metrics, logsums, core summaries batch/R/Cube scripts
- Integrate with `travel-diary-survey-tools` for validation and calibration analyses

### Step 4: Wire in PopulationSim and land use
- PopulationSim produces synthetic population from census PUMS + control totals
- Land use inputs (UrbanSim or static) feed both PopulationSim and ActivitySim
- End-to-end: land use → PopulationSim → ActivitySim → assignment

### What dies
- RunModel.bat, RunIteration.bat, RuntimeConfiguration.py
- JPPF/Java startup, PrepAssign.job, core/ Java code

### What stays (as subprocess calls)
- All `.job` files (Cube skims, assignment, nonres, preprocessing)
- `transitDwellAccess.py` (Wrangler dependency)

### CLI design
- Installed via pyproject.toml → `tm1` command
- `run_model.py` at repo root as convenience alias (thin wrapper)

CLI usage examples:
```
tm1 run --scenario scenarios/base_2023
tm1 run --scenario scenarios/base_2023 --max-iterations 1 --sample-rate 0.1
tm1 batch scenarios/scenario_batches.yaml
```

Batch manifest example:
```yaml
# scenarios/scenario_batches.yaml
scenarios:
  - scenarios/base_2023
  - scenarios/foo_2025
  - scenarios/bar_2050
common_overrides:
  max_iterations: 3
```

For AWS/parallel: one `tm1 run` per machine, parallelism is infrastructure not CLI.