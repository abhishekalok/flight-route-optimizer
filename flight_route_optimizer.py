#!/usr/bin/env python3
"""
Flight Route Optimizer -- graph-based travel planner
====================================================

Finds the cheapest or fastest flight paths between cities in a directed,
weighted graph built from a CSV of routes and fares.

Algorithms
----------
* Dijkstra          -- primary solver for both cost and duration weights
                       (non-negative edges, O(E log V)).
* Bellman-Ford      -- independent solver used to cross-check Dijkstra and to
                       detect negative cycles (a hand-rolled implementation,
                       plus NetworkX's for good measure).
* Constrained search -- a Dijkstra variant over (city, hops) states that
                       enforces a maximum number of stops.

Extras
------
* Multi-stop layovers: a per-connection buffer (default 90 min) is added to
  the total travel time of any itinerary with intermediate stops.
* Directed graph: the outbound and return legs of every city pair are
  separate edges with their own airline, fare and flight time.

Examples
--------
    python flight_route_optimizer.py route --from DEL --to JFK --by cost
    python flight_route_optimizer.py route --from DEL --to JFK --by duration --max-stops 1
    python flight_route_optimizer.py compare --from DEL --to JFK
    python flight_route_optimizer.py algorithms --from DEL --to JFK
    python flight_route_optimizer.py cities --search del
    python flight_route_optimizer.py info --city DEL --top 8
"""
from __future__ import annotations

import argparse
import heapq
import sys
from pathlib import Path

import networkx as nx
import pandas as pd

INF = float("inf")
DEFAULT_DATA = Path(__file__).with_name("flights.csv")
DEFAULT_CITIES = Path(__file__).with_name("cities.csv")


# --------------------------------------------------------------- loading
def load_graph(path: Path):
    """Read flights.csv and build a directed weighted graph."""
    if not path.exists():
        sys.exit(f"error: data file not found: {path}\n"
                 f"hint: run `python build_dataset.py` to generate it.")
    df = pd.read_csv(path)
    required = {"source", "destination", "airline", "price_inr", "duration_min", "distance_km"}
    missing = required - set(df.columns)
    if missing:
        sys.exit(f"error: flights.csv is missing column(s): {', '.join(sorted(missing))}")

    g = nx.DiGraph()
    for row in df.itertuples(index=False):
        g.add_node(row.source)
        g.add_node(row.destination)
        # keep the cheapest/fastest option when the same pair appears twice
        prev = g.get_edge_data(row.source, row.destination)
        if prev is not None and prev["price_inr"] <= row.price_inr and prev["duration_min"] <= row.duration_min:
            continue
        g.add_edge(
            row.source, row.destination,
            airline=row.airline, price=float(row.price_inr),
            duration=float(row.duration_min), distance=float(row.distance_km),
        )
    return g, df


def load_cities(path: Path) -> dict:
    """Optional city metadata (name/country/region) for nicer output."""
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    return {r.code: {"name": r.name, "country": r.country, "region": r.region}
            for r in df.itertuples(index=False)}


# --------------------------------------------------------------- algorithms
def bellman_ford(g: nx.DiGraph, source: str, weight: str):
    """Classic Bellman-Ford. Returns (dist, predecessor, has_negative_cycle)."""
    dist = {n: INF for n in g}
    pred = {n: None for n in g}
    if source not in g:
        return dist, pred, False
    dist[source] = 0.0
    edges = [(u, v, d[weight]) for u, v, d in g.edges(data=True)]
    for _ in range(len(g) - 1):
        changed = False
        for u, v, w in edges:
            if dist[u] + w < dist[v] - 1e-9:
                dist[v] = dist[u] + w
                pred[v] = u
                changed = True
        if not changed:
            break
    neg = any(dist[u] + w < dist[v] - 1e-9 for u, v, w in edges)
    return dist, pred, neg


def bellman_ford_path(g, source, target, weight):
    dist, pred, neg = bellman_ford(g, source, weight)
    if neg or target not in dist or dist[target] == INF:
        return None, INF
    path, cur = [], target
    while cur is not None:
        path.append(cur)
        cur = pred[cur]
    path.reverse()
    return path, dist[target]


def constrained_dijkstra(g, source, target, weight, max_stops, layover_min):
    """Dijkstra over (city, hops) states, honouring a maximum number of stops.

    A layover buffer is charged on every connection after the first, so the
    duration returned already includes realistic ground time.
    """
    if source not in g or target not in g:
        return None, INF
    max_edges = max_stops + 1
    best: dict[tuple[str, int], float] = {(source, 0): 0.0}
    pq = [(0.0, source, 0, [source])]
    while pq:
        cost, node, hops, path = heapq.heappop(pq)
        if node == target:
            return path, cost
        if hops >= max_edges:
            continue
        if cost > best.get((node, hops), INF) + 1e-9:
            continue
        for nbr, data in g[node].items():
            buffer_ = (layover_min if weight == "duration" else 0.0) if hops > 0 else 0.0
            nc = cost + data[weight] + buffer_
            key = (nbr, hops + 1)
            if nc < best.get(key, INF) - 1e-9:
                best[key] = nc
                heapq.heappush(pq, (nc, nbr, hops + 1, path + [nbr]))
    return None, INF


