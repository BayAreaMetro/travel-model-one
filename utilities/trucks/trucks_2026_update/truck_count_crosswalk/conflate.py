"""Match Caltrans count locations onto TM1 model links, producing a crosswalk.

Step 2 of three: standardize -> **conflate** -> analysis.  This step is
deliberately year-free.  Count locations barely move -- 90% of Bay Area
location keys appear in all twelve report years and only three named places
ever changed postmile -- so the crosswalk is a property of the *location*, and
every year question is a downstream join onto it.

What a match is
---------------
A Caltrans count is a *two-way* volume.  The model spreads that same traffic
across a **corridor cross-section**: one directed link chain per carriageway,
plus separate managed-lane chains where they exist.  A match is therefore a
*set* of links, typically two (one per direction) and four where managed lanes
run alongside.  On I-80 at Appian Way the nearest single link carries under
half the count.

The ahead/back problem
----------------------
Caltrans publishes up to two legs per location: ``A`` ahead (increasing
postmile) and ``B`` back.  Both are published at the *same coordinate* -- every
A/B pair in this data is 0.0 m apart -- yet their volumes routinely differ
because a junction sits between them (Concord at Route 242: A=10,392 vs
B=4,935).  Geometry alone cannot separate them.  They are split by which side
of the corridor a link falls on, along a direction of increasing postmile
derived from the postmile-ordered sequence of count points, never from assuming
postmiles increase northbound or eastbound.  ``O`` is a location with no
ahead/back split; ``X`` is rare and always reviewed.

How a location is matched
-------------------------
Automatic matching is purely geometric and runs the same five steps for every
location.  Each step's threshold is a named constant below, so the rules can be
read off in one place rather than inferred from behaviour.

0. **Is it in scope at all?**  A location whose ``route`` no model link carries
   is ``no_model_route``; one lying more than ``FAR_FROM_MODEL`` (5 km) from
   that route's corridor is ``off_network``.  Both are carried through
   unmatched, with the reason recorded, and stay assignable by hand.

1. **Build the route corridor** (``network.py``).  Route-numbered links whose
   facility type is mainline (freeway, expressway, arterial, managed freeway,
   and collector -- rural state highways are coded as collectors).  Ramps and
   freeway-to-freeway connectors are excluded: they carry the route number but
   are not the through route, and sit closer to an interchange count than the
   mainline does.  The result is split into connected components; every
   component at least ``SUBSTANTIAL_CHAIN`` (2 km) long is kept, and shorter
   ones only if they run within ``PARALLEL_LATERAL`` (200 m) alongside one that
   was -- which is how a brief managed-lane chain stays in.

2. **Find the increasing-postmile direction**, from the postmile-ordered
   sequence of that route's count points.  Without it the ahead/back split
   cannot be made, so the location is flagged ``no_postmile_direction`` and the
   nearest link's own bearing is used as a fallback axis.

3. **Gather candidate links.**  A corridor link is a candidate when it lies
   within ``SEARCH_RADIUS`` (400 m) perpendicular of the count point *and* runs
   within ``BEARING_TOLERANCE`` (55 degrees) of the corridor axis or its
   reverse.  If nothing qualifies, the search is retried at ``WIDE_SEARCH``
   (1.2 km) and flagged ``wide_search`` -- a match a reviewer can see and reject
   beats a silent absence.

4. **Assign one link per carriageway.**  Candidates are grouped by carriageway,
   meaning the pair (which way the link runs, whether it belongs to a parallel
   managed chain).  Leg ``A`` takes the candidates lying ahead of the point
   along increasing postmile, ``B`` those lying back, ``O`` all of them; within
   each carriageway group the closest link wins.  That yields the two-to-four
   link cross-section a two-way count is spread across.

What forces a human decision
----------------------------
A location is ``confident`` when none of the following applies, ``review`` when
any does, and ``unmatched`` when step 3 found nothing at either radius:

``no_corridor_candidate``   nothing within 1.2 km of the corridor.
``far_from_corridor(Nm)``   nearest candidate further than ``NODE_SNAP``
                            (250 m) -- the point does not sit on this road.
``wide_search(Nm)``         only found by the widened search.
``one_carriageway_leg_L``   a leg drew links running in one direction only, so
                            the cross-section is half a two-way count.
``tie_leg_L(x vs y)``       two candidates on the same side and carriageway
                            within ``TIE_MARGIN`` (40 m) of each other -- the
                            geometry does not prefer either.
``no_postmile_direction``   step 2 failed; ahead/back may be reversed.
``mixed_O_leg``, ``X_leg``  leg codes that do not fit the A/B model.

``legs_share_links`` is recorded as a *note*, not a reason: when A and B resolve
to the same links the model simply has no node at that junction, and there is
nothing for a reviewer to choose.

Reviewed decisions overlay the automatic result rather than replacing this
logic: matching re-derives everything from scratch on every run, then applies
``decisions.json`` on top, so re-running never reverts a call made by hand.

Modelled volume plays no part
-----------------------------
Nothing here reads the model's assigned volumes -- not to choose a link, not
even to flag one.  Calibrating those volumes against the counts is the whole
point of the exercise downstream, so letting them influence which links a count
is tied to, however indirectly, would corrupt the answer before it is asked.
Matching is geometry and topology only.

Nothing is silently discarded
-----------------------------
Every located count location is carried through and reported, including the
ones no match was attempted for: a location whose route the model does not
carry, or one sitting too far from that route's corridor.  They appear in the
crosswalk with a status saying why, and on the review map, so a wrongly
discarded location can be seen and assigned by hand rather than vanishing.

Outputs
-------
``crosswalk.csv``   one row per location and leg.  ``count_location_id`` keys the
                    physical count location, ``link_ids`` holds the assigned model
                    links as space-separated ``A-B`` node pairs; both names match
                    the truck project's observed-data schema so the two join
                    directly.
``review.json``     the same plus candidate geometry, for the review tool.
"""

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import paths
import polars as pl
from network import NETWORK_CRS, Corridor, load_corridors
from pyproj import Transformer

