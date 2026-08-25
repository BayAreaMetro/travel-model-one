# AequilibraE Usage Guide

How to run, configure, and modify the open-source (AequilibraE) assignment/skimming
track that replaces Cube Voyager's `HwyAssign`, `TransitAssign`, and skim jobs.

This is the **operator's guide**. For *why it matches Cube* (validation numbers) see
[aequilibrae_migration.md](aequilibrae_migration.md); for the *mechanics of assignment
itself* see [assignment_primer.md](assignment_primer.md).

---

## 1. What it is and when it runs

Travel Model One's feedback loop alternates **demand** (ActivitySim) with **network
supply** (assignment + skims). The `aeq` track is a drop-in replacement for the supply
half — it takes trip tables + a network and produces loaded volumes and level-of-service
skims, with **no Cube license, no Cube binaries, and no network shares**.

| Cube job (legacy) | aeq replacement | Code |
|---|---|---|
| `HwyAssign.job` | Frank-Wolfe user equilibrium, Cube's exact facility-type VDF | `src/tm1/assignment/aeq/highway.py` |
| `TransitAssign.job` | Spiess-Florian optimal-strategy assignment | `src/tm1/assignment/aeq/transit.py` |
| `HwySkims` / `TransitSkims.job` | component skims → `skims.omx` | `src/tm1/assignment/aeq/transit_skims.py`, `runner.py` |
| `PrepHwyNet` net2csv, TRNBUILD build | one-time input extraction | `scripts/build_aeq_inputs.py` |

The engine (`src/tm1/assignment/aeq/`) is **generic**; all MTC policy lives in
`default-configs/assignment/aeq_params.yaml` (see §4). This separation is deliberate — never
put policy constants in `src/`.

---

## 2. One-time setup: build the Cube-free input set

Before the first run (or whenever the source network / reference run changes), extract the
static inputs once:

```bash
python scripts/build_aeq_inputs.py \
    --reference //MODEL3-C/Model3C-Share/Projects/2023_TM161_IPA_35_testrun \
    --out E:/aeq_inputs
```

This produces under `--out`:

| File | What it is |
|---|---|
| `highway_links.csv` | per-link attrs/tolls/use-codes/capclass — the aeq highway network (a copy of Cube's net2csv export, so link **row order is identical** to Cube's loaded network) |
| `transitLines.lin` | master TRNBUILD line file (ASCII source) |
| `fares/` | `.far` / fare-block files for fare skims |
| `support_links.parquet` | modes 1–9 access/egress/transfer/funnel links per run type |
| `link_distance.parquet` | directional link distances (rail RUNTIME distribution) |
| `ref_ride_time.parquet` | reference in-vehicle times per (A,B,mode) — fallback for rail links whose line has no RUNTIME |
| `nonres/trips{P}.omx` | non-residential demand (IX/truck/air/HSR), TPP→OMX |

The reference run is used **purely as a data source for extraction** — nothing is run
through Cube. After this, per-iteration runs touch only `--out`.

---

## 3. How to run it

Assignment runs inside the ActivitySim pipeline's feedback loop, selected per-scenario in
`scenario_config.yaml`. Set `iterations > 0` and add an `assignment` block under
`simulate_activitysim`:

```yaml
simulate_activitysim:
  iterations: 3                 # feedback iterations (0 = static skims, no assignment)
  assignment:
    backend: aeq                # "aeq" (open-source) or "cube" (legacy Voyager loop)
    demand: "{proj_dir}/output/trips_{period}.omx"   # optional; this is the default
    network_csv: "{reference_run}/hwy/iter3/avgload5period_vehclasses.csv"
    nonres_dir:  "{reference_run}/nonres"
    skims_omx:   "{proj_dir}/data/skims.omx"
    transit_inputs_dir: "E:/aeq_inputs"
    cores: 48
    max_iter: 100               # Frank-Wolfe inner cap per period
    gap_target: 0.001           # relative-gap convergence target
    archive: true
```

Or start from [`scenarios/base_2023_activitysim_aeq/`](../scenarios/base_2023_activitysim_aeq/),
which is `base_2023_activitysim` with this block swapped in and everything else shared, so
the two can be run side by side as an engine comparison.

`demand` is the artifact the engine consumes — the same key the Cube backend reads, so the
two engines are pointed at demand identically. `{period}` expands to `ea/am/md/pm/ev`
(`{PERIOD}` gives `EA/AM/...`).

The dispatch is [`run_backend`](../src/tm1/steps/assignment.py) and its `_BACKENDS` table,
shared with the CT-RAMP path so there is one backend selection for the whole pipeline
(`backend` defaults to `cube`). The aeq entry point is
[`run_assignment_iteration`](../src/tm1/assignment/aeq/runner.py#L173). Each iteration, for
all five periods, it: assembles demand (ActivitySim personal trips + nonres) → assigns
(equilibrium) → skims highway + transit → writes `skims.omx` for the next ActivitySim pass.

Run the pipeline as usual:

```bash
python -m tm1 run --scenario <your_scenario> --steps simulate_activitysim
```

**Performance:** highway ≈ 10 min/iter, transit skims ≈ 6 min/iter on TM2-B (48 cores).
The transit **fare lookup** is computed once and cached to
`aeq_transit_fare_cache.npz` beside `skims.omx` — fares are static (a function of the fare
system + line topology, not times or demand), so later iterations reuse it exactly. The
time-dependent parts (congested bus times, optimal strategy) are recomputed every
iteration. Deleting the cache forces a one-time (~7 min) rebuild; it is **not** an accuracy
knob.

---

## 4. How to modify it

### Policy (the common case) — `default-configs/assignment/aeq_params.yaml`

Every model knob lives here, with per-block provenance noting the Cube job it came from.
Load via `tm1.assignment.params.load_aeq_params()` — shared with the Cube demand bridge,
so both engines fold ride-hail and occupancy the same way. Highlights:

- `periods.capfac` — hours per period (Cube `HwyAssign.job capfac`).
- `transit_cost.assign_wait_perceive` / `skim_wait_perceive` — `iwaitfac`/`xwaitfac`.
- `transit_cost.assign_board_penalties`, `walk_board_penalties`, `drive_board_penalties` —
  escalating boarding penalties (perceived min).
- `transit_cost.spread_window` — Spiess-Florian frequency inflation that shrinks the
  attractive set toward the lines Cube's `COMBINE` would pool (parity knob; per-line-haul
  overrides under `linehauls:`).
