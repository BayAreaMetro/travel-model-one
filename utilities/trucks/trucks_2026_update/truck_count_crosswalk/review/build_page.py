"""Build the self-contained conflation review page.

Takes the review payload written by ``conflate.py``, packs the whole network
alongside it, and injects both into ``page_template.html``.  The result is one
HTML file with no external requests, so it can be opened from disk, served by
``serve.py``, or published as an artifact.

The entire network ships once as parallel arrays -- cheaper than duplicating
each location's neighbourhood, and it lets the map zoom from one junction out
to the whole region.  Original node IDs travel with each link because the page
lets the reviewer assign *any* link, and a saved pick must carry the same
``A-B`` key the crosswalk uses.

Modelled 24-hour volume is read *here*, never in ``conflate.py``.  The matcher
must stay blind to it so the crosswalk cannot be tuned toward agreement, but a
reviewer comparing magnitudes can tell whether a counter is measuring one
carriageway or both -- which is a question about what the counter covers, not
about which answer is wanted.
"""

import argparse
import json
import sys
from pathlib import Path

import polars as pl

import cubeio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

TEMPLATE = Path(__file__).with_name("page_template.html")
PLACEHOLDER = "/*__REVIEW_DATA__*/"

# Facility types drawn on the map: freeway, expressway, arterial, managed
# freeway, plus ramps, connectors and collectors so interchanges and the street
# grid read correctly. Centroid connectors (6) are modelling artefacts, not
# roads, and are never drawn.
CONTEXT_FT = frozenset({1, 2, 3, 4, 5, 7, 8, 10})


def load_links(network_path: Path) -> list[tuple]:
    """Return drawable links as ``(a, b, ax, ay, bx, by, ft, lanes, route, volume)``.

    Read from the same ``.net`` ``network.py`` matches against, so the map the
    reviewer clicks on and the candidates the matcher offers cannot drift apart.
    """
    network = cubeio.read_net(network_path)
    coordinates = {node["N"]: (node["X"], node["Y"]) for node in network["nodes"]}
    out = []
    for link in network["links"]:
        a, b, ft = link["A"], link["B"], int(link["FT"])
        if ft not in CONTEXT_FT or a not in coordinates or b not in coordinates:
            continue
        ax, ay = coordinates[a]
        bx, by = coordinates[b]
        # Trucks here means large/combination (4+ axle): the only model class
        # whose definition matches what Caltrans counts as a truck.
        trucks = round(float(link["VOL24HR_HV"]) + float(link["VOL24HR_HVT"]))
        out.append((int(a), int(b), ax, ay, bx, by, ft, int(link["LANES"]),
                    int(link["ROUTENUM"]), str(link["ROUTEDIR"]).strip().strip("'"),
                    round(float(link["VOL24HR_TOT"])), trucks))
    return out


def pack_network(links: list[tuple]) -> dict:
    """Pack the network as parallel arrays with deduplicated node coordinates.

    ``ia``/``ib`` are the original model node numbers: the page reconstructs
    each link's ``A-B`` key from them so a hand-picked link saves in exactly
    the form ``conflate.py`` expects back.  Coordinates are metres rounded to
    integers, well inside the precision anything here needs.
    """
    index: dict[tuple[int, int], int] = {}
    xs: list[int] = []
    ys: list[int] = []

    def node_index(x: float, y: float) -> int:
        key = (int(round(x)), int(round(y)))
        found = index.get(key)
        if found is None:
            found = len(xs)
            index[key] = found
            xs.append(key[0])
            ys.append(key[1])
        return found

    packed = {"x": xs, "y": ys, "a": [], "b": [], "ia": [], "ib": [],
              "ft": [], "lanes": [], "route": [], "dir": [], "vol": [], "trk": []}
    for a, b, ax, ay, bx, by, ft, lanes, route, routedir, volume, trucks in links:
        packed["a"].append(node_index(ax, ay))
        packed["b"].append(node_index(bx, by))
        packed["ia"].append(a)
        packed["ib"].append(b)
        packed["ft"].append(ft)
        packed["lanes"].append(lanes)
        packed["route"].append(route)
        packed["dir"].append(routedir)
        packed["vol"].append(volume)
        packed["trk"].append(trucks)
    return packed