COUNT_CRS = "EPSG:4326"  # counts are published in WGS 84

# Geometry thresholds, all metres.
SEARCH_RADIUS = 400.0  # corridor links this close to the point are candidates
WIDE_SEARCH = 1200.0  # retried radius when nothing is found at SEARCH_RADIUS
NODE_SNAP = 250.0  # a point this close to a corridor node sits "at" that node
BEARING_TOLERANCE = 55.0  # degrees a link may deviate from the corridor axis
TIE_MARGIN = 40.0  # same-side candidates this close together are a tie
FAR_FROM_MODEL = 5000.0  # counts beyond this from the route are outside the model

LEG_AHEAD, LEG_BACK, LEG_SINGLE = "A", "B", "O"

# Columns identifying one physical count location. Prefix and suffix are part of
# identity, not decoration: Route 35 in San Mateo carries R23.037, 23.037, and
# L23.037 at three different junctions.
LOCATION_KEY = (
    "route", "route_suffix", "district", "county",
    "postmile_prefix", "postmile", "postmile_suffix",
)


def _round(value: float | None) -> float | None:
    """Round a summary statistic, keeping ``None`` for a single-year series."""
    return None if value is None else round(value, 1)


def location_id(values: dict) -> str:
    """Build the stable identifier used by the crosswalk, decisions, and the page."""
    return "|".join(str(values.get(name) or "") for name in LOCATION_KEY)


@dataclass
class Candidate:
    """One corridor link considered for a count location."""

    link: object
    offset: float
    t: float
    along: float  # signed metres along increasing postmile, link midpoint vs point
    forward: bool  # runs in the increasing-postmile direction
    parallel: bool  # belongs to a parallel (managed/express) chain

    def as_dict(self) -> dict:
        return {
            "link": self.link.key, "a": self.link.a, "b": self.link.b,
            "routedir": self.link.routedir, "ft": self.link.ft, "lanes": self.link.lanes,
            "parallel": self.parallel, "offset_m": round(self.offset, 1),
            "t": round(self.t, 3), "along_m": round(self.along, 1),
            "forward": self.forward,
            "geometry": [
                [round(self.link.ax, 1), round(self.link.ay, 1)],
                [round(self.link.bx, 1), round(self.link.by, 1)],
            ],
        }


