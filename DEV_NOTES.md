# Dev Notes

Working notes on the Travel Model One → Python migration (branch `activitysim_revival`):
scope, progress to date, and the status of each component.

## Goal

Replace the Cube Voyager + Java CT-RAMP stack with an open-source Python stack
(PopulationSim + ActivitySim + AequilibraE, driven by a `tm1` CLI). Two hard requirements:

1. **Match Cube results.** Faithful replication, not a rebuild. Every divergence requires a
   documented, falsifiable justification.
2. **Match or exceed Cube performance.**

**Reference run** — the last CT-RAMP run, the benchmark for every comparison:

```
\\MODEL3-C\Model3C-Share\Projects\2023_TM161_IPA_35_testrun     (local mirror: E:\ref_2023_TM161)
```

---

## The migration journey

Progress to date, with current status. Steps 1–4 are the core sequence; the two bonus tracks
extend past the original scope.

### 1. Port the skims — cubeless TPP ↔ OMX converter — **DONE**

Pure-Python Cube Voyager matrix I/O, no DLLs and no Cube install (`src/cubeio/`):
`tpp_read.py` decodes every TPP block type, `tpp_write.py` writes them back, `omx.py`
bridges to OMX. Validated bit-exact against Cube CSV dumps (golden pairs in
`tests/data/golden/`). The `tm1.steps.convert_skims` step reads the ~96 reference TPPs and
emits a single 1-based `skims.omx` for ActivitySim.

- Mapping: [`docs/SKIM_MAPPING.md`](docs/SKIM_MAPPING.md).

### 2. Convert the UECs to ActivitySim — **DONE**

Ported the CT-RAMP utility expression calculators (`.xls` UEC workbooks) to ActivitySim
specs, submodel by submodel: auto ownership, work-from-home, CDAP, mandatory/non-mandatory
tour location, tour & trip mode choice, at-work subtours. To make "did the coefficient move,
or just the expression algebra?" answerable, I built a **coefficient viewer / comparator**
(`scripts/migration_validation/activitysim/compare_coefficients.py`, `uec_mappings.py`,
`compare_template.html`) that parses the CT-RAMP `.xls` and the ActivitySim spec side by side.

- Notes: [`docs/ACTIVITYSIM_MIGRATION_NOTES.md`](docs/ACTIVITYSIM_MIGRATION_NOTES.md).

### 3. Validate ActivitySim against CT-RAMP on frozen skims — **DONE** (iterates on #2)

With the reference `skims.omx` frozen (no assignment, no feedback), run both engines on the
same inputs and diff stage by stage. This is where step 2 got its feedback loop: a mismatch
in a stage's output sent me back to fix a coefficient or expression, then re-run.

- CT-RAMP runs **headless** via `src/tm1/steps/simulate_ctramp.py`.
- The **ablation harness** (`scripts/migration_validation/activitysim/ablation_activitysim.py`,
  `ablation_ctramp.py`, `evaluate_stages.py`) freezes upstream stages to CT-RAMP output and
  isolates one submodel at a time, so a diff can't hide behind an upstream diff.
- Submodels aligned one at a time (auto ownership → WFH → CDAP → work/school location →
  tour/trip mode → non-work destination → at-work subtours), each landing at CT-RAMP parity.