# Facility classes the volume gauge behaves differently on.
GAUGE_CLASS = {1: "freeway", 2: "freeway", 8: "freeway", 10: "freeway",
               3: "arterial", 7: "arterial", 4: "collector", 5: "ramp"}


def gauge_baselines(payload: dict, links: list[tuple]) -> dict:
    """Measure what model-over-count ratio actually looks like, per facility class.

    The gauge is only useful against its own baseline.  Modelled volume runs
    about three quarters of counted AADT on freeways, so reading a ratio as if
    1.00 were correct would call every good match low.  On rural collectors the
    model barely loads the road at all and the ratio carries no information,
    which is worth saying rather than leaving the reviewer to infer.
    """
    volume = {f"{link[0]}-{link[1]}": link[10] for link in links}
    facility = {f"{link[0]}-{link[1]}": link[6] for link in links}

    samples: dict[str, list[float]] = {}
    for location in payload["locations"]:
        if location["status"] not in ("confident", "review", "reviewed"):
            continue
        for leg, keys in location["assigned"].items():
            counted = (location["legs"].get(leg) or {}).get("vehicle_median")
            if not keys or not counted:
                continue
            modelled = sum(volume.get(key, 0) for key in keys)
            if not modelled:
                continue
            kinds = {GAUGE_CLASS.get(facility.get(key)) for key in keys}
            kind = kinds.pop() if len(kinds) == 1 else "mixed"
            samples.setdefault(kind or "mixed", []).append(modelled / counted)

    baselines = {}
    for kind, values in samples.items():
        values.sort()
        if len(values) < 8:
            continue
        baselines[kind] = {
            "median": round(values[len(values) // 2], 3),
            "low": round(values[len(values) // 4], 3),
            "high": round(values[3 * len(values) // 4], 3),
            "n": len(values),
        }
    return baselines


def load_coverage(conflation_dir: Path) -> list[dict]:
    """Read the funnel conflate.py wrote, for the header line and its hover."""
    path = conflation_dir / "coverage.csv"
    if not path.is_file():
        return []
    return pl.read_csv(path).to_dicts()


# The stable location identifier, exactly as conflate.py builds it.
LOCATION_KEY = ("route", "route_suffix", "district", "county",
                "postmile_prefix", "postmile", "postmile_suffix")


def pack_table(counts_path: Path, payload: dict) -> dict:
    """Pack the standardized count CSV as parallel arrays for the Data tab.

    ``loc`` carries each row's index into ``payload["locations"]`` (or -1), so
    a table row can jump straight to its location on the map.
    """
    frame = pl.read_csv(counts_path, infer_schema_length=20000)
    index = {loc["location"]["id"]: i for i, loc in enumerate(payload["locations"])}
    table = {"year": [], "route": [], "county": [], "pm": [], "leg": [], "desc": [],
             "veh": [], "trk": [], "ax2": [], "ax3": [], "ax4": [], "ax5": [],
             "flags": [], "loc": []}
    for row in frame.iter_rows(named=True):
        identifier = "|".join(str(row.get(k) or "") for k in LOCATION_KEY)
        table["year"].append(row["report_year"])
        table["route"].append(row["route"])
        table["county"].append(row["county"])
        table["pm"].append(row["postmile_raw"])
        table["leg"].append(row["leg"])
        table["desc"].append(row["description"])
        table["veh"].append(row["vehicle_aadt"])
        table["trk"].append(row["truck_aadt"])
        table["ax2"].append(row["truck_2_axle_aadt"])
        table["ax3"].append(row["truck_3_axle_aadt"])
        table["ax4"].append(row["truck_4_axle_aadt"])
        table["ax5"].append(row["truck_5_plus_axle_aadt"])
        table["flags"].append(row["quality_flags"] or "")
        table["loc"].append(index.get(identifier, -1))
    return table


def median(values: list) -> float | None:
    """Median of the non-null values, or ``None`` when there are none."""
    clean = sorted(v for v in values if v is not None)
    if not clean:
        return None
    mid = len(clean) // 2
    return clean[mid] if len(clean) % 2 else (clean[mid - 1] + clean[mid]) / 2


def pack_fit(counts_path: Path, payload: dict, links: list[tuple]) -> list[dict]:
    """One scatter point per matched location-leg: count median vs model total.

    ``trucks`` compares Caltrans 4-axle + 5-plus-axle against the model's
    large/combination class -- the one pairing whose definitions line up.
    ``vehicles`` compares total AADT against total loaded volume.
    """
    volume = {f"{link[0]}-{link[1]}": (link[10], link[11]) for link in links}
    frame = pl.read_csv(counts_path, infer_schema_length=20000)
    heavy: dict[tuple, list] = {}
    for row in frame.iter_rows(named=True):
        identifier = "|".join(str(row.get(k) or "") for k in LOCATION_KEY)
        ax4, ax5 = row["truck_4_axle_aadt"], row["truck_5_plus_axle_aadt"]
        value = (ax4 or 0) + (ax5 or 0) if not (ax4 is None and ax5 is None) else None
        heavy.setdefault((identifier, row["leg"]), []).append(value)

    points = []
    for i, loc in enumerate(payload["locations"]):
        if loc["status"] not in ("confident", "review", "reviewed"):
            continue
        for leg, keys in loc["assigned"].items():
            if not keys:
                continue
            model_veh = sum(volume.get(k, (0, 0))[0] for k in keys)
            model_trk = sum(volume.get(k, (0, 0))[1] for k in keys)
            count_hvy = median(heavy.get((loc["location"]["id"], leg), []))
            count_veh = (loc["legs"].get(leg) or {}).get("vehicle_median")
            points.append({
                "loc": i, "leg": leg,
                "cx_trk": count_hvy, "cy_trk": model_trk,
                "cx_veh": count_veh, "cy_veh": model_veh,
            })
    return points


def build(conflation_dir: Path, network_path: Path, output: Path) -> None:
    """Inject the review payload, network, and funnel into the page template."""
    payload = json.loads((conflation_dir / "review.json").read_text(encoding="utf-8"))
    links = load_links(network_path)
    payload["network"] = pack_network(links)
    payload["coverage"] = load_coverage(conflation_dir)
    payload["gauge"] = gauge_baselines(payload, links)
    payload["table"] = pack_table(paths.COUNTS_CSV, payload)
    payload["fit"] = pack_fit(paths.COUNTS_CSV, payload, links)
    print(f"{len(payload['table']['year']):,} count rows packed for the Data tab, "
          f"{len(payload['fit'])} points for the Fit tab")
    for kind, stats in sorted(payload["gauge"].items()):
        print(f"  gauge {kind:<10} median {stats['median']:.2f} "
              f"IQR {stats['low']:.2f}-{stats['high']:.2f}  (n={stats['n']})")
    print(f"{len(links):,} network links packed for the map")

    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        msg = f"Template {TEMPLATE} has no {PLACEHOLDER} placeholder"
        raise ValueError(msg)
    page = template.replace(PLACEHOLDER, json.dumps(payload, separators=(",", ":")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    size_mb = output.stat().st_size / 1_048_576
    print(f"{len(payload['locations']):,} locations -> {output} ({size_mb:.2f} MB)")


def main() -> None:
    """Parse arguments and build the page."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conflation", type=Path, default=paths.OUT)
    parser.add_argument("--network", type=Path, default=paths.NETWORK)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = args.output or (args.conflation / "review.html")
    build(args.conflation.resolve(), args.network.resolve(), output.resolve())


if __name__ == "__main__":
    main()
