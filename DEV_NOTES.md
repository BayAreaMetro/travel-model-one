# Repo Layout Notes

This is where I keep notes for myself and others about the proposed repo layout, and the rationale behind it. This is a living document, and will likely change as I go. But for now, this is the general direction I'm thinking about.

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

No Cube on the development machine. The plan is designed around that constraint:
use frozen reference skims, validate ActivitySim against CTRAMP outputs, and
only bring in assignment (AequilibraE) once demand modeling is proven equivalent.

### Reference model run

The last CTRAMP model run, used as the benchmark for validation:

```
\\MODEL3-C\Model3C-Share\Projects\2023_TM161_IPA_35_testrun
```

### Step 0: Pure-Python TPP reader (`src/tm1/tpp.py`)
- Pure-Python reader for Cube Voyager TPP binary matrices — no DLLs, no Cube.
- Decodes all 6 block types (0x00, 0x40, 0x80, 0xC0, 0xC8, 0xE8).
- Validated bit-exact against Cube CSV dumps (17,700 checks, 0 errors).
- Portable golden test suite: 7 TPP/CSV pairs in `tests/data/golden/`.
- **STATUS: DONE.** Reader is complete, optimized, committed.

### Step 0.5: Build `skims.omx` from reference TPPs (`scripts/build_omx_skims.py`)
- Read ~96 TPP files from reference run via `read_tpp()`
- Rename Cube table names → ActivitySim skim keys (mapping in `docs/skim_conversion_mapping.md`)
- Write single `skims.omx` with 1-based zone mapping
- One-time conversion — output goes into the scenario data directory
- **STATUS: NOT STARTED.**

### Step 1: Validate ActivitySim against CTRAMP (frozen skims, no assignment)
- Wire `skims.omx` into ActivitySim configs (`network_los.yaml` already expects it)
- Map CTRAMP `.properties` → ActivitySim settings/configs (~30 params)
- Run ActivitySim single-shot (no feedback loop — frozen skims, no assignment)
- Compare ActivitySim outputs to CTRAMP reference using existing summarizers
- Iterate on UECs until ActivitySim results are comparable to CTRAMP
- This is the hard, iterative part — the UECs have diverged
- **STATUS: NOT STARTED.** Blocked on Step 0.5.

### Step 2: Pythonify summarizers (OMX-native)
- Rewrite core summaries / validation scripts in Python reading OMX directly
- Drop Cube dependency from post-processing entirely
- Integrate with `travel-diary-survey-tools` for calibration analyses

### Step 3: Drop in AequilibraE for assignment (proposed?)
- Replace Cube highway assignment with AequilibraE (Python-native)
- Close the feedback loop: skims → ActivitySim → assignment → new skims
- Full iteration now runs without Cube on any machine

### Step 4: Wire in PopulationSim and land use
- PopulationSim produces synthetic population from census PUMS + control totals
- Land use inputs (UrbanSim or static) feed both PopulationSim and ActivitySim
- End-to-end: land use → PopulationSim → ActivitySim → assignment

### What dies (eventually)
- RunModel.bat, RunIteration.bat, RuntimeConfiguration.py
- JPPF/Java startup, PrepAssign.job, core/ Java code
- All `.job` files (Cube skims, assignment, nonres, preprocessing)
- Anything not in `base-model/`, `scenarios/`, `scripts/`, or `src/`


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