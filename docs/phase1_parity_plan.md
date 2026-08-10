# Phase 1 end-to-end: running the whole model through the harness

Scope and plan for extending #103 from "runtime harness" to "runtime harness + model
parity" — the complete `RunModel.bat` pipeline driven by the Python runner, with every
legacy `.job` and `.py` executed **unmodified, in place**.

Phase 4 then bulldozes the legacy scripts one at a time. This document is both the phase
spec and phase 4's demolition checklist.

## The rule

**`.bat` is orchestration → harness. `.job` / `.py` / `.R` are artifacts → run as-is.**

Clean, and it settles the awkward cases without special pleading:

- `trnAssign.bat` is a `.bat`, so #103's existing native `run_transit` is *correct* under
  the rule, not a deviation to undo.
- `javaOnly_runMain.cmd` / `javaOnly_runNode0.cmd` likewise — already native in
  `simulate_ctramp`.
- `SetPath.bat`, `pip_list.bat`, `extractkeyfiles.bat` are orchestration and die.
- `RuntimeConfiguration.py` is a `.py`, so it runs unmodified even though phase 4 has
  already written its native replacement.

## Scope

| In | Out, and why |
|---|---|
| Steps 1–2 setup; step 3 pre-process; step 4 non-motorized | NGF / EN7 / off-model / horizon-year conditionals — the `.bat` skips them for a base-2023 run too |
| Iterations 0–3, complete `RunIteration.bat` body | EMFAC, logsums, core summaries, RTP metrics — need R on the box; deferred today and stay deferred |
| Step 11 `SkimsDatabase.job`, `net2csv_avgload5period.job` | AWS `s3 sync`, `shutdown.exe` — deployment, not model |
| Step 18 clean-up: `.prn`/`.log` collection, cluster close | `extractkeyfiles` + robocopy — staging files so they can be copied again |

The clunky intermediates the parity run is meant to retain — `SkimsDatabase`'s 4.4 GB of
CSV, `x3avgload{P}.net`, `avgload5period_vehclasses.csv` — are all upstream of that line.

## Verification findings

Five things checked before writing this, because each could have changed the plan.

### 1. Iteration 0 is a slice of the loop body, run once

`RunIteration.bat:19` (`if %ITER%==0 goto hwyAssign`) jumps into the shared body at a
label: iteration 0 runs everything from `HwyAssign` onward and none of the demand side.
It is a *slice*, not a separate pipeline — 11 of its 12 steps are ones the loop already
runs, differing only in round. `warm_start:` names that slice; see the config shape
below.

Phase 4's `warmstart.py` is not the model for it. That module bundles two things the
`.bat` keeps apart, and adds a third the `.bat` does not have:

| `warmstart.py` does | `RunModel.bat` |
|---|---|
| copies `INPUT/warmstart/{main,nonres}/*.tpp` into place | lines 176–177, in the **setup copy block** — not iteration 0 |
| runs `assignment` at iteration 0 | lines 252–264, the `ITER=0` call to `RunIteration.bat` |
| `from: coldstart` — writes zero demand | **no legacy equivalent**; its own docstring says so |

So the copy belongs in `copy_inputs`, and iteration 0 belongs in `warm_start:`. Phase 4's
consolidation is phase 4's business.

### 2. `updateTelecommute_forEN7.py` — the crosswalk row is mechanically wrong

`RunIteration.bat:78` runs it **unconditionally**, every iteration. The crosswalk records
it as "not wired / EN7 scenarios only", which describes the effect but not the mechanism:
the script self-guards, reading `os.environ['EN7']`, fatal-erroring if the value is not
in `['ENABLED','DISABLED']`, and `sys.exit(0)`-ing immediately when `DISABLED` — before
touching any input file.

Parity therefore **runs it every iteration** as a `command:` step with `EN7`,
`ITER` and `MAXITERATIONS` in the environment. With `EN7=DISABLED` it does nothing, at
the cost of a process spawn. `RunModel.bat:115-128` refuses to start when `EN7` is unset,
so the harness must require it too rather than defaulting it.

### 3. `HwySkims` moved from the head of iteration N to the tail of N−1 — equivalent

`RunIteration.bat` runs `HwySkims`/`Accessibility` at the *start* of each iteration
(`:skims`, line 31); `run_iteration` runs them at the *end* (`build_skims`). Counted out,
the two produce the same three skim builds from the same three networks:

