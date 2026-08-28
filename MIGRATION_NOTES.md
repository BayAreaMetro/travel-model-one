# Migration Notes

Working notes on the Travel Model One → Python migration (branch `activitysim_revival`):
scope, progress to date, and the status of each component. This is a living log, not a fixed
plan or a PR description — it covers the whole multi-year journey and will lag behind the
code between updates. For a specific PR's scope, write a dedicated summary rather than
pointing at this whole file.

## Phases

The migration ships as a sequence of independently reviewable PRs, ordered by dependency.
CT-RAMP + Cube remain the production stack throughout — nothing below changes what runs in
production until its own phase lands and passes its own gate.

| # | Phase | Scope | ~files | Status |
|---|---|---|---|---|
| 1 | Runtime harness | `tm1` CLI, runner, project config chain; flat steps + project-supplied steps; `copy_inputs` / `simulate_ctramp` / `assignment`; `PBA50+_FBP`; target-layout scaffold | ~40 | **in progress** |
| 2 | Cube matrix I/O | `cubeio` — pure-Python TPP ↔ OMX, no Cube install; bit-exact golden tests | ~30 | ready |
| 3 | Calibration reporting | HTML calibration/validation report system (needs #2 to read `.tpp` skims) | ~37 | ready |
| 4 | Model parity | the rest of `RunModel.bat`, ported for *equivalent results* rather than in kind (see [Port the intent, not the mechanism](#port-the-intent-not-the-mechanism)): preprocess (`SetTolls`, `SetHovXferPenalties`, `CreateFiveHighwayNetworks`, `HsrTripGeneration`, `CreateNonMotorizedNetwork`, `NonMotorizedSkims`, `csvToDbf.py`, `transitDwellAccess.py`), inputs from the reference run's pristine `INPUT/`, then post-processing (EMFAC, logsums, core summaries, metrics) — dropping the steps that exist only to move data between Cube, R and batch | — | not started |
| 5 | ActivitySim swap-in | config corpus + projects + ActivitySim/PopulationSim steps + Cube harness and the ActivitySim↔Cube demand bridge | ~200 | pending full PBA50 review |
| 6 | Assignment backend | AequilibraE engine, params, parity validation | ~25 | prototype — needs buy-in |
| 7 | Housekeeping | legacy triage of `core/`, `model-files/`, `utilities/` (see [Diffs from legacy → target](#diffs-from-legacy--target)) | — | not started |
| 8 | Documentation | published docs for the Python stack -- CLI, project config, step contract, migration status; replaces the wiki pages that describe the `.bat` workflow | — | not started |
| 9 | Beyond | network enhancements, etc. | — | not scoped |

### One variable at a time

Each phase changes exactly one of the two moving pieces, so every phase can be validated
against the one before it:

| Phase | Demand | Assignment | What actually changes |
|---|---|---|---|
| 1–3 | CT-RAMP | Cube | orchestration, matrix I/O, reporting — no model change |
| 4 | CT-RAMP | Cube | the non-residential models move to Python |
| 5 | **ActivitySim** | Cube | the demand engine, and nothing else |
| 6 | ActivitySim | **AequilibraE** | the assignment engine, and nothing else |

The combination deliberately never built is CT-RAMP + AequilibraE. AequilibraE exists to
serve ActivitySim; CT-RAMP and Cube retire together. That is what keeps this a diagonal
rather than a grid, and it is why the demand→assignment seam needs one modern format plus
one legacy adapter rather than every engine speaking to every other.

Phase 4 comes *before* the ActivitySim swap-in deliberately. Until preprocess is ported, a
run inherits its period networks from a completed reference run instead of building them
from `freeflow.net` — so an ActivitySim-vs-CT-RAMP comparison made through this harness
cannot separate "the demand model differs" from "the harness is not reproducing the
baseline". Establish parity, then swap components.

Notes on the ordering:

- **Phase 1 replaces `SetUpModel.bat`'s staging and all of `RunIteration.bat`** -- CT-RAMP
  demand plus Cube assignment, feedback and skims, every `.job` script run unmodified. It
  does *not* replace `RunModel.bat` end to end: that script's preprocess and post-processing
  phases are phase 4. It needs no `cubeio`: CT-RAMP's demand reaches Cube through
  `PrepAssign.job`, a Cube job, so no Python code touches matrix content. ActivitySim is the
  case that needs a Python bridge (phase 5), because it emits OMX.
- **Phase 5 is irreducibly large** — ~164 of its files are the ported UEC specs, which are
  validated by output comparison rather than by reading. It is a data drop, not a code review.
- **Phases 2 and 3 are separable from 1** only because nothing in a CT-RAMP-only pipeline
  reads Cube matrices from Python; the calibration report is the first thing that does.


## Port the intent, not the mechanism

Parts of the legacy pipeline exist to bridge its toolchain rather than to model anything.
The clearest case: `.tpp` matrices could only be read by Cube, so data was exported to CSV
and passed between Cube, R and batch. Given the tools available, that was a sound design.
Re-implementing it in Python would carry the cost forward without the constraint that
motivated it.

Measured on the 2023 reference run (~53 GB), roughly **10 GB per run is derived or
duplicated data**:

| Artifact | Size | Why it exists |
|---|---|---|
| `database/*SkimsDatabase{period}.csv` | 4.4 GB | `SkimsDatabase.job` exports the `.tpp` skims to CSV so R and Python can read them |
| `main/indivTripDataIncome_3.csv` | 1.6 GB | `joinTripsWithIncome.R` rewrites the 1.5 GB trip table to attach one income column |
| `extractor/` | 2.2 GB | a subset materialised as a folder so the next line can `Robocopy` it to `M:` |
| `updated_output/*.rdata` | 1.0 GB | R re-serialisation of data already written as CSV |
| `INPUT/` copied into working dirs | 0.6 GB | preserves pristine inputs by duplicating them |
| `CTRAMP/` model code | 0.2 GB | the model source, copied into every run directory |

Plus smaller copies that align a file with a name a downstream script expects --
`popsyn/hhFile.*.csv` → `hhFile.csv`, `main/ShadowPricing_7.csv` →
`logsums/shadowPricing_7.csv`, `INPUT/metrics/BC_config.csv` → `metrics/`.

The principles that follow, and which the port should hold to:

- **Read the native format.** `cubeio` (phase 2) reads `.tpp` directly, so `database/` has
  no reason to exist. That single capability removes 4.4 GB per run *and* the `.job` script,
  the R reader and the Cube/R/batch handoff around it.
- **Join at read time; do not materialise.** Attaching income to trips is a merge, not a
  1.6 GB artifact.
- **Select with a list, not a folder.** Ship a manifest, or write straight to the
  destination — do not stage a copy in order to copy it again.
- **Resolve paths in config** rather than copying a file to match an expected name.
- **Machine differences belong in configuration.** `RunLogsums.bat` selects its host IP
  from eleven `if %computername%==...` lines, and `CopyFilesToM.bat`'s destination still
  points at an RTP2017 path -- both are easier to keep current in a `.env`.

So phase 4 targets *parity of results*, not of file layout. Where a step exists to move data
between tools, the port should reproduce the result rather than the step — and say so, with
the before and after, so reviewers can check the reasoning rather than the diff.

`projects/PBA50+_FBP/hooks.py` is the small worked example of the target shape: it
reads an output the pipeline already writes and aggregates it to a few rows, rather than
copying anything.


## Repo layout

### Existing (legacy)

```text
travel-model-one/
|-- core/          legacy Java/Ant model code + bundled dependencies
|-- model-files/   runnable model assets, runtime configs, batch files
|-- utilities/     one-off analysis, calibration, GIS, data-prep scripts
```

### Target

```text
travel-model-one/
|-- default-configs/   base configs, specs, lookup tables, default assets (activity/ assignment/ population/)
|-- projects/      config.yaml + cases.yaml per project (base_2023_activitysim, PBA50+_FBP, ...)
|-- scripts/       run/prep/export entrypoints + migration_validation/{activitysim,assignment}
`-- src/           shared Python: cubeio/, tm1/ (steps, assignment/{cube,aeq})
```

### Diffs from legacy → target

- `core/` → retire from day-to-day layout; use installable `activitysim` where possible.
- `model-files/model/` → `default-configs/`.
- `model-files/runtime/` → split between `default-configs/` and `scripts/`.
- `model-files/scripts/` → move into `scripts/` or `src/`.
- `utilities/` → cherry-pick only maintained pieces into `scripts/` or `src/`.
- `utilities/RTP/config_RTP2025/` → `projects/RTP2025/`.

### Working principle

Separate (1) base model assets, (2) project/case deltas, (3) operational scripts, (4) shared code.
That keeps the repo reasonable to reason about and makes eventual deletions obvious.

### What dies (eventually)

- `RunModel.bat`, `RunIteration.bat`, `RuntimeConfiguration.py`
- JPPF/Java startup, `PrepAssign.job`, `core/` Java code
- All `.job` files (Cube skims, assignment, nonres, preprocessing) — once `backend=aeq` fully
  replaces the Cube launcher
- Anything not in `default-configs/`, `projects/`, `scripts/`, or `src/`

---

## CLI

Installed via `pyproject.toml` → `tm1` command. This is the only entry point; there is
no launcher script to keep in sync. The project argument takes a name under `projects/`
or a path, so a project can live outside the repo.

```
tm1 run PBA50+_FBP                        # the whole pipeline
tm1 run PBA50+_FBP --steps assignment     # one step
tm1 run PBA50+_FBP --iterations 3         # override iterate.count
tm1 run E:/runs/one_off                         # a project outside the repo
tm1 run PBA50+_FBP --slack verbose
```

Flags: `--steps`, `--iterations`, `--resume-at`, `--until`, `--slack {off,minimal,verbose}`.

`cases.yaml` declares the runs a project defines -- explicit, ladder (cumulative)
or matrix (cross product) -- each a set of overrides addressed by where the value
lives in `config.yaml`. `tm1 cases <project>` expands them and checks every address;
a case that does not resolve stops a run before it starts.

**Not implemented** — selecting a case to run, and running many across machines.
The intent is that each machine runs the same `tm1 run <project>` and a per-case
lock file in a shared index decides who takes what.

---

### 1. Runtime harness

Dual purpose:
- Streamline the runtime and eliminate the `.bat` script chain, while CT-RAMP + Cube remain
  in production, unchanged, throughout.
- Stand up the platform ActivitySim swaps into once current calibration work wraps up,
  without disrupting that work.

**A full global iteration.** CT-RAMP runs headless from the `tm1` CLI, then the Cube
launcher drives `PrepAssign -> HwyAssign -> transit -> feedback -> HwySkims` -- the same
scripts `RunIteration.bat` calls, in the same order.

Also lays down the target directory structure as empty, README-only placeholders, so the
layout can be argued over while it is still free to change.

Project-specific pre/post-processing scripts (currently scattered across `utilities/` and
`model-files/scripts/`) now have a home: any step can point at Python via `script:` or
`module:`, and where it sits under `steps:` decides whether it runs before or after the
model. `projects/PBA50+_FBP/hooks.py` ports the runnable subset of
`utilities/RTP/ExtractKeyFiles.bat` as a worked example. Which of the remaining legacy
scripts are worth carrying forward is phase 7's triage.

### 2. Cube matrix I/O

`src/cubeio/` — pure-Python Cube Voyager matrix I/O (TPP ↔ OMX), no DLLs and no Cube
install, validated bit-exact against Cube's own CSV dumps. Standalone library; nothing in a
CT-RAMP-only pipeline needs it, which is why it is separable from phase 1.

### 3. Calibration reporting

The HTML calibration/validation report system (`src/tm1/steps/summaries/calibration/`) —
survey vs model comparison per submodel. Engine-agnostic: CT-RAMP exercises it today, and it
is the first consumer of phase 2, since it reads distance skims straight from `.tpp`.

### 4. Model parity

The rest of `RunModel.bat`: the preprocess phase that builds the period networks from
`freeflow.net`, inputs sourced from the reference run's pristine `INPUT/` rather than its
post-run working directories, and then post-processing. Ported for *equivalent results*
rather than in kind — see [Port the intent, not the mechanism](#port-the-intent-not-the-mechanism).

Sequenced before the ActivitySim swap-in deliberately: until a run derives its own networks
instead of inheriting a completed Cube run's, an ActivitySim-vs-CT-RAMP comparison made
through this harness cannot separate a demand-model difference from a harness difference.

### 5. ActivitySim swap-in

Enable ActivitySim as the production demand model, after a thorough review against **PBA50**
CT-RAMP runs — broader than the 2023 reference run validated against so far (see
[The migration journey](#the-migration-journey) below for that validation detail).

Also carries the Python Cube harness (`src/tm1/assignment/cube/`) and the ActivitySim↔Cube
demand bridge, because ActivitySim is what first drives them: its trip output is OMX, and
Cube assignment wants `trips{PERIOD}.tpp`.

### 6. Assignment backend upgrade

Currently runs on Cube. AequilibraE is viable (Bonus 3 below) but replacing Cube in
production requires buy-in beyond engine-level parity — this phase doesn't start until that
buy-in exists.

### 7. Housekeeping

Go through `core/`, `model-files/`, `utilities/` file by file: decide what's worth keeping
(and where it moves — `scripts/`, `src/`, `default-configs/`) vs what gets deleted (retained
in git history, never truly gone). This is where the [Repo layout](#repo-layout) "Existing →
Target" mapping below actually gets executed, not just documented. Deliberately sequenced
*after* phase 5, not alongside phase 1 — moving legacy CT-RAMP/Cube paths while they're still
production-critical risks breaking scheduled runs for no functional gain.

### 8. Documentation

The [User's Guide](https://github.com/BayAreaMetro/modeling-website/wiki/UsersGuide) and
[Setup and Configuration](https://github.com/BayAreaMetro/modeling-website/wiki/SetupConfiguration)
pages describe the `.bat` workflow: edit a properties file, name the project folder so
`RunModel.bat` can slice a year out of it, run the batch chain.  None of that is how the
Python stack works, and the README cannot carry the whole story.

What needs writing: the CLI, the project config format (steps, `iterate`, custom steps
via `script:`/`module:`), the step contract for people adding their own, how to read a run
log, and where the migration has got to.  Plus a decision on where it lives -- a generated
site (mkdocs, published from this repo so it versions with the code) or the existing wiki,
which is easier to edit but drifts from the code and cannot be reviewed alongside it.

Sequenced late because documenting a convention that is still moving wastes the effort;
phase 1 fixes the config shape, and phases 4-6 settle what the pipeline actually contains.
Until then the README and
[Pipeline configuration conventions](#pipeline-configuration-conventions) are the record.

### 9. Beyond

Network enhancements and whatever else follows once the core migration is done. Not scoped.

---

## Pipeline configuration conventions

The project YAML is the interface most people will touch, and phase 1 fixes its shape.
Stated here so later phases extend it rather than inventing alternatives.

### Steps are a flat, ordered mapping

Every step is a key under `steps:` and runs in the order written. Reading top to bottom
tells you what runs and when. Deliberately no grouping: a category that only collects
steps adds a second place to look without saying anything the order does not, and invites
sub-steps whose ordering rule differs from the top level's.

### One nesting construct: `iterate`

```yaml
steps:
  copy_inputs: {}
  iterate:
    count: 3
    steps:
      simulate_ctramp: {}
      assignment: {}
  vmt_vht_metrics: {}
```

A global iteration is demand **plus** assignment — demand responds to the congested skims
the previous assignment produced, which is what `RunModel.bat` expresses by calling
`RunIteration.bat` N times. The body is nested rather than listed by name elsewhere, so
contiguity is structural instead of validated and each step is named once. Steps before
the loop run at iteration 1; steps after it run once at the final iteration, since they
summarise a finished run.

This is not a return to the `setup.copy_inputs` grouping: that was an arbitrary category,
whereas a loop body is a real construct with real semantics.

### Project-supplied steps

```yaml
  vmt_vht_metrics:
    script: "hooks.py:vmt_vht_metrics"     # path, relative to the project directory
  trip_length_report:
    module: "mtc_local.reports:trip_lengths"   # importable dotted path
```

Either may name the function after a colon; without one, `run` is called, matching the
built-in steps. There is no separate hook concept — a step written before
`simulate_ctramp` is pre-processing, one written after `assignment` is post-processing.
Position is the whole mechanism.

### Steps meet at artifacts

A step declares the artifact it consumes, never the step that produced it:

```yaml
  assignment:
    demand: "{run_dir}/main/trips{PERIOD}.tpp"
```

`PrepAssign.job` writes that file today, but nothing in the assignment step knows so.
Pointing a different demand model at the same seam is a config change rather than a code
change. Declaring it also gives the failure a name: a demand model that returns cleanly and
produces nothing fails here, at the seam, instead of several minutes later inside the
engine with an unrelated error.

`{PERIOD}` expands to `EA`/`AM`/`MD`/`PM`/`EV`. `resolve_templates` substitutes with
`str.replace`, so placeholders it has no value for pass through untouched — which is why
`{run_dir}` resolves at config load while `{PERIOD}` survives to the backend.

### `backend:` value, or a separate step name?

> Use a **`backend:` value** where the implementations share a contract.
> Use **separate step names** where they do not.

So `assignment` takes `backend: cube|aeq|…` while the demand models stay
`simulate_ctramp` and `simulate_activitysim`.

Assignment has one contract, whatever solves it:

| | |
|---|---|
| **in** | demand — one matrix per class × period (the `demand:` key) |
| | network — capacity, free-flow speed, tolls, class permissions |
| | parameters — value of time by class, periods, convergence target |
| **out** | a loaded network — volumes by class per link |
| | skims — time, distance, toll, cost by class × period |

Cube, AequilibraE and anything after them differ in *how* they solve that, not in what goes
in or comes out. Demand models differ in what they **model**: swapping CT-RAMP for
ActivitySim changes the inputs, the outputs, the calibration targets and the skim format.

The distinction is not how similar the implementations are — ActivitySim is a
reimplementation of CT-RAMP's design, so on similarity grounds demand could be generic too.
Nor is it permanence: an engine that wins a bake-off eventually deletes its rivals, exactly
as CT-RAMP is being deleted. What holds is *where the choice is made*:

- **Assignment is chosen within a project.** Same demand, same network, same inputs,
  different solver — which is precisely the comparison that decides which engine to adopt.
  One step name means the two runs being compared differ only in the solver, and not in the
  shape of the pipeline or its `--resume-at` points.
- **Demand is chosen between projects.** There is no useful run in which the demand engine
  changes and everything else holds; `PBA50+_FBP` and `base_2023_activitysim` are
  separate directories for that reason.

This is not a one-way door: adding a generic `simulate:` step later is additive, so the
choice defers rather than forecloses.

### What is additive, and what would break

Later phases can add freely: **new keys** in any step config, **new top-level blocks**,
**new built-in step names**, **new `backend:` entries**.

Avoid, because projects would have to be rewritten: renaming `assignment` to
per-engine steps, changing `iterate`'s shape, or moving a step's config somewhere other
than under its own name — for instance nesting assignment under a demand step, which the
ActivitySim path did before phase 1 unified the two.

See also [Port the intent, not the mechanism](#port-the-intent-not-the-mechanism): the
adapters that bridge Cube's formats are scaffolding, and the configuration should not make
them load-bearing.

---

## Goal

Two independent moving pieces:

- **Piece A — demand model.** Java CT-RAMP → Python ActivitySim (+ PopulationSim for the
  synthetic population). This is the committed direction.
- **Piece B — assignment/skimming.** Cube Voyager → a Python-native alternative.
  **Not yet decided.** AequilibraE is the current prototype/candidate (Bonus 3 below); Cube
  driven headlessly from the `tm1` Python harness (step 4) is also a viable long-term state
  if nothing beats it convincingly. Piece B's status has no bearing on Piece A and vice versa.

Both tracks share two hard requirements:

1. **Match Cube/CT-RAMP results.** Faithful replication, not a rebuild. Every divergence
   requires a documented, falsifiable justification.
2. **Match or exceed Cube/CT-RAMP performance.**

**Reference run** — the last CT-RAMP run, the benchmark for every comparison:

```
\\MODEL3-C\Model3C-Share\Projects\2023_TM161_IPA_35_testrun     (local mirror: E:\ref_2023_TM161)
```

---

## The migration journey

Progress to date, with current status. Steps 1–4 are the core sequence; the two bonus tracks
extend past the original scope. Engineering detail, not a second phase numbering — it cuts
across phases 1–3 and 5, with Bonus 3 (AequilibraE) being phase 6 prototyping done ahead of
schedule.

### 1. Port the skims — cubeless TPP ↔ OMX converter — **DONE**

* Pure-Python Cube Voyager matrix I/O, no DLLs and no Cube install (`src/cubeio/`):
`tpp_read.py` decodes every TPP block type, `tpp_write.py` writes them back, `omx.py`
bridges to OMX. 
* Validated bit-exact against Cube CSV dumps (golden pairs in
`tests/data/golden/`). 
* The `tm1.steps.convert_skims` step reads the ~96 reference TPPs and
emits a single 1-based `skims.omx` for ActivitySim.
* When using CUBE backend assignment, `tm1.steps.convert_skims` also reads the ActivitySim skims and writes them back to TPP for Cube assignment.

- Mapping: [`docs/SKIM_MAPPING.md`](docs/SKIM_MAPPING.md).

### 2. Convert the UECs to ActivitySim — **DONE**

* Ported the CT-RAMP utility expression calculators (`.xls` UEC workbooks) to ActivitySim
specs, submodel by submodel.
* A bit tedious because sometimes the a past modelers took different approaches to compute the same number (e.g., define global constants vs hardcode in the expression or a pre-computed value versus compute on the fly). The ActivitySim spec is more explicit and verbose, but the CT-RAMP UECs are more compact and sometimes opaque. The goal was to match the outputs, not the implementation.
* Built a crude coefficient viewer / comparator
(`scripts/migration_validation/activitysim/compare_coefficients.py`, `uec_mappings.py`,
`compare_template.html`) that parses the CT-RAMP `.xls` and the ActivitySim spec side by side.

- Notes: [`docs/ACTIVITYSIM_MIGRATION_NOTES.md`](docs/ACTIVITYSIM_MIGRATION_NOTES.md).

### 3. Validate ActivitySim against CT-RAMP on frozen skims — **IN VALIDATION** (iterates on #2)

With the reference `skims.omx` frozen (no assignment, no feedback), run both engines on the
same inputs and diff stage by stage. This is where step 2 got its feedback loop: a mismatch
in a stage's output sent me back to fix a coefficient or expression, then re-run.

- CT-RAMP runs **headless** via `src/tm1/steps/simulate_ctramp.py`.
- The **ablation harness** (`scripts/migration_validation/activitysim/ablation_activitysim.py`,
  `ablation_ctramp.py`, `evaluate_stages.py`) freezes upstream stages to CT-RAMP output and
  isolates one submodel at a time, so a diff can't hide behind an upstream diff.
- Submodels aligned one at a time (auto ownership → WFH → CDAP → work/school location →
  tour/trip mode → non-work destination → at-work subtours).
- Full-model checks: population, auto ownership, trip generation, and trip-length
  distributions all match CT-RAMP within ~2%; major mode shares (auto, walk) within ±4%.
  A disaggregate mode-share parity check — now a standing table in the calibration report —
  exposed over-prediction of the minor transit modes and led to the one CT-RAMP subsystem
  the port had missed entirely: **walk-to-transit subzones** (`walkAccessBuffers`), which
  gate transit availability and set access walk times. Ported (segments sampled per
  household-location in the mode-choice preprocessors); re-validation in progress.
- Cost-per-mile coefficient corrected to match CT-RAMP (tour/trip mode choice).
- Location-choice shadow pricing: parity is proven under a frozen jig (loading CT-RAMP's own
  converged prices, one pass, no re-solve), but the underlying update rule doesn't converge
  for *either* engine — it's an undamped, fixed-point-free iteration, not an ActivitySim
  defect. Full write-up: [`docs/ACTIVITYSIM_MIGRATION_NOTES.md`](docs/ACTIVITYSIM_MIGRATION_NOTES.md#shadow-pricing--location-choice-parity).


### 4. Assignment — wire in the Cube launcher via Python — **DONE**

Rather than reimplement Cube assignment first, drive the *existing* Cube `.job` scripts from
Python and close the loop: ActivitySim trip OMX → TPP demand → Cube assignment → skims back.

- `src/tm1/cube.py` — runs Cube Voyager jobs over SSH via the `schtasks` interactive-session
  launcher (the Bentley license pipe is unreachable from SSH/VS Code), with license recovery
  and MatReaderOpen hang detection. Cluster jobs go through `DistributeMultistep`.
- `src/tm1/assignment/cube/{highway,transit,runner}.py` — faithful Cube highway + transit
  assignment and network prep, wired into the feedback loop in `simulate_activitysim`.


### BONUSES

#### Bonus 1 — Sidegrade CT-RAMP — **DONE**
Made CT-RAMP run headless from the Python harness, so we can run a reference CT-RAMP run in the same way.


#### Bonus 2 — Wire in PopulationSim directly — **PARTIAL** (runs end-to-end, cached)

`src/tm1/steps/populationsim.py` + `default-configs/population/` produce a synthetic population
from PUMS + controls. The end-to-end chain (land use → PopulationSim → ActivitySim →
assignment) runs, with PopulationSim output cached between runs. Not yet fully harmonized —
see [Open items](#known-gaps--open-items).

#### Bonus 3 — AequilibraE as the assignment alternative — **IN VALIDATION**

A Cube-free, Python-native assignment backend (`src/tm1/assignment/aeq/`), selectable with
`backend=aeq`, so the skims → ActivitySim → assignment → skims loop can run without Cube.
Policy constants live in `default-configs/assignment/aeq_params.yaml` (never in `src`), loaded via
`params.py`.

Preliminary parity against the reference run is strong. Validators feed Cube's *own* demand to
isolate the assignment from any demand difference (`scripts/migration_validation/assignment/`):

| Component | Method | Parity vs Cube (preliminary) | Cube time | Aeq time |
|---|---|---|---|---|
| Highway assignment | Frank-Wolfe user equilibrium | VMT +0.1 to +0.2%; PCE link vol r 0.997 (AM) | ~26 min/iter | ~10 min/iter |
| Transit assignment | Spiess–Florian optimal strategy | boardings med 2.2% r 0.97; link vol med 2.9% r 0.99 | ~11 min/iter | ~6 min/iter |
| Transit skims | cost along the strategy | median component within ~1%, r 0.91–0.99 | ~3.7 hr/iter | ~16 min/iter + one-time ~7 min fare pass |

**Not signed off.** These are engine-level comparisons, not a full vetting. Beyond aggregate
PCE, highway **per-class** link volumes are now validated across all five periods (median |Δ|
0.6%, r 0.97; TOT_PCE r 0.99). Remaining for a production sign-off:

- distributional checks (screenlines, volume-vs-count by facility type, congested speeds)
  rather than summary medians;
- documented resolution of every entry in the divergence ledger.

Write-up + divergence ledger: [`docs/aequilibrae_migration.md`](docs/aequilibrae_migration.md);
primer: [`docs/assignment_primer.md`](docs/assignment_primer.md); rerunnable scorecards +
usage guide: [`docs/aequilibrae_usage.md`](docs/aequilibrae_usage.md).

---

## Known gaps / open items

- **PopulationSim harmonization.** Runs end-to-end. `_create_seed_population` (PUMS→seed
  ETL) is irreducible — PopulationSim's `input_pre_processor` only supports rename/drop/
  keep/recode, no groupby/merge/arithmetic, so the cross-table work (worker counts, income
  deflation, GQ classification, PUMA crosswalk) has nowhere else to live.
  - `person_id` post-processing IS required, not droppable — ActivitySim's `index_col:
    person_id` needs a real column at read time, and PopulationSim's
    `write_synthetic_population` never generates a unique per-person id (unlike households,
    which get `synthetic_hh_id`).
  - `pemploy`, `pstudent`, `ptype`, `num_workers`, `income` must stay pre-computed.
  - Two real remaining opportunities: bake `numhh_gq`/`hh_size_1_gq` into the source TAZ
    control CSV instead of computing them in `_prepare_controls`; move the `HHT` NaN-fill
    into `annotate_households.csv` (declarative, where ActivitySim already classifies HHT).

---


## Detailed docs

- [`docs/ACTIVITYSIM_MIGRATION_NOTES.md`](docs/ACTIVITYSIM_MIGRATION_NOTES.md) — UEC/coefficient alignment
- [`docs/SKIM_MAPPING.md`](docs/SKIM_MAPPING.md) — Cube TPP → ActivitySim skim keys
- [`docs/OUTPUT_MAPPING.md`](docs/OUTPUT_MAPPING.md) — output/skim mapping (incl. TNC scoping)
- [`docs/aequilibrae_migration.md`](docs/aequilibrae_migration.md) — AequilibraE parity + divergence ledger
- [`docs/aequilibrae_usage.md`](docs/aequilibrae_usage.md) — how to run/configure the aeq track, Cube→aeq translation guide
- [`docs/assignment_primer.md`](docs/assignment_primer.md) — assignment concepts primer
