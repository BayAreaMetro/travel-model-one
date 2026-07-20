# Network assignment: a primer

*For someone arriving cold: what assignment is, how Cube did it, how AequilibraE does it,
and how this repository puts the two together. Companion to
[`aequilibrae_migration.md`](aequilibrae_migration.md), which is the evidence that this
implementation reproduces Cube's. This file explains what is being reproduced.*

---

## 1. What assignment produces

Assignment is the supply half of the model. Demand (ActivitySim) decides who travels where,
when and by what mode; assignment routes those trips over the physical network and returns:

1. **A loaded network**: volumes per road link, boardings per transit line.
2. **Skims**: zone-by-zone matrices (1475 × 1475) of the *cost* of travelling between each
   origin and destination: time, distance, toll, wait, fare.

The skims are what close the loop. Mode and destination choice need travel costs, and those
costs depend on the choices:

```
        ┌──────────────── skims (travel costs) ────────────────┐
        ↓                                                      │
   ActivitySim  ──── trips ────►  Assignment  ──── loaded network
   (who/where/mode)               (what route)
```

Run to a fixed 3–4 iterations. This document is about the right-hand box, which resolves the
same circularity one level down (route choice against congestion) with **user equilibrium**
on the highway side and **optimal strategies** on the transit side.

---

## 2. Highway assignment

### The ingredients

- **Network**: ~34,000 directional links. Each carries a free-flow time, a distance, a
  capacity, a facility type (freeway / arterial / ramp / connector), an area type
  (downtown … rural), tolls, and use restrictions (HOV-only, no-trucks).
- **Demand**: origin–destination trip matrices, one per *vehicle class*.
- **A cost function**: what a traveller minimises.
- **A congestion function**: how travel time degrades as a link fills up.

### Vehicle classes (13 of them)

Demand is split into classes that are assigned *simultaneously but separately*. They share
the road (and congest each other) but each sees its own costs and its own restrictions.

| # | Class | Demand | VOT | PCE | Toll paid | Excluded from |
|---|---|---|---|---|---|---|
| 1 | `da` | drive alone | $15 | 1.0 | - | HOV lanes; priced express lanes |
| 2 | `sr2` | shared ride 2 (persons ÷ 2.0) | $15 | 1.0 | - | HOV3+ lanes; priced express lanes |
| 3 | `sr3` | shared ride 3+ (persons ÷ 3.25) | $15 | 1.0 | - | priced express lanes |
| 4 | `sml` | small truck | $30 | 1.0 | - | HOV lanes; priced express lanes |
| 5 | `lrg` | large truck | $30 | **2.0** | - | HOV lanes; truck-restricted links; priced express lanes |
| 6 | `datoll` | drive alone, tolled | $15 | 1.0 | full | HOV lanes |
| 7 | `sr2toll` | shared ride 2, tolled | $15 | 1.0 | ÷ 1.75 | HOV3+ lanes |
| 8 | `sr3toll` | shared ride 3+, tolled | $15 | 1.0 | ÷ 2.50 | - |
| 9 | `smltoll` | small truck, tolled | $30 | 1.0 | full | HOV lanes |
| 10 | `lrgtoll` | large truck, tolled | $30 | **2.0** | full | HOV lanes; truck-restricted links |
| 11–13 | `daav` `s2av` `s3av` | autonomous variants | $15 | 1.0 | - | as their human equivalents |

Three things distinguish a class:

- **Value of time** converts money into minutes. It is what decides whether a toll is worth
  paying. The shared-ride divisors (÷1.75, ÷2.50) are the toll *cost share*: the toll is
  split across occupants, so a carpool feels less of it per vehicle.
- **Where it may go.** The un-tolled classes are excluded from priced express lanes (they'd
  have to pay, so they must use their toll twin instead); trucks are excluded from
  truck-restricted links; everyone but carpools is excluded from HOV lanes. Cube calls these
  `excludegrp`. Here they are implemented by setting the link's cost to effectively
  infinite for that class.