@dataclass
class Match:
    """The conflation outcome for one count location."""

    location: dict
    legs: dict
    assigned: dict = field(default_factory=dict)
    candidates: list = field(default_factory=list)
    reasons: list = field(default_factory=list)
    # Worth recording, but nothing a reviewer can act on, so it never queues.
    notes: list = field(default_factory=list)
    axis_bearing: float | None = None
    node_distance: float | None = None
    # Set when the location never reached matching at all.
    outside: str | None = None
    # Set only when a reviewed decision has been overlaid.
    decision: str | None = None
    note: str = ""
    resolved_reasons: list = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.decision == "reject":
            return "unmatched"
        if self.decision in {"accept", "edited"}:
            return "reviewed"
        if self.outside:
            return self.outside
        if not self.candidates:
            return "unmatched"
        return "review" if self.reasons else "confident"


def load_locations(counts_path: Path) -> tuple[int, int, pl.DataFrame, dict[str, dict]]:
    """Return ``(total rows, located rows, locations, legs)``.

    Years collapse here.  Each leg keeps the mean counted volume across every
    year it appears in and its standard deviation, so how much a location moves
    year to year is visible without opening the series.  A single-year leg has
    no deviation and reports ``None``.  The two row counts are returned so the
    coverage funnel can show what was dropped before locations were even formed.
    """
    raw = pl.read_csv(counts_path, infer_schema_length=20000)
    frame = raw.filter(pl.col("longitude").is_not_null() & pl.col("latitude").is_not_null())
    # Empty strings and nulls both occur in the key columns; make them one thing
    # so grouping and joining agree on what a location is.
    frame = frame.with_columns([
        pl.col(name).fill_null("")
        for name in ("route_suffix", "postmile_prefix", "postmile_suffix", "leg")
    ])
    transformer = Transformer.from_crs(COUNT_CRS, NETWORK_CRS, always_xy=True)
    x, y = transformer.transform(frame["longitude"].to_numpy(), frame["latitude"].to_numpy())
    frame = frame.with_columns(x=pl.Series(x), y=pl.Series(y))

    legs_by_location: dict[str, dict] = defaultdict(dict)
    grouped = frame.group_by([*LOCATION_KEY, "leg"]).agg([
        pl.col("vehicle_aadt").mean().alias("vehicle_mean"),
        pl.col("vehicle_aadt").std().alias("vehicle_sd"),
        pl.col("vehicle_aadt").median().alias("vehicle_median"),
        pl.col("truck_aadt").mean().alias("truck_mean"),
        pl.col("truck_aadt").std().alias("truck_sd"),
        pl.col("truck_aadt").median().alias("truck_median"),
        # The per-year values themselves, ordered by year, so the reviewer can
        # see the series rather than only its summary.
        pl.col("vehicle_aadt").sort_by("report_year").alias("vehicle_by_year"),
        pl.col("truck_aadt").sort_by("report_year").alias("truck_by_year"),
        # standardize.py flags suspect rows at the source; carry them through
        # rather than re-deriving a weaker version here.
        pl.col("quality_flags").sort_by("report_year").alias("flags_by_year"),
        pl.col("report_year").n_unique().alias("n_years"),
        pl.col("report_year").unique().sort().alias("years"),
    ])
    for row in grouped.iter_rows(named=True):
        legs_by_location[location_id(row)][row["leg"]] = {
            "vehicle_mean": _round(row["vehicle_mean"]),
            "vehicle_sd": _round(row["vehicle_sd"]),
            "vehicle_median": _round(row["vehicle_median"]),
            "truck_mean": _round(row["truck_mean"]),
            "truck_sd": _round(row["truck_sd"]),
            "truck_median": _round(row["truck_median"]),
            "vehicle_by_year": list(row["vehicle_by_year"]),
            "truck_by_year": list(row["truck_by_year"]),
            "flags_by_year": [f or "" for f in row["flags_by_year"]],
            "n_years": row["n_years"],
            "years": [int(year) for year in row["years"]],
        }

    # One row per location, described by its most recent appearance: Caltrans
    # re-types landmark names between years.
    locations = (
        frame.sort("report_year", descending=True)
        .unique(subset=[*LOCATION_KEY], keep="first")
    )
    return raw.height, frame.height, locations, legs_by_location


