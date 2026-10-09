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

## Validation scope

Tests cover RNG vectors, reproducibility, rejection boundaries, duplicate
handling, attempt limits, and exclusion of future draws. Ticket-by-ticket
compatibility with the original application has not been verified. History
windows, default bonus pools, and draw-code handling describe this project's
behavior. Server algorithms are outside its scope.
