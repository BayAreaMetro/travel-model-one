# Phase 3 refactor assessment

**Status:** candidate list for review. Nothing here is decided. Yuqi leads what stays
and what goes; this document lays out what *could* change now that cubeio (phase 2,
PR #104) can read and write Cube files from Python.

**Scope of phase 3:** replace legacy glue around the model with native Python while the
model itself stays CT-RAMP + Cube. Demand and assignment do not change in this phase,
so every result should be reproducible against a run made before it.

The earlier phase 3 attempt (PR #115, branch `phase-3-streamlining`) is closed. Its
commits remain available for reuse — see [Earlier work](#earlier-work-available-for-reuse).

---

## What cubeio can and cannot do

| Function | Does |
|---|---|
| `read_tpp` / `write_tpp` | Cube matrix (`.tpp`) ↔ numpy arrays, cell-exact |
| `tpp_to_omx` / `omx_to_tpp` | Cube matrix ↔ OMX (readable from Python, R and others) |
| `read_net`, `read_net_links`, `read_net_nodes`, `iter_net_links` | read a Cube highway network (`.net`) |

**There is no `.net` writer**, and none is planned. Anything that produces a network
stays in Cube.

That gives one rule for sorting every Cube job in the pipeline:

- **writes a `.net`** → stays in Cube
- **only reads and writes matrices** (Cube `MATRIX` program) → could become Python
- **only reads a `.net`** → could become Python via `read_net`

The tables below apply that rule to every Cube job in
`default-configs/ctramp-cube-model.yaml`, found by reading each job's file declarations.

---

## 1. Exports of Cube files to CSV

These steps exist only to get data out of Cube's binary formats so that R and Python
scripts could read it. cubeio can read the source files directly — **but both outputs
are read by many downstream scripts**, so they behave like published data products, not
internal handoffs.

### `skims_database` — `SkimsDatabase.JOB`

Writes `database/{Time,Distance,Cost,ActiveTime}SkimsDatabase{PERIOD}.csv` from the
skim matrices. About 4.4 GB per run.

Read by:

| In the pipeline | Elsewhere in the repo |
|---|---|
| `core_summaries` (`CoreSummaries.R`) | `RTP/ITHIM/PerCapitaDailyTravelDistanceTime.R` |
| `count_trips` (`countTrips.py`) | `NextGenFwys/metrics/E1_reweighting_temp.py` |
| `scenario_metrics` (`scenarioMetrics.py`) | `NextGenFwys/metrics/travel-cost-by-income-driving-households.r` |
| `npa_metrics_goal_1a_to_1f`, `npa_metrics_goal_3` | `bespoke-requests/fare-study/join_trips_with_skims.R` |

### `net2csv_avgload5period` — `utilities/RTP/metrics/net2csv_avgload5period.job`

Writes `hwy/iter{N}/avgload5period_vehclasses.csv`, the final loaded network with
per-vehicle-class volumes.

Read by about 30 scripts. In the pipeline: `emfac_prep_between_zones`
(`BetweenZonesVMT.py`), `topsheet.R`, `RunResults.py`, `scenarioMetrics.py`,
`NPA_metrics_Goal_3.py`, and both projects' `hooks.py`. Elsewhere: NextGenFwys (~12
scripts), Emissions (3), ITHIM (2), TIP_STIP PHED metrics (R), HPMS and roadway
validation, `hwynet.py`, `bus_opcost.py`, `copyFilesAcrossScenarios.py`.

(A different file, `avgload5period.csv`, is written by `MergeNetworks.job` inside the
loop. That job writes networks, so it stays in Cube.)

### Options for each export

- **Keep the CSV, produce it without Cube.** A Python step using `read_tpp` /
  `read_net` writes the same file. No reader changes; removes a Cube job.
- **Replace the CSV.** Readers switch to OMX (R has an `omx` package) or to
  cubeio. Removes the disk cost; every reader above has to change.
- **Leave as is.**

---

## 2. Cube jobs that only read networks

| Step | Job | Writes | Note |
|---|---|---|---|
| `test_network_convergence` | `feedback/TestNetworkConvergence.job` | `logs/feedback.rpt` (a report) | Computes gap / RMSE between iterations' loaded networks. The harness runs a fixed iteration count (`iterate.count`), so the report informs rather than stops the loop. |
| `net2csv_avgload5period` | (see section 1) | | |

Related: **`npa_metrics_goal_3` fails on every run.** It needs `network_trn_links.shp`,
produced by `cube_to_shapefile.py`, which needs NetworkWrangler (not installed by the
harness). The step is marked `continue_on_error`, so the run carries on. `read_net` could
supply the highway links; transit lines (`.lin`) are not covered by cubeio.

---

## 3. Cube jobs that only read and write matrices

These could become numpy code via `read_tpp` / `write_tpp`. Unlike sections 1–2, most
contain **model logic**, not just file handling, so each would be a rewrite whose
outputs need comparing against a reference run.

| Where | Step | Job | Note |
|---|---|---|---|
| before the loop | `hsr_trip_generation` | `preprocess/HsrTripGeneration.job` | ported in the earlier attempt |
| in the loop | `ix_forecasts` | `nonres/IxForecasts_horizon.job` | internal–external (gateway) trips |
| | `ix_time_of_day` | `nonres/IxTimeOfDay.job` | |
| | `ix_toll_choice` | `nonres/IxTollChoice.job` | choice model, reads skims |
| | `truck_trip_generation` | `nonres/TruckTripGeneration.job` | uses Cube's `TRIPGEN` module; reads/writes DBF, not matrices |
| | `truck_trip_distribution` | `nonres/TruckTripDistribution.job` | uses Cube's `TRIPDIST` (gravity) module |
| | `truck_time_of_day` | `nonres/TruckTimeOfDay.job` | |
| | `truck_toll_choice` | `nonres/TruckTollChoice.job` | choice model, reads skims |
| | `hsr_transit_submode_choice` | `nonres/HsrTransitSubmodeChoice.job` | choice model |
| | `move_air_pax_trips` | `nonres/MoveAirPaxTrips_IfNoFreePath.job` | |
| | `prep_assign` | `assign/PrepAssign.job` | builds assignment tables from CT-RAMP trip lists |
| | `accessibility` | `skims/Accessibility.job` | writes `skims/accessibility.csv`, which CT-RAMP reads |
| | `find_no_access_zones` | `skims/FindNoAccessZones.job` | ported in the earlier attempt (with `filterUnconnectedHouseholds.py`) |
| after the loop | `emfac_prep_within_zones` | `emfac/CreateSpeedBinsWithinZones.job` | |
| | `prep_assign_income` | `metrics/prepAssignIncome.job` | |
| | `sum_auto_times` | `metrics/sumAutoTimes.job` | |
| | `sum_transit_times` | `metrics/sumTransitTimes.job` | |
| | `sum_nonmot_times` | `metrics/sumNonmotTimes.job` | |

---

## 4. Stays in Cube

Every job that writes a network, plus the assignment and skimming engines:

- **network building:** `set_tolls`, `set_hov_xfer_penalties`,
  `create_five_highway_networks`, `create_nonmotorized_network`, `prep_hwy_net`,
  `build_transit_networks`
- **feedback:** `rename_assignment_variables`, `average_network_volumes`,
  `calculate_speeds`, `merge_networks`
- **engines:** `hwy_assign`, `transit_assign`, `hwy_skims`, `transit_skims`,
  `nonmotorized_skims`

---

## 5. Not about cubeio

From the earlier attempt's description (PR #115). Sizes are per run and were not
re-measured for this document.

| What | Size | Why it exists |
|---|---|---|
| `updated_output/*.rdata` | ~1.0 GB | R re-saving data already written as CSV |
| `main/indivTripDataIncome_3.csv` | ~1.6 GB | the trip table rewritten to add one column (`join_trips_with_income`) |
| `extractor/` | ~2.2 GB | a subset of outputs staged as a folder so it can be copied to M: |
| `INPUT/` copied into working folders | ~0.6 GB | keeps pristine inputs by duplicating them |

Also: `csv_to_dbf` (`csvToDbf.py`, depends on `dbfpy3`) and `aggregateTransitLinks.py`
(DBF handling) — small Python glue the earlier attempt replaced or simplified.

---

## Earlier work available for reuse

On `origin/phase-3-streamlining`. These were written against the project layout before
`steps.yaml` / `scen_*.yaml` and against the pre-rebase phase 2, so they need adapting
rather than cherry-picking.

| Commit | What |
|---|---|
| `0d0d61f7` | `filter_popsyn`: one native step replacing `FindNoAccessZones.job` + `filterUnconnectedHouseholds.py`. Output checked byte-identical to a reference run. |
| `44fbfeea` | `build_highway_networks` + `build_nonmotorized_skims`: native DBF writer replaces `csvToDbf.py`; the Cube jobs themselves moved as-is. |
| `66a77d2d` | `build_transit_lines` (drops the NetworkWrangler dependency) + `build_hsr_trips` (replaces `HsrTripGeneration.job` via cubeio) |
| `fe67d291` | fix to `build_hsr_trips` (reads `MODEL_YEAR` from the project) |
| `38092f81` | `docs/legacy_crosswalk.md`: where every piece of `RunModel.bat` went |
| `c5b36788` | Ctrl-C during a Cube job clears the cluster it started. A harness fix, not phase 3 material — may belong in phase 1. |

---

## How much checking each change needs

- **Moved** (same program, same script, same inputs, only launched differently): it ran
  and produced its outputs.
- **Rewritten** (new code doing the old job's work): compare its outputs against a
  reference run — cell by cell for matrices, field by field for tables.

Sections 1–3 are all rewrites.

---

## Decisions for Yuqi

1. For each CSV export in section 1: keep it (produced without Cube), replace it, or
   leave it.
2. Which section 3 jobs, if any, are worth rewriting now, given they are model logic
   and CT-RAMP + Cube will eventually be retired together.
3. Which section 5 items to take on.
4. Which earlier commits to adapt.