**Open item:** this config does not model TNC/ride-hail as a mode (skims zeroed). CT-RAMP
models it, so ActivitySim should too — see [Open items](#known-gaps--open-items).

### 4. Assignment — wire in the Cube launcher via Python — **DONE**

Rather than reimplement Cube assignment first, drive the *existing* Cube `.job` scripts from
Python and close the loop: ActivitySim trip OMX → TPP demand → Cube assignment → skims back.

- `src/tm1/cube.py` — runs Cube Voyager jobs over SSH via the `schtasks` interactive-session
  launcher (the Bentley license pipe is unreachable from SSH/VS Code), with license recovery
  and MatReaderOpen hang detection. Cluster jobs go through `DistributeMultistep`.
- `src/tm1/assignment/cube/{highway,transit,runner}.py` — faithful Cube highway + transit
  assignment and network prep, wired into the feedback loop in `simulate_activitysim`.

### Bonus 1 — Wire in PopulationSim directly — **PARTIAL** (runs end-to-end, cached)

`src/tm1/steps/populationsim.py` + `base-models/population/` produce a synthetic population
from PUMS + controls. The end-to-end chain (land use → PopulationSim → ActivitySim →
assignment) runs, with PopulationSim output cached between runs. Not yet fully harmonized —
see [Open items](#known-gaps--open-items).

### Bonus 2 — AequilibraE as the assignment alternative — **IN VALIDATION**

A Cube-free, Python-native assignment backend (`src/tm1/assignment/aeq/`), selectable with
`backend=aeq`, so the skims → ActivitySim → assignment → skims loop can run without Cube.
Policy constants live in `base-models/assignment/aeq_params.yaml` (never in `src`), loaded via
`params.py`.

Preliminary parity against the reference run is strong. Validators feed Cube's *own* demand to
isolate the assignment from any demand difference (`scripts/migration_validation/assignment/`):

| Component | Method | Parity vs Cube (preliminary) | Cube time | Aeq time |
|---|---|---|---|---|
| Highway assignment | Frank-Wolfe user equilibrium | VMT +0.1 to +0.2%; PCE link vol r 0.997 (AM) | ~26 min/iter | ~10 min/iter |
| Transit assignment | Spiess–Florian optimal strategy | boardings med 2.2% r 0.97; link vol med 2.9% r 0.99 | ~11 min/iter | ~6 min/iter |
| Transit skims | cost along the strategy | median component within ~1%, r 0.91–0.99 | ~3.7 hr/iter | ~16 min/iter + one-time ~7 min fare pass |

**Not signed off.** These are engine-level comparisons, not a full vetting. Replacing Cube in
production requires a validation package that will withstand review, beyond aggregate PCE:

- highway **per-class** link volumes across all five periods (AM per-class proven ±2.3%; the
  full battery is the open item), not just the PCE total;
- distributional checks (screenlines, volume-vs-count by facility type, congested speeds)
  rather than summary medians;
- documented resolution of every entry in the divergence ledger.

Write-up + divergence ledger: [`docs/aequilibrae_migration.md`](docs/aequilibrae_migration.md);
primer: [`docs/assignment_primer.md`](docs/assignment_primer.md).

---

## Known gaps / open items

- **Add TNC to ActivitySim.** The current config omits TNC/ride-hail as a mode (skims zeroed,
  "not in scope" in `docs/OUTPUT_MAPPING.md`). CT-RAMP models it (~204k person-trips/period →
  ~99k highway vehicle-trips as AV classes). CT-RAMP modeled it, so ActivitySim should match:
  add a ride-hail mode to the mode-choice UECs to reproduce the reference demand composition.
  This is a demand-side change, not an assignment defect — the aeq engine reproduces Cube's
  link volumes when fed Cube's demand.
- **PopulationSim harmonization.** Runs end-to-end but not tidy:
  - `person_id` post-processing is unnecessary (ActivitySim handles indexing) — drop it.
  - `occupation` (SOC→1–6) is computed but consumed by nothing in ActivitySim — drop it.
  - `pemploy`, `pstudent`, `ptype`, `num_workers`, `income` must stay pre-computed.
  - Scenario config section is written but commented out in `base_2023_activitysim`.

---

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
|-- base-models/   base configs, specs, lookup tables, default assets (activity/ assignment/ population/)
|-- scenarios/     scenario overrides only (base_2023_activitysim, base_2023_ctramp, ...)
|-- scripts/       run/prep/export entrypoints + migration_validation/{activitysim,assignment}
`-- src/           shared Python: cubeio/, tm1/ (steps, assignment/{cube,aeq})
```

### Diffs from legacy → target

- `core/` → retire from day-to-day layout; use installable `activitysim` where possible.
- `model-files/model/` → `base-models/`.
- `model-files/runtime/` → split between `base-models/` and `scripts/`.
- `model-files/scripts/` → move into `scripts/` or `src/`.
- `utilities/` → cherry-pick only maintained pieces into `scripts/` or `src/`.
- `utilities/RTP/config_RTP2025/` → `scenarios/RTP2025/`.

### Working principle

Separate (1) base model assets, (2) scenario deltas, (3) operational scripts, (4) shared code.
That keeps the repo reasonable to reason about and makes eventual deletions obvious.

### What dies (eventually)

- `RunModel.bat`, `RunIteration.bat`, `RuntimeConfiguration.py`
- JPPF/Java startup, `PrepAssign.job`, `core/` Java code
- All `.job` files (Cube skims, assignment, nonres, preprocessing) — once `backend=aeq` fully
  replaces the Cube launcher
- Anything not in `base-models/`, `scenarios/`, `scripts/`, or `src/`

---

## CLI

Installed via `pyproject.toml` → `tm1` command; `run_model.py` at repo root is a thin alias.

```
tm1 run --scenario scenarios/base_2023_activitysim
tm1 run --scenario scenarios/base_2023_activitysim --max-iterations 1 --sample-rate 0.1
tm1 batch scenarios/scenario_batches.yaml
```

Batch manifest:

```yaml
# scenarios/scenario_batches.yaml
scenarios:
  - scenarios/base_2023_activitysim
  - scenarios/foo_2025
  - scenarios/bar_2050
common_overrides:
  max_iterations: 3
```

---

## Detailed docs

- [`docs/ACTIVITYSIM_MIGRATION_NOTES.md`](docs/ACTIVITYSIM_MIGRATION_NOTES.md) — UEC/coefficient alignment
- [`docs/SKIM_MAPPING.md`](docs/SKIM_MAPPING.md) — Cube TPP → ActivitySim skim keys
- [`docs/OUTPUT_MAPPING.md`](docs/OUTPUT_MAPPING.md) — output/skim mapping (incl. TNC scoping)
- [`docs/aequilibrae_migration.md`](docs/aequilibrae_migration.md) — AequilibraE parity + divergence ledger
- [`docs/assignment_primer.md`](docs/assignment_primer.md) — assignment concepts primer
