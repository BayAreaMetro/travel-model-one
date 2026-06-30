# ActivitySim → CTRAMP Output Mapping

Column mapping from ActivitySim 1.5.1 output CSVs to the CTRAMP-format CSVs
that `CoreSummaries.R` expects. Used by `tm1.steps.summarize` to shim
ActivitySim outputs for legacy R summaries.

**Source files** (ActivitySim `output/`):
- `final_households.csv`
- `final_persons.csv`
- `final_tours.csv`
- `final_trips.csv`
- `final_joint_tour_participants.csv`
- `final_land_use.csv`

**Target files** (CTRAMP `main/`):
- `householdData_{iter}.csv`
- `personData_{iter}.csv`
- `indivTourData_{iter}.csv`
- `jointTourData_{iter}.csv`
- `indivTripData_{iter}.csv`
- `jointTripData_{iter}.csv`
- `wsLocResults_{iter}.csv`

---

## householdData_{iter}.csv

Source: `final_households.csv`

| CTRAMP Column | ActivitySim Column | Notes |
|---|---|---|
| `hh_id` | `household_id` | rename |
| `taz` | `home_zone_id` | rename |
| `walk_subzone` | — | **TODO**: needs walkAccessBuffers; hardcoded 0. Affects JourneyToWork group-by. |
| `income` | `income` | direct |
| `autos` | `auto_ownership` | rename |
| `size` | `hhsize` | rename. Note: popsyn has `PERSONS`; CTRAMP householdData uses `size`. |
| `workers` | `num_workers` | rename. Note: popsyn has `hworkers`; CTRAMP householdData uses `workers`. R reads `hworkers` from popsyn. |
| `sampleRate` | `sample_rate` | rename |

CTRAMP also outputs `cdap_pattern`, `jtf_choice`, `jtf_pattern`, `auto_suff`,
`humanVehicles`, `autonomousVehicles`, `pct_of_poverty`, and 21 random-seed
columns — none are used by R after the join, so we omit them.

---

## personData_{iter}.csv

Source: `final_persons.csv`

| CTRAMP Column | ActivitySim Column | Notes |
|---|---|---|
| `hh_id` | `household_id` | rename |
| `person_id` | `person_id` | direct |
| `person_num` | derive | row number within household (rank by person_id) |
| `age` | `age` | direct |
| `gender` | `sex` | map: 1→"m", 2→"f" |
| `type` | `ptype` | map int→text label (e.g. 1→"Full-time worker"). R uses this text version. |
| `value_of_time` | `value_of_time` | direct |
| `fp_choice` | `free_parking_at_work` | rename |
| `activity_pattern` | `cdap_activity` | rename; values M/N/H |
| `imf_choice` | `mandatory_tour_frequency` | rename |
| `inmf_choice` | `non_mandatory_tour_frequency` | rename |
| `sampleRate` | `sample_rate` | rename |
| `wfh_choice` | — | submodel not active yet; hardcode 0 |

CTRAMP also outputs `workDCLogsum`, `schoolDCLogsum`, `industry` — not used
by CoreSummaries.R, so omitted.

---

## indivTourData_{iter}.csv

Source: `final_tours.csv` filtered to `tour_category != "joint"`, joined with persons.

| CTRAMP Column | ActivitySim Column | Notes |
|---|---|---|
| `hh_id` | `household_id` | rename |
| `person_id` | `person_id` | direct |
| `tour_id` | `tour_id` | direct |
| `tour_purpose` | `primary_purpose` | rename |
| `tour_category` | `tour_category` | direct; values: `mandatory`, `non_mandatory`, `atwork` |
| `orig_taz` | `origin` | rename |
| `dest_taz` | `destination` | rename |
| `start_hour` | `start` | rename |
| `end_hour` | `end` | rename |
| `tour_mode` | `tour_mode` | direct — **verify numeric codes match CTRAMP encoding** |
| `person_num` | derive | from persons table (rank within HH) |
| `person_type` | `ptype` | rename. R drops this but it must exist in the CSV. |
| `atWork_freq` | `stop_frequency` | rename. R drops this but it must exist in the CSV. |
| `sampleRate` | `sample_rate` | rename |

---

## jointTourData_{iter}.csv

Source: `final_tours.csv` filtered to `tour_category == "joint"`, joined with
`final_joint_tour_participants.csv` to build `tour_participants`.

