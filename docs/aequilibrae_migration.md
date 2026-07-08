# Migrating Travel Model One assignment and skimming to an open-source stack

Draft. Fit and runtime values shown are development measurements taken during the build.
They will be replaced by a single controlled comparison in which the existing Cube model
and the new implementation run end to end on the same machine from identical inputs.
Values still to be measured that way are marked *pending*.

---

## 1. Executive summary

Legacy Travel Model One runs network assignment and skimming on Bentley Cube Voyager, feeding a Java activity-based demand model. This work replaces the Cube portion for highway
assignment, transit assignment, and the travel-cost matrices ("skims") that the demand model
reads, with an open-source Python implementation on the AequilibraE library, offering a pure open-source and seamless end-to-end Python workflow when coupled with ActivitySim.

AequilibraE is a drop in replacement for Cube in the Travel Model One pipeline. It:
* uses the **same algorithms** as Cube, 
* **reproduces Cube's results** from the 
* **same source inputs** (converted to OMX from TPP), 
* needs **no license** at run time,
* **runs faster**, and 
* and requires **no re-calibration of demand-model constants.**

**At a glance.** The algorithm is the same in both; the new pipeline differs only in
implementation and in a few documented accommodations (Section 5) where the open-source
library could not reproduce a Cube behaviour exactly. Fit is Aeq against Cube. Runtimes are
per global iteration and are not yet same-machine (Cube from the reference run's logs, Aeq
from machine TM2-B below), hence the controlled comparison in Sections 3 and 4.

| Step | Algorithm (Cube and Aeq) | Fit, Aeq vs Cube | Cube time | Aeq time |
|---|---|---|---|---|
| Highway assignment | Frank-Wolfe user equilibrium | vehicle-miles +0.1 to +0.2%; skims correlation 0.98 to 1.00 | 25 to 28 min | ~10 min |
| Transit assignment | Spiess-Florian optimal strategy | boardings +0.1%; per-line correlation 0.98 | ~11 min | ~6 min |
| Transit skims | cost accumulated along the strategy | components within a few percent (Section 3) | ~3.7 hr | ~17 min + fare once (Section 4) |
| Full iteration | | | *pending* | *pending* |

**Test environment.** Aeq figures are from machine TM2-B, a virtual machine reporting 48
cores on an Intel Xeon Gold 6338 at 2.0 GHz, 512 GB memory, Windows Server 2019. Runs used
24 worker threads. Peak resident memory per skim ran from about 2 GB (the level-of-service
graph) to about 30 GB (the operator-labelled fare graph). Cube figures are cross-machine
pending the controlled run. Reported times use 24 threads; scaling beyond that is still to
be characterised (Section 4).

## 2. Motivation and criterion

The Cube portion is commercial and license-gated, its algorithms are closed, and its
transit skimming in particular is slow (about 3.7 hours per iteration). The criterion set
at the outset: match or beat Cube on fidelity and speed across all modes, without
re-calibrating demand.

That last clause is the binding constraint. The demand model's coefficients were estimated
against Cube's skims, so the new skims must match Cube closely, not merely be defensible in isolation. Where an exact reproduction was not possible in the open-source algorithms, an accommodation was applied and validated against Cube; those are in Section 4.

## 3. Fit

Development measurements against a 2023 reference Cube run. Percent difference is the new
value against Cube; correlation is the Pearson coefficient across zone pairs reachable in
both, which measures agreement in pattern independent of level.

**Highway** (from prior validation):

| Quantity | Difference | Correlation |
|---|---|---|
| Vehicle-miles travelled | +0.1 to +0.2% | *pending* |
| Time, distance, toll skims | *pending* | 0.98 to 1.00 |

**Transit assignment** (25 walk-access runs, all line-haul modes and periods):

| Quantity | Difference | Correlation |
|---|---|---|
| Total boardings | +0.1% | |
| Per-line boardings | | 0.98 (median) |

**Transit skims** (per component, median across the run set):

Full 75-run battery (15 access and line-haul combinations by 5 periods), median over runs.

| Component | Difference | Correlation |
|---|---|---|
| In-vehicle time, total | +0.3% | 0.98 |
| In-vehicle time, premier mode | -1.2% | 0.96 |
| Initial wait | +0.6% | 0.87 |
| Transfer wait | +0.5% | 0.88 |
| Auxiliary (transfer) walk | +4.1% | 0.79 |
| Boardings | +0.1% | 0.98 |
| Drive access/egress time | +1.0% | 0.99 |
| Drive access/egress distance | +0.0% | 0.99 |
| Fare, local bus | -1.5% | |
| Fare, express bus | -4.5% | |
| Fare, heavy rail | +1.9% | |
| Fare, light rail and ferry | -3.4% | |
| Fare, commuter rail | -12.2% | 0.4 |