| | skim builds |
|---|---|
| `.bat` | iter 0 none; iter 1, 2, 3 each skim the *previous* iteration's networks |
| harness | iter 0, 1, 2 each skim their own networks at the tail; iter 3 `build_skims=False` |

Identical set. This is a faithful reordering, not a behaviour change — recorded here so it
does not resurface as a suspected parity bug. It does change what `--resume-at` lands on.

### 4. `args:` states the resulting argv, not the `.bat`'s text

`RunModel.bat:146-147` sets the two complex-mode variables to **a single space**, with
the comment *"NOTE the blank ones should have a space"*. `cmd` collapses that on
expansion, so `transitDwellAccess.py` actually receives five arguments:

    NORMAL NoExtraDelay Simple complexDwell complexAccess

and parses both mode lists as empty (`transitDwellAccess.py:320-326`: `complexAccess`
appears at index 0 of the dwell list, so both slices come out empty).

Transcribing the `.bat` *textually* — passing `""` where `%COMPLEXMODES_DWELL%` appears —
produces seven arguments instead, and line 320 hits `int("")` and raises. The empty-
variable-with-a-space idiom is a `cmd` artifact with no YAML equivalent.

**Rule for the whole config: `args:` is the argv the script receives, derived by
expanding the `.bat` as `cmd` would — not a transliteration of the `.bat` line.**
Any legacy invocation using a possibly-empty `%VAR%` needs the same check.

### 5. Every iteration guard dissolves — no per-step round tags

`RunIteration.bat` is one body called four times with different `%ITER%` values, so it
branches internally five times. None of those branches needs a config mechanism.

| `.bat` guard | What it is actually for | Where it goes |
|---|---|---|
| `ITER==0 goto hwyAssign` | this round has no demand model | iteration 0 is its own step list → gone |
| `ITER==1` FindNoAccessZones + filterUnconnectedHouseholds | one-time popsyn cleanup that needs skims | steps between the warm start and the loop → gone |
| `ITER==1` javaOnly_runMain / runNode0 | start the JPPF services once | absorbed into `simulate_ctramp` → gone |
| `ITER GTR 0` PrepAssign | iteration 0's demand is pre-made | goes with iteration 0 → gone |
| `ITER GTR 1` average, `ELSE` copy | seeding a running average | **see below** — gone, for one changed value |

The config is therefore two flat step lists (warm start, then the loop body) with no
conditionals, no `rounds:`, and no `iterations:` on any step.

#### The averaging branch, and why it is safe to delete

The `.bat` skips `AverageNetworkVolumes`/`CalculateSpeeds` at iteration 1 and copies the
loaded network instead. That looks like a real initialization problem — a running
average needs a seed — but the weights already encode the seed:

| iteration | `WGT` | `PREV_WGT` |
|---|---|---|
| 1 | 1.0 | **0.00** |
| 2 | 0.50 | 0.50 |
| 3 | 0.33 | 0.67 |

At iteration 1 the job would compute `0.00 × previous + 1.00 × current` — exactly the
copy. The only thing preventing it from running is that `PREV_ITER` is **1** at
iteration 1, so `AverageNetworkVolumes.job:33` reads
`hwy/iter1/avgload{P}.net` — the file the `ELSE` branch is about to create. It points
at itself.

Setting `PREV_ITER=0` at iteration 1 makes it read iteration 0's network, weight it
`0.00`, and produce the same result. **`trnAssign.bat:15-16` already applies exactly
this fix for its own use** (`IF %ITER% EQU 1 SET PREV_TRN_ITER=0`), so the wart was
already recognised locally rather than fixed at source.

```
                        iteration 1

                     HwyAssign.job
                          │
                          ▼
                 hwy/iter1/LOAD{P}.net
                          │
                          ▼
            RenameAssignmentVariables.job
                          │
                          ▼
             hwy/iter1/LOAD{P}_renamed.net
                          │
        ┌─────────────────┴─────────────────────┐
        │ LEGACY                                │ THIS PLAN
        │ IF %ITER% GTR 1 -> false, so ELSE:    │ AverageNetworkVolumes.job
        │                                       │   neti[1] iter0/avgload  x 0.00
        │   copy LOAD{P}_renamed.net            │   neti[2] iter1/renamed  x 1.00
        │        -> avgLOAD{P}.net              │   ---------------------------
        │                                       │   = 1.00 x renamed
        │                                       │   -> xavgload{P}.net
        │                                       │ CalculateSpeeds.job
        │                                       │   -> avgload{P}.net
        └─────────────────┬─────────────────────┘
                          ▼
                hwy/iter1/avgLOAD{P}.net
             volumes identical by construction
```

