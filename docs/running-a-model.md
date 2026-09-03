# Running a model

This replaces `RunModel.bat`. The model, its inputs and its results are unchanged: every
legacy `.job` and `.py` runs unmodified, from where it already lives. Only the
orchestration differs.

The sections below are ordered for a reader who knows `RunModel.bat`.

---

## Where RunModel.bat went

| RunModel.bat | now |
|---|---|
| Step 1 — set path variables | `.env` (machine-specific) + `config.yaml` (everything else) |
| Step 2 — create the directory structure | the `make_directories` step |
| Step 3 — pre-process | the `copy_inputs` step, then the pre-process steps |
| Steps 4, 4.5 — non-motorized LOS, transit files | steps in `config.yaml`, in order |
| Step 5 — prepare iteration 0 | the `warmstart:` block |
| Steps 6–9 — RunIteration, four times | the `iterate:` block, `count: 3` |
| the `.job` calls throughout | still `.job` calls — run through Cube, unmodified |
| Steps 11, 13 — skim databases, logsums | steps after the loop |
| Steps 14–17 — core summaries, metrics | steps after the loop |
| `logs/feedback.rpt` | the run log — read it with `tm1 status` |
| Step 18 — directory clean up | gone. Nothing is ever deleted |

---

## Differences from RunModel.bat

Three, and they are the ones that change existing habits.