def postmile_bearings(locations: pl.DataFrame) -> dict[tuple, float]:
    """Derive the empirical bearing of increasing postmile at each location.

    Caltrans postmiles increase in a route's nominal direction and reset at each
    county line, so the direction is taken from the data itself: points on one
    route and county are ordered by postmile and each takes the bearing from its
    previous to its next neighbour.
    """
    bearings: dict[tuple, float] = {}
    for (route, county), group in locations.group_by(["route", "county"]):
        points = group.select(["postmile", "x", "y"]).unique(subset=["postmile"]).sort("postmile")
        if points.height < 2:
            continue
        postmiles = points["postmile"].to_list()
        xs, ys = points["x"].to_list(), points["y"].to_list()
        for index, postmile in enumerate(postmiles):
            low, high = max(0, index - 1), min(len(postmiles) - 1, index + 1)
            dx, dy = xs[high] - xs[low], ys[high] - ys[low]
            if low != high and (dx or dy):
                bearings[(route, county, float(postmile))] = (
                    math.degrees(math.atan2(dx, dy)) % 360.0
                )
    return bearings


def angular_difference(first: float, second: float) -> float:
    """Return the smallest absolute angle between two compass bearings."""
    return abs((first - second + 180.0) % 360.0 - 180.0)


def candidates_near(
    corridor: Corridor, px: float, py: float, axis: float, radius: float = SEARCH_RADIUS
) -> list[Candidate]:
    """Return corridor links near the point, oriented against the increasing-pm axis."""
    axis_radians = math.radians(axis)
    ux, uy = math.sin(axis_radians), math.cos(axis_radians)
    parallel_keys = {link.key for link in corridor.parallel}
    found = []
    for link in corridor.links:
        offset, t = link.project(px, py)
        if offset > radius:
            continue
        delta = angular_difference(link.bearing, axis)
        if min(delta, 180.0 - delta) > BEARING_TOLERANCE:
            continue
        mx, my = link.midpoint()
        found.append(
            Candidate(
                link=link, offset=offset, t=t,
                along=(mx - px) * ux + (my - py) * uy,
                forward=delta <= 90.0,
                parallel=link.key in parallel_keys,
            )
        )
    return sorted(found, key=lambda candidate: candidate.offset)


def carriageway(candidate: Candidate) -> tuple[bool, bool]:
    """Identify which physical carriageway a candidate belongs to."""
    return candidate.forward, candidate.parallel


def assign_legs(candidates: list[Candidate], legs: set[str]) -> dict[str, list[Candidate]]:
    """Choose the cross-section serving each published leg.

    Each carriageway present -- both directions, general-purpose and parallel
    managed chains -- contributes one link, because the count totals them all.
    ``A`` takes the links lying ahead of the point along increasing postmile and
    ``B`` those lying back; ``O`` takes whichever links straddle the point.
    """
    assignment: dict[str, list[Candidate]] = {}
    for leg in legs:
        if leg in {LEG_AHEAD, LEG_BACK}:
            want_ahead = leg == LEG_AHEAD
            side = [c for c in candidates if (c.along > 0) == want_ahead]
        else:
            side = candidates
        if not side:
            side = candidates
        best: dict[tuple, Candidate] = {}
        for candidate in side:
            group = carriageway(candidate)
            if group not in best or candidate.offset < best[group].offset:
                best[group] = candidate
        assignment[leg] = sorted(best.values(), key=lambda candidate: candidate.offset)
    return assignment


def classify(
    match: Match,
    candidates: list[Candidate],
    assignment: dict[str, list[Candidate]],
    legs: set[str],
) -> None:
    """Attach every reason this location needs a human decision."""
    if not candidates:
        match.reasons.append("no_corridor_candidate")
        return

    if candidates[0].offset > NODE_SNAP:
        match.reasons.append(f"far_from_corridor({candidates[0].offset:.0f}m)")

    # Whether the ahead/back split survived is answerable directly: did the two
    # legs end up with the same links?  The old proxy -- distance to the nearest
    # model node -- flagged 37 locations of which only 15 had actually collapsed.
    # And when they do collapse there is nothing to decide: the model simply has
    # no node at that junction, so it is recorded, not queued.
    if {LEG_AHEAD, LEG_BACK} <= legs:
        ahead = sorted(c.link.key for c in assignment.get(LEG_AHEAD, []))
        back = sorted(c.link.key for c in assignment.get(LEG_BACK, []))
        if ahead and ahead == back:
            match.notes.append("legs_share_links")

    # A two-way count needs both carriageways present.
    for leg, chosen in assignment.items():
        if len({candidate.forward for candidate in chosen}) < 2:
            match.reasons.append(f"one_carriageway_leg_{leg}")
            break

    # Near-tie between competing links on the same side and carriageway.
    for leg, chosen in assignment.items():
        want_ahead = leg == LEG_AHEAD
        side = [c for c in candidates if leg == LEG_SINGLE or (c.along > 0) == want_ahead]
        grouped: dict[tuple, list[Candidate]] = defaultdict(list)
        for candidate in side:
            grouped[carriageway(candidate)].append(candidate)
        for members in grouped.values():
            if len(members) < 2:
                continue
            ordered = sorted(members, key=lambda candidate: candidate.offset)
            if ordered[1].offset - ordered[0].offset < TIE_MARGIN:
                match.reasons.append(
                    f"tie_leg_{leg}({ordered[0].link.key} vs {ordered[1].link.key})"
                )
                break
        else:
            continue
        break

    if LEG_SINGLE in legs and legs != {LEG_SINGLE}:
        match.reasons.append("mixed_O_leg")
    if "X" in legs:
        match.reasons.append("X_leg")


