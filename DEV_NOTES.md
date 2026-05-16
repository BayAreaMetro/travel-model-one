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
| `CoordinatedDailyActivityPattern.xls` | WorkFromHome | `work_from_home.csv` | `work_from_home_coefficients.csv` | Binary logit; EN7 SD boosts as placeholders |
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
| `work_from_home` | | | ✓ | | | | | |
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

##### Ported Submodels

**Work From Home (WFH) model — migrated.**
CTRAMP has a WFH sub-model embedded inside the CDAP model class
(`WorkFromHome` sheet in `CoordinatedDailyActivityPattern.xls`). It runs a
binary logit (WFH vs DoesNotWFH) per worker using income, industry, home/work
county, distance, and 34 superdistrict-level calibration constants. Workers
chosen as WFH have Mandatory blocked (`-999` on OnePerson row 85); remaining
FT/PT workers get compensating M boosts (rows 86–87: `+0.5638`, `+0.6822`).

ActivitySim port:
- `work_from_home.yaml` / `work_from_home.csv` / `work_from_home_coefficients.csv`
  in `base-models/activity/configs/` implement the same binary logit with all
  12 estimated coefficients plus the calibration constant (−0.340).
- `work_from_home_annotate_persons_preprocessor.csv` computes industry dummies
  (stochastic draw from employment mix at work TAZ, matching CTRAMP's Java),
  county/superdistrict lookups, and the eastbay↔SF dummy.
- `settings.yaml` pipeline: `work_from_home` inserted between `free_parking`
  and `cdap_simulate`.
- `cdap_indiv_and_hhsize1.csv` has 3 new rows: M unavailable for WFH workers
  (`-999`), FT worker M boost (`+0.5638`), PT worker M boost (`+0.6822`).
- EN7 superdistrict boosts (34 constants, all 0.0 in base) are present as
  commented-out placeholders in `work_from_home.csv`, ready for EN7 scenarios.

Note: CTRAMP OnePerson rows 77–82 use tokens (`usualWorkLocationIsHome`,
`noUsualWorkLocation`, `noUsualSchoolLocation`) that always return 0 in the MTC
implementation — effectively dead code. No ActivitySim equivalent needed.

**Validation artifacts:**
- `coefficient_comparison.html` — tabs: Workplace Location, School Location, Auto Ownership, CDAP, Work From Home, Tour Mode Choice, Trip Mode Choice, Size Terms.
- `ablation_report.html` — per-stage calibration: TLFD plots, mode share tables, AO distributions, WFH rates by county (stage 3+).

##### Coefficient Alignment Status

Automated comparison (`scripts/migration_validation/compare_coefficients.py`)
reads CTRAMP UEC `.xls` sheets and ASim spec CSVs side-by-side, using a
crosswalk (`scripts/migration_validation/uec_mappings.py`) to match CTRAMP row
numbers to ASim expression labels. Final status across all submodels:

| Submodel | Diffs | Notes |
|----------|------:|-------|
| Workplace Location | 0 | |
| School Location | 0 | |
| Auto Ownership | 0 | |
| CDAP | 0 | See "CDAP dead-code rows" below |
| Work From Home | 0 | |
| Tour Mode Choice | 0 | |
| Trip Mode Choice | 1 | Accepted structural diff (see below) |
| **Total** | **1** | |

**Trip MC accepted diff — DA_FREE Unavailable on at-work sub-tours:**
CTRAMP's WorkBased sheet has no generic "DA Unavailable" row (the concept is
handled elsewhere in CTRAMP for sub-tours). ASim's `sov_available == False →
-999` is an extra safety net that fires for the `atwork` purpose. This is
harmless and intentional — accepted as a structural difference.

**CDAP dead-code rows (79–84):**
CTRAMP `CoordinatedDailyActivityPattern.xls` rows 79–84 are not ported to
ActivitySim. Disposition:

- **Rows 79–80** (FT/PT worker × `noUsualWorkLocation`, coef −0.5935):
  Dead code in MTC — the token `noUsualWorkLocation` is always 0 in the MTC
  implementation, so these rows never fire. No ASim equivalent needed.
- **Rows 81–82** (school child × `noUsualSchoolLocation`, coef −0.8660):
  Dead code in MTC — the token `noUsualSchoolLocation` is always 0 in the MTC
  implementation, so these rows never fire. No ASim equivalent needed.
- **Rows 83–84** (retired/non-working adult → M unavailable, coef −999):
  Functionally present in ASim — absorbed into the person-type ASC rows in
  `cdap_indiv_and_hhsize1.csv` which apply `coef_UNAVAILABLE` (−999) to the M
  column for ptypes 4 and 5.

The crosswalk in `uec_mappings.py` documents these exclusions with comments
explaining the rationale.

##### Key fixes applied during coefficient alignment

1. **Trip MC Transit ASC coefficient swap:** Several `heavy_rail` and
   `express_bus` per-purpose ASC coefficients were pulled from the wrong CTRAMP
   row (`light_rail`) during the original migration. Fixed in
   `trip_mode_choice_coefficients.csv`.

2. **Trip MC "didn't drive to work" dead code:** CTRAMP WorkBased sheet has
   `didn't_drive_to_work` rows with coeff 0.0 (dead code), but ASim had −999.
   Changed ASim to 0 to match. Fixed in `trip_mode_choice.csv`.