- **How much road it takes.** A large truck counts as 2 passenger cars (its **PCE**) when
  measuring congestion, though only 1 vehicle when counting volumes.

Each class minimises **generalised cost**:

```
cost = congested_time + (0.6 / VOT) × (distance × operating_cost + toll)
```

The `0.6/VOT` factor converts cents to minutes (`60 min/hr ÷ 100 ¢/$ ÷ VOT $/hr`).

> **Where these numbers come from.** All of them are **ported from the legacy Cube scripts**,
> not fitted or chosen during this effort: `hwyParam.block` (values of time, occupancies, PCE, toll cost
> shares), `HwyAssign.job` (the class definitions, exclusion groups, generalised-cost
> formula, capacity factors), `SpeedFlowCurve.block` (the VDF curves below) and
> `FreeFlowSpeed.block` (critical speeds). Each sits in
> [`aeq_params.yaml`](../base-models/assignment/aeq_params.yaml) with its source file noted.
>
> What is *not* ported, and is therefore an assumption: (a) the **solver**, Frank–Wolfe
> with an exact line search, converged to a relative gap of 1e-3. Cube's own solver and
> stopping rule are different. What matches is its *result* (VMT within 0.1-0.2%), not its
> iteration path. (b) The AV
> classes carry **zero demand**, because this ActivitySim configuration folds TNC and AV
> trips into the drive-alone and shared-ride tables.

### The congestion function (VDF)

A *volume-delay function* maps how loaded a link is (`V/C`, volume over capacity) to how
slow it gets. MTC uses different curves for different roads:

- **Freeways**: a classic BPR curve: `time = free_flow × (1 + 0.20 × ((V/C) / 0.75)^6)`, time explodes when capacity is approached.
- **Arterials**: the Akcelik curve, which behaves better when *over* capacity (`V/C > 1`)
  because it models a queue draining over the period rather than returning nonsense.
- **Connectors**: fixed time. They are bookkeeping artefacts, not real roads.

→ `vdf.py`. Curve constants live in
[`base-models/assignment/aeq_params.yaml`](../base-models/assignment/aeq_params.yaml).

### Solving it: Frank–Wolfe
The standard algorithm:

1. *All-or-Nothing:* Find shortest paths using current travel times and assign all traffic to them.
2. *Direction Finding:* Subtract the current traffic flow from the all-or-nothing flow to find the updated direction.
3. *Line Search:* Compute optimal step size λ to shift traffic, update flows, and repeat until stable.

Choosing λ correctly (an exact line search on the Beckmann objective) is what makes this
converge. Convergence is measured by the **relative gap**: how much total travel time you
could save if everyone jumped to their current shortest path. Zero gap = perfect
equilibrium. The threshold here is 1e-3, typically 5 to 40 iterations per period.

→ `highway.py` (`equilibrium_assignment`, `_fw_step`).

### Periods and averaging

