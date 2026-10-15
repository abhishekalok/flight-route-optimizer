# Contributing

Thanks for your interest in improving the Flight Route Optimizer. This is a
small, focused project, so the process is light.

## Getting set up

```bash
git clone https://github.com/abhishekalok/flight-route-optimizer.git
cd flight-route-optimizer

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install pytest
```

## Running the tests

```bash
pytest -q
```

Please make sure the suite passes before opening a pull request. CI runs the
same tests on Python 3.10, 3.11 and 3.12.

## Regenerating the dataset

`flights.csv` and `cities.csv` are produced deterministically by
`build_dataset.py` (seeded, so results are reproducible):

```bash
python build_dataset.py
```

If you change the generator, regenerate the CSVs in the same commit so the data
and the code stay in sync.

## Guidelines

- Keep the code dependency-light — standard library plus `networkx` and `pandas`.
- Add or update a test for any behavioural change.
- Match the existing style: type hints where useful, short docstrings, and clear
  commit messages (imperative mood, e.g. "Add --avoid flag").
- One logical change per pull request.

## Reporting issues

Open an issue with the exact command you ran, what you expected, and what
happened instead. Paste the full output — it makes problems much faster to
reproduce.
