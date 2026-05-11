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
only bring in assignment (AequilibraE or something similar) once proven equivalent.

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
- **STATUS: DONE.**

### Step 1: Validate ActivitySim against CTRAMP (frozen skims, no assignment)
- Wire `skims.omx` into ActivitySim configs (`network_los.yaml` already expects it)
- Map CTRAMP `.properties` → ActivitySim settings/configs (~30 params)
- Run ActivitySim single-shot (no feedback loop — frozen skims, no assignment)
- Compare ActivitySim outputs to CTRAMP reference using existing summarizers
- This is the hard, iterative part — the UECs have diverged
- Iterate on UECs until ActivitySim results are comparable to CTRAMP
- **STATUS: STARTED.** Ongoing validation and UEC iteration in `scripts/migration_validation/ablation_ctramp.py`
 
#### Step b: Convert/Align UECs
- Convert CTRAMP UECs from XLSX format to ActivitySim YAML format -- Most of it is already there, but needs to be thoroughly checked through. Complicated by the fact that some expressions differ in how coefficients/constants are applied either embedded in the expression or the choice column. 

##### Matrix 1: CTRAMP UEC → ActivitySim Spec Crosswalk

| CTRAMP UEC | Sheet(s) | ActivitySim Spec | Coefficients | Notes |
|------------|----------|-----------------|--------------|-------|
| `DestinationChoice.xls` | Work | `workplace_location.csv` | `workplace_location_coefficients.csv` | |
| `DestinationChoice.xls` | University, HighSchool, GradeSchool | `school_location.csv` | `school_location_coefficients.csv` | 3 sheets → 1 spec |
| `DestinationChoice.xls` | (non-work) | `non_mandatory_tour_destination.csv` | — | Shared size terms |
| `AutoOwnership.xls` | Auto ownership | `auto_ownership.csv` | `auto_ownership_coefficients.csv` | |
| `FreeParkingEligibility.xls` | — | `free_parking.csv` | `free_parking_coefficients.csv` | |
| `CoordinatedDailyActivityPattern.xls` | OnePerson | `cdap_indiv_and_hhsize1.csv` | `cdap_coefficients.csv` | + interaction CSVs |
| `IndividualMandatoryTourFrequency.xls` | — | `mandatory_tour_frequency.csv` | `mandatory_tour_frequency_coefficients.csv` | |
| `TourDepartureAndDuration.xls` | (per purpose) | `tour_scheduling_*.csv` | `tour_scheduling_coefficients.csv` | |
| `ModeChoice.xls` | Work, Univ, School, … | `tour_mode_choice.csv` | template + `tour_mode_choice_coefficients.csv` | 10 sheets → 1 spec |
| `JointTours.xls` | Frequency, Composition, Participation | `joint_tour_frequency.csv`, etc. | — | Multiple sub-models |
| `IndividualNonMandatoryTourFrequency.xls` | — | `non_mandatory_tour_frequency.csv` | — | |
| `AtWorkSubtourFrequency.xls` | — | `atwork_subtour_frequency.csv` | `atwork_subtour_frequency_coefficients.csv` | |
| `StopFrequency.xls` | — | `stop_frequency_*.csv` | — | Per purpose |
| `StopDestinationChoice.xls` | — | `trip_destination.csv` | — | |
| `TripModeChoice.xls` | Work, Univ, School, … | `trip_mode_choice.csv` | template + `trip_mode_choice_coefficients.csv` | 10 sheets → 1 spec |

##### Matrix 2: ActivitySim Spec → Ablation Stage

Stages are cumulative — each includes all models from prior stages.

