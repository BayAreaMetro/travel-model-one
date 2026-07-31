# base_2023_activitysim_aeq

ActivitySim demand with **AequilibraE** assignment — the Cube-free closed loop.

```bash
tm1 run --scenario base_2023_activitysim_aeq
```

## What this is for

This scenario and [`base_2023_activitysim`](../base_2023_activitysim/) differ in
exactly one block: the assignment engine. Everything else — inputs, the synthetic
population, the ActivitySim config chain, the calibration submodels — is shared,
literally: `configs:` here points at the other scenario's directories rather than
copying them, so there is one definition of the demand model and no way for the two
to drift apart.

That makes the pair the engine comparison. Run both, compare loaded networks and
skims, and the only thing that changed is the solver.

| | demand | assignment | Cube licence |
|---|---|---|---|
| `base_2023_activitysim` | ActivitySim | Cube Voyager | required |
| `base_2023_activitysim_aeq` | ActivitySim | AequilibraE | not required |

## What it still needs from Cube

No Cube *licence*, but two artifacts from a completed Cube run:

- `network_csv` — the link table with capacities, free-flow speeds, tolls and
  per-class permissions
- `nonres_dir` — the frozen non-residential demand (internal/external, trucks, air
  passengers, HSR), which ActivitySim does not model

Phase 4 ports those four models to Python and removes the dependency. Until then
this is a Cube-licence-free loop, not a Cube-free one.

Transit level of service *is* Cube-free: set `transit_inputs_dir` to the output of
`scripts/build_aeq_inputs.py`, and transit skims are rebuilt each iteration from the
source network using this iteration's congested bus times. Omit it and the existing
transit matrices are preserved instead.

## Before the first run

1. Build the transit inputs once:
   ```bash
   python scripts/build_aeq_inputs.py --out E:/aeq_inputs
   ```
2. Point `reference_run`, `proj_dir` and `aeq_inputs` at your machine.

## Iterations

`iterations: 3` runs ActivitySim, then three rounds of assignment → ActivitySim.
Per-iteration provenance (`skims_iter{N}.omx`, `trips_{p}_iter{N}.omx`) is archived
under `{data_dir}/skim_archive/` so any round's inputs can be reconstructed; set
`archive: false` to turn that off.

Note the loop currently ends on a demand run whose trips are not assigned — see the
warning in `tm1/steps/simulate_activitysim.py`. That is a known divergence from the
CT-RAMP loop shape, deferred deliberately.
