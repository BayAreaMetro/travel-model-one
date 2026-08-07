# Truck count locations → TM1 network links

Match observed count locations to model links, so counts can later be compared
against modelled volumes. Nothing here needs Cube, a licence, or a network
connection.

The only source wired up today is the Caltrans published truck-AADT book, but
the crosswalk itself is a property of a *location*, not of a publisher: another
source of counted truck volumes joins by supplying its own standardizer, and
everything downstream of `conflate.py` is unchanged.

This is separate from, and parallel to, the `src/data/observed/caltrans/`
pipeline, which processes the **2018 hourly class-count stations** — a different
set of locations from a different publication.

## Inputs

The model network is read straight from a Cube `.net` through `cubeio`, so
there is no export step and no Cube licence involved:

```
data/interim/cube_io/mtc_net/avgload5period.net
```

That file is `extractor/avgload5period.net` taken from
`2023_TM161_IPA_35.zip` — the base scenario the TM1.7 truck scenarios are built
from, on Box under `Development/Travel Model 1.7/2023_TM161_IPA_35/`. It is the
same network as the truck project's own `data/interim/cube_io/mtc_net/
mtc_links.shp`: identical link set, identical `FT` and `ROUTENUM`.

TM1.7 changes truck demand, not the network, so this crosswalk holds for every
TM1.7 scenario. Swapping in a scenario's own loaded network changes only the
volume shown in the reviewer, never the matching — `conflate.py` and
`network.py` do not read volume at all.

### Requires `cubeio`, which is not on this branch

`network.py` and `review/build_page.py` call `cubeio.read_net`. `cubeio` lives in
`src/cubeio/` on `phase-2-cubeio` ([PR #104](https://github.com/BayAreaMetro/travel-model-one/pull/104)),
which merges into `master` on its own track — so it is not here and will not be
until that track and this one meet.

Two files import it directly, but `conflate.py` imports `network`, so the reach
is wider than it looks:

| | needs `cubeio` |
|---|---|
| `standardize.py`, `paths.py` | no — step 1 runs as-is |
| `network.py`, `review/build_page.py` | yes, directly |
| `conflate.py`, `review/serve.py` | yes, through the two above |

`crosswalk.csv` itself is plain data and needs nothing at all, so the finished
deliverable stays readable either way.

To run the two that do need it, install `cubeio` from that branch. Nothing is
copied into this repo:

```bash
git worktree add ../tm1-cubeio phase-2-cubeio
uv pip install -e ../tm1-cubeio
```

`cubeio` imports nothing from the rest of that branch, so this pulls in the
readers and nothing else. Delete these steps once `src/cubeio/` arrives here.

> **Run this from the truck project's own venv**, built from
> `trucks_2026_update/pyproject.toml` — not from the `.venv` at the repo root.
> That one holds an editable install pointing at `<repo>/src`, which does not
> exist on this branch, so `import cubeio` there quietly resolves to an *empty
> namespace package*. It imports fine and then fails later with
> `AttributeError: module 'cubeio' has no attribute 'read_net'`, which looks
> like a broken reader rather than a missing one.

## The workflow

```
1  python standardize.py      Excel workbooks -> one long CSV
2  python conflate.py         locations -> crosswalk.csv, uncertain ones flagged
3  python review/serve.py     step through the flagged ones -> decisions.json
4  python conflate.py         re-run: your decisions merge into crosswalk.csv
```

**Steps 3 and 4 are a loop.** Review some, re-run, review more. Nothing is lost
between passes — the matcher re-derives everything from scratch each time, then
overlays your decisions on top, so re-running never reverts a call you made.

**Step 4 is not optional.** The reviewer saves to `decisions.json`; only
`conflate.py` writes `crosswalk.csv`. Until you re-run it, your decisions are
saved but not yet in the deliverable:

```
before re-run:  status=review    decision=''       links=5830-5794 5797-5838
after re-run:   status=reviewed  decision=accept   links=<your picks>
```

Every path is declared in `paths.py`. Everything lands in
`data/interim/observed_data/caltrans/truck_aadt_book/`:

| File | Written by | Contents |
|---|---|---|
| `crosswalk.csv` | `conflate.py` | **the deliverable** — one row per location · leg |
| `review.json` | `conflate.py` | same plus candidate geometry, read by the reviewer |
| `decisions.json` | the reviewer | your verdicts and link picks |
| `review.html` | the reviewer | the page itself, rebuilt when it goes stale |

Step 5 — joining counts by year and analysing them — is not built yet. It will
read `crosswalk.csv` and never re-do matching.

## Where it stands

380 Bay Area locations matched — 92% of those the model can carry — producing
503 crosswalk rows, since a location with both an A and a B leg yields two.

| | locations | crosswalk rows |
|---|---:|---:|
| confident | 206 | 246 |
| flagged for review | 157 | 237 |
| unmatched | 17 | 20 |
| **total** | **380** | **503** |

---

## 1. Standardize

Flattens one Caltrans workbook per year (two incompatible layouts) into
`caltrans_truck_aadt_2013_2024.csv`, joining the published point layer for
coordinates.

## 2. Conflate

**Year-free by design.** Count locations barely move — 90% of Bay Area location
keys appear in all twelve report years, and only three named places ever
changed postmile — so the crosswalk is a property of the *location*. Years are
a later join onto it.

`network.py` holds the network side only: loading links and reducing each state
route to its through corridor. It knows nothing about counts.

### What a match is

A Caltrans count is a **two-way volume**, and the model spreads that traffic
across a corridor cross-section — one directed chain per carriageway, plus
separate managed-lane chains. So a match is a *set* of links: usually two, four
where HOV lanes run alongside. On I-80 at Appian Way the nearest single link
carries under half the count.

A route is **not** one connected chain: each carriageway is its own, and
non-mainline stretches split what remains. US-101 arrives as 13 components
whose largest is 31% of the route. Every substantial component is kept; only
short orphan stubs are dropped — the remnants that sit closer to a junction
count than the mainline does.

### Model volumes never choose links

Selecting links by how well their volumes matched the counts would rig the
count-versus-model comparison this crosswalk feeds. Volume is used once, as the
`volume_implausible` flag: when assigned links' modelled volume is under 0.33×
or over 3× the counted volume, the location goes to review. That means either
the match is wrong or the model is wrong there, and both deserve a human.
Nothing is dropped or silently accepted on volume. The counted side is the
median across all years, so no report year is chosen.

### Why the legs are the hard part

Caltrans publishes up to two legs per location — `A` ahead (increasing
postmile) and `B` back — and **both carry the same coordinate**: every A/B pair
in this data is 0.0 m apart, while their volumes routinely differ (Concord at
Route 242: A=10,392 vs B=4,935). No amount of geocoding separates them. They
are split by which side of the corridor a link falls on, along a direction of
increasing postmile derived from the postmile-ordered sequence of count points,
never from assuming postmiles increase northbound or eastbound. `O` is a
location with no ahead/back split (county lines, inspection stations).

### Flags

| Flag | Meaning |
|---|---|
| `legs_collapse` | No model node at this junction, so the A/B split cannot be represented at all |
| `volume_implausible` | Modelled volume <0.33× or >3× the count — wrong links, or the model is off here |
| `far_from_corridor` | Nearest corridor link is beyond the node-snap distance |
| `wide_search` | Nothing within 400 m; found only on a widened search |
| `no_corridor_candidate` | No corridor link in range, usually outside the modelled area |
| `one_carriageway_leg_*` | Only one direction found where a two-way count needs both |
| `tie_leg_*` | Two links on the same side and carriageway within 40 m — geometry can't pick |
| `no_postmile_direction` | Too few locations on this route and county to derive a direction |
| `mixed_O_leg`, `X_leg` | Rare leg codes; four `A+O`/`B+O` locations exist statewide |

## 3. Review

`review/serve.py` builds the page if needed and opens it. It is standalone: it
reads `review.json` and the network, and knows nothing about how conflation ran.

Left pane is the queue, right is the corridor map. Numbered coloured links are
the candidates you can assign — blue runs with increasing postmile, orange
against, dashed means a parallel managed chain. Grey is the surrounding
network, drawn so you can tell what a place is: freeways heaviest with width
tracking lanes, arterials medium, ramps and connectors thin and dashed. Hover
any grey link for its route, facility type, and lanes.

`J`/`K` move, `1`–`9` toggle a link into the active leg, `A`/`E`/`X` accept /
mark edited / reject. A guide opens on first use; `?` reopens it.

Decisions autosave to `decisions.json` — commit it, diff it, hand it over.
Opening `review.html` directly also works, but decisions then live in browser
storage and the header says so; **Export** is the durable copy in that mode and
**Import** reads it back.

Facility-type labels follow MTC's own
[`crosswalk_pems_to_TM.R`](../../../prepare-validation-data/crosswalk_pems_to_TM.R),
which does the same conflation for PeMS. That script identifies HOV lanes via
`USECLASS` and on- vs off-ramps via `RAMP`; neither field exists in this
network's 216 link attributes, so HOV is inferred here from a short parallel
chain instead, and ramps are not split by direction.