| ActivitySim Spec | S1 UWSL | S2 Pre-Tour | S3 CDAP | S4 Mandatory | S5 Joint | S6 Non-Mand | S7 At-Work | S8 Stops |
|-----------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `workplace_location` | ✓ | | | | | | | |
| `school_location` | ✓ | | | | | | | |
| `auto_ownership` | | ✓ | | | | | | |
| `free_parking` | | ✓ | | | | | | |
| `cdap_simulate` | | | ✓ | | | | | |
| `mandatory_tour_frequency` | | | | ✓ | | | | |
| `mandatory_tour_scheduling` | | | | ✓ | | | | |
| `tour_mode_choice` | | | | ✓ | ✓ | ✓ | ✓ | |
| `joint_tour_frequency` | | | | | ✓ | | | |
| `joint_tour_composition` | | | | | ✓ | | | |
| `joint_tour_participation` | | | | | ✓ | | | |
| `joint_tour_destination` | | | | | ✓ | | | |
| `joint_tour_scheduling` | | | | | ✓ | | | |
| `non_mandatory_tour_frequency` | | | | | | ✓ | | |
| `non_mandatory_tour_destination` | | | | | | ✓ | | |
| `non_mandatory_tour_scheduling` | | | | | | ✓ | | |
| `atwork_subtour_frequency` | | | | | | | ✓ | |
| `atwork_subtour_destination` | | | | | | | ✓ | |
| `atwork_subtour_scheduling` | | | | | | | ✓ | |
| `atwork_subtour_mode_choice` | | | | | | | ✓ | |
| `stop_frequency` | | | | | | | | ✓ |
| `trip_purpose` | | | | | | | | ✓ |
| `trip_destination` | | | | | | | | ✓ |
| `trip_scheduling` | | | | | | | | ✓ |
| `trip_mode_choice` | | | | | | | | ✓ |

**Key cascading effects:**
- `tour_mode_choice` spans stages 4–7 (one spec, purpose-segmented via template coefficients).
- Shadow pricing (stage 1) shifts zone attractiveness → all downstream tour destinations and modes.
- CDAP (stage 3) determines who travels at all — M/N/H share drift propagates to stages 4–8.

##### Known Gaps

**Work From Home (WFH) model — deferred.**
CTRAMP has a WFH sub-model embedded inside the CDAP model class
(`WorkFromHome` sheet in `CoordinatedDailyActivityPattern.xls`). It runs a
binary logit (WFH vs DoesNotWFH) per worker using income, industry, home/work
county, distance, and 34 superdistrict-level calibration constants. Workers
chosen as WFH have Mandatory blocked (`-999` on OnePerson row 85); remaining
FT/PT workers get compensating M boosts (rows 86–87: `+0.5638`, `+0.6822`).

ActivitySim has an equivalent `work_from_home` model in the package (also binary
logit, with built-in iterative calibration to a target WFH percent), but it is
**not yet added to the pipeline**. To close this gap:
1. Add `work_from_home` to `settings.yaml` between `workplace_location` and
   `cdap_simulate`.
2. Create `work_from_home.yaml` / `work_from_home.csv` / coefficients with
   equivalent terms from the CTRAMP UEC.
3. Add CDAP spec rows for the WFH→CDAP interaction (block M for WFH workers,
   boost M for remaining workers).

Note: CTRAMP OnePerson rows 77–82 use tokens (`usualWorkLocationIsHome`,
`noUsualWorkLocation`, `noUsualSchoolLocation`) that always return 0 in the MTC
implementation — effectively dead code. No ActivitySim equivalent needed.

**Validation artifacts:**
- `coefficient_comparison.html` — tabs: Workplace Location, School Location, Auto Ownership, CDAP, Tour Mode Choice, Trip Mode Choice, Size Terms.
- `ablation_report.html` — per-stage TLFD plots, mode share tables, AO distributions.




### Step 2: Pythonify summarizers (OMX-native)
- Rewrite core summaries / validation scripts in Python reading OMX directly
- Drop Cube dependency from post-processing entirely
- Integrate with `travel-diary-survey-tools` for calibration analyses
- **STATUS: PAUSED.** Started migrating some scripts, but was too slow and clunky for development, so I created a separate lightweight summarizer specifically for UEC alignment in Step 1.

### Step 3: Compare alternative Traffic Assignment tool (AequilibraE?)
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