**Volumes are provably identical. `CTIM` is not proven identical** — the copy inherits
`HwyAssign`'s own converged congested time, while `CalculateSpeeds` recomputes it from
the volume-delay function over those same volumes. The two should agree, since it is
the same VDF over the same volumes, but "should" is not "verified". Cell-diff
iteration 1's `avgLOAD{P}.net` against the reference run before relying on it; if it
does not reproduce, the fallback is a seeding step at the head of the loop rather than
a round tag.

Side effect, an improvement: `TestNetworkConvergence` at iteration 1 currently compares
iteration 1 against *itself* and reports a zero gap. With `PREV_ITER=0` it reports a
real gap against iteration 0. Nothing parses `feedback.rpt`, so nothing breaks.

## The enumeration

### `RunModel.bat`

| Line | Command | Fate |
|---|---|---|
| 21 | `call CTRAMP\runtime\SetPath.bat` | absorbed — venv |
| 24 | `call CTRAMP\runtime\pip_list.bat` | eliminated — `uv.lock` |
| 27 | `Cluster ... 1-48 Starthide` | absorbed — `run_cube_job(cluster_nodes=)` |
| 30–49 | `HOST_IP_ADDRESS`, `INSTANCE` by `%computername%` | absorbed — config |
| 53–110 | `MODEL_YEAR`, `PROJECT`, `FUTURE` sliced from folder name | absorbed — explicit in scenario YAML |
| 115–128 | `EN7` validation | absorbed — required config key (see finding 2) |
| 133 | `notify_slack.py "Starting"` | absorbed — `tm1.slack` |
| 135–147 | `MAXITERATIONS`, `TRNCONFIG`, `COMPLEXMODES_*` | absorbed — config → step env |
| 156–165 | `mkdir` ×10 | absorbed — each step creates what it writes |
| 168 | `echo STARTED >> logs\feedback.rpt` | absorbed — run log |
| 172–178 | `copy INPUT\{hwy,trn,landuse,nonres,warmstart\main,warmstart\nonres,logsums}` | `copy_inputs` |
| 190 | `python ...\RuntimeConfiguration.py` | `command:` |
| 193–200 | NGF `updateUECsToUseTollDist.py` | out of scope — NGF only |
| 203 | `python ...\csvToDbf.py hwy\tolls.csv hwy\tolls.dbf` | `command:` + `args` |
| 207 | `runtpp ...\SetTolls.job` | `job:` |
| 211 | `runtpp ...\SetHovXferPenalties.job` | `job:` |
| 215 | `runtpp ...\CreateFiveHighwayNetworks.job` | `job:` |
| 219 | `runtpp ...\HsrTripGeneration.job` | `job:` |
| 231 | `runtpp ...\CreateNonMotorizedNetwork.job` | `job:` |
| 235 | `runtpp ...\NonMotorizedSkims.job` | `job:` |
| 239 | `python ...\transitDwellAccess.py NORMAL NoExtraDelay Simple complexDwell "" complexAccess ""` | `command:` + `args` |
| 252–264 | `ITER=0` → `call RunIteration.bat` | `warmstart` step, before the loop |
| 276–336 | `ITER=1,2,3`: `RuntimeConfiguration.py --iter N` then `RunIteration.bat` | `iterate:` body |
| 340 | `taskkill /f /im java.exe` | absorbed — `simulate_ctramp` owns its JVMs |
| 350 | `runtpp ...\SkimsDatabase.job` | `job:` |
| 364 | `runtpp ...\net2csv_avgload5period.job` | `job:` |
| 369–428 | EMFAC ×2, logsums, core summaries, metrics ×2, off-model | out of scope — deferred |
| 439–440 | `extractkeyfiles` + robocopy | out of scope |
| 446–454 | `copy *.prn logs\`, `Cluster Close`, `del` | `cleanup` step |
| 461–473 | slack, s3 sync, shutdown | absorbed / out of scope |

### `RunIteration.bat`

`WGT`/`PREV_WGT` come from the enclosing iteration (1.0/0.00, 1.0/0.00, 0.50/0.50,
0.33/0.67); `SAMPLESHARE` follows the runner's existing 0.15/0.30/0.50 ramp.

| Line | Command | Fate | Runs at |
|---|---|---|---|
| 19 | `if %ITER%==0 goto hwyAssign` | warm start sits outside the loop (finding 5) | — |
| 31 | `runtpp ...\HwySkims.job` | inside `assignment` (`build_skims`) | see finding 3 |
| 38 | `runtpp ...\Accessibility.job` | ditto | ditto |
| 52 | `runtpp ...\FindNoAccessZones.job` | `job:` | iter 1 |
| 56 | `python ...\filterUnconnectedHouseholds.py popsyn` | `command:` | iter 1 |
| 60–65 | `javaOnly_runMain.cmd`, `javaOnly_runNode0.cmd` | absorbed — `simulate_ctramp` | iter 1 |
| 69 | `java ... MtcTourBasedModel -iteration -sampleRate -sampleSeed` | `simulate_ctramp` | 1+ |
| 74 | `copy mtcTourBased.properties ..._%ITER%` | absorbed — `simulate_ctramp` | 1+ |
| 78 | `python ...\updateTelecommute_forEN7.py` | `command:` (see finding 2) | 1+ |
| 90–123 | 9 nonres jobs | inside `assignment` (`run_nonres`) | 1+ |
| 135 | `runtpp ...\PrepAssign.job` | inside `assignment` | 1+ |
| 140 | `runtpp ...\HwyAssign.job` | inside `assignment` | all |
| 145–146 | `copy trnAssign.bat` + `call` | absorbed — `run_transit` | all |
| 159–164 | `mkdir hwy\iter%ITER%`, `move LOAD*.net` | inside `run_highway_feedback` | all |
| 168 | `runtpp ...\RenameAssignmentVariables.job` | ditto | all |
| 172–181 | `AverageNetworkVolumes` + `CalculateSpeeds`, else copy `*_renamed` | ditto | 2+ / else |
| 185 | `runtpp ...\TestNetworkConvergence.job` | ditto | all |
| 189 | `runtpp ...\MergeNetworks.job` | ditto | all |
| 193–200 | `copy avgLOAD*.net hwy\`, `del x*.net` | ditto | all |
| 209–211 | `feedback.rpt`, slack | absorbed | all |

Everything marked *inside `assignment`* is already built and validated in #103. That is
why the parity config adds roughly **15 steps, not 40**.

## Two new step types

```
job:            → run_cube_job(path)             PERMANENT — engine-boundary rule;
                                                 retires with Cube in phase 6
