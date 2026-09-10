"""Load the TM1 highway network and reduce each state route to its corridor.

This module knows nothing about counts.  It answers one question: for a given
state route number, which model links make up the through route, and which are
interchange stubs that only look like it?

A route is *not* one connected chain in this network.  Each carriageway is its
own chain sharing no nodes with the other, managed (HOV/express) lanes form
further chains, and every stretch coded as a non-mainline facility type splits
what remains again.  US-101 arrives as 13 components whose largest is 31% of
the route; Route 85 arrives as four near-equal quarters.  Any rule that keeps
"the largest component" therefore throws away most of the corridor.

Every component long enough to be real through-route is kept.  Only short
orphans are dropped -- the remnants that sit closer to a junction count than
the mainline does, which is how a 2-lane stub carrying 8k vehicles can beat the
6-lane mainline carrying 51k that sits 600 m further away.
"""

import math
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import cubeio

# The TM1 network is NAD83 / UTM zone 10N, in metres.
NETWORK_CRS = "EPSG:26910"

# Facility types a mainline state-route count can land on.  Collector (4) is in
# the list because that is how TM1 codes a rural two-lane state highway: 66% of
# Route 1 and 81% of Route 128 are collectors, and leaving them out put counts
# sitting *on* their own route tens of kilometres from anything the matcher
# could see.  Only route-numbered links are loaded at all, so the ~7,400
# unnumbered collectors -- ordinary residential streets -- never enter.
#
# Freeway-to-freeway connectors (1) and ramps (5) stay out: they carry route
# numbers but are not the through route, and they sit closer to an interchange
# count than the mainline does.
MAINLINE_FT = frozenset({2, 3, 4, 7, 8})

PARALLEL_LATERAL = 200.0  # metres: a chain this close alongside another is parallel
SUBSTANTIAL_CHAIN = 2000.0  # metres: a component this long is through-route, not a stub


@dataclass(frozen=True)
class Link:
    """One directed model link with its endpoint geometry."""

    a: int
    b: int
    route: int
    routedir: str
    ft: int
    lanes: int
    distance: float
    ax: float
    ay: float
    bx: float
    by: float

    @property
    def key(self) -> str:
        return f"{self.a}-{self.b}"

    @property
    def bearing(self) -> float:
        """Compass bearing from the A node to the B node, in degrees."""
        return math.degrees(math.atan2(self.bx - self.ax, self.by - self.ay)) % 360.0

    @property
    def length(self) -> float:
        return math.hypot(self.bx - self.ax, self.by - self.ay)

    def project(self, px: float, py: float) -> tuple[float, float]:
        """Return ``(offset, t)``: perpendicular distance and position along the link."""
        vx, vy = self.bx - self.ax, self.by - self.ay
        length_squared = vx * vx + vy * vy
        if length_squared == 0.0:
            return math.hypot(px - self.ax, py - self.ay), 0.0
        t = ((px - self.ax) * vx + (py - self.ay) * vy) / length_squared
        clamped = min(1.0, max(0.0, t))
        return math.hypot(self.ax + clamped * vx - px, self.ay + clamped * vy - py), t

    def midpoint(self) -> tuple[float, float]:
        return (self.ax + self.bx) / 2.0, (self.ay + self.by) / 2.0


@dataclass
class Corridor:
    """One route's through corridor: its main chains plus any parallel chains."""

    route: int
    main: list[Link]
    parallel: list[Link]
    excluded: int  # route links dropped as orphan stubs

    @property
    def links(self) -> list[Link]:
        return self.main + self.parallel

    def nodes(self) -> dict[int, tuple[float, float]]:
        points = {}
        for link in self.links:
            points[link.a] = (link.ax, link.ay)
            points[link.b] = (link.bx, link.by)
        return points

    def nearest_node(self, px: float, py: float) -> float:
        """Return the distance from a point to the closest corridor node."""
        return min(
            (math.hypot(x - px, y - py) for x, y in self.nodes().values()), default=math.inf
        )


def load_network(network_path: Path) -> dict[int, list[Link]]:
    """Load mainline route links indexed by route number.

    Reads a Cube Voyager ``.net`` directly through ``cubeio``, so the network
    needs no intermediate export and no Cube licence.  Nodes and links come
    from the same file, which is what guarantees they describe one network.
    """
    network = cubeio.read_net(network_path)
    coordinates = {node["N"]: (node["X"], node["Y"]) for node in network["nodes"]}
    by_route: dict[int, list[Link]] = defaultdict(list)
    for link in network["links"]:
        route, a, b = int(link["ROUTENUM"]), link["A"], link["B"]
        if route == 0 or int(link["FT"]) not in MAINLINE_FT:
            continue
        if a not in coordinates or b not in coordinates:
            continue
        ax, ay = coordinates[a]
        bx, by = coordinates[b]
        by_route[route].append(
            Link(a, b, route, str(link["ROUTEDIR"]).strip().strip("'"),
                 int(link["FT"]), int(link["LANES"]), float(link["DISTANCE"]),
                 ax, ay, bx, by)
        )
    return by_route


def connected_components(links: list[Link]) -> list[list[Link]]:
    """Split links into components connected through shared nodes."""
    adjacency: dict[int, list[int]] = defaultdict(list)
    at_node: dict[int, list[Link]] = defaultdict(list)
    for link in links:
        adjacency[link.a].append(link.b)
        adjacency[link.b].append(link.a)
        at_node[link.a].append(link)
        at_node[link.b].append(link)

    seen_nodes: set[int] = set()
    components = []
    for start in adjacency:
        if start in seen_nodes:
            continue
        group_nodes = {start}
        queue = deque([start])
        seen_nodes.add(start)
        while queue:
            node = queue.popleft()
            for neighbour in adjacency[node]:
                if neighbour not in seen_nodes:
                    seen_nodes.add(neighbour)
                    group_nodes.add(neighbour)
                    queue.append(neighbour)
        component = {link.key: link for node in group_nodes for link in at_node[node]}
        components.append(list(component.values()))
    return components


def lateral_distance(link: Link, reference: list[Link]) -> float:
    """Return how far a link's midpoint sits from the nearest reference link."""
    mx, my = link.midpoint()
    return min((other.project(mx, my)[0] for other in reference), default=math.inf)


def build_corridors(by_route: dict[int, list[Link]]) -> dict[int, Corridor]:
    """Reduce each route to its through corridor, dropping only orphan stubs."""
    corridors = {}
    for route, links in by_route.items():
        components = connected_components(links)
        if not components:
            continue
        components.sort(key=lambda group: sum(link.length for link in group), reverse=True)
        main: list[Link] = []
        parallel: list[Link] = []
        excluded = 0
        for component in components:
            if sum(link.length for link in component) >= SUBSTANTIAL_CHAIN:
                # Long enough to be through-route in its own right.
                (main if not main else parallel).extend(component)
                continue
            if not main:
                main.extend(component)
                continue
            # Short: keep it only if it runs alongside what we already have,
            # which is how a brief managed-lane or frontage chain appears.
            close = [link for link in component if lateral_distance(link, main) <= PARALLEL_LATERAL]
            if len(close) >= max(1, len(component) // 2):
                parallel.extend(component)
            else:
                excluded += len(component)
        corridors[route] = Corridor(route, main, parallel, excluded)
    return corridors


def load_corridors(network_path: Path) -> dict[int, Corridor]:
    """Load the network and build every route corridor in one call."""
    return build_corridors(load_network(network_path))
