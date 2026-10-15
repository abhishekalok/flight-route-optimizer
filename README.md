# Flight Route Optimizer

![CI](https://github.com/abhishekalok/flight-route-optimizer/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Tests: pytest](https://img.shields.io/badge/tests-pytest-brightgreen.svg)

A graph-based travel planner that finds the **cheapest** or **fastest** flight
paths between cities, built on a directed weighted graph with **Dijkstra's** and
**Bellman-Ford** algorithms.

Given a network of routes and fares, it answers questions like *"What is the
cheapest way to fly from Delhi to New York, and how much longer does it take
than the fastest route?"* — including itineraries that require one or more
connections.

---

## Highlights

- **Directed, weighted graph** — every city pair is stored as two independent
  legs (outbound and return differ in airline, fare and flight time), so the
  model matches how real flight networks behave.
- **Two algorithms, cross-checked** — Dijkstra solves both cost and duration
  weights; a hand-rolled Bellman-Ford independently verifies the result and
  scans for negative cycles.
- **Multi-stop itineraries** with a realistic **layover buffer** (default 90
  minutes per connection) added to the total travel time.
- **Constraint support** — cap the number of stops with `--max-stops` via a
  Dijkstra variant that searches over `(city, hops)` states.
- **Clean CLI** — query a route, compare cheapest vs fastest, inspect a city's
  routes, or list the network.

---

## Requirements

```
Python 3.10+
networkx
pandas
```

Install:

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
# cheapest route
python flight_route_optimizer.py route --from DEL --to JFK --by cost

# fastest route, at most one stop
python flight_route_optimizer.py route --from DEL --to JFK --by duration --max-stops 1

# cheapest vs fastest, side by side
python flight_route_optimizer.py compare --from DEL --to JFK

# verify Dijkstra against Bellman-Ford on the same query
python flight_route_optimizer.py algorithms --from DEL --to JFK

# explore the network
python flight_route_optimizer.py cities --search india
python flight_route_optimizer.py info --city BOM --top 8
```

### Options

| Flag | Applies to | Meaning |
|------|-----------|---------|
| `--from` / `--to` | route, compare, algorithms | City codes (e.g. `DEL`, `JFK`) |
| `--by` | route | `cost` or `duration` |
| `--max-stops` | route, compare | Maximum intermediate stops (default: unlimited) |
| `--layover` | route, compare | Minutes of ground time per connection (default: 90) |
| `--search` | cities | Filter by city code, name or country |
| `--data` | all | Path to an alternative `flights.csv` |

---

## Sample output

```
$ python flight_route_optimizer.py compare --from DEL --to JFK

  Comparing DEL -> JFK   (max-stops=None, layover=1h 30m)

  CHEAPEST
  ------------------------------------------------------------------
  LEG                       AIRLINE                 FARE    FLIGHT
  ------------------------------------------------------------------
  1. DEL -> DXB             United             INR 7,450    3h 17m
  2. DXB -> CAI             LATAM              INR 7,350    3h 48m
  3. CAI -> FRA             Turkish            INR 9,100    4h 18m
  4. FRA -> JFK             Turkish           INR 20,300    8h 19m
  ------------------------------------------------------------------
  Route        : DEL -> DXB -> CAI -> FRA -> JFK
  Stops        : 3 connection(s) between 4 leg(s)
  Total fare   : INR 44,200
  Flight time  : 19h 42m
  Layovers     : +4h 30m (3 x 1h 30m)
  Total time   : 24h 12m

  FASTEST
  ------------------------------------------------------------------
  LEG                       AIRLINE                 FARE    FLIGHT
  ------------------------------------------------------------------
  1. DEL -> JFK             BritishAirways    INR 95,300   13h 21m
  ------------------------------------------------------------------
  Total fare   : INR 95,300
  Total time   : 13h 21m

  ==================================================================
  Verdict: cheapest saves INR 51,100 but takes 10h 51m longer.
  ==================================================================
```

---

## How it works

**Graph model.** Each city is a node. Each scheduled leg is a directed edge
carrying three weights: `price`, `duration` and `distance`. When the same
directed pair appears more than once, the dominating (cheapest *and* fastest)
option is kept.

**Dijkstra.** The default solver for both objectives. Edge weights are all
non-negative, so Dijkstra is optimal and runs in `O(E log V)`.

**Bellman-Ford.** Implemented from scratch (relax all edges `V-1` times, then
run a final pass to detect negative cycles). It is used by the `algorithms`
command to confirm that Dijkstra's answer is correct. Because it tolerates
negative edges, the same code would catch a "fare arbitrage" cycle if the data
ever contained one.

**Constrained search.** `--max-stops` runs a Dijkstra variant over `(city, hops)`
states, so a hop limit is enforced exactly rather than by pruning after the
fact. Layover time is charged on each connection after the first, which is why
the reported total time is higher than the raw flight time.

---

## Dataset

Generated by `build_dataset.py` (deterministic, seed 42) and shipped as
`flights.csv`:

- **69 cities** across India, the Middle East, Europe, the Americas, Asia-Pacific
  and Africa.
- **538 directed legs** over **269 city-pairs**, operated by **20 airlines**.
- A **hub-and-spoke** topology: spokes connect to their nearest hubs, hubs link
  to each other, and nearby cities get regional short-haul routes.
- Fares and flight times are derived from real great-circle distances, so the
  numbers are physically plausible (fares INR 1,100 – 164,650).
- Twelve **premium ultra-long-haul nonstops** (e.g. DEL–JFK) are deliberately
  priced high and fast — these create genuine cases where the cheapest route
  needs a connection while the fastest is the pricey direct flight.

`cities.csv` holds the city metadata (name, country, region, coordinates) used
to enrich the CLI output.

To regenerate the data:

```bash
python build_dataset.py
```

---

## Files

| File | Purpose |
|------|---------|
| `flight_route_optimizer.py` | Graph engine, algorithms and CLI |
| `build_dataset.py` | Deterministic generator for the CSV data |
| `flights.csv` | Directed routes with airline, fare, duration, distance |
| `cities.csv` | City metadata |
| `requirements.txt` | Python dependencies |

---

## Notes and possible extensions

- All fares are in Indian rupees (INR) and durations in minutes.
- A natural next step is to model time-dependent layovers, multiple carriers
  per leg, or a `--avoid` flag for cities/airlines; the graph representation
  already supports them.

---

## Testing

```bash
pip install pytest
pytest -q
```

The suite checks the dataset invariants, confirms that Dijkstra and Bellman-Ford
agree on the optimal cost, verifies that `--max-stops` is honoured, and runs the
CLI end to end. CI runs it on Python 3.10, 3.11 and 3.12.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: fork, branch, add a test, run
`pytest -q`, and open a pull request.

---

## License

Released under the [MIT License](LICENSE).
