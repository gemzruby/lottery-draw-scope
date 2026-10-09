# Lottery DrawScope

A Python tool for frequency-weighted lottery ticket generation, historical
statistics, and backtesting. Supports Lotto 5/35 (`535`), Mega 6/45 (`645`), and
Power 6/55 (`655`). Historical results are stored in `databases/`.

## Quick start

Requires Python 3.10+. The engine has no external Python dependencies.

```bash
make help
make crawl
make predict
make predict PRODUCT=535 SEED=123 TICKETS=10 WINDOW=60
make simulate PRODUCT=645 SAMPLES=1000
make stats PRODUCT=655
make backtest PRODUCT=645
make test
```

Defaults: `PRODUCT=645`, `SEED=42`, `TICKETS=5`, `WINDOW=60`.
Override the interpreter with `PYTHON=.venv/bin/python` when using a virtual environment.

You can also run commands directly:

```bash
python3 main.py predict --data databases/645.csv --product 645 --seed 42 --tickets 5
python3 main.py stats --data databases/645.csv --product 645 --window 60
python3 main.py backtest --data databases/645.csv --product 645 --window 60
python3 -m unittest discover -s tests -v
python3 crawl.py
```

Prediction requires `--seed`. Identical inputs and parameters produce identical
results. `--window` defaults to 60 draws; 0 uses all available history.
`--target-code CODE` limits prediction and statistics to draws with smaller codes.

The crawler updates all three CSV files, adding results that are not already
stored. Select a product with `python3 crawl.py --products 535`.

`make simulate` generates 1,000 sample tickets by default, ranks main and bonus
numbers separately, and returns a suggested combination of the highest ranked
numbers. Use `SAMPLES`, `SEED`, `PRODUCT`, and `WINDOW` to adjust the simulation.
These rankings measure engine sampling frequency, not winning probabilities.

To install the CLI in a virtual environment, run `python3 -m pip install -e .`,
then use `drawscope predict --data databases/645.csv --seed 42 --tickets 5`.

## Project layout

- `main.py`: ticket engine, CSV/SQLite loaders, statistics, backtesting, and CLI.
- `crawl.py`: incremental result updates from Lotto-8 for all three products.
- `databases/`: one CSV per product.
- `tests/`: engine and crawler tests.
- `docs/`: [algorithm](docs/ALGORITHM.md), [crawler](docs/CRAWL.md),
  and [datasets](docs/DATABASES.md).
- `Makefile`: command shortcuts.

CSV columns are `draw_code,draw_date,numbers,bonus`. Main numbers are separated
by spaces. Mega 6/45 has an empty bonus field. For 645/655, draw codes are
synthetic `YYYYMMDD` identifiers. For 535, codes come from the API's draw label,
allowing multiple draws on the same date.

## Limitations

Frequency-weighted generation does not establish better predictive performance.
Backtesting reports main-number matches; prize rules and ROI are not implemented.
The engine has not been compared ticket by ticket with the original LottoForecast
application. The project implements an offline engine; server algorithms are
outside its scope.