def match_location(
    location: dict, legs: dict, corridor: Corridor, axis: float | None
) -> Match:
    """Conflate one physical count location onto the corridor."""
    match = Match(location=location, legs=legs)
    px, py = location["x"], location["y"]
    if axis is None:
        match.reasons.append("no_postmile_direction")
        nearest = min(corridor.links, key=lambda link: link.project(px, py)[0], default=None)
        if nearest is None:
            match.reasons.append("no_corridor_candidate")
            return match
        axis = nearest.bearing
    match.axis_bearing = round(axis, 1)

    candidates = candidates_near(corridor, px, py, axis)
    if not candidates:
        # Rather than drop the location, look further out and say so. A match a
        # reviewer can see and reject beats a silent absence from the table.
        candidates = candidates_near(corridor, px, py, axis, WIDE_SEARCH)
        if candidates:
            match.reasons.append(f"wide_search({candidates[0].offset:.0f}m)")
    match.candidates = [candidate.as_dict() for candidate in candidates]

    leg_names = set(legs)
    assignment = assign_legs(candidates, leg_names) if candidates else {}
    match.assigned = {
        leg: [candidate.link.key for candidate in chosen] for leg, chosen in assignment.items()
    }
    match.node_distance = round(corridor.nearest_node(px, py), 1)
    classify(match, candidates, assignment, leg_names)
    return match


def load_decisions(decisions_path: Path | None) -> dict[str, dict]:
    """Load reviewed decisions, keyed by :func:`location_id`."""
    if decisions_path is None or not decisions_path.is_file():
        return {}
    payload = json.loads(decisions_path.read_text(encoding="utf-8"))
    picks = dict(payload.get("picks") or {})
    verdicts = dict(payload.get("verdicts") or payload.get("decisions") or {})
    # An export carries a list of rows rather than an id-keyed object.
    if isinstance(payload.get("decisions"), list):
        verdicts = {}
        for row in payload["decisions"]:
            if row.get("verdict") in (None, "undecided"):
                continue
            key = row.get("id") or location_id(row)
            verdicts[key] = {"verdict": row["verdict"], "note": row.get("note", "")}
            if row.get("links_by_leg"):
                picks[key] = row["links_by_leg"]
    return {
        key: {
            "verdict": verdict.get("verdict"),
            "note": verdict.get("note", ""),
            "links_by_leg": picks.get(key, {}),
        }
        for key, verdict in verdicts.items()
    }


def apply_decision(match: Match, decision: dict) -> None:
    """Overlay one reviewed decision, so a re-run never reverts a human call."""
    match.decision = decision["verdict"]
    match.note = decision["note"]
    for leg, links in (decision["links_by_leg"] or {}).items():
        if leg in match.legs:
            match.assigned[leg] = list(links)
    if decision["verdict"] in {"accept", "edited"}:
        # The human settled it; drop the automatic doubts but keep them visible.
        match.resolved_reasons = list(match.reasons)
        match.reasons = []


@dataclass
class Stage:
    """One step of the funnel from raw count rows to matched locations."""

    label: str
    kept: int
    unit: str
    note: str = ""


