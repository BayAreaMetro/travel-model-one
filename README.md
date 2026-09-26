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

Additionally, specific releases are [tagged](https://github.com/BayAreaMetro/travel-model-one/tags).

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
| `RunModel.bat`                | `tm1 run PBA50+_FBP --scenario 2050_TM162_FBP_Plan --run-number 1` |
| Hand-edited properties files  | `scenarios.yaml` (its own values) |
| Paths edited in-place per run | Templated (`{run_dir}`, `{m_drive}`)      |

### Scope

Runs the model end to end from pristine `INPUT/`: staging, preprocess, three global
iterations of CT-RAMP demand → Cube assignment → feedback → skims, EMFAC prep, logsums,
core summaries, metrics, scenario metrics, and (for the model years that call for it)
off-model. Every `.job`, `.py` and `.R` is the stock one, run unmodified; only the
orchestration around them is new.

That covers `SetUpModel.bat`'s staging, **all of `RunIteration.bat`**, and all of
`RunModel.bat` except `RunNextGenFwysMetrics.bat` (NGF-only, not exercised by any
project here yet). A handful of individual calls inside the ported `.bat`s are not
carried over, each because there is nothing to port rather than because it was skipped:

| Dropped call | Why |
|---|---|
| `RunPrepareEmfac.bat`'s "on M" branch | reads from a robocopied `OUTPUT\` extraction; this harness always runs from its own `run_dir` |
| `RunCoreSummaries.bat`'s `commute_tours_by_inc_tp.r` | the script is not in this checkout |
| `RunMetrics.bat`'s `vmt_vht_metrics.csv` (`hwynet.py`) | commented out in the `.bat` itself, its lookup tables not refreshed; `projects/PBA50+_FBP/hooks.py`'s `vmt_vht_metrics` covers the same ground |
| `RunMetrics.bat`'s shapefile export | its two scripts live outside `utilities/RTP/metrics` and are not staged; one needs `geopandas`, not a dependency here |

The legacy preprocess scripts run here as-is, at the engine boundary. Replacing them with
native Python — and retiring the `dbfpy3` dependency with them — is the next phase; see
[`MIGRATION_NOTES.md`](MIGRATION_NOTES.md). NetworkWrangler is already gone: nothing this
harness runs needs it any more, so it is not installed at all.

Requires Cube Voyager and a licence, as before. Steps that run R (`.R`/`.r`) need
`TM1_R_HOME` set in the active environment file; the Java accessibility calculator
(`compute_logsums`) needs a local (interactive desktop) session -- unlike
`simulate_ctramp`, it has no remote-session fallback yet.

### Repository Layout

```
projects/{name}/      # scenarios.yaml (each scenario self-contained) + any project-specific step code
src/tm1/              # Python package: CLI, step orchestrator, model steps
default-configs/      # Shared model configs — the CT-RAMP+Cube pipeline every project inherits
model-files/, core/   # Legacy CT-RAMP/Cube assets, unchanged, still in production
```

### Where the Clone Lives

Modeling machines (`model3-g`, `model3-c`, ...) are shared -- several modelers use the
same Windows login -- so this repo is never cloned there, and nobody signs into GitHub on
one. Two machines are involved instead:

| Machine | Holds | Reached as |
|---|---|---|
| Your own VM (e.g. `lzorn-vm`) | your clone -- `E:\GitHub\travel-model-one` (local disk), or the shared mirror at `X:\travel-model-one-master` | yourself, via GitHub Desktop or VS Code, signed in as you |
| A modeling machine (e.g. `model3-g`) | no clone of its own -- it reaches one of the above over a mapped drive, and keeps its own venv locally | whoever is logged into its shared account |

**Changing code or config** -- a new project, an edited `scenarios.yaml` -- happens in
your own clone, committed and pushed with GitHub Desktop or VS Code, never on a modeling
machine. **Running a model** happens on a modeling machine: map a drive to reach the
clone, `cd` into it, and follow Setup below -- but see its Windows note for where the
venv itself goes, which is not the mapped drive.

### Setup

Run this on the modeling machine, cwd'd into the mapped clone. The clone lives on a
mapped network drive (see [Where the Clone Lives](#where-the-clone-lives)), so
`uv sync`'s default `.venv` is pointed at local disk instead, by convention
`E:\tm1-venv` -- left on the mapped drive, compiled packages (e.g. `psutil`) fail to
import with `DLL load failed ... The parameter is incorrect`, since Windows can't load
native `.pyd`/DLLs over a network path:

```powershell
# Install uv (one-time)
pip install uv

# Point the venv at local disk, not the mapped drive
$env:UV_PROJECT_ENVIRONMENT = "E:\tm1-venv"

# Install project in dev mode
uv sync

# Verify (or activate E:\tm1-venv\Scripts\activate first, then call tm1 directly)
uv run tm1 --help
```

> **cmd.exe note:** use `set UV_PROJECT_ENVIRONMENT=E:\tm1-venv` instead of the
> PowerShell line above -- PowerShell's own `set` is `Set-Variable`, an unrelated
> command that silently does not set an environment variable, so `uv sync` would still
> default to `.venv` on the mapped drive and may fail trying to remove or recreate
> files there.

Machine-specific paths (M drive, gawk, R, Slack) live in
[`default-configs/environments/mtc.yaml`](default-configs/environments/mtc.yaml), committed
since they are the same on every MTC machine. The one exception is `TM1_RUNS_ROOT` --
where runs go is local disk, so it is keyed there by hostname; add this machine's entry if
it is missing.

Running as a different agency or consultant, with your own machine-specific values? Add a
sibling file (e.g. `default-configs/environments/caltrans.yaml`) instead of editing MTC's,
and select it with `tm1 run --env caltrans` (or `TM1_ENV=caltrans`). MTC's own (`mtc`) is
the default when neither is given.

> **Windows note:** if `uv` is "not recognized" after `pip install uv`, pip installed
> it under your user Python `Scripts` folder (e.g.
> `%APPDATA%\Python\Python3XX\Scripts`), which may not be on `PATH`. Either add that
> folder to `PATH`, or install `uv` via the standalone installer instead, which adds
> itself to `PATH` automatically:
> ```powershell
> powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
> ```

### Running a Project

Same machine and cwd as [Setup](#setup) -- the modeling machine, in the mapped clone:

```bash
tm1 run PBA50+_FBP --scenario 2050_TM162_FBP_Plan --run-number 1

# a single step
tm1 run PBA50+_FBP --scenario 2050_TM162_FBP_Plan --run-number 1 --steps simulate_ctramp

# a project kept outside the repo
tm1 run E:/runs/my_project --run-number 1
```

`--scenario` is required whenever a project declares more than one, which
PBA50+_FBP does (`tm1 scenarios PBA50+_FBP` lists them). `--run-number` says
which `{scenario}_NNN` this run uses or continues. An unused number starts
fresh there; an existing one needs `--resume-at` too, or it is refused rather
than silently mixed with whatever is already in it.

### Restarting a Failed Run

A full run is hours of Cube, so `--resume-at` restarts at the step that died
instead of from the beginning. **The named step runs** — everything before it is
skipped:

```bash
tm1 run PBA50+_FBP --scenario 2050_TM162_FBP_Plan --run-number 1 --resume-at hwy_assign
tm1 run PBA50+_FBP --scenario 2050_TM162_FBP_Plan --run-number 1 --resume-at 2:hwy_assign   # iteration 2's
```

The `N:` prefix is needed only when a step runs more than once — that is, inside
`iterate` with `count > 1`. A bare name matching several rounds is an error
listing the candidates, not a guess, since picking the wrong one costs hours.

You rarely type it: a failure prints the exact command.

```
--- Step: hwy_assign ---
ERROR  Cube job HwyAssign.job failed (exit=2, engine ReturnCode=2)
       Full Cube log: E:/Tests/PBA50+_FBP/_cube_HwyAssign_18004_1785277879.log
       Resume with: tm1 run PBA50+_FBP --scenario 2050_TM162_FBP_Plan --run-number 1 --resume-at 2:hwy_assign
```

And the resumed run states what it is doing before doing any of it:

```
Resuming at hwy_assign, iteration 2 of 3
  skipping 4 already-completed step(s): copy_inputs@1, simulate_ctramp@1, hwy_assign@1, simulate_ctramp@2
  running 4: hwy_assign@2, simulate_ctramp@3, hwy_assign@3, vmt_vht_metrics@3
```

Two things it deliberately does not do. The named step **re-runs from the start**
rather than continuing part-way — Cube jobs are not transactional, so a killed
`HwyAssign` leaves partial `.net` files that only a fresh run overwrites. And it
refuses to resume a run number with nothing under it, since "resume" presupposes
a previous run; without that check it would skip staging and demand, then assign
whatever stale matrices happened to be lying around.

### Creating a New Project

Steps 1-4 edit the repo -- do them in your own clone, then commit and push. Step 5 runs
the model -- do it on a modeling machine, cwd'd into the mapped clone.

1. Copy `projects/PBA50+_FBP/scenarios.yaml` to `projects/<name>/`
2. Update each scenario's `copy_inputs` sources for your environment -- there is no
   project-level defaults layer, so every scenario needs its own full set
3. Adjust the shared pipeline only if this project genuinely needs a different one --
   see [`default-configs/ctramp-cube-model.yaml`](default-configs/ctramp-cube-model.yaml)
4. Declare the runs under `scenarios:`; `tm1 scenarios <name>` checks every address,
   including that no `REQUIRED` placeholder is left unresolved
5. Run with `tm1 run <name> --run-number 1`

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

Optional, in a scenario's own overrides (or the shared model file):

```yaml
logging:
  level: DEBUG            # what reaches the file; console stays at INFO
  dir: "{run_dir}/logs"  # override the location
```

This replaces `RunModel.bat`'s `echo ... >> logs\feedback.rpt`, which recorded
only start and finish milestones.

### Template Placeholders

Three different things all look like `{...}`, resolved in different places:

| Placeholder | Resolved | Works |
|---|---|---|
| `{env:NAME}` | first, from the environment | anywhere in the config |
| `{key}` | after `{env:...}`, from any top-level scalar in the resolved config | anywhere in the config |
| `{iteration}`, `{PERIOD}` | later, per step invocation | only inside the step that declares them |

`{key}` is not a fixed list -- any top-level scalar the config has becomes a
placeholder everywhere below it, whether a scenario/model file wrote it (`m_drive`,
`model_year`, `slack`, `logging`) or the runner injects it right before resolving
templates, and so is **not settable** by a scenario:

| Key | Value |
|---|---|
| `run_dir` | `{runs_root}/{scenario}_{NNN}` |
| `runs_root` | `TM1_RUNS_ROOT` (from the active environment file, keyed by hostname) |
| `project` | the project's folder name, e.g. `PBA50+_FBP` |
| `scenario` | the scenario's own `id`, e.g. `PLAN-2050-V16` |
| `run` | `{scenario}_{NNN}`, e.g. `PLAN-2050-V16_002` -- `run_dir`'s last segment |

`{iteration}` and `{PERIOD}` are different: they survive config loading unexpanded
and are filled in later, once per step invocation -- `{iteration}` to whichever
round is currently running, `{PERIOD}` once per assignment period
(`EA`/`AM`/`MD`/`PM`/`EV`). They only work inside a step's own block (e.g.
`cwd: "trn/TransitAssignment.iter{iteration}"`), not as a top-level config value.

Set in `src/tm1/run/prepare.py` (`run_dir`/`runs_root`/`project`/`scenario`/`run`),
`src/tm1/project/config.py` (`{env:...}`/`{key}` resolution), and
`src/tm1/steps/external.py` (`{iteration}`/`{PERIOD}`).

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

`projects/PBA50+_FBP/hooks.py` is a worked example: `vmt_vht_metrics` reads
the loaded network the feedback block writes and summarises VMT, VHT and implied
congested speed by facility type — a reduced form of
`utilities/RTP/metrics/hwynet.py`. It aggregates rather than copies, which is the
pattern the migration is trying to establish; see
[`MIGRATION_NOTES.md`](MIGRATION_NOTES.md) on porting intent rather than mechanism.