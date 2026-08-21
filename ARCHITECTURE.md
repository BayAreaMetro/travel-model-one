# Architecture

For people changing this code. If you want to *run* a model, read
[docs/running-a-model.md](docs/running-a-model.md) instead.

---

## What this is

Given a **project** (a config), optionally permuted into **cases**, produce results by
executing an ordered sequence of **steps**, some of which drive **external engines**,
resumably, on one or many machines, leaving a record.

Those four nouns stack, and the stack is the architecture:

```
CLI

  PROJECT     config.yaml, cases.yaml, overrides       reads files, decides nothing
     |
  RUN         which steps, which round, which directory, and doing it
     |
  STEPS       the model's units of work
     |
  ENGINES     Cube, CT-RAMP, ActivitySim, AequilibraE
```

Two rules fall out, and they are most of what matters:

**An engine never knows a project exists.** It takes paths and parameters. That is what
lets Cube process-probing serve both the runner and `tm1 status` without either importing
the other.

**A step is an adapter, not an implementation.** Config in, one call into an engine,
outputs on disk. A step that grows past a few hundred lines means engine knowledge leaked
upward.

## The tree

```
src/
  cube/                      THE CUBE PROGRAM.  Zero tm1 imports.
    job.py            459    run a .job: cluster, licence, interactive session
    process.py        162    read-only: are this run's Cube processes working, or wedged?

  tm1/
    cli.py            262    tm1 run / tm1 status / tm1 cases

    project/                 READING THE TWO YAMLs.  No I/O beyond reading files.
      config.py       124    config.yaml, {env:} and {run_dir} resolution
      cases.py        321    cases.yaml: explicit, ladder, matrix
      overrides.py    226    how a case changes a value, and whether it resolves

    run/                     DOING ONE RUN                    <- RunModel.bat
      directory.py    103    where does this run go?
      fingerprint.py  105    has anything changed since last time?
      receipt.py       95    what ran, on what machine, how it ended
      prepare.py      143    project + case -> a run ready to start
      iterations.py   463    which steps, which round, which of them you asked for
      model.py        467    run_model(): walk the list, call each step, log it

    status/                  CHECKING ON A RUN.  Read-only, separate process.
      __init__.py      54    status()
      read.py         227    what the log says happened, and whether it still is
      grid.py         424    the grid, the verdict, the resume line
      slack.py         91    post a message to Slack

    steps/                   THE MODEL'S STEPS
      __init__.py     175    the catalog: step name -> the function that runs it
      setup.py  staging.py  external.py  assignment.py
      configure_ctramp.py  simulate_ctramp.py

    assignment/cube/         our use of Cube: which .job files, in what order
      highway.py  transit.py  ctramp.py
```

`tm1/` root holds **one** file. That is deliberate and worth keeping.

## Invariants

These are greppable. If one starts failing, the layering has drifted:

```bash
# Cube is standalone -- it must never know a project exists
grep -rn "^from tm1\|^import tm1" src/cube/*.py                  # 0

# project/ reads files; it does not know where a run goes
grep -rn "^from tm1.run\|^from tm1.steps" src/tm1/project/*.py   # 0

# watching a run must not depend on the code that runs one
grep -rn "^from tm1.run.model" src/tm1/status/*.py               # 0

# a private import across a module boundary means the boundary is not real
grep -rn "^from tm1\..* import .*\b_[a-z]" src/tm1/ --include=*.py  # 0

# who is allowed to know Cube exists
grep -rn "^from cube\|^import cube" src/tm1/ --include=*.py
```

That last one should return exactly four kinds of caller, and no others:

| | why |
|---|---|
| `assignment/cube/*` | our use of Cube — which `.job` files, in what order |
| `steps/external.py` | the adapter for a config-declared `job:` step |
| `steps/simulate_ctramp.py` | CT-RAMP's Java needs Cube's DLL and licence |
| `status/grid.py` | is Cube working right now, or wedged? |

Anything else importing `cube` means model knowledge is leaking into the engine layer, or
engine knowledge is leaking up.

The third one is the one that bit us: `status.py` used to import four underscore-prefixed
names out of the runner, so any change to the runner could silently break the tool you use
to find out what the runner did — and 255 passing tests did not notice.

## Naming

Every module is named after a noun a modeler already says. If a name needs a paragraph to
justify it, it is the wrong name.

Rejected, and why:

| rejected | chosen | |
|---|---|---|
| `harness/` | `project/` `run/` `status/` | jargon; these are the words people type |
| `address.py` | `overrides.py` | it is how a case overrides the config |
| `sequence.py` | `iterations.py` | RunModel.bat's own word |
| `execute.py` + `run_model` | `run/model.py` -> `run_model()` | one name for one thing |
| `status.py` + `status_render.py` | `status/read.py` + `status/grid.py` | what happened / the picture |
| `report.py` | deleted | competed with `status` |
| `registry.py` | `steps/__init__.py` | open the steps package, see the steps |

## Where RunModel.bat went

| RunModel.bat | here |
|---|---|
| Step 1 — path variables | `project/config.py` + `.env` |
| Steps 2–3 — directories, pre-process | `steps/staging.py`, `steps/setup.py` |
| Steps 4, 4.5 — non-motorized LOS, transit files | config-declared `job:` steps |
| Steps 5–9 — iteration N | `run/iterations.py` drives the plan |
| the `.job` calls | `cube/job.py` |
| `logs/feedback.rpt` | the run log, read back by `status/` |
| Step 18 — clean up | gone; nothing is ever deleted |

## Adding things

**A step**: write the module, add one line to `STEPS` in `steps/__init__.py`. That is
deliberately the whole procedure — it is the seam every later phase attaches to, and a
one-line change is one a rebase can resolve. Before this existed, four downstream branches
all edited the same dict in a 1,055-line module.

**An assignment backend**: a folder beside `assignment/cube/`, plus one catalog line. The
transit engine is unsettled — Cube TRNBUILD today, Bentley PT likely, AequilibraE
possible — so nothing above `steps/assign` may know which one is in use.

**A machine-specific path**: `.env`, never code. Code may keep a `_DEFAULT_*` only as
"what to try when `.env` says nothing". Point at *files*, not directories to be searched —
the search is what breaks when a vendor moves something.

## Deliberate exceptions

**`steps/simulate_ctramp.py` is 1,051 lines and stays that way.** The parity claim rests on
it, so every change costs a full verification run to re-establish that the numbers still
match. Change it for correctness, never for tidiness. CT-RAMP is being *strangled* by
ActivitySim, not maintained — the file has a bounded life and refactoring it buys nothing.
The same reasoning covers `steps/configure_ctramp.py` and `assignment/cube/transit.py`.

Everything else is ~500 lines or less.
