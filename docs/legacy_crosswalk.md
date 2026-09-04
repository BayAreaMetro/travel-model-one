# RunModel.bat → `tm1`: where everything went

A crosswalk for reviewers who know the legacy batch pipeline. It is organized by the
**legacy** structure — `RunModel.bat`'s own step numbers — so you can start from the thing
you know and find where it lives now, or why it is gone. Every file the batch pipeline
touches appears exactly once.

Each item has one of five fates:

| Fate | Meaning |
|---|---|
| **moved** | same code executes, new caller — Cube `.job` files and CT-RAMP Java run unmodified via the harness |
| **rewritten** | same function, same output, new native code in `src/tm1/` — the legacy script/job is never invoked |
| **absorbed** | the *function* is now a property of the harness itself (config, logging, CLI), not a step at all |
| **eliminated** | the reason it existed no longer holds — nothing replaces it because nothing needs to |
| **not wired / deferred** | deliberately not carried over (yet); the trigger that would revive it is named |

The boundary rule behind every row: **legacy execution ends at the engine boundary.**
Cube jobs and CT-RAMP Java are engines — they run as-is and retire whole. Everything
between them (batch logic, Python wrangling, format shuffling) is glue, and glue is
rewritten in harness idioms or eliminated.

Legacy files stay in `model-files/` untouched — the old `.bat` path still works. This
document describes what the **new runner** executes.

---

## RunModel.bat, step by step

### Steps 1–2 · Set up (paths, cluster, directories, inputs)

| Legacy | Fate | Now |
|---|---|---|
| `SetPath.bat` | **absorbed** | the `tm1` CLI + Python venv; no PATH mutation |
| `pip_list.bat` → `pip_list.log` | **eliminated** | `uv.lock` is the environment record, versioned |
| Cube Cluster start (held for whole run) | **absorbed** | `run_cube_job(cluster_nodes=…)` starts/stops per job that needs one |
| `MODEL_YEAR` / `FUTURE` sliced from the *folder name* | **eliminated** | explicit `model_year:` / `future:` in scenario YAML — results no longer depend on how a directory is spelled |
| directory creation | **absorbed** | each step creates what it writes |
| input copying (13.3 GB of working dirs) | **moved + repointed** | `copy_inputs` step, sourced from pristine `INPUT/` (25 MB) — *this PR* |
| `notify_slack.py` | **absorbed** | `src/tm1/slack.py` |

### Step 3 · Pre-process

