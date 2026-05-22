# ActivitySim Migration Notes

Decisions, fixes, and gotchas encountered migrating TM1 from CTRAMP to
ActivitySim 1.5.1. All scenario-specific fixes live in
`scenarios/base_2023/configs/` as overrides — base model configs in
`base-models/` are unchanged.

## Reference Model Run

The last CTRAMP model run, used as the benchmark for validation:

```
\\MODEL3-C\Model3C-Share\Projects\2023_TM161_IPA_35_testrun
```

---

## Package Structure

| Package | Purpose |
|---|---|
| `src/cubeio` | Pure-Python Cube Voyager I/O (TPP reader, OMX converter) |
| `src/tm1` | TM1-specific utilities (config, Slack, output shimming, CLI) |
| `src/tm1/steps/` | Pipeline steps: setup, convert_skims, simulate, summarize |
| `scripts/run_model.py` | Convenience entry point — runs full pipeline |
| `scripts/migration_validation/` | Coefficient comparison, ablation, calibration tools |

---

## Input Table Column Mapping

### persons.csv (from PopulationSim `personFile.csv`)

| CSV Column | ActivitySim Column | Notes |
|---|---|---|
| `HHID` | `household_id` | Rename added — was missing in prototype configs |
| `PERID` | `person_id` | Index column |
| `AGE` | `age` | Case fix (CSV is uppercase) |
| `SEX` | `sex` | Case fix (CSV is uppercase) |
| `pemploy` | `pemploy` | No change |
| `pstudent` | `pstudent` | No change |
| `ptype` | `ptype` | No change |

`PNUM` removed from `keep_columns` — ActivitySim derives it internally.

### households.csv (from PopulationSim `hhFile.csv`)

| CSV Column | ActivitySim Column | Notes |
|---|---|---|
| `HHID` | `household_id` | Index column |
| `TAZ` | `home_zone_id` | |
| `HINC` | `income` | |
| `PERSONS` | `hhsize` | |
| `hworkers` | `num_workers` | |
| `VEHICL` | `auto_ownership` | |
| `HHT` | `HHT` | No rename needed |

### land_use.csv (from `tazData.csv`)

| CSV Column | ActivitySim Column | Notes |
|---|---|---|
| `ZONE` | `zone_id` | |
| `COUNTY` | `county_id` | |
| `AREATYPE` | `area_type` | |

---

## Skim Conversion (TPP → OMX)

Skims are converted from Cube TPP to a single `skims.omx` by
`src/tm1/steps/convert_skims.py`. Full mapping in
[SKIM_MAPPING.md](SKIM_MAPPING.md).

Key decisions:
- `wacc`/`wegr` (walk access/egress time) added — prototype configs omitted
  these but `accessibility.csv` references `WLK_TRN_WLK_WACC` / `_WEGR`.
- Aggregate `WLK_TRN_WLK_*` skims come from Cube's "best-path" combined
  transit files. `trn` added to mode list alongside `loc`, `lrf`, `exp`,
  `hvy`, `com`. Same for `DRV_TRN_WLK` and `WLK_TRN_DRV`.
- `WLK_TRN_WLK_IVT` → `WLK_TRN_WLK_TOTIVT`: prototype used `_IVT` for
  aggregate but `_TOTIVT` for mode-specific. Fixed to `TOTIVT` everywhere.
- External zones (1455–1475) included in matrix but unused by ActivitySim
  demand models (assignment-only in TM1 zone system).
- Transit skims use highest available `*.avg.iter{N}.tpp` from reference run.

---

## Output Column Mapping (ActivitySim → CTRAMP)

`tm1.steps.summaries.ctramp_output` shims ActivitySim outputs into
CTRAMP-format CSVs so legacy `CoreSummaries.R` can consume them. Full mapping
in [OUTPUT_MAPPING.md](OUTPUT_MAPPING.md). To be deprecated when R summaries
are replaced.

---

## UEC Crosswalk