command:  → subprocess, cwd = proj_dir     SCAFFOLD — deleted in phase 4
```

`script:` already exists but imports a module and calls `run(scenario_dir, cfg, **kwargs)`.
Legacy scripts are `sys.argv`/cwd CLI programs, so they need the second key. Both hang off
`_load_step`'s existing `_CUSTOM_KEYS` seam.

**Phase 4 is complete when `command:` has zero users** — a grep, not a judgement
call. Its deletion is one module, two `_CUSTOM_KEYS` entries, and the `legacy` extra;
NetworkWrangler, dbfpy3 and xlrd go out in the same commit.

## Config shape

```yaml
steps:
  # RunModel.bat 172-178
  copy_inputs:
    hwy:              {from: "{proj_dir}/INPUT/hwy",               to: "{proj_dir}/hwy"}
    trn:              {from: "{proj_dir}/INPUT/trn",               to: "{proj_dir}/trn"}
    landuse:          {from: "{proj_dir}/INPUT/landuse",           to: "{proj_dir}/landuse"}
    nonres:           {from: "{proj_dir}/INPUT/nonres",            to: "{proj_dir}/nonres"}
    warmstart_main:   {from: "{proj_dir}/INPUT/warmstart/main",    to: "{proj_dir}/main"}
    warmstart_nonres: {from: "{proj_dir}/INPUT/warmstart/nonres",  to: "{proj_dir}/nonres"}

  # 190, 203
  runtime_configuration:
    command: "CTRAMP/scripts/preprocess/RuntimeConfiguration.py"
  csv_to_dbf:
    command: "CTRAMP/scripts/preprocess/csvToDbf.py"
    args: ["hwy/tolls.csv", "hwy/tolls.dbf"]

  # 207-219
  set_tolls:              {job: "CTRAMP/scripts/preprocess/SetTolls.job"}
  set_hov_xfer_penalties: {job: "CTRAMP/scripts/preprocess/SetHovXferPenalties.job"}
  create_five_networks:   {job: "CTRAMP/scripts/preprocess/CreateFiveHighwayNetworks.job"}
  hsr_trip_generation:    {job: "CTRAMP/scripts/preprocess/HsrTripGeneration.job"}

  # 231-239
  create_nonmotorized_network: {job: "CTRAMP/scripts/skims/CreateNonMotorizedNetwork.job"}
  nonmotorized_skims:          {job: "CTRAMP/scripts/skims/NonMotorizedSkims.job"}
  transit_dwell_access:
    command: "CTRAMP/scripts/skims/transitDwellAccess.py"
    # NOT ["...", "complexDwell", "", "complexAccess", ""] -- see finding 4.
    args: ["NORMAL", "NoExtraDelay", "Simple", "complexDwell", "complexAccess"]

  # RunIteration.bat's ITER==1 block, hoisted out of the loop (see finding 5)
  find_no_access_zones: {job: "CTRAMP/scripts/skims/FindNoAccessZones.job"}
  filter_unconnected_households:
    command: "CTRAMP/scripts/preprocess/filterUnconnectedHouseholds.py"
    args: ["popsyn"]

  # 252-336 -- iteration 0, then iterations 1-3
  iterate:
    count: 3

    # RunIteration.bat:19 -- `if %ITER%==0 goto hwyAssign`.  Iteration 0 runs this
    # slice of the body below, named rather than duplicated, and seeds the running
    # average rather than computing it.
    warm_start:
      - hwy_assign
      - stage_transit_lines
      - prep_hwy_net
      - build_transit_networks
      - transit_assign
      - transit_skims
      - stage_loaded_networks
      - rename_assignment_variables
      - seed_average_networks:              # the only step the loop does not have
          module: "tm1.steps.staging:seed_average_networks"
      - test_network_convergence
      - merge_networks
      - publish_networks

    steps:
      hwy_skims:     {job: "CTRAMP/scripts/skims/HwySkims.job", cluster_nodes: 5}
      accessibility: {job: "CTRAMP/scripts/skims/Accessibility.job"}
      runtime_configuration_iter:
        command: "CTRAMP/scripts/preprocess/RuntimeConfiguration.py"
        args: ["--iter", "{iteration}"]
      simulate_ctramp: {...}               # unchanged from #103
      update_telecommute_en7:
        command: "CTRAMP/scripts/preprocess/updateTelecommute_forEN7.py"
      ...9 nonres jobs...
      prep_assign: {job: "CTRAMP/scripts/assign/PrepAssign.job", cluster_nodes: 5}
      hwy_assign:  {job: "CTRAMP/scripts/assign/HwyAssign.job",  cluster_nodes: 48}
      stage_transit_lines: {module: "tm1.steps.staging:stage_transit_lines"}
      prep_hwy_net:
        job: "CTRAMP/scripts/skims/PrepHwyNet.job"
        cwd: "trn/TransitAssignment.iter{iteration}"
      ...3 more transit jobs...
      stage_loaded_networks:      {module: "tm1.steps.staging:stage_loaded_networks"}
      rename_assignment_variables: {job: ".../RenameAssignmentVariables.job"}
      average_network_volumes:     {job: ".../AverageNetworkVolumes.job"}
      calculate_speeds:            {job: ".../CalculateSpeeds.job", cluster_nodes: 5}
      test_network_convergence:    {job: ".../TestNetworkConvergence.job"}
      merge_networks:              {job: ".../MergeNetworks.job"}
      publish_networks:            {module: "tm1.steps.staging:publish_networks"}

  # 350, 364, 446-454
  skims_database: {job: "CTRAMP/scripts/database/SkimsDatabase.job"}
  net2csv:        {job: "CTRAMP/scripts/metrics/net2csv_avgload5period.job"}
  cleanup:        {...}