The day is split into five periods: EA, AM, MD, PM, EV. Each has
a *capacity factor* (AM = 4 hours' worth of capacity, EV = 8).

### Method of successive averages (MSA)
Skims are **not** built from the raw equilibrium of the current iteration.
They are built from a running average of volumes across the global feedback iterations. 
Without it the whole model oscillates where everyone piles
onto the road that was empty last iteration, then flees it.

 → `runner.py::_msa_average`.

### Output

For six skim classes (SOV, HOV2, HOV3 and their toll variants), skim time, distance and
bridge toll along the path that class actually chose; the three toll classes also skim
value toll. 21 matrices per period, **105 total**. 

→ `skim.py`.

---

## 3. Transit assignment

Transit uses a different algorithm from highway. Both tools implement the same
frequency-based framework (Spiess–Florian optimal strategies, 1989), but they are separate
implementations of it, and they differ in exactly two rules. Where the rules coincide, the
results reproduce: in-vehicle time within 1%, boardings within 0.1%, 64% of fares to the
cent. Where they do not, the results cannot match exactly — one of the two rules is bridged
by a calibrated parameter, not reproduced outright. Both rules are stated at the end of this
section.

### A passenger picks a set of lines, not a route

You are at a stop. Two buses go where you want: one every 10 minutes, one every 20. You board
whichever arrives first. You never "chose a route", and no shortest path describes what you
did.

So the algorithm does not look for a path. At every stop it picks the **set of lines worth
boarding** (the *attractive set*), and the passenger takes whichever of them shows up first.
That set, across the whole trip, is called a *hyperpath*.

If the attractive set at a stop has frequencies `f1 ... fn`:

```
expected wait   = 1 / (f1 + ... + fn)
chance of line i = fi / (f1 + ... + fn)
```

Two things follow, and both matter when reading model output:

**Frequencies add up.** Putting more lines at a stop shortens the wait for everyone who would
board them, even if the extra lines are slower. Four BART lines through the same tunnel, each
every 15 minutes, are a 3.75 minute service, not a 15 minute one.

**A strategy is a set, so reporting one number requires a choice.** The passenger may take
any line in the attractive set, so there is no single travel time or fare. Cube reports the
***best*** single path in the set; AequilibraE reports the ***probability-weighted
average*** across it. The skims show this directly: Cube's boardings are integers (1, 2, 3);
AequilibraE's are fractional (2.3). This is the second of the two implementation
differences stated at the end of this section.

### What the passenger minimizes

Not clock time, but *perceived* time. Waiting and walking feel worse than sitting on a train,
and every transfer adds a flat penalty on top:

```
perceived = in_vehicle x mode_factor
          + wait  x 2.0
          + walk  x 2.0
          + boarding_penalty (0, then 20, then 45 ... minutes, rising with each transfer)
```

`mode_factor` is how the model says riders prefer rail to bus: a minute on a local bus can
count as 1.5 minutes, a minute on commuter rail as 1.0.

### Line-haul skim sets

Cube does not produce one transit skim. It runs the whole assignment once per **tier** of
service, each time hiding the faster modes:

| Set | Modes allowed |
|---|---|
| `loc` | local bus only |
| `lrf` | + light rail, ferry |
| `exp` | + express bus |
| `hvy` | + heavy rail (BART) |
| `com` | + commuter rail (Caltrain) |

Each set answers "what is the best trip if this is the fanciest mode you will take". Mode
choice then picks between them, which is why `WALK_LOC` and `WALK_HVY` are separate modes in
ActivitySim. A sixth set, `trn`, allows everything and feeds the accessibility calculation.

Three access/egress combinations (walk-walk, drive-walk, walk-drive) x six sets x five
periods = **90 transit skims per iteration**, 750 output matrices.

### Cube & AequilibraE

Both tools implement the behavioral model above, and both must track the same journey state
to apply the rules: boardings so far, last operator, whether the last move was a walk. The
implementation difference is **where that state lives**, in the search state or in the graph.

* TRNBUILD was purpose-built for transit, with state tracking designed in: each partial
path in its search carries `{stop, cost, boardings, last operator, last move}`, and the
penalty and prohibition logic reads those fields at run time. 

* AequilibraE's solver is
general-purpose and does not track state: its inner loop carries `{node, cost}` and
nothing else, with no extra fields and no hook for custom rules. Adding state tracking
would mean modifying AequilibraE source.

That leaves two options:

1. **Modify the AequilibraE solver**: add the transit fields to its label and hard-code
   MTC's rules into its inner loop. This amounts to writing a private TRNBUILD.
2. **Move the state into the graph**: the solver sees only the node ID, so make the node ID
   carry the history. Each stop is duplicated once per journey state:

```
node = (stop, boardings so far, arrival type, last operator)
```

This implementation moves the state into the graph. The cost is memory, since duplicating
stops makes the graph larger, but the expansion is sparse: only states a passenger can
actually reach are built, and most combinations of stop and history are impossible, so the
graph stays small. In exchange the prebuilt graph is read-only and shared, so the 90 skim
runs parallelize freely across cores, while Cube dispatches TRNBUILD as a cluster of
single-threaded processes, one search running serially against its own private state.

Each history-dependent rule then becomes an ordinary edge cost between states ("the second
boarding costs 20 minutes" becomes "the edge from layer 1 to layer 2 costs 20 minutes").
This is *state-space expansion*: the bookkeeping TRNBUILD performs in engine memory at run
time, rebuilt as input data ahead of time. Both tools search the same expanded state space,
and rules expressed this way reproduce exactly.

The rules that need it:

| Rule | Required history |
|---|---|
| Boarding penalty rises with each transfer (0, 20, 45 min) | boardings so far |
| Certain walk sequences are prohibited (`transferprohibitors_*.block`) | how the stop was reached |
| Transfer fare depends on the previous operator (`xfare`) | last operator ridden |



-> `transit.py` (graph + solver), `transit_skims.py` (the 90-run battery), `fares.py`.

### Why the results do not match exactly

The graph controls everything outside the solver, and every rule expressed in it reproduces
exactly; components governed by those rules (in-vehicle time, boardings, walk times) match
Cube to within 1%. Two decisions are made *inside* the solver, beyond the graph's reach,
and the two tools make them differently. These are the only sources of disagreement.

**1. Which lines enter the pool.** Cube admits every line whose run time is within 20
minutes of the best (10 for commuter rail). Spiess–Florian admits a line only if boarding
it reduces the expected cost. Different pools give different waits, because the reported
wait is half the pooled headway. Replicating Cube's rule exactly would require modifying
the solver; instead the gap is bridged by the single calibrated parameter in the model,
`spread_window`, which controls how tightly the Spiess–Florian pool is drawn and is fitted
so that reported waits reproduce Cube's.

**2. Which number is reported.** A strategy is a set of lines, so a skim cell requires
reducing the set to one value. Cube reports the best single path; AequilibraE reports the
probability-weighted mean. They coincide only where one line is attractive. Fare shows the
consequence: fare is a step function of the boarding station, so a mean over two stations
falls between two tariffed values. 64% of fare pairs match Cube to the cent, and every
off-grid value lies between two adjacent fares.

Finally, Cube is closed source. Its internals cannot be inspected, so agreement is
demonstrated statistically against its outputs (the migration brief's scorecard), not
proven line by line.

### Assignment and skimming are not the same thing

Only one of them runs in the feedback loop:

* **Skimming** builds the zone-to-zone cost matrices that mode choice needs. Runs every
  iteration.
* **Assignment** loads passengers onto lines to get *boardings per line*. That is a reporting
  output, not something demand reads back. It is built and validated
  (`transit.py::assign_transit`, boardings within +0.1% of Cube, r = 0.98) but the loop does
  not currently call it.

---

## 4. How Cube does it

Cube Voyager is a licensed, closed, Windows desktop product. It is a **scripting
environment**, not a library: you write `.job` files in Cube's own language and run them.

```
HwyAssign.job          highway equilibrium
TransitSkims.job       the transit skim battery
TransitAssign.job      transit loading
*.block                include files holding the parameters
```

Key vocabulary, which is cryptic and appears throughout the code comments:

| Cube term | Means |
|---|---|
| `.net` | a network (links + nodes), binary |
| `.tpp` | a matrix file (skims, demand), binary |
| `.lin` | transit line file (ASCII): each line's stops, headway per period, mode |
| `pathload` | "assign this class along this cost" |
| `excludegrp` | links this class may not use |
| `modefac` / `skipmodes` | the per-mode perceived-time factors / which modes to hide |
| `boardpen` | boarding penalties |
| `COMBINE` / `MAXDIFF` | which lines pool into one service for the wait calculation |
| `IWAITMAX` | cap on the initial wait (so a 60-min Caltrain doesn't vanish from choice) |
| TRNBUILD | the transit engine inside Cube (it implements Spiess–Florian) |

Cube parallelises by launching a **cluster of single-threaded processes**. The transit skim
battery is dispatched to 15 of them, one per access × line-haul combination. It recomputes
*everything* on every iteration, including fares, which never change.

---

## 5. How AequilibraE does it

AequilibraE is an **open-source Python library** for the same computations. It is a library,
not a scripting environment: you build objects and call methods.

```python
graph  = Graph(...)              # links, costs, which nodes are centroids
graph.set_graph("cost")          # what to minimise
graph.set_skimming([...])        # what to accumulate along the path
TrafficAssignment(...).execute() # Frank-Wolfe / MSA / etc.
HyperpathGenerating(...)         # the Spiess-Florian transit solver
```

**What this provides:** an unlicensed, inspectable implementation that runs multi-threaded
within a single process and can be driven from ordinary Python. The latter is what permits
the fare pass to be computed once and cached, and the skims to be assembled with NumPy rather
than a proprietary matrix language.

**What it does not provide:** the model itself. AequilibraE supplies *algorithms*; it does
not supply MTC's conventions. The vehicle classes, VDF curves, mode factors, transfer
prohibitions and fare structures must all be re-expressed in the graph and cost vectors
handed to it. Doing that re-expression is what this codebase is.

One defect was identified and corrected upstream during this work: AequilibraE's transit
kernel sorted edges with a comparator that triggered worst-case behaviour in MSVC's
quicksort, degrading performance by roughly two orders of magnitude on Windows. The fix is
merged upstream (PR 806).

---

## 6. How this repository applies it

### The inputs

Everything is converted **once** from a reference Cube run (`scripts/build_aeq_inputs.py`)
into a self-contained input set, after which no Cube licence is needed:

| File | What it is |
|---|---|
| `highway_links.csv` | the road network: geometry, capacity, tolls, use codes |
| `transitLines.lin` | the transit lines: stops, headways, modes (Cube's own ASCII format) |
| `support_links.parquet` | walk/drive access, egress and transfer connectors |
| `link_distance.parquet` | link distances (for rail run-time distribution and fares) |
| `ref_ride_time.parquet` | fallback rail run times |
| `fares/*.far` | boarding, transfer, per-link and station-to-station fares |
| `nonres/*.tpp` | frozen non-residential demand (trucks, airport, external, HSR) |

Trips come from ActivitySim (`trips_{period}.omx`); everything else is static.

### The modules

```
runner.py          the iteration: orchestrates everything below
├── network.py     Cube link table  →  AequilibraE graph
├── demand.py      ActivitySim trips + frozen non-residential  →  13 vehicle-trip tables
├── classes.py     the 13 classes: VOT, tolls, exclusions, PCE
├── vdf.py         the congestion curves
├── highway.py     Frank-Wolfe user equilibrium
├── skim.py        highway level-of-service skims
├── transit_network.py   transitLines.lin  →  ride links at this iteration's bus speeds
├── transit.py     the Spiess-Florian graph (layers, states, fares) + solver + skims
├── transit_skims.py     drives the 90-run battery, caches the fare pass
├── fares.py       the fare model
└── params.py      loads all model policy from aeq_params.yaml
```

**No model policy lives in the code.** Every ported Cube constant (value of time, mode
factors, boarding penalties, VDF curves, fare bands) is in
[`base-models/assignment/aeq_params.yaml`](../base-models/assignment/aeq_params.yaml), with a
comment saying which Cube file it came from. The engine reads it at start-up. A scenario can
point at a different copy.

### One iteration, end to end

```
for each of the 5 periods:
    build graph  →  assemble demand  →  build 13 classes
    Frank-Wolfe to equilibrium (gap < 1e-3)
    MSA-average the volumes across iterations
    skim highway LOS from the averaged network
    derive bus in-vehicle times from the congested road times   ← the coupling
                                                                  buses feel traffic
transit:
    one-time exact-fare pass (cached: fares don't change with congestion)
    90 level-of-service skims from the source network at this iteration's bus speeds
write everything into skims.omx  →  ActivitySim reads it next iteration
```

**Timing** (48-core box): highway ~10 min, transit skims ~16 min, roughly 26 min per
iteration after a one-time ~7 min fare pass — against ~4 hr for the Cube equivalent, mostly
because the fare pass is computed once and cached rather than rebuilt every iteration.

### The output

A single `skims.omx` (~1.1 GB): 105 highway matrices + 750 transit + non-motorised, named
the way ActivitySim expects (`WLK_HVY_WLK_TOTIVT__AM`, `SOV_TIME__AM`, …). Per-iteration
copies are archived under `skim_archive/`.

---

## 7. Principal subtleties

The hard parts of matching Cube's results. Each is written up in full in the migration
brief's divergence ledger.

- **Cube and AequilibraE report different summaries of the same strategy.** Cube reports
  the single best path in it; AequilibraE reports the expectation, the average outcome a
  passenger following the strategy actually experiences over repeated trips. Neither is
  incorrect. Because fare is a step function of boarding station, an expectation taken over
  several boarding stations falls *between* two tariffed fares. This is a consequence of
  averaging, not a computational error.
- **The definition of waiting is a modelling choice.** Which lines contribute to a
  passenger's wait determines the reported wait time. Cube pools lines within 20 minutes of
  the best; Spiess–Florian pools by an optimality condition. Reconciling the two without
  distorting path choice is the hardest part of the transit code, and is what the one
  calibrated parameter in the model is for ([§3](#3-transit-assignment)).
- **Congestion couples the two networks.** Buses operate in mixed traffic, so transit skims
  depend on the highway assignment of the same iteration; rail does not.
- **Static quantities should not be recomputed.** Fares are independent of congestion.
  Exploiting this, by computing the fare pass once and caching it, accounts for most of the
  runtime advantage over Cube.

---

## 8. Glossary

| Term | Meaning |
|---|---|
| **TAZ / zone** | Traffic analysis zone; the model's unit of geography (1,475 here) |
| **Skim** | A zone-by-zone matrix of some travel cost (time, distance, fare, wait) |
| **OD pair** | An origin–destination pair; one cell of a skim |
| **Centroid / connector** | The fake node representing a zone, and the fake links tying it to the real network |
| **Assignment** | Loading trips onto a network to find routes and volumes |
| **User equilibrium** | The state where nobody can improve their own trip by switching routes |
| **Relative gap** | How far from equilibrium you are; the convergence measure |
| **VDF** | Volume-delay function: how travel time rises with load |
| **BPR / Akcelik** | The two VDF curve families used here (freeway / arterial) |
| **V/C** | Volume over capacity; the input to the VDF |
| **PCE** | Passenger-car equivalent; how much road a vehicle takes (a truck = 2) |
| **VOT** | Value of time; converts money to minutes |
| **Generalised cost** | Time + money-converted-to-time; what a traveller minimises |
| **All-or-nothing** | Putting all demand on the current shortest path (one Frank–Wolfe step) |
| **Frank–Wolfe** | The algorithm that finds user equilibrium |
| **MSA** | Method of successive averages; damps oscillation between iterations |
| **Line-haul** | The premium mode tier a transit trip uses (loc/lrf/exp/hvy/com) |
| **Headway** | Minutes between vehicles on a line; frequency is its reciprocal |
| **Hyperpath / strategy** | The set of lines a transit rider is willing to board, not a single route |
| **Spiess–Florian** | The optimal-strategy transit assignment algorithm |
| **Attractive set** | The lines a rider will actually board at a stop |
| **IVT / OVT** | In-vehicle time / out-of-vehicle time (wait + walk) |
| **Boarding penalty** | The perceived cost of a transfer, over and above its time |
| **TRNBUILD** | Cube's transit engine |
| **TPP** | Cube's binary matrix format |
| **OMX** | Open Matrix, the open format ActivitySim and AequilibraE use |

---

## 9. Where to go next

- [`aequilibrae_migration.md`](aequilibrae_migration.md): the evidence for how closely this
  reproduces Cube, where it differs, and why. Read its divergence ledger before trusting
  any single number.
- [`base-models/assignment/aeq_params.yaml`](../base-models/assignment/aeq_params.yaml):
  every model parameter, with the Cube file it came from. The best map of "what decisions
  does this model actually make".
- [`aequilibrae_usage.md`](aequilibrae_usage.md): how to run, configure, and modify the
  assignment/skimming track.
