# Python algorithm

The engine lives in `main.py`. It selects history, counts frequencies, samples
numbers with fixed weights, removes duplicates, sorts main numbers, and appends
a bonus number when applicable.

## Inputs and outputs

```python
from main import Draw, predict

results = predict(
    draws=[Draw(1, (1, 2, 3, 4, 5, 6))],
    product='645',
    seed=42,
    tickets=5,
)
```

Each result is `{"numbers": [...], "label": "heuristic-only"}`.
Seeds wrap modulo `2**64`. Requested ticket counts range from 0 to 255.

| Product | Main count | Main range | Bonus range |
| --- | --- | --- | --- |
| 535 | 5 | 1..35 | 1..12 |
| 645 | 6 | 1..45 | None |
| 655 | 6 | 1..55 | 1..55 |

## Weights and sampling

For each main number `n`, `weight[n] = frequency[n] + 1`. Frequencies count only
main numbers in the supplied history. Each sampling attempt selects a number
with probability `weight[n] / sum(weights)`.

Sampling uses replacement. If a selected number is already in the ticket,
that attempt is discarded and sampling continues. Weights stay fixed across
all tickets. Switching to weighted sampling without replacement would change
RNG consumption and outputs.

Main numbers are sorted in ascending order. For 535/655, the bonus is appended
at the end. The full vector is not sorted again, and a generated bonus may
match a main number.

The default `bonus_pool` contains historical bonus values in input order.
Sampling chooses a pool position, preserving duplicates and their weighting.
An empty pool uses uniform sampling within the bonus range. Python callers can
pass `bonus_pool=[]` or a custom pool; the CLI uses the default pool.

Complete ticket vectors identify duplicates. The engine allows at most 500
complete-ticket attempts, including duplicates, and may return fewer tickets
than requested. Requesting zero tickets returns an empty list.

## Random number generation

The RNG preserves reproducible results through these steps:

1. PCG expands a u64 seed into eight u32 key words, using multiplier
   `0x5851f42d4c957f2d` and increment `0xa17654e46fbe17f3`.
2. ChaCha8 starts with a zero u64 counter and zero nonce. Its buffer contains
   four blocks, or 64 u32 words.
3. A u64 read is `low_u32 | (high_u32 << 32)`. Mixing u32/u64 reads does not
   realign the position, including reads crossing a buffer boundary.
4. Integer sampling uses multiply-high with rejection. A sample is accepted
   when the low product is `<= zone`.

For u64 sampling in `[0, n)`:

```python
zone = ((n << (64 - n.bit_length())) - 1) & ((1 << 64) - 1)
```

For u32 sampling in `[0, n)`:

```python
zone = (~(((1 << 32) - n) % n)) & ((1 << 32) - 1)
```

Main-number and pool-index sampling use u64 reads. Bonus sampling with an empty
pool uses u32 reads. Replacing this RNG with Python's `random` changes outputs.

## Monte Carlo simulation

`simulate(draws, product, seed, samples=1000)` generates one ticket per seed,
using `(seed + i) % 2**64` for sample `i`. Each sample uses the same history and
weights. Duplicate tickets across samples are counted, preserving their effect
on the estimated sampling distribution. The prediction ticket-count limit does
not restrict the number of simulation samples.

Main and bonus numbers are counted separately. Rankings include every number
in the relevant range and sort by descending count, then ascending number for
ties. `sample_rate` is the fraction of tickets containing the number in that
role, not the probability of winning a future draw.

`suggested_numbers` contains the highest-ranked main numbers, sorted ascending,
followed by the highest-ranked bonus when applicable. This combination need not
have appeared in a sampled ticket. A simulation is reproducible with the same
inputs, seed, and sample count.

```bash
make simulate PRODUCT=645 SAMPLES=1000 SEED=42 WINDOW=60
python3 main.py simulate --data databases/535.csv --product 535 --seed 42 --samples 1000
```

Backtesting supports both direct predictions and simulation-ranked suggestions.
Use `make backtest STRATEGY=simulate SAMPLES=1000` to evaluate the latter.