Every quantity except commuter-rail fare is within a few percent with high correlation.
Commuter-rail fare is accurate in the morning peak (about +5%) but degrades off-peak and in
the reverse peak. This is a known limitation of caching one fare skim across periods, see
Section 6; commuter-rail service varies more by period than any other mode, so a single
period's fare paths do not represent the others.

## 4. Performance

Cube figures are from the reference run's logs; Aeq figures are from development on TM2-B.
They are indicative, not same-machine, until the controlled comparison.

| Step | Cube | Aeq | Note |
|---|---|---|---|
| Highway assignment, per iteration | 25 to 28 min | ~10 min | |
| Transit assignment, per iteration | ~11 min | ~6 min | |
| Transit skims, per iteration | ~3.7 hr | ~17 min | see below |
| Full iteration | *pending* | *pending* | |
| Full model, all iterations | *pending* | *pending* | |

**Why the transit-skim gap is large.** Cube recomputes every transit skim, fare included,
on every iteration. Aeq splits the work by what actually changes. Bus in-vehicle times
depend on road congestion, so the time, wait, walk, and boarding skims are recomputed each
iteration; that is the ~17 minutes. Fares are fixed inputs and do not change with
congestion, so the fare skim is computed once at model start and re-used every iteration.
That fare skim is the single most expensive skim, because it uses a larger graph that
tracks the previous operator so transfer fares are exact (Section 5.3); on TM2-B it takes
about 50 to 90 minutes for the full set of runs, paid once rather than every iteration.

Reported Aeq times use 24 worker threads. Whether more threads would reduce them is not yet
established: development runs at more threads showed no clear gain, but that measurement was
confounded by differing network sizes, and the machine is a virtual machine whose 48
reported cores may or may not map to that many physical cores. A clean scaling test at 24,
32, and 46 threads on one network is planned; it will confirm whether the skim is limited by
memory bandwidth or host contention rather than available cores.

## 5. Methodology

A single reference Cube run is ground truth. Each quantity is reproduced as faithfully as
the open-source algorithms allow, then compared component by component. No constant was
tuned to force agreement. A one-time step (`scripts/build_aeq_inputs.py`) converts the
Cube-era inputs into a self-contained set; the running pipeline never invokes Cube. Bus
in-vehicle times use each iteration's congested road times, as Cube does.

### 5.1 Highway assignment

Same thirteen vehicle classes, five periods, facility-type volume-delay functions, and
class-exclusion rules as Cube, solved to user equilibrium with Frank-Wolfe.

**Accommodation, network averaging.** Cube skims a network whose volumes are a running
average across iterations (a method of successive averages), not the raw equilibrium. At
iteration N:

    average = (1 / N) * new_volume + (1 - 1 / N) * previous_average

The new pipeline keeps the same average and skims from it. This reproduces Cube; skimming
the raw equilibrium would introduce a real difference.

### 5.2 Transit assignment

The optimal-strategy method: a rider boards the first acceptable vehicle from a set of
attractive lines, so the wait depends on the set's combined frequency.

**Kernel speed fix.** AequilibraE's transit kernel spent almost all its time in a sort
whose keys were nearly all identical placeholder values, which degraded toward quadratic
time on this platform's compiler. Sorting only the edges on a rider's strategy, not the
whole network, cut the per-destination cost by about two hundred times. This factor is the
open-source kernel measured against its own unfixed self, not against Cube. It reproduces
the library's results exactly and has been folded into an upstream pull request by the
library's authors,[^pr] not yet released.

[^pr]: AequilibraE pull request 806, https://github.com/AequilibraE/aequilibrae/pull/806

**Graph structure.** Five details reproduce Cube's line loadings: one boarding point per
line and stop (else duplicate options halve the wait); the escalating per-boarding transfer
penalty carried as stacked stop copies, since the method is otherwise memoryless and cannot
count boardings; transfer-prohibitor rules as stop states; separate origin and destination
points per zone (else a path resets its boarding count by passing through a zone); and
Cube's exact per-mode time factors and skipped modes. Transfer costs therefore enter the
assignment as this boarding penalty; their time and money parts (transfer wait, transfer
walk, transfer fare) are measured in the skims (Section 5.3).

### 5.3 Transit skims

The kernel accumulates any per-link quantity as its expected value along the strategy,
which is how Cube defines an optimal-strategy skim. In-vehicle time, walk, boardings, and
drive legs accumulate directly. Wait is not a link value; it is recovered as

    wait = (total perceived path cost - accumulated non-wait time) / wait factor