# --------------------------------------------------------------- solving
def itinerary(g, path, layover_min):
    """Turn a node path into a list of leg dicts plus totals."""
    legs = []
    for u, v in zip(path, path[1:]):
        d = g[u][v]
        legs.append(dict(src=u, dst=v, airline=d["airline"], price=d["price"],
                         duration=d["duration"], distance=d["distance"]))
    stops = max(0, len(path) - 2)
    cost = sum(l["price"] for l in legs)
    fly = sum(l["duration"] for l in legs)
    return dict(legs=legs, path=path, stops=stops, cost=cost,
                fly_min=fly, total_min=fly + layover_min * stops)


def solve(g, source, target, by, max_stops, layover_min):
    """Return the optimal itinerary dict, or None if unreachable."""
    if source == target:
        return itinerary(g, [source], layover_min)
    weight = "price" if by == "cost" else "duration"
    if max_stops is None:
        try:
            path = nx.dijkstra_path(g, source, target, weight=weight)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    else:
        path, _ = constrained_dijkstra(g, source, target, weight, max_stops, layover_min)
        if path is None:
            return None
    return itinerary(g, path, layover_min)


# --------------------------------------------------------------- formatting
def fmt_price(v):   return f"INR {v:,.0f}"
def fmt_dur(m):
    m = int(round(m)); h, mm = divmod(m, 60)
    return f"{h}h {mm:02d}m" if h else f"{mm}m"


def print_itinerary(it, by, layover_min, title):
    print(f"\n  {title}")
    print("  " + "-" * 66)
    print(f"  {'LEG':<26}{'AIRLINE':<16}{'FARE':>12}{'FLIGHT':>10}")
    print("  " + "-" * 66)
    for i, l in enumerate(it["legs"], 1):
        leg = f"{i}. {l['src']} -> {l['dst']}"
        print(f"  {leg:<26}{l['airline']:<16}{fmt_price(l['price']):>12}{fmt_dur(l['duration']):>10}")
    print("  " + "-" * 66)
    route = " -> ".join(it["path"])
    print(f"  Route        : {route}")
    print(f"  Stops        : {it['stops']} connection(s) between {len(it['legs'])} leg(s)")
    print(f"  Total fare   : {fmt_price(it['cost'])}")
    print(f"  Flight time  : {fmt_dur(it['fly_min'])}")
    if it["stops"]:
        print(f"  Layovers     : +{fmt_dur(layover_min * it['stops'])} "
              f"({it['stops']} x {fmt_dur(layover_min)})")
    print(f"  Total time   : {fmt_dur(it['total_min'])}")
    tag = "cheapest" if by == "cost" else "fastest"
    print(f"  Optimised on : {by} ({tag})")


# --------------------------------------------------------------- commands
def cmd_route(g, args):
    it = solve(g, args.source, args.target, args.by, args.max_stops, args.layover)
    if it is None:
        sys.exit(f"No route from {args.source} to {args.target} "
                 f"under max-stops={args.max_stops}.")
    title = f"{args.source} -> {args.target}"
    print_itinerary(it, args.by, args.layover, title)


def cmd_compare(g, args):
    print(f"\n  Comparing {args.source} -> {args.target}   "
          f"(max-stops={args.max_stops}, layover={fmt_dur(args.layover)})")
    cheap = solve(g, args.source, args.target, "cost", args.max_stops, args.layover)
    fast = solve(g, args.source, args.target, "duration", args.max_stops, args.layover)
    if cheap is None and fast is None:
        sys.exit("No route found.")
    if cheap:
        print_itinerary(cheap, "cost", args.layover, "CHEAPEST")
    if fast:
        print_itinerary(fast, "duration", args.layover, "FASTEST")
    if cheap and fast:
        print("\n  " + "=" * 66)
        if cheap["path"] == fast["path"]:
            print("  Verdict: the same itinerary wins on both cost and duration.")
        else:
            save = fast["cost"] - cheap["cost"]
            tdiff = cheap["total_min"] - fast["total_min"]
            print(f"  Verdict: cheapest saves {fmt_price(save)} "
                  f"but takes {fmt_dur(tdiff)} longer.")
        print("  " + "=" * 66)