## History, statistics, and backtesting

The loader validates number counts, ranges, unique main numbers, and unique draw
codes, then sorts draws by descending code. The CLI selects up to `window` draws,
defaulting to 60; zero uses all history. Direct `predict()` calls use every draw
supplied and do not apply a window.

Statistics include frequencies, hot/cold rankings, gaps, odd-number counts, and
number pairs. Only main-number frequencies affect ticket generation.

Backtesting uses only draws preceding each target. The target seed is
`(target.code + 0x00c0ffee12345677) % 2**64`. The baseline uses empty history and
`(target.code + 0x175efdd434567869) % 2**64`. Results count main-number matches.
ROI is not implemented. `cost_vnd` currently assumes VND 10,000 per ticket.
`--seed` adds an offset to each backtest seed; the Makefile uses
`BACKTEST_SEED=0` by default. Bonus matches are recorded separately and do not
represent prize eligibility.

## Round evaluation

Run `make round PRODUCT=645` (or `make evaluate PRODUCT=645`) for ten backtest
iterations. Each iteration compares predict and simulate across windows 30, 60,
120, and 0 (all preceding history), with one seed offset. Ten widely spaced
seed offsets provide variation across the round. Default simulations use 1,000
samples per target in both development and holdout evaluation.

The 60 targets immediately before the final 60 draws form the development block.
Each iteration selects a strategy and window by development mean main hits;
only that configuration is scored on the holdout. Splits keep same-date draws
together. Earlier holdout results become history for later predictions.
All configurations use at least 120 preceding draws to ensure comparable targets.

Each run also generates a suggestion using the selected configuration and the
latest audited history. The round summary counts appearances in the ten
suggestions, then returns the requested main-number combinations under an additive
consensus score (`RECOMMENDATIONS=2` by default). Ties prefer smaller numbers. Bonus numbers are ranked separately.
Holdout scores are reported but never used to select or weight suggestions.

Files use the round start time in Asia/Ho_Chi_Minh:

```text
backtests/645/645_1425_091026/runs/645_1425_091026_1.json
...
backtests/645/645_1425_091026/runs/645_1425_091026_10.json
backtests/suggestions/645_1425_091026.json
```

The summary is written only after all ten iterations succeed. A repeated round
for the same product/minute is rejected rather than overwriting results. Each
run includes the source CSV hash, audit, split codes, selected configuration,
per-draw backtest results, and its generated suggestion. See [ROUNDS.md](ROUNDS.md).

Raw CSV files are preserved. Power 6/55 records dated before its documented launch,
2017-08-01, are excluded from evaluation. Other weekday anomalies are flagged
for review. Results have not been independently verified in full.

All ten iterations reuse the same history, and earlier full-history backtests
were already inspected. This is exploratory, not ten independent datasets or
proof of improved winning probabilities. Future draws are needed for genuinely
unseen validation. ROI is not computed.

## Validation scope

Tests cover RNG vectors, reproducibility, rejection boundaries, duplicate
handling, attempt limits, and exclusion of future draws. Ticket-by-ticket
compatibility with the original application has not been verified. History
windows, default bonus pools, and draw-code handling describe this project's
behavior. Server algorithms are outside its scope.

## Sampling stability

`make stability PRODUCT=645 WORKERS=4` evaluates nested 10-, 30-, and 100-run
checkpoints on a fixed dataset. Earlier iterations are reused, and comparisons
report consensus changes, configuration counts, seed spread, and mean matches.
Results live in each product/round directory. See [STABILITY.md](STABILITY.md).

ChaCha8 block outputs are cached by immutable key and counter, with a maximum
of 16,384 entries per process. Cache hits preserve counter advancement and word
consumption; returned block lists cannot mutate cached tuples.

Stability checkpoints are configurable, for example
`make stability PRODUCT=655 STAGES="20 50 200" RECOMMENDATIONS=5 WORKERS=4`.
Recommendations are distinct main-number sets, ranked by additive consensus
score with deterministic rank-index tie breaks. The highest-ranked bonus remains
separate. Increasing the count does not change backtest selection or the RNG.