def report_funnel(stages: list[Stage], output_dir: Path) -> None:
    """Print and save how the matched total was arrived at.

    A coverage number nobody can retrace is a number nobody should trust, so
    every filter between the raw CSV and the final count is named, with what it
    cost.
    """
    print("\ncoverage funnel")
    previous: Stage | None = None
    for stage in stages:
        # A drop is only meaningful between stages counting the same thing:
        # rows collapsing into locations is a change of unit, not a loss.
        lost = ""
        if previous is not None and previous.unit == stage.unit:
            lost = f"  -{previous.kept - stage.kept:,}"
        note = f"   {stage.note}" if stage.note else ""
        print(f"  {stage.label:<42} {stage.kept:6,} {stage.unit:<10}{lost:>9}{note}")
        previous = stage
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "coverage.csv"
    pl.DataFrame([
        {"step": index + 1, "stage": stage.label, "kept": stage.kept,
         "unit": stage.unit, "note": stage.note}
        for index, stage in enumerate(stages)
    ]).write_csv(path)
    print(f"  wrote {path}")


def conflate(
    counts_path: Path, network_path: Path, decisions_path: Path | None = None
) -> tuple[list[Match], list[Stage]]:
    """Match every count location onto the network, and record how many survived."""
    corridors = load_corridors(network_path)
    kept = sum(len(corridor.links) for corridor in corridors.values())
    dropped = sum(corridor.excluded for corridor in corridors.values())
    print(f"{len(corridors)} route corridors: {kept:,} links, {dropped:,} orphan stubs dropped")

    reviewed = load_decisions(decisions_path)
    if reviewed:
        print(f"{len(reviewed):,} reviewed decisions <- {decisions_path}")

    total_rows, located_rows, locations, legs_by_location = load_locations(counts_path)
    stages = [
        Stage("count rows in the standardized CSV", total_rows, "rows",
              "every district, every report year"),
        Stage("rows carrying a coordinate", located_rows, "rows",
              "the point layer is a single-year snapshot"),
        Stage("distinct physical locations", locations.height, "locations",
              "route/suffix/district/county/postmile/prefix/suffix"),
    ]

    on_route = locations.filter(pl.col("route").is_in(list(corridors)))
    stages.append(
        Stage("on a state route the model carries", on_route.height, "locations",
              "matched by ROUTENUM")
    )
    bearings = postmile_bearings(on_route)

    matches = []
    attempted = 0
    for row in locations.iter_rows(named=True):
        identifier = location_id(row)
        location = {
            "id": identifier, "route": row["route"], "district": row["district"],
            "county": row["county"], "route_suffix": row["route_suffix"],
            "postmile_prefix": row["postmile_prefix"], "postmile": row["postmile"],
            "postmile_suffix": row["postmile_suffix"], "postmile_raw": row["postmile_raw"],
            "description": row["description"],
            "longitude": row["longitude"], "latitude": row["latitude"],
            "x": round(row["x"], 1), "y": round(row["y"], 1),
        }
        legs = legs_by_location[identifier]
        corridor = corridors.get(row["route"])
        if corridor is None:
            # The model does not carry this route at all.
            match = Match(location=location, legs=legs, outside="no_model_route")
        elif corridor.nearest_node(row["x"], row["y"]) > FAR_FROM_MODEL:
            distance = corridor.nearest_node(row["x"], row["y"]) / 1000.0
            match = Match(location=location, legs=legs, outside="off_network")
            match.reasons.append(f"{distance:.1f} km from the nearest Route {row['route']} link")
        else:
            attempted += 1
            match = match_location(
                location, legs, corridor,
                bearings.get((row["route"], row["county"], row["postmile"])),
            )
        decision = reviewed.get(identifier)
        if decision:
            apply_decision(match, decision)
        matches.append(match)

    stages.append(
        Stage(f"within {FAR_FROM_MODEL / 1000:.0f} km of that route's corridor", attempted,
              "locations", "beyond this is outside the modelled area")
    )
    with_links = sum(1 for match in matches if match.candidates)
    stages.append(
        Stage("with at least one candidate link", with_links, "locations",
              "the rest are reported as unmatched")
    )
    districts = defaultdict(int)
    for match in matches:
        if not match.outside:
            districts[match.location["district"]] += 1
    spread = ", ".join(
        f"D{district}: {n}" for district, n in sorted(districts.items(), key=lambda kv: -kv[1])
    )
    # Not a filter: the model area is never selected on district, it just
    # happens to end a little past the District 4 boundary.
    stages.append(Stage("(districts represented)", len(districts), "districts", spread))
    return matches, stages


