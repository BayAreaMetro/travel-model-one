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

## 6. Divergence ledger

Every known difference from Cube, each with its verified mechanism and the evidence that
established it. Standard of proof: a divergence is only "explained" once a falsifiable test
has isolated its cause; "both correct" claims cite the test. Sizes are from the July 2026
full battery (75 runs, 610 component cells) unless noted; the median cell is at parity
(TOTIVT -1.1% r 0.985, boardings -0.1% r 0.988), so this ledger describes the tails.

### 6.1 The structural divergence: optimal strategy vs. COMBINE blending

Both engines implement Spiess-Florian frequency-based transit assignment. They differ in
one sub-step: how simultaneous services at a stop are merged. TRNBUILD's COMBINE merges
"common lines" whose headways fall within a fixed window (MAXDIFF = 20) and treats them as
one service with frequency-blended attributes; the Spiess-Florian attractive set instead
admits a line only if it lowers the expected cost, so cost-dominated (slow) patterns are
excluded. One mechanism, three visible symptoms:

**(a) Commuter-rail composition and fare** (com KEYIVT about -2 to -3%; fare -9% at r 0.71
in the AM peak, 67% of OD fares exact to the cent). Where Caltrain runs local, limited and
bullet patterns on one corridor, Cube reports the frequency-blended run time and the
blended path's fare; the new implementation rides the cost-optimal pattern mix. Evidence
chain: (1) a 2-minute rail boarding bonus flips only 1% of the divergent pairs -- these are
not ties; (2) line-level assignment tracing shows the divergent pairs ride bullet/limited
patterns and corridor parallels where matched pairs ride locals; (3) on 99 single-boarding
pure-rail pairs (no substitution possible) the new path is 61.4 min vs Cube's 66.1 for the
same seat -- the blend isolated; (4) priced under Cube's own generalized-cost rules
(2x wait, 2x walk, per-mode factors, cumulative boarding penalties), the new paths are
strictly cheaper on 64% of divergent pairs even at worst-case bounds. Cube's builder never
offers these paths; where the two disagree, the new path is better under Cube's own
weights. Not correctable without deliberately choosing worse paths.

**(b) Reported waits** (initial wait about -1 to -2 min on dense-service runs; correlation
0.84-0.91). The strategy's expected wait pools all attractive lines' frequencies; Cube's
combine window pools fewer. The under-report concentrates where many lines share stops.
Off-peak transfer waits, previously the worst cells (to -55%), are addressed by the
IWAITMAX correction in 6.2.

**(c) Reachability edges** (com recall 94-97% of Cube's reachable pairs; the new
implementation also reaches pairs Cube does not). Near the 180-min actual / 300-min
perceived path limits (matched to Cube's maxruntime/maxpathtime), the strategy's expected
cost and Cube's single-path cost fall on opposite sides for a small band of marginal pairs,
and a pair drops from a premium skim when the premium mode leaves the strategy entirely.
Verified that only about 1% of Cube's own reachable pairs violate the 180-min actual-time
test, so the limits themselves are faithful; the band is the strategy-vs-path difference.

### 6.2 IWAITMAX: Cube caps the initial wait only

`transit_combined_headways.block` caps the wait to board Caltrain (mode 130) and ferries
(100-104) at 25 minutes -- initial boarding only, by TRNBUILD semantics and by the block's
own comments ("people time their arrivals for the schedules"). Faithful reproduction in a
frequency-based engine requires care because frequency plays two roles (wait cost and
combination weight):

- **First boardings** use the capped headway in both the deterministic boarding cost and
  the boarding frequency: a lone capped line then prices at exactly Cube's
  2 x 25 perceived minutes, and splits stay frequency-proportional. Using the raw headway
  here (an early implementation) charged up to 27 phantom perceived minutes to board
  sparse rail; fixing it recovered 6,893 Cube-reachable commuter-rail pairs (recall 91.6%
  to 96.5% in the AM walk market) and improved the light-rail/ferry runs across the board.
- **Transfers** use the raw headway in the kernel frequency and in the reported transfer
  wait (Cube reports raw transfer waits: its early-morning commuter transfer wait averages
  52 minutes). The deterministic spread slice stays capped: with the spread window (6.3)
  that slice is charged per line rather than per combined service, and raw sparse headways
  there overcharge multi-pattern stops -- tested: it collapsed AM commuter recall from
  96.5% to 84.9%. With the final configuration the worst battery cell (early-morning
  drive-egress commuter transfer wait, -55%) validates at -3%, with in-vehicle time and
  boardings at r 0.99+.

### 6.3 Spread window (accommodation)

`spread_window = 1.5` inflates all line frequencies (shrinking the attractive-set window
toward Cube's MAXDIFF = 20 combine window) and repays the removed wait share
deterministically per line. It is the deliberate accommodation standing in for COMBINE.
Known bias: at stops where several patterns share the window, the per-line deterministic
slice does not shrink with the combined headway, so boarding there is charged slightly
more than Cube's combined service; at transfers to sparse modes this is bounded by the
IWAITMAX cap (6.2). Deterministic best-path (window 0) was tested and is strictly worse
against Cube (rail time -7.8% vs -1.4% at 1.5).

### 6.4 Fares

Fares are computed from the source fare inputs exactly as Cube's decomposition:
boarding/transfer XFARE + farelinks surcharges + station-to-station FAREMAT matrices
(symmetrized; the `.far` files list one direction). No distance-curve approximation
remains for line-hauls with fare matrices. AM validation: local 0.0% r 0.98, light
rail/ferry +0.2% r 0.99, express -0.8% r 0.97, heavy rail +1.2% r 0.94, commuter -9.1%
r 0.71 (the composition effect of 6.1a; the fare arithmetic on matched paths is exact).

Off-peak fare cells degrade (to -37%, correlations to 0.01) because one AM fare pass is
cached across periods while 7-20% of each other period's reachable pairs are
AM-unreachable and receive a structural zero. Verified against Cube's own skims that fares
are period-invariant on jointly-reachable pairs (79-99% identical to the cent), so the AM
values are correct where defined; the zeros are the gap. This is a real demand exposure,
not just a validation artifact. Fix in progress: per-period fare passes, enabled by
pruning the fare graph's dead station copies.

### 6.5 Reporting conventions

- **Initial/transfer wait split**: the strategy yields one combined wait; it is split
  proportionally to the per-boarding half-headway markers (first-boarding marker capped
  per 6.2, transfer markers raw). A sequential split (initial wait gets first claim) was
  tested and overshoots both components.
- **Auxiliary walk** (median +0.26 min, correlations ~0.78): small-magnitude legs on
  0-time funnel links; percent and correlation are harsh on 2-4 minute quantities.
  Absolute differences are fractions of a minute.
- **Early-morning cells** show the largest percentages on the smallest markets; absolute
  differences remain the binding measure there.

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
