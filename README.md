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
| `RunModel.bat`                | `tm1 run base_2023_ctramp`              |
| Hand-edited properties files  | `config.yaml` per project               |
| Paths edited in-place per run | Templated (`{run_dir}`, `{reference_run}`) |

### Scope

Runs a full global iteration: input staging, CT-RAMP demand, then Cube assignment, feedback
and skims. Every Cube `.job` script is the stock one, run unmodified; only the orchestration
around them is new.

That covers `SetUpModel.bat`'s staging and **all of `RunIteration.bat`**. It does *not* yet
cover two phases of `RunModel.bat`:

| Not yet ported | What it does |
|----------------|--------------|
| Preprocess | `SetTolls`, `SetHovXferPenalties`, `CreateFiveHighwayNetworks`, `HsrTripGeneration`, `CreateNonMotorizedNetwork`, `NonMotorizedSkims`, `csvToDbf.py`, `transitDwellAccess.py` |
| Post-processing | `SkimsDatabase`, `net2csv`, EMFAC, logsums, core summaries, metrics, `ExtractKeyFiles` |

Because preprocess is absent, a project currently seeds `hwy/` from a completed reference
run rather than building the period networks from `freeflow.net`. Closing both gaps — and
sourcing from the reference run's pristine `INPUT/` — is phase 4; see
[`MIGRATION_NOTES.md`](MIGRATION_NOTES.md).

Requires Cube Voyager and a licence, as before.

### Repository Layout

```
projects/{name}/      # config.yaml + cases.yaml + any project-specific step code
src/tm1/              # Python package: CLI, step orchestrator, model steps
default-configs/      # Shared model configs — scaffolded, populated in phase 5
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

### Running a Project

```bash
tm1 run base_2023_ctramp

# a single step
tm1 run base_2023_ctramp --steps simulate_ctramp

# a project kept outside the repo
tm1 run E:/runs/my_project
```

### Restarting a Failed Run

A full run is hours of Cube, so `--resume-at` restarts at the step that died
instead of from the beginning. **The named step runs** — everything before it is
skipped:

```bash
tm1 run base_2023_ctramp --resume-at assignment
tm1 run base_2023_ctramp --resume-at 2:assignment   # iteration 2's
```

The `N:` prefix is needed only when a step runs more than once — that is, inside
`iterate` with `count > 1`. A bare name matching several rounds is an error
listing the candidates, not a guess, since picking the wrong one costs hours.

You rarely type it: a failure prints the exact command.

```
--- Step: assignment ---
ERROR  Cube job HwyAssign.job failed (exit=2, engine ReturnCode=2)
       Full Cube log: E:/Tests/base_2023_ctramp/_cube_HwyAssign_18004_1785277879.log
       Resume with: tm1 run base_2023_ctramp --resume-at 2:assignment
```

And the resumed run states what it is doing before doing any of it:

```
Resuming at assignment, iteration 2 of 3
  skipping 4 already-completed step(s): copy_inputs@1, simulate_ctramp@1, assignment@1, simulate_ctramp@2
  running 4: assignment@2, simulate_ctramp@3, assignment@3, vmt_vht_metrics@3
```

Two things it deliberately does not do. The named step **re-runs from the start**
rather than continuing part-way — Cube jobs are not transactional, so a killed
`HwyAssign` leaves partial `.net` files that only a fresh run overwrites. And it
refuses to resume into an empty project directory, since "resume" presupposes a
previous run; without that check it would skip staging and demand, then assign
whatever stale matrices happened to be lying around.

### Creating a New Project

1. Copy `projects/base_2023_ctramp/config.yaml` and `cases.yaml` to `projects/<name>/`
2. Update `reference_run` and `run_dir` for your environment
3. Adjust the `steps:` block — iterations, sample rate, threads, model components
4. Run with `tm1 run <name>`

### Run Logs

Every run writes a timestamped log to `{run_dir}/logs/`:

```
logs/tm1_20260728_161042_18004.log
```

It captures more than the console does — each step boundary and how long it took,
every Cube job's engine `ReturnCode` and the path to that job's own log, and the
full traceback if a step fails. The console stays at INFO; the file records DEBUG.

The name carries a timestamp and pid, so concurrent runs and repeat attempts never
write into each other's log — a failed run's log survives the next attempt.

Optional, in `config.yaml`:

```yaml
logging:
  level: DEBUG            # what reaches the file; console stays at INFO
  dir: "{run_dir}/logs"  # override the location
```

This replaces `RunModel.bat`'s `echo ... >> logs\feedback.rpt`, which recorded
only start and finish milestones.

### Adding Your Own Pre- or Post-Processing

Steps are flat — every step is a top-level key under `steps:`, and they run in the
order written. So a step placed *before* `simulate_ctramp` is pre-processing, and
one placed *after* `assignment` is post-processing. There is no separate "hook"
concept; position is the whole mechanism.

Point a step at your own code with `script:` (a path, relative to the project
directory) or `module:` (an importable dotted path):

```yaml
steps:
  copy_inputs: {...}

  clean_inputs:                          # runs before the model
    script: "hooks.py:clean_inputs"
    drop_zero_hh: true                   # anything else is yours

  simulate_ctramp: {...}
  assignment: {...}

  vmt_vht_metrics:                       # runs after
    script: "hooks.py:vmt_vht_metrics"
```

Naming the function after a colon lets one file hold several steps. Without it,
`run` is called — the same name the built-in steps use.

A step is any function with this signature:

```python
def clean_inputs(config_dir, cfg, **kwargs):
    """Return "skipped" to record a no-op, or None."""
    settings = cfg["steps"]["clean_inputs"]    # your own keys
    run_dir = cfg["run_dir"]                 # {templates} already expanded
```

- `cfg` is the fully resolved config — `{run_dir}` and friends already expanded
- `cfg` is shared, so a step may modify it to pass values to later steps
- Custom steps work with `--steps <name>` like any other
- Built-in step names cannot be redefined; pick a different name

`projects/base_2023_ctramp/hooks.py` is a worked example: `vmt_vht_metrics` reads
the loaded network the feedback block writes and summarises VMT, VHT and implied
congested speed by facility type — a reduced form of
`utilities/RTP/metrics/hwynet.py`. It aggregates rather than copies, which is the
pattern the migration is trying to establish; see
[`MIGRATION_NOTES.md`](MIGRATION_NOTES.md) on porting intent rather than mechanism.