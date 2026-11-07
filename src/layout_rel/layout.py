"""Field geometry: wells, candidate manifold sites, host, and distances.

The field is stored as a NetworkX graph:
- nodes carry ``kind`` ("well", "site", "host") and ``pos`` (x, y) in metres;
- edges are the *candidate* connections with a ``length`` attribute in metres:
  every well to every manifold site, and every site to the host.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from .config import read_yaml


@dataclass
class Field:
    name: str
    graph: nx.Graph
    wells: list[str]
    sites: list[str]
    host: str

    def pos(self, node: str) -> tuple[float, float]:
        return self.graph.nodes[node]["pos"]

    def length(self, a: str, b: str) -> float:
        """Route length between two nodes [m]."""
        return self.graph.edges[a, b]["length"]


def _euclid(p: tuple[float, float], q: tuple[float, float]) -> float:
    return math.hypot(p[0] - q[0], p[1] - q[1])


def build_field(data: dict, length_factor: float = 1.0) -> Field:
    """Build a Field from a dict (same structure as the field YAML).

    ``length_factor`` scales straight-line distance to route length
    (1.0 = straight line).
    """
    g = nx.Graph()
    host = data["host"]["name"]
    g.add_node(host, kind="host", pos=(data["host"]["x"], data["host"]["y"]),
               host_type=data["host"].get("type", ""))
    wells = [w["name"] for w in data["wells"]]
    sites = [s["name"] for s in data["manifold_sites"]]
    for w in data["wells"]:
        g.add_node(w["name"], kind="well", pos=(w["x"], w["y"]))
    for s in data["manifold_sites"]:
        g.add_node(s["name"], kind="site", pos=(s["x"], s["y"]))

    for s in sites:
        for w in wells:
            d = _euclid(g.nodes[w]["pos"], g.nodes[s]["pos"]) * length_factor
            g.add_edge(w, s, kind="infield", length=d)
        d = _euclid(g.nodes[s]["pos"], g.nodes[host]["pos"]) * length_factor
        g.add_edge(s, host, kind="tieback", length=d)

    if len(set(wells + sites + [host])) != len(wells) + len(sites) + 1:
        raise ValueError("Node names must be unique")
    return Field(name=data.get("name", ""), graph=g, wells=wells,
                 sites=sites, host=host)


def load_field(path: str | Path, length_factor: float = 1.0) -> Field:
    return build_field(read_yaml(path), length_factor)
