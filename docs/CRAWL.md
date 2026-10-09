# Updating lottery history

```bash
python3 crawl.py
```

One run updates `databases/535.csv`, `databases/645.csv`, and `databases/655.csv`.
Select specific products or adjust the request delay:

```bash
python3 crawl.py --products 655
python3 crawl.py --products 535 645 655 --delay 0.2
```

## Update behavior

1. Request the API with `Lindex=100000` and take `max(dex)` as the latest index.
2. Retain the latest record from this discovery response, since subsequent API
   calls exclude the record at the cursor itself.
3. Query from the discovered index, then use the smallest returned `dex` as the
   next cursor.

For an empty dataset, batches are collected down to index 9, inclusive. Existing
datasets are updated until the fetched history overlaps the latest stored draw.
This also handles updates after a long interval without fetching the entire
history again.

New draws are appended without rewriting existing rows. If no results are new,
the CSV stays unchanged. The loader sorts draws by code, so physical CSV order
does not matter. Duplicate codes are compared; conflicting results cause an
error before writing. Missing records found in the fetched overlap are filled
using a temporary file and replacement.

All requests for a product must succeed before writing. Initial downloads use
a temporary file and replacement. Each product is updated independently.

## API and fields

```text
POST https://www.lotto-8.com/Json_lto.asp?Lkind=ltoVM35&Lindex=100000&Ldesc=desc
POST https://www.lotto-8.com/Json_lto.asp?Lkind=ltoVM45&Lindex=100000&Ldesc=desc
POST https://www.lotto-8.com/Json_lto.asp?Lkind=ltoVM55&Lindex=100000&Ldesc=desc
```

| Product | Main numbers (`num`) | Bonus (`sp`) |
| --- | --- | --- |
| 535 | Five numbers in 1..35 | 1..12 |
| 645 | Six numbers in 1..45 | Empty |
| 655 | Six numbers in 1..55 | 1..55 |

For 645/655, `draw_code` is a synthetic `YYYYMMDD` identifier. For 535, it is the
draw label at the beginning of the API's `date` field. Deduplication uses codes,
allowing multiple 535 draws on the same date. Results come from Lotto-8 and have
not been independently verified against official Vietlott records.

## Requirements and options

Requires Python 3.10+ with no external Python dependencies. On macOS, if Python
lacks CA certificates, the crawler uses system `curl` with TLS verification
enabled. Each request has a 30-second timeout and up to three attempts.

- `--products`: products to update; defaults to all three.
- `--delay`: delay between history batches, default 0.2 seconds.
- `--end-index`: initial-download lower boundary, default 9.
- `--output-dir`: destination directory, default `databases/` in the project.