- `highway.occupancy`, `highway.vot`, toll classes, PCE — the 13-class definitions.

To run a **variant** (e.g. a fare study) without editing the base file, point a scenario
at an alternate copy:

```yaml
simulate_activitysim:
  assignment:
    params: "path/to/aeq_params_farestudy.yaml"
```

### Engine (rare) — `src/tm1/assignment/aeq/`

Change engine behavior only when policy can't express it:

- **Add / change a highway class:** `classes.py` (`CLASS_ORDER` + `_class_spec`). The order
  is the demand/skim/highway contract — keep it aligned with the `.tpp`/OMX table order.
- **VDF / congestion:** `vdf.py` (`congested_time`) — Cube's facility-type volume-delay.
- **Transit graph / fares:** `transit.py` (graph construction, boarding layers),
  `fares.py` (XFARE / FAREMAT / farelinks parsing).
- **Skim assembly / OMX layout:** `transit_skims.py`, `runner.py`.

After any engine change, re-run the assignment validation scorecard (§6) — that is the
guard that keeps aeq ≡ Cube.

---

## 5. Cube → aeq translation guide

For analysts fluent in the Cube job stack:

| You knew (Cube) | It's now (aeq) |
|---|---|
| `HwyAssign.job` `pathload` class blocks | `classes.py CLASS_ORDER` (13 classes, same order) |
| `combine = equi` (equilibrium) | `equilibrium_assignment(algorithm="fw")` — Frank-Wolfe + exact Beckmann line search |
| Facility-type BPR/VDF lookups | `vdf.py congested_time` (same facility-type params) |
| `capfac`, VOT, op-cost, toll classes | `aeq_params.yaml highway:` block |
| `trips{P}.tpp` (person trips, SR divided in-job) | assembled to vehicle-class tables by `demand.assemble_demand` (SR ÷ occupancy) |
| `net2csv` link export | `highway_links.csv` (built once) |
| `TransitSkims.job` / `TransitAssign.job` | `transit_skims.py` / `transit.py` (Spiess-Florian) |
| `iwaitfac` / `xwaitfac` / boarding penalties | `aeq_params.yaml transit_cost:` |
| TRNBUILD `.lin` line file | `transitLines.lin` → `parse_lin` |
| `COMBINE` line pooling | S&F `spread_window` (attractive-set shaping) |
| `.far` fare files, FAREMAT | `fares/` → `fares.py` |
| Loaded network `avgload5period_vehclasses.csv` | aeq `flows[class]` per link (same row order) |
| `trnline.csv` / `trnlink.csv` | `boardings_by_line()` / `link_volumes()` |

**Mental model:** Cube's jobs are a script pipeline over shared binary matrices; aeq is a
Python library called once per iteration that keeps matrices in memory and writes only
`skims.omx`. The *numbers* are held to Cube within a fraction of a percent (see
[aequilibrae_migration.md](aequilibrae_migration.md)); the *interfaces* are the config
block (§3) and `aeq_params.yaml` (§4).

---

## 6. Verifying a change didn't drift from Cube

The invariant is **aeq ≡ Cube on identical demand**: feed Cube's *own* trip tables into aeq
and diff against Cube's loaded network. The demand is byte-identical (same `.tpp` matrices)
and the Cube side is already computed, so any difference is purely the engine. Rerun this
after any engine or `aeq_params.yaml` change — it is the guard that keeps aeq ≡ Cube.

Scripts live in `scripts/migration_validation/assignment/`:

```bash
# Highway: Cube trips{P}.tpp + nonres -> 13 classes (as HwyAssign folds them) ->
# Frank-Wolfe -> per-link vs avgload5period_vehclasses.csv (per class, PCE, by facility type)
python scripts/migration_validation/assignment/validate_highway_assignment.py --cores 16

# Transit: Cube trips{P}.tpp transit tables -> Spiess-Florian -> per-line boardings vs
# trnline.csv and per-link AB_VOL vs trnlink.csv
python scripts/migration_validation/assignment/validate_transit_assignment.py --threads 16

# Regenerate the migration-doc figures from the scorecards
python scripts/migration_validation/assignment/make_migration_figures.py
```

Each writes a scorecard CSV (`scorecard_hwy_assign.csv`, transit per-run-type) with
CUBE vol / aeq vol / %diff / correlation per class × period. **Targets:** highway PCE within
a few tenths of a percent (r ≥ 0.99), per-class within ~1–2%; transit boardings/link volumes
within a few percent at r ≥ 0.97. The expected *structural* difference to leave alone: Cube
reports the single best path (integer boardings), aeq reports the strategy-expected value
(fractional), so per-OD differs on the tail while per-line/per-link aggregates agree.

Current numbers are summarized in [aequilibrae_migration.md](aequilibrae_migration.md) §3.