**1. `.env` is configured once per machine.**
Machine-specific roots — a drive letter, a UNC share, the location of gawk — live there
instead of in `config.yaml`. See [README.md#setup](../README.md#setup).

**2. The run does not execute in the working directory.**
`RunModel.bat` ran in the directory containing it. A run now executes in
`{TM1_RUNS_ROOT}/{project}/{case}-{NNN}`, a new numbered directory each time.

No existing run is deleted or overwritten. Re-running after a land use update produces
`-002` alongside an intact `-001`.

**3. `config.yaml` is declarative.**
It states what runs, not how. It is intended to be read from top to bottom.

---

## Quickstart

Setup (installing `uv`, the project and its `--extra legacy` dependencies) is in the
top-level [README.md](../README.md#setup) -- one copy, so the two cannot drift apart.

```bash
uv run tm1 run PBA50+_FBP
```

To report on a run, from any shell, during it or after it:

```bash
uv run tm1 status PBA50+_FBP
```

To list the cases a project declares and check that the project is runnable:

```bash
uv run tm1 cases PBA50+_FBP
```

A project is a directory under `projects/` containing a `config.yaml`. A path is also
accepted, so a project may live outside the repository:

```bash
uv run tm1 run E:/my_projects/cordon_pricing
```

### About `uv run`

`uv run <command>` executes a command inside the project's virtual environment, creating
or updating that environment first if the lockfile has changed. It removes the need to
activate anything, and it guarantees the command runs against the dependency versions
`uv.lock` pins rather than whatever happens to be installed on the machine.

If the environment is already activated, the prefix is unnecessary and `tm1 …` is
equivalent:

```bash
.venv\Scripts\activate        # Windows
tm1 run PBA50+_FBP           # no prefix needed from here on
```

The remainder of this document writes `tm1 …` without the prefix. Add `uv run` in front
of any of them if the environment is not activated.

---

## Recovering an interrupted run

A run can be interrupted by a lost Cube licence, an unavailable network path, or a machine
restart. The run directory survives, and completed steps remain completed.

```bash
tm1 status PBA50+_FBP        # what ran, what failed, and how to resume
```

`status` reports the command that resumes the run, normally one of:

```bash
tm1 run PBA50+_FBP --resume-at hwy_assign
tm1 run PBA50+_FBP --resume-at 2:hwy_assign   # when the step runs in several rounds
```

The named step re-runs from its beginning, never part-way through, and every step before
it is skipped. `--until` is the converse; the two combine to run any contiguous slice:

```bash
tm1 run PBA50+_FBP --until 0:publish_networks   # just the warm start
```

---

## The config format

### Declaring a step

Four ways. The first two spawn a process; paths in them are relative to the run directory.

| | |
|---|---|
| `job:` | a Cube `.job`, run through Cube |
| `command:` | any other program |
| `module:` | an importable dotted path, called with the resolved config |
| `script:` | a `.py` in this project's directory |

```yaml
  - set_tolls:
      job: "CTRAMP/scripts/preprocess/SetTolls.job"

  - csv_to_dbf:
      command: "CTRAMP/scripts/preprocess/csvToDbf.py"
      args: ["hwy/tolls.csv", "hwy/tolls.dbf"]
```

### Rounds

Steps run in the order written. Two entries nest, and they are the only thing that decides
a step's round:

| | |
|---|---|
| `warmstart:` | runs its steps once at iteration 0 — RunModel.bat's `set ITER=0` |
| `iterate:` | repeats its steps `count` times, rounds 1..count |

Anything written flat runs once where it sits: round 1 before the loop, the final round
after it. There is no per-step iteration key.

`--iterations N` overrides `count` from the command line.

### Other keys a step may declare

| | |
|---|---|
| `cwd:` | run from a subdirectory of the run directory |
| `env:` | extra environment variables, layered on the project's |
| `verify:` | files that must exist afterwards, or the step failed |
| `timeout:` | seconds before the step is considered hung |
| `cluster_nodes:` | Cube Cluster nodes to start — a machine setting, not a model one |
| `skip_if_exists:` | its work is done when this file is on disk |
| `enabled: false` | skip this step entirely |

### The `skip_if_exists` rule

> A step may only name a file that is **its** product and nobody else's.

Naming a file that a later round overwrites makes the check answer a different question
— *does round 3's output exist* — and skip work that was never performed. Deleting the
named file forces a rebuild.

A step without the key always runs, which is frequently correct: inexpensive file
operations repeat harmlessly, and a step whose output is not round-specific must rebuild,
or a resumed run differs from a fresh one.

### Machine settings vs. model settings

`cluster_nodes`, `threads`, `intrastep_processes` and `timeout` tune a machine. They are
held in `config.yaml` rather than `.env` because they are not paths, and they do not affect
results — which is what allows runs from different machines to be compared.

`intrastep_processes` is constrained: it selects a real file, and only
`HwyIntraStep_48.block` and `HwyIntraStep_64.block` exist. A value that is too high does
not fail. Cube addresses processes that were never started, falls back to serial
execution, and the run completes in roughly five times the expected duration.

---

## Starting a new project

A project is a folder with two files:

```
projects/my_project/
  config.yaml     the full model, with real values          (required)
  cases.yaml      named variations on it                    (optional)
```

Copy the nearest existing project and edit it. `PBA50+_FBP` is the RunModel.bat
parity run and the usual starting point.

```bash
cp -r projects/PBA50+_FBP projects/my_project
tm1 cases my_project          # verify before committing to a full run
```

Then work down `config.yaml`. Most projects change only a few regions:

| intended change | what to edit |
|---|---|
| a different forecast year | `env.MODEL_YEAR`, and the `copy_inputs` entries for land use, popsyn and networks |
| a different network or land use | the `from:` of the relevant `copy_inputs` entry |
| a policy variant | the `.job` of the step that implements it, e.g. `set_tolls` |
| running on a different machine | nothing here; `cluster_nodes` / `threads` if the machine differs in size |
| a shorter test run | `iterate.count`, and `simulate_ctramp`'s `sample_rate` |

The step list itself rarely changes. Adding or removing steps generally indicates a
different project rather than a case — see rule 4 below.

> **Verify before running.** `tm1 cases my_project` completes in about a second and checks
> the three conditions that would otherwise surface part-way through a run:
>
> - `config.yaml` parses and `cases.yaml` expands
> - every `.env` variable the project references is set
> - every case's overrides resolve to a real value in the config
>
> It exits non-zero on failure, so it is usable in a script.

---

## Cases: one project, many runs

A **case** is a named set of overrides on `config.yaml`. `config.yaml` is the full model
with its default values; `cases.yaml` says how each run differs from it.

Each case runs in its own directory, `{case}-{NNN}`, so cases never collide.

### Addressing a value

An override names *where the value lives* in `config.yaml`:

```yaml
m_drive: "X:/models"                               a top-level key
env.MODEL_YEAR: 2035                               inside a top-level mapping
env.EN7: ENABLED                                   ... and its siblings survive
copy_inputs.input_landuse.from: "M:/.../landuse"   inside a step
iterate.count: 1                                   the loop's own key
iterate.simulate_ctramp.threads: 12                a step inside the loop
warmstart.hwy_assign.cluster_nodes: 24             the same step, at round 0
```

Four rules, and they are the whole mechanism:

1. **The address must already exist.** Nothing is declared up front — the config's value at
   an address *is* the default, its type *is* the type, and its existence *is* the
   validation. An address that resolves to nothing is an error naming the closest match, so
   a typo cannot quietly run the default.
2. **Values replace, never merge.** Naming a mapping replaces it whole. Name a deeper
   address to change one key — overriding `env:` to change `EN7` would silently drop `PATH`.
3. **A step in both blocks must say which.** Twelve steps appear in both `warmstart:` and
   `iterate:`. Bare, they are ambiguous, so write `warmstart.hwy_assign...` or
   `iterate.hwy_assign...`.
4. **`steps` itself is not addressable.** A case varies values inside the pipeline; it never
   adds, removes or reorders steps. A different pipeline shape is a different project.
   (The one exception is `enabled: false`, which any step accepts.)

### Three ways to declare them

All three expand to the same flat list, so the rules above apply regardless of which is
used. They may be combined in one file.

**`cases:` — written out, one entry per run.** For runs with little in common.

```yaml
cases:
  PARITY-2023:
    description: RunModel.bat parity, adopted networks and land use.

  NOPK-2035:
    description: 2035 land use, no parking cost growth.
    env.MODEL_YEAR: 2035
    copy_inputs.input_landuse.from: "{m_drive}/.../LandUse_n_Popsyn/2035_v12/landuse"
```

**`ladder:` — cumulative.** Rung *k* carries rungs 1..*k*, so the difference between
adjacent rungs isolates the single intervention that was added. This is the form used to
attribute a contribution to each component of a package.

```yaml
ladder:
  - id: "L1-{n}-{rung}-2035"
    description: 2035 blueprint, built up one strategy at a time.
    env.MODEL_YEAR: 2035                   # applies to every rung
    rungs:
      - TRNF:
          description: Transit frequency.
          env.EN7: ENABLED
      - CORD:
          description: Cordon pricing.
          set_tolls.job: "variants/SetTolls_cordon.job"
```

Produces `L1-01-TRNF-2035` and `L1-02-CORD-2035`; the second carries both overrides.

**`matrix:` — the cross product of named axes.** For sweeps.

```yaml
matrix:
  - id: "A1-{tolls}-{landuse}"
    axes:
      tolls:
        NOTL:                              # no overrides: the config as written
        CORD:
          set_tolls.job: "variants/SetTolls_cordon.job"
      landuse:
        ADPT:
        JHBL:
          env.MODEL_YEAR: 2035
    exclude:
      - {tolls: CORD, landuse: JHBL}       # combinations that are not meaningful
```

Produces `A1-NOTL-ADPT`, `A1-NOTL-JHBL` and `A1-CORD-ADPT`. Exclusions are reported rather
than silently dropped from the count. An `exclude:` rule may name a subset of the axes, so
it remains correct when a further axis is added.

A matrix case's description is assembled from its axis points, so each point should carry a
`description:`. Without one, `tm1 cases` lists the case with an empty description, leaving
the ID as the only identifying information in a large sweep:

```yaml
      tolls:
        NOTL:
          description: No new tolls.
        CORD:
          description: Cordon pricing.
          set_tolls.job: "variants/SetTolls_cordon.job"
```

### Case IDs

`SERIES-TOKENS-YEAR` — uppercase, hyphen-separated, e.g. `A001-NOPK-2035`.

**IDs are permanent.** The ID names the run directory, so renaming a case converts a
completed run into an unrun one, at the cost of the full run time. Descriptive text belongs
in `description:`, not in the ID.

Ladder and matrix generate IDs from the `id:` template, with two consequences:

- **Adding a matrix axis value does not rename existing cases.** The tokens are part names,
  not positions.
- **Inserting a ladder rung renames every rung after it.** This is correct: it changes what
  each later rung represents.

### Running one

```bash
tm1 cases my_project              # what the project declares, and whether it resolves
tm1 run my_project --case NOPK-2035
```

---

## What the run leaves behind

```
{TM1_RUNS_ROOT}/{project}/{case}-001/
  INPUT/          every input staged in, as the run's record of what it consumed
  hwy/ trn/ skims/ landuse/ popsyn/ nonres/ main/ database/ logsums/ metrics/
  logs/           the run log
  CTRAMP/         the model code this run used, copied from this checkout
```

`INPUT/` is what makes a run self-contained and interpretable later. Nothing the model
*produces* is staged there — no skims, no accessibility, no synthetic population — so a
failure in the steps that build those outputs cannot be masked by a stale file.
