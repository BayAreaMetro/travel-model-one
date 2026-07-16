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

`src/tm1/steps/populationsim.py` + `base-models/population/` produce a synthetic population
from PUMS + controls. The end-to-end chain (land use → PopulationSim → ActivitySim →
assignment) runs, with PopulationSim output cached between runs. Not yet fully harmonized —
see [Open items](#known-gaps--open-items).

#### Bonus 3 — AequilibraE as the assignment alternative — **IN VALIDATION**

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

**Not signed off.** These are engine-level comparisons, not a full vetting. Beyond aggregate
PCE, highway **per-class** link volumes are now validated across all five periods (median |Δ|
0.6%, r 0.97; TOT_PCE r 0.99). Remaining for a production sign-off:

- distributional checks (screenlines, volume-vs-count by facility type, congested speeds)
  rather than summary medians;
- documented resolution of every entry in the divergence ledger.

Write-up + divergence ledger: [`docs/aequilibrae_migration.md`](docs/aequilibrae_migration.md);
primer: [`docs/assignment_primer.md`](docs/assignment_primer.md).

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