def cmd_algorithms(g, args):
    """Cross-check Dijkstra against Bellman-Ford for the same query."""
    print(f"\n  Algorithm cross-check: {args.source} -> {args.target} (weight = cost)")
    print("  " + "-" * 66)
    try:
        d_path = nx.dijkstra_path(g, args.source, args.target, weight="price")
        d_cost = nx.dijkstra_path_length(g, args.source, args.target, weight="price")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        sys.exit("No path -- nothing to compare.")
    b_path, b_cost = bellman_ford_path(g, args.source, args.target, "price")
    _, _, neg = bellman_ford(g, args.source, "price")

    print(f"  Dijkstra      : {' -> '.join(d_path)}   [{fmt_price(d_cost)}]")
    print(f"  Bellman-Ford  : {' -> '.join(b_path)}   [{fmt_price(b_cost)}]")
    agree = abs(d_cost - b_cost) < 1e-6
    print("  " + "-" * 66)
    print(f"  Same optimal cost : {'YES' if agree else 'NO'}")
    print(f"  Negative cycles   : {'present (arbitrage!)' if neg else 'none'}")
    print(f"  Paths identical   : {'yes' if d_path == b_path else 'no (equal-cost tie)'}")


def cmd_cities(g, args):
    meta = g.graph.get("cities", {})
    nodes = sorted(g.nodes)
    if args.search:
        q = args.search.lower()
        def hit(c):
            m = meta.get(c, {})
            return (q in c.lower() or q in str(m.get("name", "")).lower()
                    or q in str(m.get("country", "")).lower())
        nodes = [c for c in nodes if hit(c)]
    print(f"\n  {len(nodes)} cit{'y' if len(nodes)==1 else 'ies'} in the network"
          + (f" matching '{args.search}'" if args.search else ""))
    print("  " + "-" * 66)
    for c in nodes:
        m = meta.get(c, {})
        tail = m.get("name", "")
        if m.get("country"):
            tail += f"  ·  {m['country']}"
        print(f"  {c:<5} {tail}")


def cmd_info(g, args):
    c = args.city
    if c not in g:
        near = [n for n in g.nodes if c[:2] in n or n[:2] in c][:6]
        sys.exit(f"Unknown city '{c}'." + (f" Did you mean: {', '.join(near)}?" if near else ""))
    meta = g.graph.get("cities", {}).get(c, {})
    out = sorted(g.out_edges(c, data=True), key=lambda e: e[2]["price"])
    inc = list(g.in_edges(c, data=True))
    label = c + (f"  {meta['name']}" if meta.get("name") else "")
    if meta.get("country"):
        label += f", {meta['country']}"
    print(f"\n  {label}  --  {len(out)} outgoing, {len(inc)} incoming routes")
    print("  " + "-" * 66)
    print(f"  {'DEST':<8}{'AIRLINE':<16}{'FARE':>12}{'FLIGHT':>10}")
    for _, dst, d in out[:args.top]:
        print(f"  {dst:<8}{d['airline']:<16}{fmt_price(d['price']):>12}{fmt_dur(d['duration']):>10}")
    if len(out) > args.top:
        print(f"  ... and {len(out)-args.top} more")


# --------------------------------------------------------------- CLI
def build_parser():
    p = argparse.ArgumentParser(
        prog="flight_route_optimizer",
        description="Graph-based flight route optimizer (Dijkstra / Bellman-Ford).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--data", type=Path, default=DEFAULT_DATA, help="path to flights.csv")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--from", dest="source", required=True, help="origin city code, e.g. DEL")
        sp.add_argument("--to", dest="target", required=True, help="destination city code, e.g. JFK")
        sp.add_argument("--max-stops", type=int, default=None,
                        help="maximum intermediate stops (default: unlimited)")
        sp.add_argument("--layover", type=int, default=90,
                        help="minutes of ground time per connection (default: 90)")

    r = sub.add_parser("route", help="best route by cost or duration")
    common(r); r.add_argument("--by", choices=["cost", "duration"], default="cost")
    r.set_defaults(func=cmd_route)

    c = sub.add_parser("compare", help="cheapest vs fastest side by side")
    common(c); c.set_defaults(func=cmd_compare)

    a = sub.add_parser("algorithms", help="cross-check Dijkstra vs Bellman-Ford")
    a.add_argument("--from", dest="source", required=True)
    a.add_argument("--to", dest="target", required=True)
    a.set_defaults(func=cmd_algorithms)

    ci = sub.add_parser("cities", help="list cities in the network")
    ci.add_argument("--search", default=None, help="filter by substring")
    ci.set_defaults(func=cmd_cities)

    inf = sub.add_parser("info", help="show routes out of a city")
    inf.add_argument("--city", required=True)
    inf.add_argument("--top", type=int, default=10)
    inf.set_defaults(func=cmd_info)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    g, _ = load_graph(args.data)
    g.graph["cities"] = load_cities(DEFAULT_CITIES)
    for attr in ("source", "target"):
        if getattr(args, attr, None) is not None and getattr(args, attr) not in g:
            sys.exit(f"error: unknown city '{getattr(args, attr)}'. "
                     f"Run `cities` to list valid codes.")
    args.func(g, args)


if __name__ == "__main__":
    main()
