# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-15

### Added

- Directed, weighted graph model of a 69-city flight network built from
  `flights.csv` (538 directed legs, 269 city-pairs, 20 airlines).
- Cheapest-route and fastest-route solving with **Dijkstra's algorithm**.
- An independent **Bellman-Ford** implementation used to cross-check Dijkstra
  and to detect negative cycles.
- A constrained Dijkstra variant over `(city, hops)` states supporting
  `--max-stops`.
- Multi-stop layover handling with a configurable per-connection buffer
  (default 90 minutes).
- Command-line interface with `route`, `compare`, `algorithms`, `cities` and
  `info` subcommands.
- Deterministic dataset generator (`build_dataset.py`) and city metadata
  (`cities.csv`).
- Test suite (`pytest`) and a GitHub Actions CI workflow.
- Documentation: `README.md` and `CONTRIBUTING.md`.

[Unreleased]: https://github.com/abhishekalok/flight-route-optimizer/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/abhishekalok/flight-route-optimizer/releases/tag/v1.0.0