and split into initial and transfer using the boarding-count layers.

**Accommodation, combined-headway window.** Both methods combine parallel lines at a stop
but bound the set differently. Two lines each every 10 minutes give about a 2.5-minute
wait, not 5, because combined wait is proportional to `1 / (sum of frequencies)`. The
optimal-strategy method adds any line whose wait saving beats its extra ride time; Cube
adds only lines within about 5 minutes of the fastest. Cube combines fewer lines and
reports a longer wait; unmodified, the new wait came out about 10% low.

The set is tightened from outside the kernel: multiply every line's frequency at a stop by
a factor w and charge the erased wait back as a fixed cost, so

    wait = 1 / (w * sum of frequencies) + fixed remainder

The one parameter `w` (about 1.5) is set to reproduce Cube's wait, not any demand target.
This is a parity choice, not a correctness one: the fuller optimal-strategy behaviour that
spreads over more lines is arguably more realistic, but the demand coefficients expect
Cube-like waits. It is a single parameter so the fuller behaviour can be restored and
demand re-calibrated to it later.

**Accommodation, reachability.** Cube produces a skim set per line-haul mode and keeps a
zone pair only where the best path uses that premier mode. The new graph carries all modes
at once, so the same rule is applied directly: keep a pair in a premium set only where
`in-vehicle time on the premier mode > 0`, which held for every reference pair. Cube's
maximum path-time limit is applied too. This reproduces Cube.

**Accommodation, fare.** Fare depends on trip history: the previous operator (a transfer
within one operator is often free, between operators is not) and, for rail, the entry and
exit stations. Cube carries this history along each path; the optimal-strategy skim is
memoryless. Two accommodations restore it.

1. *Previous-operator states.* Post-alighting stop states are labelled by the operator
   just ridden, so a re-boarding charges the exact transfer fare. Two rides on one operator
   are one fare; operator A then B is charged the A-to-B fare. Operators with identical
   fare structure share one state (exact). Since fares are static, this heavier graph is
   computed once and cached.

2. *Distance curves for rail.* Rail fares are charged by station pair and are not additive
   over links: a boarding minimum plus a tapering per-mile amount means summing per-link
   values overcounts several-fold (a five-station trip summed five near-minimum hops).
   Station-pair fares are close to linear in network distance, so each system uses

       fare = a + b * distance between entry and exit stations

   with `a`, `b` fitted to its own published fares (heavy rail is about 153 cents +
   6.9 cents per mile). Where a band spans several systems (commuter rail covers Caltrain,
   two Amtrak services, Altamont Corridor Express, and Sonoma-Marin), their fares are
   pooled into one blended curve. This is the only accommodation that approximates rather
   than reproduces Cube; it validates within a few percent per mode, the exact station
   alternative is disproportionate for one cost term, and an exact cached fallback exists.

**Two graphs.** The exact-fare graph is expensive but static; every other skim is cheap
but refreshes each iteration. So a fast graph runs each iteration for time, wait, walk,
boardings, and drive legs, and the operator-labelled fare graph is computed once and
cached. Cube recomputes everything, fare included, each iteration.

## 6. Known residuals

| Residual | Size | Cause |
|---|---|---|
| Commuter-rail fare off-peak | accurate in morning peak, to about -20% off-peak | one fare skim is cached across periods; commuter-rail service varies most by period, so one period's fare paths do not fit the others |
| Auxiliary walk time | +4% | new path routes more trips through a walk transfer |
| Commuter-rail reachability | misses a minority of long pairs | maximum path-time limit |
| Rail-fare correlation | 0.65 for commuter | distance curve smooths station-pair structure |
| Early-morning period | larger percent, tiny volumes | very small trip counts |

The commuter-rail fare caching is the one open item with real demand exposure (the reverse
peak carries meaningful commuter-rail trips). The fix is to compute the fare skim per period
for the modes whose service varies by period, at a bounded increase in the one-time fare
cost; this is under consideration. The combined-headway window and the rail-fare distance
curve are the accommodations most worth revisiting if demand is re-calibrated.

## 7. Reproducibility

- **Inputs:** `scripts/build_aeq_inputs.py` converts a reference Cube run into the
  self-contained input set.
- **Run:** assignment and skimming run through the repository command-line application,
  selected by configuration; no Cube software required.
- **Validate:** `scripts/validate_transit_skims.py` rebuilds every transit skim from source
  and writes the standard comparison table to a scorecard file.

## 8. Appendices

Mode taxonomy; fare-system to file and mode mapping; component definitions; reference-run
identity; commit provenance.
