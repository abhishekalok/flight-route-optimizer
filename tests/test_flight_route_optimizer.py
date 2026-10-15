"""
Test suite for the flight route optimizer.

Run with:  pytest -q
"""
import math
import subprocess
import sys

import networkx as nx
import pytest

from flight_route_optimizer import (
    DEFAULT_DATA,
    bellman_ford,
    bellman_ford_path,
    constrained_dijkstra,
    load_graph,
    solve,
)


@pytest.fixture(scope="module")
def graph():
    g, _ = load_graph(DEFAULT_DATA)
    return g


# --------------------------------------------------------------- dataset
def test_dataset_loads(graph):
    assert graph.number_of_nodes() >= 50, "expected 50+ cities"
    assert graph.number_of_edges() >= 300, "expected a dense route network"


def test_all_weights_non_negative(graph):
    # non-negativity is what makes Dijkstra valid here
    for _, _, d in graph.edges(data=True):
        assert d["price"] >= 0
        assert d["duration"] >= 0
        assert d["distance"] >= 0


def test_graph_is_directed(graph):
    assert graph.is_directed()


# --------------------------------------------------------------- algorithms
def test_dijkstra_matches_bellman_ford(graph):
    """The two independent solvers must agree on the optimal cost."""
    pairs = [("DEL", "JFK"), ("BOM", "SIN"), ("BLR", "LHR"), ("SIN", "SYD")]
    for s, t in pairs:
        d_cost = nx.dijkstra_path_length(graph, s, t, weight="price")
        _, b_cost = bellman_ford_path(graph, s, t, "price")
        assert math.isclose(d_cost, b_cost, rel_tol=1e-6), f"{s}->{t}"


def test_bellman_ford_detects_no_negative_cycle(graph):
    _, _, negative = bellman_ford(graph, "DEL", "price")
    assert negative is False


# --------------------------------------------------------------- routing
def test_every_leg_is_a_real_edge(graph):
    it = solve(graph, "DEL", "JFK", "cost", None, 90)
    assert it is not None
    for u, v in zip(it["path"], it["path"][1:]):
        assert graph.has_edge(u, v)


def test_max_stops_is_respected(graph):
    it = solve(graph, "DEL", "JFK", "cost", 1, 90)
    assert it is not None
    assert it["stops"] <= 1


def test_layovers_are_added_to_total_time(graph):
    it = solve(graph, "DEL", "JFK", "duration", None, 90)
    assert it["total_min"] >= it["fly_min"]
    assert it["total_min"] == pytest.approx(it["fly_min"] + 90 * it["stops"])


def test_cheapest_costs_no_more_than_fastest(graph):
    cheap = solve(graph, "DEL", "JFK", "cost", None, 90)
    fast = solve(graph, "DEL", "JFK", "duration", None, 90)
    assert cheap["cost"] <= fast["cost"] + 1e-6


def test_same_origin_and_destination_is_trivial(graph):
    it = solve(graph, "DEL", "DEL", "cost", None, 90)
    assert it["path"] == ["DEL"]
    assert it["cost"] == 0


def test_unreachable_city_returns_none(graph):
    assert solve(graph, "DEL", "ZZZ", "cost", None, 90) is None


def test_constrained_dijkstra_returns_valid_path(graph):
    path, cost = constrained_dijkstra(graph, "DEL", "JFK", "price", 2, 90)
    assert path is not None and path[0] == "DEL" and path[-1] == "JFK"
    assert len(path) - 2 <= 2
    assert cost > 0


# --------------------------------------------------------------- CLI
def test_cli_route_command_runs():
    script = DEFAULT_DATA.parent / "flight_route_optimizer.py"
    out = subprocess.run(
        [sys.executable, str(script), "route",
         "--from", "DEL", "--to", "JFK", "--by", "cost"],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    assert "DEL" in out.stdout and "JFK" in out.stdout