3. **Per-sheet crosswalk dicts:** Many CTRAMP expressions have different row
   numbers across purpose sheets (e.g., Walk Time is row 233 on Work, 235 on
   WorkBased, 236 on others). The crosswalk uses per-sheet dicts like
   `{"Work": 233, "WorkBased": 235, "*": 236}` with `None` meaning the row
   doesn't exist on that sheet.

4. **Tour MC per-sheet dict collision fix:** Adding per-sheet dicts broke
   desc-matching when dict target row numbers collided with other entries on
   different sheets. Fixed by introducing `_raw_by_sheet_no` to preserve raw
   row data before desc-matching.

5. **Trip MC hesitance rows:** 10 hesitance constant rows added to
   `trip_mode_choice.csv` with supporting coefficients in
   `trip_mode_choice.yaml` (IVT multipliers for LRT/ferry, work transit
   hesitance, rail transit hesitance).

6. **Trip MC joint ride-hail zeroing:** `joint_ride_hail_ASC_walk_transit`
   template row zeroed for non-joint purposes in
   `trip_mode_choice_coefficients_template.csv`.


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


## Migration Notes Summary

Detailed migration notes live in `docs/`:
- [`docs/ACTIVITYSIM_MIGRATION_NOTES.md`](docs/ACTIVITYSIM_MIGRATION_NOTES.md) — input/output column mapping, pandas fixes, package structure
- [`docs/OUTPUT_MAPPING.md`](docs/OUTPUT_MAPPING.md) — ActivitySim → CTRAMP output column mapping for legacy R summaries
- [`docs/skim_conversion_mapping.md`](docs/skim_conversion_mapping.md) — Cube TPP → OMX skim key mapping

### Input table remapping

PopulationSim outputs (`personFile.csv`, `hhFile.csv`, `tazData.csv`) need
column renames and case fixes to match ActivitySim expectations. Key changes:
- `HHID` → `household_id`, `PERID` → `person_id`, `TAZ` → `home_zone_id`
- `HINC` → `income`, `PERSONS` → `hhsize`, `VEHICL` → `auto_ownership`
- `PNUM` removed from `keep_columns` — ActivitySim derives it internally
- Full mapping in `docs/ACTIVITYSIM_MIGRATION_NOTES.md`

### Skim conversion decisions

Highway, transit, and non-motorized skims are converted from Cube TPP to a
single `skims.omx` via `scripts/build_omx_skims.py`. Notable decisions:
- **`wacc`/`wegr`** (walk access/egress time) added to transit mapping — the
  prototype configs omitted these but `accessibility.csv` references them.
- **`WLK_TRN_WLK_IVT` → `TOTIVT`**: The prototype used `_IVT` for aggregate
  transit but `_TOTIVT` for all 15 mode-specific keys. Fixed to use `TOTIVT`
  everywhere.
- **Aggregate `trn` skims excluded** from OMX — used only for accessibility,
  not by mode choice UECs. Mode-specific (`loc`, `lrf`, `exp`, `hvy`, `com`)
  are included.
- External zones (1455–1475) included in matrix but unused by ActivitySim.
- Full mapping in `docs/skim_conversion_mapping.md`

### Output shimming (ActivitySim → CTRAMP format)

`tm1.steps.summarize` converts ActivitySim outputs to CTRAMP-format CSVs so
legacy `CoreSummaries.R` can consume them. Full column mapping in
`docs/OUTPUT_MAPPING.md`. Eventually deprecated when R summaries are replaced.

### `write_trip_matrices` duplicate `tour_id` fix

Joint tours share a `tour_id` across participants, creating duplicates in the
tours index. pandas 2.x rejects `.map()` on non-unique indexes (pandas 1.x
silently used the first match). Fixed with `drop_duplicates(subset='tour_id')`
before mapping. Upstream `prototype_mtc` has the same bug.

### Slack notifications

Migrated from `model-files/scripts/notify_slack.py` → `src/tm1/slack.py`.
Webhook URL from `SLACK_WEBHOOK_URL` env var or MTC default file. Notifications
at setup, ActivitySim start, pipeline milestones, and finish/error. Disable
with `--no-slack`.

### Package structure

