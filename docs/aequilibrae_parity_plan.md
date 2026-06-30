# AequilibraE functional-parity plan (Task 2)

**Goal.** Prove AequilibraE (open source) reproduces *everything* MTC Travel Model One's
Cube Voyager assignment does — same network + demand → matching link volumes and skims —
and is **faster**, validated against the faithful Cube baseline built in Task 1.
Deliverable: a feature **parity matrix** + **performance report** for the team leads.

## The parity bar (what Cube does, established in Task 1)

- **Highway** — 13-class equilibrium assignment (drive-alone / shared-2 / shared-3+ ×
  free/toll, 2 truck classes × free/toll, 3 AV/TNC classes), Frank–Wolfe, relative gap
  5e-4. **Custom VDF** = `SpeedCapacity_1hour.block` lookup (Akcelik-style, *not* BPR).
  Bridge + value tolls; HOV/HOT/no-truck link exclusions (`excludegrp`); per-class
  generalized cost `time + (0.6/VOT)·(dist·opcost + toll)`; AV PCE. Produces loaded
  networks + ~793 skims (time/dist/btoll/vtoll per class × 5 periods).
- **Transit** — TRNBUILD optimal-strategy / hyperpath assignment, 15 tasks/period
  (access-egress × line-haul), fares + dwell → 18-mode × 5-period skims.

**Cube baseline validation (Task 1):** highway skims matched to ~0.2 min; full
converged HwyAssign reproduced reference link volumes to **VMT +0.63%, per-link
R² > 0.998**. This is the ground truth Task 2 is measured against.

## Phases

### Phase 0 — Code organization ✅ (done)
`src/tm1/assignment/` package split by engine so Cube and AequilibraE code stay separate:
```
src/tm1/assignment/
  cube/   runner.py · highway.py · transit.py     # faithful Cube backend (Task 1)
  aeq/    network.py · vdf.py · highway.py · transit.py   # AequilibraE (added Phase 3+)
```

### Phase 1 — Network import ✅ (prototyped)
Cube `net2csv` link export → AequilibraE graph (33,953 links, 12,267 nodes, 1,475
centroids). **Remaining:** export OT/fixed-time link times faithfully (currently
patched), and a node-coordinate export for skim geometry.

### Phase 2 — Single-class assignment ✅ (prototyped)
BFW equilibrium runs end-to-end (AM drive-alone, 31s). Uses BPR — *not yet* Cube's VDF.

### Phase 3 — Highway parity ← **the real work**
1. **Custom VDF** (top risk): read `SpeedCapacity_1hour.block` + `SpeedFlowCurve.block`;
   replicate Cube's congested-time curve in AequilibraE (fit per-capclass parameters or
   a custom delay function). *This is what makes volumes match.*
2. **Generalized cost per class** = `time + (0.6/VOT)·(dist·opcost + toll)` as the cost field.
3. **Multi-class (13) + exclusions** — `excludegrp` (HOV-only, value-toll, no-truck) via
   per-class link exclusion; class PCE.
4. **Validate** — same demand+network as Cube → link-volume RMSE / R² / %gap vs the
   Task-1 baseline (target R² > 0.99).
5. **Skims** — all highway skims via `compute_skims`; compare to Cube.
6. **Benchmark** runtime vs Cube's ~33 min converged run.

### Phase 4 — Transit parity (highest risk)
`.lin` line files → AequilibraE transit network; optimal-strategy assignment vs TRNBUILD;
fares; 18-mode skims. AequilibraE's transit module is GTFS-oriented — the make-or-break
question is whether it matches TRNBUILD's strategy assignment. Output: parity **or** an
honest gap analysis.

### Phase 5 — Synthesis
Formalize into `src/tm1/assignment/aeq/`; parity matrix; performance report; recommendation.

## Biggest risks (named up front)
1. **Custom VDF fidelity** — without matching Cube's speed-flow curve, volumes won't match.
   First concrete Phase-3 task.
2. **Transit strategy assignment** — AequilibraE may not reproduce TRNBUILD hyperpath/fares;
   the crux of "can it really replace Cube."
3. **Toll path-splitting** — Cube pre-splits free vs toll demand into separate classes.

## Next concrete step
Phase 3.1 — implement Cube's VDF in AequilibraE, re-run the single-class DA assignment
**with the real VDF**, and compare to a single-class Cube run. That one result tells us
whether volume parity is achievable before building the full 13-class model.