| CTRAMP UEC | Sheet(s) | ActivitySim Spec | Notes |
|------------|----------|-----------------|-------|
| `DestinationChoice.xls` | Work | `workplace_location.csv` | |
| `DestinationChoice.xls` | University, HighSchool, GradeSchool | `school_location.csv` | 3 sheets → 1 spec |
| `DestinationChoice.xls` | (non-work) | `non_mandatory_tour_destination.csv` | |
| `AutoOwnership.xls` | — | `auto_ownership.csv` | 11-alt AV-aware model |
| `FreeParkingEligibility.xls` | — | `free_parking.csv` | |
| `CoordinatedDailyActivityPattern.xls` | WorkFromHome | `work_from_home.csv` | New standalone step |
| `CoordinatedDailyActivityPattern.xls` | OnePerson | `cdap_indiv_and_hhsize1.csv` | |
| `IndividualMandatoryTourFrequency.xls` | — | `mandatory_tour_frequency.csv` | |
| `TourDepartureAndDuration.xls` | (per purpose) | `tour_scheduling_*.csv` | |
| `ModeChoice.xls` | Work, Univ, School, … | `tour_mode_choice.csv` | 10 sheets → 1 spec via template |
| `JointTours.xls` | Freq, Comp, Part | `joint_tour_frequency.csv`, etc. | |
| `IndividualNonMandatoryTourFrequency.xls` | — | `non_mandatory_tour_frequency.csv` | |
| `AtWorkSubtourFrequency.xls` | — | `atwork_subtour_frequency.csv` | |
| `StopFrequency.xls` | — | `stop_frequency_*.csv` | Per purpose |
| `StopDestinationChoice.xls` | — | `trip_destination.csv` | |
| `TripModeChoice.xls` | Work, Univ, School, … | `trip_mode_choice.csv` | 10 sheets → 1 spec via template |

### Coefficient Alignment Status

Automated comparison (`scripts/migration_validation/compare_coefficients.py`)
reads CTRAMP UEC sheets and ASim spec CSVs side-by-side using the crosswalk in
`scripts/migration_validation/uec_mappings.py`.

| Submodel | Diffs | Notes |
|----------|------:|-------|
| Workplace Location | 0 | |
| School Location | 0 | |
| Auto Ownership | 0 | |
| CDAP | 0 | Dead-code rows excluded (see below) |
| Work From Home | 0 | |
| Tour Mode Choice | 0 | |
| Trip Mode Choice | 1 | Accepted structural diff (see below) |
| **Total** | **1** | |

**Trip MC accepted diff:** ASim has `sov_available == False → -999` for `atwork`
purpose as a safety net. CTRAMP handles DA unavailability for sub-tours
elsewhere. Harmless and intentional.

**CDAP dead-code rows (79–84):** Not ported.
- Rows 79–82: tokens `noUsualWorkLocation`/`noUsualSchoolLocation` always
  return 0 in MTC implementation — never fire.
- Rows 83–84: M unavailable for retired/non-working — functionally present in
  ASim via `coef_UNAVAILABLE` (−999) on M column for ptypes 4 and 5.

---

## Ported Submodels

### Work From Home

CTRAMP has a WFH sub-model embedded in CDAP (`WorkFromHome` sheet). It runs a
binary logit per worker using income, industry, home/work county, distance, and
34 superdistrict calibration constants. Workers chosen WFH get Mandatory
blocked (−999); remaining FT/PT workers get compensating M boosts (+0.5638,
+0.6822).

ActivitySim port:
- `work_from_home.yaml` / `.csv` / `_coefficients.csv` implement the same
  binary logit with all 12 estimated coefficients plus calibration constant.
- `work_from_home_annotate_persons_preprocessor.csv` computes industry dummies
  (stochastic draw from employment mix at work TAZ), county/superdistrict
  lookups, and eastbay↔SF dummy.
- Pipeline: `work_from_home` inserted between `free_parking` and
  `cdap_simulate`.
- `cdap_indiv_and_hhsize1.csv` has 3 new rows: M unavailable for WFH workers,
  FT M boost, PT M boost.
- EN7 superdistrict boosts (34 constants, all 0.0) present as placeholders.

### Auto Ownership (11-alt AV-aware)

TM1's AO model uses 11 alternatives distinguishing human/AV ownership
patterns. `auto_ownership_annotate_households.csv` remaps the 11-alt choice
back to 0–4 vehicle count for downstream models.

---

## Runtime Fixes

### Fix 1: CDAP M-pattern leak → invalid mandatory tours

**Problem:** `mandatory_tour_scheduling` crashes with "probabilities do not add
up to 1" for ~600 work tours.

**Cause:** `cdap_fixed_relative_proportions.csv` assigns M pattern to persons
in 5+ member households using only `ptype`, ignoring whether they have a valid
mandatory destination. When all MTF alternatives get −999 simultaneously, the
penalties cancel in softmax and MTF picks an alternative with `destination = -1`.

**Fix:** `annotate_persons_cdap.csv` — resets `cdap_activity` from 'M' to 'N'
for persons where `workplace_zone_id < 0 AND school_zone_id < 0`.

**Impact:** ~600 persons (~0.04%). No effect on CTRAMP comparison.