| CTRAMP Column | ActivitySim Column | Notes |
|---|---|---|
| `hh_id` | `household_id` | rename |
| `tour_id` | `tour_id` | direct |
| `tour_category` | `tour_category` | direct |
| `tour_purpose` | `primary_purpose` | rename |
| `tour_composition` | `composition` | rename |
| `tour_participants` | derive | space-separated `person_num`s from `final_joint_tour_participants.csv`. R unwinds this to get per-person rows. |
| `orig_taz` | `origin` | rename |
| `dest_taz` | `destination` | rename |
| `start_hour` | `start` | rename |
| `end_hour` | `end` | rename |
| `tour_mode` | `tour_mode` | direct |
| `sampleRate` | `sample_rate` | rename |

---

## indivTripData_{iter}.csv

Source: `final_trips.csv` joined to `final_tours.csv` (for `tour_category`, `tour_mode`),
filtered to individual tours. Column order matches CTRAMP Java `formIndivTripColumnNames()`.

| CTRAMP Column | ActivitySim Column | Notes |
|---|---|---|
| `hh_id` | `household_id` | rename |
| `person_id` | `person_id` | direct |
| `person_num` | derive | from personData (rank within HH) |
| `tour_id` | `tour_id` | direct |
| `stop_id` | `trip_num` | `trip_num - 1` |
| `inbound` | `outbound` | `1 - outbound` |
| `tour_purpose` | `primary_purpose` | rename (from tour join) |
| `orig_purpose` | derive | previous trip's `purpose`; first outbound = `"Home"`, first return = tour purpose |
| `dest_purpose` | `purpose` | rename |
| `orig_taz` | `origin` | rename |
| `orig_walk_segment` | — | hardcode 0; not modeled in ActivitySim |
| `dest_taz` | `destination` | rename |
| `dest_walk_segment` | — | hardcode 0; not modeled in ActivitySim |
| `depart_hour` | `depart` | rename |
| `trip_mode` | `trip_mode` | direct |
| `tour_mode` | join from tours | `tour_mode` |
| `tour_category` | join from tours | |
| `avAvailable` | — | hardcode 0; AV not in scope |
| `sampleRate` | `sample_rate` | join from households |
| `taxiWait` | — | hardcode 0.0; TNC not in scope |
| `singleTNCWait` | — | hardcode 0.0; TNC not in scope |
| `sharedTNCWait` | — | hardcode 0.0; TNC not in scope |

---

## jointTripData_{iter}.csv

Source: `final_trips.csv` joined to `final_tours.csv`, filtered to joint tours.
Column order matches CTRAMP Java `formJointTripColumnNames()`.

| CTRAMP Column | ActivitySim Column | Notes |
|---|---|---|
| `hh_id` | `household_id` | rename |
| `tour_id` | `tour_id` | direct |
| `stop_id` | `trip_num` | `trip_num - 1` |
| `inbound` | `outbound` | `1 - outbound` |
| `tour_purpose` | `primary_purpose` | rename (from tour join) |
| `orig_purpose` | derive | same logic as indivTripData |
| `dest_purpose` | `purpose` | rename |
| `orig_taz` | `origin` | rename |
| `orig_walk_segment` | — | hardcode 0; not modeled in ActivitySim |
| `dest_taz` | `destination` | rename |
| `dest_walk_segment` | — | hardcode 0; not modeled in ActivitySim |
| `depart_hour` | `depart` | rename |
| `trip_mode` | `trip_mode` | direct |
| `num_participants` | join from tours | `number_of_participants` |
| `tour_mode` | join from tours | `tour_mode` |
| `tour_category` | join from tours | |
| `avAvailable` | — | hardcode 0; AV not in scope |
| `sampleRate` | `sample_rate` | join from households |
| `taxiWait` | — | hardcode 0.0; TNC not in scope |
| `singleTNCWait` | — | hardcode 0.0; TNC not in scope |
| `sharedTNCWait` | — | hardcode 0.0; TNC not in scope |

No `person_id`/`person_num` in joint trips (matches CTRAMP).

---

## wsLocResults_{iter}.csv

Source: `final_persons.csv` joined to `final_households.csv` and `final_land_use.csv`.
Filtered to persons with `workplace_zone_id > 0`.

| CTRAMP Column | ActivitySim Column | Notes |
|---|---|---|
| `HHID` | `household_id` | rename |
| `PersonID` | `person_id` | rename |
| `PersonNum` | derive | row number within household |
| `HomeTAZ` | `home_zone_id` | rename |
| `HomeSubZone` | — | **TODO**: needs walkAccessBuffers; hardcoded 0. Used in JourneyToWork group-by. |
| `Income` | `income` | join from households |
| `WorkLocation` | `workplace_zone_id` | rename |
| `WorkSubZone` | — | **TODO**: needs walkAccessBuffers or reference run lookup; hardcoded 0. Used in JourneyToWork group-by. |
| `homeSD` | join from `land_use` | `SD` by `home_zone_id` |
| `workSD` | join from `land_use` | `SD` by `workplace_zone_id` |