```

### `warm_start:` — the one branch that survives

Iteration 0 is a *slice of the loop body*, not a second pipeline: 11 of its 12 steps are
the ones the loop already defines, differing only by round. Naming them keeps each step
defined once, so a change to `transit_assign`'s cluster size or `cwd` cannot drift
between the two.

A bare name reuses the loop's definition; a name with a body defines a step only the
warm start has. `seed_average_networks` is the only one — the loop computes the running
average where iteration 0 must seed it, since round 0 has no earlier iteration
directory to average against. (Round *1* does, which is what finding 5 exploits; round
0 does not, which is why one step remains.)

A name that matches nothing in the body is an error raised while the plan is built,
before any step runs — a typo would otherwise be a step that silently never happens.


## Environment contract

The `.bat` set these implicitly and every `.job` reads them. They become per-iteration
values the runner supplies:

| Variable | Source |
|---|---|
| `ITER`, `PREV_ITER` | the `iterate:` block |
| `WGT`, `PREV_WGT` | per-iteration table: `1.0/0.00`, `1.0/0.00`, `0.50/0.50`, `0.33/0.67` |
| `SAMPLESHARE`, `SEED` | existing 0.15/0.30/0.50 ramp; seed 0 |
| `MODEL_YEAR`, `FUTURE` | top-level `model_year:` / `future:` — promoted from the assignment step, since the pre-process reads them too |
| `TRNCONFIG`, `COMPLEXMODES_DWELL`, `COMPLEXMODES_ACCESS` | `env:` block; defaults transcribed from the `.bat` |
| `MAXITERATIONS`, `EN7` | `env:` block; `EN7` required, never defaulted |
| `COMMPATH`, `MODEL_DIR`, `HOST_IP_ADDRESS` | runner |

## Files

**New: 4** (possibly 5)

- `src/tm1/steps/external.py` — the `job:` and `command:` handlers plus the
  environment contract
- `src/tm1/steps/staging.py` — the `mkdir`/`move`/`copy`/`del` lines `RunIteration.bat`
  does inline, as four steps rather than buried
- `tests/test_external_steps.py`, `tests/test_iteration_plan.py` — phase 1 had no
  tests at all before this
- `src/tm1/steps/cleanup.py` — if it does not fold cleanly into `setup.py`

**Edited: 3**

- `src/tm1/runner.py` — two `_CUSTOM_KEYS` entries, a `_load_step` branch, `step_name`
  passed to every step, and `warm_start:` expansion in `_iteration_plan`.
- `scenarios/base_2023_ctramp/scenario_config.yaml` — the bulk of the work
- `pyproject.toml` — `legacy` extra

`docs/legacy_crosswalk.md` also needs its fates recut against this document, but that
file lives on the phase-4 branch, so it is a phase-4 edit rather than part of this work.

## Commit sequence

1. `job:` and `command:` step types, with tests
2. Environment/cwd contract — the `.bat`'s implicit environment made explicit
3. `warm_start:` on `iterate:` -- iteration 0 as a named slice of the body
4. The scenario config, sourced from `INPUT/` only — and with it, the first **live-Cube
   smoke test of the `job:` path**. It has never run real Cube: the tests patch
   `run_cube_job`, and `run_cube_job` itself has no automated tests at all, only the
   live run recorded in `c78ac6fd`. `SetTolls.job` is the one to prove it with — fast,
   no cluster, deterministic, and its `tolls.dbf` output is already verified byte-for-byte
5. `cleanup` step
6. Parity run, with its diff report committed as the baseline

## Risks

**Bare relative paths.** `PrepAssign.job` reads by bare relative path, and every legacy
script assumes `cwd == MODEL_DIR`. This is where the bugs will be, and it is why
`command:` fixes `cwd` rather than making it configurable.

**`RuntimeConfiguration.py` runs four times** — bare at line 190, then `--iter N` at 284,
308 and 332. This is the source of the "reference `.original` files are already patched"
gotcha. Parity must reproduce all four, not collapse them.

**The `legacy` extra** (NetworkWrangler, dbfpy3, xlrd) lands here and dies in phase 4.

**Cascade.** Rewriting #103 rebases phases 2–6. Rescue-tag first; `--onto <old tip>`, not
`merge-base`.