| Legacy | Fate | Now |
|---|---|---|
| `RuntimeConfiguration.py` (805 ln) | **rewritten** | split in two: host IP / JPPF distribution / shadow pricing / popsyn paths / project dir were already native in `simulate_ctramp` (`patch_properties` + JPPF patching); the remainder — parse `INPUT/params.properties`, propagate auto/truck opcost, WFH factors, free parking into `.properties`, `hwyParam.block`, and UEC `.xls` (`costPerMile`) — becomes the native `configure_ctramp` step — *this PR* |
| `updateUECsToUseTollDist.py` | **not wired** | NGF scenarios only; trigger: an NGF run |
| `csvToDbf.py` (94 ln) | **rewritten** | ~20 lines inside `build_highway_networks` (tolls.csv → the `.dbf` Cube's HWYNET reads) — *this PR* |
| `SetTolls.job` | **moved** | `build_highway_networks` step, via `run_cube_job` — *this PR* |
| `SetHovXferPenalties.job` | **moved** | ditto (note: its output may be read by nothing — runs regardless under re-wire; flagged, not blocking) |
| `CreateFiveHighwayNetworks.job` | **moved** | ditto — produces `hwy/avgload{P}.net`, the artifact runs currently inherit |
| `HsrTripGeneration.job` | **rewritten** | `build_hsr_trips`: `cubeio` reads `tripsHsr{P}_{2040,2050}.tpp`, interpolates to `model_year`, writes — one Cube job deleted — *this PR* |

### Step 4 · Non-motorized level of service

| Legacy | Fate | Now |
|---|---|---|
| `CreateNonMotorizedNetwork.job` | **moved** | `build_nonmotorized_skims` step — *this PR* |
| `NonMotorizedSkims.job` | **moved** | ditto — produces `skims/nonmotskm.tpp`, which the calibration report currently reads from a reference run; that dependency ends here |

### Step 4.5 · Initial transit files

| Legacy | Fate | Now |
|---|---|---|
| `transitDwellAccess.py` Simple mode (538 ln, needs NetworkWrangler) | **rewritten** | `build_transit_lines`: parse the ASCII `.lin`, demux by time period, apply simple dwell by mode → `trn/transitOriginal{P}.lin`. The NetworkWrangler dependency goes with it — *this PR* |
| its `transitVehicleVolsOnLink{P}.dbf` output | **eliminated** | referenced only by the script that writes it; nothing consumes it |

### Steps 5–9 · The iteration loop (`RunIteration.bat` × 4)

The loop structure itself — `goto` logic, `ITER`/`SAMPLESHARE` env vars, the
0.15/0.30/0.50 sample ramp — was **absorbed** by the runner's `iterate:` block in #103.
Inside it:

| Legacy | Fate | Now |
|---|---|---|
| Step 1 `HwySkims.job` + `Accessibility.job` | **moved** | `tm1.assignment.cube.ctramp.run_skims` |
| Step 1 (iter 1 only) `FindNoAccessZones.job` → `unconnected_zones.csv` → `filterUnconnectedHouseholds.py` | **rewritten** | `filter_popsyn`, one native step *before* the loop (the `ITER==1` guard was preprocess parked inside the loop): `cubeio` reads the skim, unconnected zones computed in memory, popsyn filtered with pandas. A Cube job, a handoff file, and a script collapse into one function — *this PR* |
| Step 2 CT-RAMP Java (JPPF cluster, matrix/household managers) | **moved** | `simulate_ctramp` step — runs the stock Java |
| Step 2 `updateTelecommute_forEN7.py` | **not wired** | EN7 scenarios only (`EN7=ENABLED`); trigger: an EN7 run |
| Step 3 non-residential models (9 jobs: Ix\*, Truck\*, air pax, HSR submode) | **moved** | `run_nonres` inside the `assignment` step — all nine stock jobs. These are *model components* (trucks and internal-external are full models; air pax and HSR process input tables) and are orthogonal to any future demand-engine swap |
| Step 4 `PrepAssign.job` → `HwyAssign.job` | **moved** | `assignment` step; `PrepAssign` output verified against the declared `demand:` artifact |
| Step 4 transit (`PrepHwyNet`, `BuildTransitNetworks`, `TransitAssign`, `TransitSkims`) | **moved** | `tm1.assignment.cube.transit.run_transit` |
| Step 5 feedback (5 jobs: Rename, Average, CalculateSpeeds, TestConvergence, MergeNetworks) | **moved** | `run_highway_feedback` |

### Step 11 · Skim databases

| Legacy | Fate | Now |
|---|---|---|
| `SkimsDatabase.job` (4.4 GB CSV per run) | **eliminated** | existed only because nothing outside Cube could read `.tpp`; `cubeio` reads them directly |
| `updated_output/*.rdata` (1.0 GB) | **eliminated** | R re-serialization of the CSVs above; no Cube→CSV→R hop remains |

### Steps 12–17 · Post-processing

| Legacy | Fate | Now |
|---|---|---|
| `RunPrepareEmfac.bat` ×2 | **deferred** | trigger: air-quality conformity demand — regulatory, likeliest early revival |
| `RunLogsums.bat` | **deferred** | re-runs the entire CT-RAMP Java stack; establish whether that is avoidable before ever wiring it |
| `RunCoreSummaries.bat` (4× R) | **deferred** | fundamental deliverable; toolchain (port vs shell-to-R) undecided |
| `RunMetrics` / `RunScenarioMetrics` (`utilities/RTP`, 115 files) | **not wired** | analysis run *against* outputs, not part of producing them |
| off-model calculation (2035/2050 only) | **not wired** | trigger: a horizon-year run |
| `net2csv_avgload5period.job` | **not wired** | revive when a consumer needs the per-class link CSV |

### Step 18 · Directory clean-up

| Legacy | Fate | Now |
|---|---|---|
| `ExtractKeyFiles.bat` (2.2 GB staging) | **eliminated** | files staged so they could be copied again; ship a manifest if sharing is needed |

---

## Supporting directories

| Legacy | Fate | Now |
|---|---|---|
| `scripts/block/*.block` (speed/capacity tables, params) | **moved** | still read by the Cube jobs, unmodified; `hwyParam.block` is now *written* by `configure_ctramp` from scenario params instead of by `RuntimeConfiguration.py` |
| `scripts/assign`, `skims`, `feedback`, `nonres` `.job` files | **moved** | run unmodified via `run_cube_job` — see rows above |
| `scripts/core_summaries/` | **deferred** | see Step 14 |
| `scripts/emfac/` | **deferred** | see Step 12 |
| `scripts/database/` | **eliminated** | see Step 11 |
| `utilities/` (386 scripts: bespoke requests, calibration one-offs, fare studies, select-link) | **not wired** | ad-hoc analyses against model outputs; they keep working against outputs and are not model-parity work |

---

## What a reviewer should check

1. **Completeness** — every `runtpp`/`python`/`Rscript`/`call` in `RunModel.bat` and
   `RunIteration.bat` has a row here. If you find one that doesn't, that's a review
   finding.
2. **Rewrites are output-identical** — each *rewritten* row is verified against the
   reference run: text-diff for `.properties`/`.block`/`.lin`/CSV, cell-diff via `cubeio`
   for `.tpp`. The `.net` files (built by *moved* Cube jobs) are verified indirectly
   through their derived link CSV and skims.
3. **Eliminations name the dead constraint** — if you think the constraint still holds
   (something does read `SkimsDatabase` CSVs that can't use `cubeio`), that's a review
   finding.
4. **Deferred items have triggers, not apologies** — if a trigger is already live (someone
   needs EMFAC now), say so and it moves into scope.