| Package | Purpose |
|---|---|
| `src/cubeio` | Generic Cube Voyager I/O (TPP reader, OMX converter) |
| `src/tm1` | TM1-specific utilities (config loading, Slack, output shimming) |
| `scripts/run_model.py` | Orchestrator — setup + launch ActivitySim |
| `scripts/build_omx_skims.py` | One-time TPP → OMX conversion |
| `scripts/migration_validation/` | Coefficient comparison, ablation, calibration tools |

---

## Migration Fixes Log

Fixes applied during the CTRAMP → ActivitySim migration that address runtime
crashes or incorrect model behavior. Each fix is in `scenarios/base_2023/configs/`
as a scenario override — the base model configs in `base-models/` are unchanged.

### Fix 1: CDAP M-pattern leak → invalid mandatory tours

**Problem:** `mandatory_tour_scheduling` crashes with "probabilities do not add
up to 1" for ~600 work tours and ~30 school tours.

**Root cause:** ActivitySim's `cdap_fixed_relative_proportions.csv` assigns
activity patterns to persons in households with 5+ members using fixed
proportions based only on `ptype`. It ignores whether the person has a valid
mandatory destination. Additionally, in rare smaller-household edge cases, CDAP
assigns M pattern to persons with no valid workplace or school.

When such a person reaches `mandatory_tour_frequency`, all 5 alternatives
(work1, work2, school1, school2, work_and_school) receive the `-999`
unavailability penalty simultaneously:
- Work alts blocked because `workplace_zone_id = -1`
- School alts blocked because `school_zone_id = -1`

Since `exp(-999)` is identical for all alternatives, the penalties cancel in the
softmax denominator and MTF picks an alternative based on residual utility. The
resulting tour has `destination = -1`, causing NaN skim lookups in scheduling.

**Fix:** `annotate_persons_cdap.csv` — post-CDAP annotation resets
`cdap_activity` from 'M' to 'N' for persons where
`workplace_zone_id < 0 AND school_zone_id < 0`. These persons cannot make any
mandatory tour, so non-mandatory is the correct pattern.

**Impact:** ~600 persons (~0.04% of population) get N instead of M. No effect
on CTRAMP comparison since CTRAMP doesn't have this edge case (its CDAP
implementation handles availability differently).

---

### Fix 2: Tour mode choice density preprocessor NaN crash

**Problem:** `tour_mode_choice_simulate` crashes in stage 4+ when computing
origin/destination density categories. The `pd.cut()` call fails with
"cannot convert float NaN to integer" for tours whose origin or destination
zone is -1 (invalid).

**Root cause:** A small number of tours (from the same M-pattern leak above)
have `destination = -1`. When the preprocessor does
`reindex(land_use.density_measure, tour.destination)`, zone -1 isn't in the
land_use index → NaN → `pd.cut(...).astype(int)` fails.

**Fix:** `tour_mode_choice_annotate_choosers_preprocessor.csv` — the `pd.cut()`
expressions use `.cat.add_categories(0).fillna(0).astype(int)` to defensively
handle NaN density values by assigning density category 0. With Fix 1 in place,
this code path should no longer be triggered, but the defensive handling remains
as a safety net.

---

### Fix 3: Person type label alignment (calibration reporting)

**Problem:** The CDAP calibration report was silently dropping person types 4
(Nonworker), 6 (Driving-age child), and 7 (Pre-driving-age child) — the bar
chart showed only 5 of 8 person types.

**Root cause:** Two label dictionaries were inconsistent:
- `PTYPE_LABELS` in `ctramp_output.py` used "Non-working adult" / "Child of
  driving age" / "Child of non-driving age"
- `CTRAMPPersonType` enum in `enums.py` used different strings

When ActivitySim integer ptypes were converted to strings via `PTYPE_LABELS`,
then looked up in `PERSON_TYPE_LOOKUP` (built from enum labels), the mismatch
caused `null` → rows filtered out.

Additionally, the enum had ptypes 6 and 7 **swapped** (6 was "non-driving",
7 was "driving") — backwards from both CTRAMP and ActivitySim conventions.

**Fix:** Aligned all labels to: "Driving-age child" (6), "Pre-driving-age
child" (7), "Nonworker" (4) across both `PTYPE_LABELS` and `CTRAMPPersonType`.

---

### Fix 4: Calibration report `work_location` column mapping

**Problem:** `evaluate_stages.py` crashed with `ColumnNotFoundError:
work_location` when generating the stage 1 calibration report.

**Root cause:** The ActivitySim column map in `io.py` mapped
`assigned_workplace_zone_id` → `work_location`, but stage 1 output
(pre-WFH) only has `workplace_zone_id`. Post-WFH stages have both.

**Fix:** `io.py` now maps both columns and prefers
`assigned_workplace_zone_id` when present, falling back to
`workplace_zone_id` for pre-WFH stages.