---

### Fix 2: Tour mode choice density preprocessor NaN crash

**Problem:** `tour_mode_choice_simulate` crashes in `pd.cut()` with "cannot
convert float NaN to integer" for tours with destination = -1.

**Cause:** Same M-pattern leak → zone -1 not in land_use index → NaN density.

**Fix:** `tour_mode_choice_annotate_choosers_preprocessor.csv` uses
`.cat.add_categories(0).fillna(0).astype(int)` as defensive handling.

---

### Fix 3: Person type label alignment

**Problem:** CDAP calibration report dropped person types 4, 6, 7.

**Cause:** `PTYPE_LABELS` in `ctramp_output.py` used different strings than
`CTRAMPPersonType` enum. Additionally, ptypes 6 and 7 were swapped in the enum.

**Fix:** Aligned all labels: "Driving-age child" (6), "Pre-driving-age child"
(7), "Nonworker" (4).

---

### Fix 4: `work_location` column mapping

**Problem:** `evaluate_stages.py` crashed with `ColumnNotFoundError:
work_location` in stage 1.

**Cause:** Column map expected `assigned_workplace_zone_id` (post-WFH) but
stage 1 only has `workplace_zone_id`.

**Fix:** `io.py` maps both columns, prefers `assigned_workplace_zone_id` when
present.

---

### Fix 5: Trip MC at-work c_ivt divisor error

**Problem:** 10 at-work sub-tour time/cost multipliers in
`trip_mode_choice_coefficients.csv` were wrong.

**Cause:** Upstream prototype_mtc divided CTRAMP absolute values by Tour MC
`c_ivt` (-0.0134) instead of Trip MC `c_ivt` (-0.0279), producing values like
1.35 instead of the correct 2.00.

**Fix:** Corrected coefficients (e.g., `coef_walktimeshort_atwork`: 1.35 → 2.00,
`coef_biketimeshort_atwork`: 2.70 → 4.00, etc.).

---

### Fix 6: Trip MC transit ASC coefficient swap

**Problem:** Several `heavy_rail` and `express_bus` per-purpose ASC coefficients
were pulled from the wrong CTRAMP row (`light_rail`) during original migration.

**Fix:** Corrected in `trip_mode_choice_coefficients.csv`.

---

### Fix 7: Trip MC "didn't drive to work" dead code

**Problem:** CTRAMP WorkBased sheet has `didn't_drive_to_work` rows with coeff
0.0 (dead code), but ASim had −999.

**Fix:** Changed ASim to 0.0 to match CTRAMP.

---

### Fix 8: Trip MC hesitance rows

10 hesitance constant rows added to `trip_mode_choice.csv` with supporting
coefficients (IVT multipliers for LRT/ferry, work transit hesitance, rail
transit hesitance).

---

### Fix 9: Transit hesitance constants

`tour_mode_choice.yaml` adds explicit constants ported from CTRAMP Java
properties:
- `work_transit_hesitance: 55.0`
- `nonwork_transit_hesitance: 0.0`
- `rail_transit_hesitance: 108.0`

Not present in prototype_mtc.

---

### Fix 10: Trip MC CONSTANTS corrections

`trip_mode_choice.yaml` CONSTANTS differ from tour MC (matching CTRAMP's
different treatment of trip-level sensitivity):
- `xfers_wlk_multiplier: 15` (tour MC: 30)
- `xfers_drv_multiplier: 20` (tour MC: 40)
- `origin_density_index_multiplier: -0.6` (tour MC: -0.1)
- `ivt_exp_multiplier: 1.0`, `ivt_com_multiplier: 0.7`

---

### Fix 11: `write_trip_matrices` duplicate `tour_id` index

**Problem:** `write_trip_matrices` crashes with `InvalidIndexError: Reindexing
only valid with uniquely valued Index objects`.

**Cause:** Joint tours share `tour_id` across participants → duplicate index.
pandas 2.x rejects `.map()` on non-unique indexes (pandas 1.x used first match
silently).

**Fix:** Deduplicate before mapping:
```python
trips.tour_id.map(
    tours.reset_index()
    .drop_duplicates(subset='tour_id')
    .set_index('tour_id')
    .number_of_participants
)
```

Upstream prototype_mtc has the same bug (as of April 2026).

---

## Slack Notifications

Migrated from `model-files/scripts/notify_slack.py` → `src/tm1/slack.py`.
- Webhook from `SLACK_WEBHOOK_URL` env var or MTC default file.
- Notifications at setup, ActivitySim start, pipeline milestones, finish/error.
- Disable with `--no-slack`.
