# Lottery datasets

Each product has its own CSV using the columns
`draw_code,draw_date,numbers,bonus`. Run `python3 crawl.py` to update all three.
Existing draws are not duplicated. See [crawler documentation](CRAWL.md).

Dates use ISO `YYYY-MM-DD`. Main numbers are separated by spaces; bonus numbers
are stored separately. New draws are appended, and the loader sorts by draw code.

## Dataset snapshot

The following counts describe the downloads on 2026-10-09:

| File | Records | Earliest date | Latest date | API kind |
| --- | --- | --- | --- | --- |
| `535.csv` | 926 | 2025-07-03 | 2026-10-08 | `ltoVM35` |
| `645.csv` | 1,564 | 2016-08-07 | 2026-10-07 | `ltoVM45` |
| `655.csv` | 1,399 | 2017-01-02 | 2026-10-08 | `ltoVM55` |

These dates and results reflect Lotto-8 data and have not been independently
verified against official Vietlott records. Downloads include API index 9 and
later records; indices 1 through 8 are outside the initial-download boundary.

The evaluation audit flags Power 6/55 record `20170102` as predating its
2017-08-01 launch, and excludes it from evaluation history and targets while
preserving the raw CSV. Mega 6/45 record `20190418` has an unusual weekday and
requires review; it is not automatically excluded. See [evaluation report](EVALUATION.md).

## Draw identifiers and number fields

For `535.csv`, `draw_code` comes from the draw label in the API's `date` field.
The initial dataset covers codes 9 through 934. Multiple draws can share a date,
so deduplication uses draw codes. `numbers` contains five values in 1..35, and
`bonus` contains the API's `sp` value in 1..12.

For `645.csv` and `655.csv`, `draw_code` is a synthetic date identifier in
`YYYYMMDD` format, not an official Vietlott draw code. These identifiers also
influence backtest seeds. Mega 6/45 stores six main numbers in 1..45 with an
empty bonus. Power 6/55 stores six main numbers in 1..55 and a separate `sp`
bonus in 1..55.

## Source and usage

The public API is
`https://www.lotto-8.com/Json_lto.asp?Lkind=KIND&Lindex=100000&Ldesc=desc`,
where `KIND` is listed in the snapshot table.

```bash
python3 crawl.py --products 535
python3 main.py predict --data databases/645.csv --product 645 --seed 42 --tickets 5
make predict PRODUCT=655
```