def write_outputs(matches: list[Match], output_dir: Path) -> None:
    """Write the crosswalk and the review payload."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for match in matches:
        location = match.location
        for leg, counts in sorted(match.legs.items()):
            links = match.assigned.get(leg, [])
            rows.append({
                # Column names follow the truck project's observed-data schema
                # (count_location_id, link_id) so this joins onto
                # caltrans_standardized_observed_aadtt.csv without translation.
                "count_location_id": location["id"], "route": location["route"],
                "county": location["county"], "postmile_raw": location["postmile_raw"],
                "description": location["description"], "leg": leg,
                "link_ids": " ".join(links), "n_links": len(links),
                "status": match.status, "flags": "; ".join(match.reasons),
                "notes_auto": "; ".join(match.notes),
                "decision": match.decision or "", "note": match.note,
                "resolved_flags": "; ".join(match.resolved_reasons),
                "count_vehicle_mean": counts["vehicle_mean"],
                "count_vehicle_sd": counts["vehicle_sd"],
                "count_vehicle_median": counts["vehicle_median"],
                "count_flagged_years": sum(1 for f in counts["flags_by_year"] if f),
                "count_truck_mean": counts["truck_mean"],
                "count_truck_sd": counts["truck_sd"],
                "count_truck_median": counts["truck_median"],
                "count_years": counts["n_years"],
                "longitude": location["longitude"], "latitude": location["latitude"],
            })
    crosswalk_path = output_dir / "crosswalk.csv"
    # Sparse columns are null for most rows, so let polars see
    # every row before deciding a type rather than inferring Null from the head.
    pl.DataFrame(rows, infer_schema_length=None).write_csv(crosswalk_path)

    review_path = output_dir / "review.json"
    review_path.write_text(
        json.dumps({
            "network_crs": NETWORK_CRS,
            "locations": [
                {
                    "location": match.location, "legs": match.legs,
                    "assigned": match.assigned, "candidates": match.candidates,
                    "reasons": match.reasons, "notes": match.notes,
                    "status": match.status,
                    "axis_bearing": match.axis_bearing, "node_distance": match.node_distance,
                    "decision": match.decision, "note": match.note,
                    "resolved_reasons": match.resolved_reasons,
                }
                for match in matches
            ],
        }),
        encoding="utf-8",
    )

    total = len(matches)
    counted: dict[str, int] = defaultdict(int)
    for match in matches:
        counted[match.status] += 1
    attempted = sum(
        counted[status] for status in ("reviewed", "confident", "review", "unmatched")
    )
    print(f"\nlocations: {total:,}   crosswalk rows: {len(rows):,}")
    print(f"  matching attempted on {attempted:,}")
    for status in ("reviewed", "confident", "review", "unmatched"):
        if counted[status]:
            print(f"    {status:<15} {counted[status]:,} ({counted[status] / attempted:.1%})")
    print("  no match attempted, carried through with a reason")
    for status in ("off_network", "no_model_route"):
        if counted[status]:
            print(f"    {status:<15} {counted[status]:,}")
    reason_counts: dict[str, int] = defaultdict(int)
    for match in matches:
        # Locations never matched carry a distance, not a flag.
        if match.outside:
            continue
        for reason in match.reasons:
            reason_counts[reason.split("(")[0]] += 1
    note_counts: dict[str, int] = defaultdict(int)
    for match in matches:
        for note in match.notes:
            note_counts[note] += 1
    if note_counts:
        print("\nnotes (recorded, not queued):")
        for note, count in sorted(note_counts.items(), key=lambda item: -item[1]):
            print(f"  {note:<28} {count:,}")
    if reason_counts:
        print("\nflags:")
        for reason, n in sorted(reason_counts.items(), key=lambda item: -item[1]):
            print(f"  {reason:<28} {n:,}")
    print(f"\nwrote {crosswalk_path}\nwrote {review_path}")


def main() -> None:
    """Parse arguments and build the crosswalk."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", type=Path, default=paths.COUNTS_CSV)
    parser.add_argument("--network", type=Path, default=paths.NETWORK)
    parser.add_argument("--output", type=Path, default=paths.OUT)
    parser.add_argument(
        "--decisions", type=Path, default=None,
        help="reviewed decisions to overlay; defaults to decisions.json beside the outputs",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    decisions = args.decisions or (output / "decisions.json")
    matches, stages = conflate(args.counts.resolve(), args.network.resolve(), decisions.resolve())
    write_outputs(matches, output)
    report_funnel(stages, output)


if __name__ == "__main__":
    main()
